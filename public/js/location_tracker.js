/**
 * Sri Lanka FloodWatch — Central Location Tracker Service
 * Single, unified Geolocation and Haversine Nearest Station Resolution engine.
 * Serves Notification monitoring, District views, Maps, and Dashboard telemetry.
 */

import { api } from './api.js';

class CentralLocationTracker {
  constructor() {
    this.currentPosition = null; // { latitude, longitude, accuracy }
    this.nearestStation = null;  // { location, distanceKm }
    this.watchId = null;
    this.isTracking = false;
    this.listeners = [];
    this.locationsCache = null;
    this.lastResolvedLocationId = null;
    this.minDistanceChangeKm = 0.25; // 250m movement threshold to reduce flutter
  }

  /**
   * Validate latitude and longitude values
   */
  isValidCoordinates(lat, lon) {
    return (
      typeof lat === 'number' &&
      typeof lon === 'number' &&
      !isNaN(lat) &&
      !isNaN(lon) &&
      isFinite(lat) &&
      isFinite(lon) &&
      lat >= -90.0 &&
      lat <= 90.0 &&
      lon >= -180.0 &&
      lon <= 180.0
    );
  }

  /**
   * Great-circle distance calculation between two GPS coordinates using Haversine formula
   */
  haversineDistanceKm(lat1, lon1, lat2, lon2) {
    const R = 6371.0; // Earth's mean radius in km
    const toRad = (deg) => (deg * Math.PI) / 180.0;

    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const rLat1 = toRad(lat1);
    const rLat2 = toRad(lat2);

    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(rLat1) * Math.cos(rLat2) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  /**
   * Fetch all 33 monitoring stations
   */
  async getLocations() {
    if (!this.locationsCache || this.locationsCache.length === 0) {
      try {
        const data = await api.getLocations();
        this.locationsCache = data.locations || [];
      } catch (e) {
        console.warn('[LocationTracker] Failed to load stations:', e);
        this.locationsCache = [];
      }
    }
    return this.locationsCache;
  }

  /**
   * Find closest station to user coordinates
   */
  async findNearestStation(userLat, userLon) {
    if (!this.isValidCoordinates(userLat, userLon)) return null;

    const locations = await this.getLocations();
    if (!locations || locations.length === 0) return null;

    let nearestLoc = null;
    let minDistance = Infinity;

    for (const loc of locations) {
      const sLat = parseFloat(loc.latitude);
      const sLon = parseFloat(loc.longitude);
      if (!this.isValidCoordinates(sLat, sLon)) continue;

      const dist = this.haversineDistanceKm(userLat, userLon, sLat, sLon);
      if (dist < minDistance) {
        minDistance = dist;
        nearestLoc = loc;
      }
    }

    if (nearestLoc) {
      return {
        location: nearestLoc,
        distanceKm: Math.round(minDistance * 100) / 100
      };
    }
    return null;
  }

  /**
   * One-time position query
   */
  async getCurrentPosition() {
    return new Promise((resolve, reject) => {
      if (typeof navigator === 'undefined' || !navigator.geolocation) {
        return reject(new Error('Geolocation is not supported by your browser.'));
      }

      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          const coords = {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy
          };
          this.currentPosition = coords;
          this.nearestStation = await this.findNearestStation(coords.latitude, coords.longitude);
          this.notify();
          resolve({
            coords,
            nearestStation: this.nearestStation
          });
        },
        (err) => {
          console.warn('[LocationTracker] Geolocation error:', err.message);
          reject(err);
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 30000
        }
      );
    });
  }

  /**
   * Start continuous GPS tracking
   */
  async startTracking() {
    if (this.isTracking) return;
    this.isTracking = true;

    // Try initial immediate fix
    try {
      await this.getCurrentPosition();
    } catch (e) {
      // Continue to watchPosition even if initial fix timed out
    }

    if (typeof navigator !== 'undefined' && navigator.geolocation) {
      this.watchId = navigator.geolocation.watchPosition(
        async (pos) => {
          const coords = {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy
          };
          this.currentPosition = coords;
          const nearest = await this.findNearestStation(coords.latitude, coords.longitude);

          if (nearest && nearest.location) {
            const hasChangedStation = !this.lastResolvedLocationId || this.lastResolvedLocationId !== nearest.location.id;
            this.nearestStation = nearest;
            this.lastResolvedLocationId = nearest.location.id;
            this.notify({ hasChangedStation });
          }
        },
        (err) => {
          console.warn('[LocationTracker] watchPosition error:', err.message);
        },
        {
          enableHighAccuracy: true,
          timeout: 15000,
          maximumAge: 10000
        }
      );
    }
  }

  /**
   * Stop continuous GPS tracking
   */
  stopTracking() {
    if (this.watchId !== null && typeof navigator !== 'undefined' && navigator.geolocation) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
    }
    this.isTracking = false;
  }

  /**
   * Subscribe to position & nearest station updates
   */
  subscribe(fn) {
    this.listeners.push(fn);
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== fn);
    };
  }

  /**
   * Broadcast updates
   */
  notify(extra = {}) {
    const data = {
      position: this.currentPosition,
      nearestStation: this.nearestStation,
      isTracking: this.isTracking,
      ...extra
    };
    this.listeners.forEach(fn => {
      try {
        fn(data);
      } catch (e) {
        console.error('[LocationTracker] Listener error:', e);
      }
    });

    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('floodwatch:location_updated', { detail: data }));
    }
  }
}

export const locationTracker = new CentralLocationTracker();
