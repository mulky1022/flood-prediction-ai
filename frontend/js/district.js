/**
 * Sri Lanka FloodWatch — Location Telemetry & Inundation Analysis Controller
 * Handles Multi-tier Browser Geolocation → Continuous Live Tracking → Haversine Nearest Station Resolution → AI Telemetry Binding
 */

import { api } from './api.js';
import { common } from './common.js';

// Configuration Constants
const REFRESH_INTERVAL_MS = 60000; // 60 seconds auto-refresh when live tracking is active
const DEFAULT_LOCATION_ID = 1; // Kolonnawa (Colombo) default fallback
const MIN_DISTANCE_CHANGE_KM = 0.25; // 250m movement threshold to switch nearest monitoring station

// State Management
let allLocations = [];
let currentLocationId = null;
let stationData = null;
let weatherData = null;
let predictionData = null;
let historyData = [];
let activeAlertsData = [];

let currentRequestId = 0;
let userManuallySelected = false;
let isLiveTrackingActive = true;
let geoWatchId = null;
let refreshTimerId = null;
let lastGpsCoords = null;
let isInitialized = false;

/**
 * Validates whether GPS coordinates are finite, well-formed numbers in valid geographic ranges
 * @param {number} lat Latitude
 * @param {number} lon Longitude
 * @returns {boolean}
 */
export function isValidCoordinates(lat, lon) {
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
 * @param {number} lat1 User Latitude
 * @param {number} lon1 User Longitude
 * @param {number} lat2 Station Latitude
 * @param {number} lon2 Station Longitude
 * @returns {number} Distance in kilometers
 */
export function haversineDistanceKm(lat1, lon1, lat2, lon2) {
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
 * Find the closest monitoring station among all available locations using Haversine formula
 * @param {number} userLat
 * @param {number} userLon
 * @param {Array} locations
 * @returns {{ location: Object, distanceKm: number } | null}
 */
export function findNearestStation(userLat, userLon, locations) {
  if (!isValidCoordinates(userLat, userLon) || !Array.isArray(locations) || locations.length === 0) {
    return null;
  }

  let nearestLoc = null;
  let minDistance = Infinity;

  for (const loc of locations) {
    const sLat = parseFloat(loc.latitude);
    const sLon = parseFloat(loc.longitude);
    if (!isValidCoordinates(sLat, sLon)) continue;

    const dist = haversineDistanceKm(userLat, userLon, sLat, sLon);
    if (dist < minDistance) {
      minDistance = dist;
      nearestLoc = loc;
    }
  }

  return nearestLoc ? { location: nearestLoc, distanceKm: minDistance } : null;
}

/**
 * Page initialization lifecycle handler
 */
document.addEventListener('DOMContentLoaded', async () => {
  if (isInitialized) return;
  isInitialized = true;

  common.initHeader('location-details');
  setupExportButton();
  setupEventListeners();
  setupLiveTrackControls();
  setupUnloadCleanup();

  window.addEventListener('floodwatch:language_changed', () => {
    populateStationDropdown(allLocations, currentLocationId);
    if (currentLocationId) {
      loadStationDetails(currentLocationId, { type: 'manual', message: 'Language switched.' });
    }
  });

  // 1. Pre-fetch real monitoring locations from backend
  await ensureLocationsLoaded();

  // 2. Resolve initial station based on strict priority:
  // Priority 1: URL location_id
  // Priority 2 & 3: Browser Geolocation / IP Geolocation → Haversine Nearest Station
  // Priority 4: Default fallback
  await resolveAndLoadLocation();
});

/**
 * Setup page unload listeners to prevent memory leaks, timer accumulation, or dangling GPS watches
 */
function setupUnloadCleanup() {
  const cleanup = () => {
    stopDataRefresh();
    stopContinuousGpsTracking();
  };
  window.addEventListener('beforeunload', cleanup);
  window.addEventListener('pagehide', cleanup);
}

/**
 * Ensure all real monitoring stations are loaded in memory from backend API
 */
async function ensureLocationsLoaded() {
  if (allLocations && allLocations.length > 0) return allLocations;
  try {
    const locRes = await api.getLocations();
    allLocations = (locRes && Array.isArray(locRes.locations)) ? locRes.locations : [];
    populateStationDropdown(allLocations);
    return allLocations;
  } catch (err) {
    console.warn('Failed to load stations list from backend:', err);
    updateLocationContextUI({
      status: 'error',
      title: 'Monitoring Locations Unavailable',
      subtitle: 'Unable to load monitoring locations from backend. Please check network connection.',
      icon: 'cloud_off',
      iconBg: 'bg-error-container text-on-error-container',
      distance: null
    });
    return [];
  }
}

/**
 * Setup UI event listeners for dropdown and manual actions
 */
function setupEventListeners() {
  const stationSelect = document.getElementById('stationSelect');
  if (stationSelect) {
    stationSelect.addEventListener('change', (e) => {
      const selectedId = parseInt(e.target.value, 10);
      if (selectedId && !isNaN(selectedId)) {
        userManuallySelected = true;
        updateUrlLocation(selectedId);
        loadStationDetails(selectedId, {
          type: 'manual',
          message: 'Manually selected monitoring station.'
        });
      }
    });
  }

  const btnDetect = document.getElementById('btnDetectLocation');
  if (btnDetect) {
    btnDetect.addEventListener('click', () => {
      userManuallySelected = false;
      detectUserLocation(true);
    });
  }

  const btnSync = document.getElementById('btnSyncNow');
  if (btnSync) {
    btnSync.addEventListener('click', async () => {
      if (currentLocationId) {
        btnSync.classList.add('opacity-75');
        const icon = btnSync.querySelector('.material-symbols-outlined');
        if (icon) icon.classList.add('animate-spin');
        await loadStationDetails(currentLocationId, {
          type: 'sync',
          message: 'Live sync executed directly against Open-Meteo & AI Inference Model.'
        });
        setTimeout(() => {
          btnSync.classList.remove('opacity-75');
          if (icon) icon.classList.remove('animate-spin');
        }, 600);
      }
    });
  }
}

/**
 * Setup Live Tracking toggle button and state handler
 */
function setupLiveTrackControls() {
  const btnToggle = document.getElementById('btnToggleLiveTrack');
  const trackLabel = document.getElementById('liveTrackLabel');
  const badge = document.getElementById('liveTrackingBadge');

  if (btnToggle) {
    btnToggle.addEventListener('click', () => {
      isLiveTrackingActive = !isLiveTrackingActive;
      if (isLiveTrackingActive) {
        userManuallySelected = false;
        if (trackLabel) trackLabel.textContent = 'Live Track: Active';
        btnToggle.classList.remove('opacity-60');
        if (badge) badge.classList.remove('hidden');
        startContinuousGpsTracking();
        startDataRefresh(currentLocationId);
        detectUserLocation(true);
      } else {
        if (trackLabel) trackLabel.textContent = 'Live Track: Paused';
        btnToggle.classList.add('opacity-60');
        if (badge) badge.classList.add('hidden');
        stopContinuousGpsTracking();
      }
    });
  }
}

/**
 * Populate the Station Select dropdown with real monitoring stations grouped by district
 */
function populateStationDropdown(locations, selectedId = null) {
  const select = document.getElementById('stationSelect');
  if (!select) return;

  if (!locations || !locations.length) {
    select.innerHTML = '<option value="">No stations available</option>';
    return;
  }

  // Group locations by district
  const districts = {};
  locations.forEach((loc) => {
    const d = loc.district || 'Sri Lanka';
    if (!districts[d]) districts[d] = [];
    districts[d].push(loc);
  });

  const html = Object.keys(districts).sort().map((districtName) => {
    const opts = districts[districtName].map((loc) => {
      return `<option value="${loc.id}">${loc.place_name}</option>`;
    }).join('');
    return `<optgroup label="${districtName} District">${opts}</optgroup>`;
  }).join('');

  select.innerHTML = html;

  if (selectedId) {
    select.value = String(selectedId);
  }
}

/**
 * Determine which location to load on initial page load based on strict priority
 */
async function resolveAndLoadLocation() {
  const urlParams = new URLSearchParams(window.location.search);
  const paramId = urlParams.get('location_id') || urlParams.get('id') || urlParams.get('station');

  // PRIORITY 1: Explicit URL parameter or stored location preference
  const targetId = paramId && !isNaN(parseInt(paramId, 10)) ? parseInt(paramId, 10) : common.getSelectedLocationId(null);

  if (targetId && !isNaN(parseInt(targetId, 10))) {
    userManuallySelected = true;
    const id = parseInt(targetId, 10);
    await loadStationDetails(id, {
      type: paramId ? 'url' : 'manual',
      message: paramId ? 'Viewing station specified in URL parameter.' : 'Viewing saved location preference.'
    });
    // Still start background live location watch
    if (isLiveTrackingActive && !userManuallySelected) {
      startContinuousGpsTracking();
    }
    return;
  }

  // PRIORITY 2 & 3: No location_id in URL or storage → Request browser geolocation / IP fallback
  await detectUserLocation(false);
}

/**
 * Multi-tier Geolocation: GPS (High Accuracy) -> GPS (Low Accuracy) -> IP Geolocation Fallback
 * @param {boolean} userInitiated Whether triggered manually
 */
async function detectUserLocation(userInitiated = false) {
  const btnDetect = document.getElementById('btnDetectLocation');
  if (btnDetect) {
    btnDetect.disabled = true;
    btnDetect.innerHTML = `<span class="material-symbols-outlined text-[16px] animate-spin text-secondary">refresh</span><span>Detecting...</span>`;
  }

  updateLocationContextUI({
    status: 'detecting',
    title: 'Detecting Live Location...',
    subtitle: 'Scanning browser GPS coordinates & telemetry feed...',
    icon: 'location_searching',
    iconBg: 'bg-secondary-container text-on-secondary-container',
    distance: null
  });

  const resetBtn = () => {
    if (btnDetect) {
      btnDetect.disabled = false;
      btnDetect.innerHTML = `<span class="material-symbols-outlined text-[16px] text-secondary">my_location</span><span>Detect GPS</span>`;
    }
  };

  // Helper to handle resolved coordinates
  const handleResolvedCoords = async (lat, lon, sourceLabel = 'GPS', accuracyM = null) => {
    resetBtn();
    if (!isValidCoordinates(lat, lon)) {
      await fallbackToDefaultStation('Received invalid location coordinates.');
      return;
    }

    lastGpsCoords = { lat, lon };

    // Update live coordinates readout badge
    const coordsReadout = document.getElementById('liveCoordsReadout');
    if (coordsReadout) {
      const accStr = accuracyM ? ` (±${Math.round(accuracyM)}m)` : '';
      coordsReadout.textContent = `[${sourceLabel}: ${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E${accStr}]`;
    }

    const locs = await ensureLocationsLoaded();
    if (!locs || locs.length === 0) {
      updateLocationContextUI({
        status: 'no_locations',
        title: 'No monitoring locations currently available',
        subtitle: 'The backend service did not return active monitoring nodes.',
        icon: 'location_off',
        iconBg: 'bg-error-container text-on-error-container',
        distance: null
      });
      return;
    }

    const match = findNearestStation(lat, lon, locs);
    if (!match || !match.location) {
      await fallbackToDefaultStation('Unable to match nearest flood station.');
      return;
    }

    const nearestStation = match.location;
    const distanceKm = match.distanceKm;

    updateUrlLocation(nearestStation.id);

    await loadStationDetails(nearestStation.id, {
      type: 'gps',
      distanceKm: distanceKm,
      stationName: nearestStation.place_name,
      district: nearestStation.district,
      message: `Live location matched: ${nearestStation.place_name} is your nearest monitoring station (${distanceKm.toFixed(1)} km away).`
    });

    if (isLiveTrackingActive) {
      startContinuousGpsTracking();
    }
  };

  // Tier 1 & 2: Browser Geolocation API
  if (navigator.geolocation) {
    const tryGps = (options) => {
      return new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, options);
      });
    };

    try {
      // Try high accuracy GPS first
      const pos = await tryGps({ enableHighAccuracy: true, timeout: 6000, maximumAge: 60000 });
      await handleResolvedCoords(pos.coords.latitude, pos.coords.longitude, 'GPS Live', pos.coords.accuracy);
      return;
    } catch (e1) {
      console.warn('High accuracy GPS timed out or failed, trying standard accuracy:', e1.message);
      try {
        const pos2 = await tryGps({ enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 });
        await handleResolvedCoords(pos2.coords.latitude, pos2.coords.longitude, 'GPS Cell/Wi-Fi', pos2.coords.accuracy);
        return;
      } catch (e2) {
        console.warn('Browser GPS unavailable or permission denied, trying IP geolocation fallback:', e2.message);
      }
    }
  }

  // Tier 3: IP Geolocation Fallback (Fast & anonymous fallback for desktop browsers)
  try {
    const ipCoords = await fetchIpGeolocation();
    if (ipCoords && isValidCoordinates(ipCoords.lat, ipCoords.lon)) {
      await handleResolvedCoords(ipCoords.lat, ipCoords.lon, 'IP Geolocation');
      return;
    }
  } catch (ipErr) {
    console.warn('IP Geolocation fallback failed:', ipErr);
  }

  // Tier 4: Default Fallback
  resetBtn();
  await fallbackToDefaultStation('Location detection unavailable. Defaulting to Colombo Basin.');
}

/**
 * Fetches approximate location via fast IP Geolocation services
 */
async function fetchIpGeolocation() {
  try {
    // Try ipwho.is (CORS enabled, fast, no auth)
    const res = await fetch('https://ipwho.is/', { cache: 'no-cache' });
    if (res.ok) {
      const data = await res.json();
      if (data && data.success && typeof data.latitude === 'number' && typeof data.longitude === 'number') {
        return { lat: data.latitude, lon: data.longitude };
      }
    }
  } catch (e) {
    // Try secondary free IP api
    try {
      const res2 = await fetch('https://freeipapi.com/api/json', { cache: 'no-cache' });
      if (res2.ok) {
        const data2 = await res2.json();
        if (data2 && typeof data2.latitude === 'number' && typeof data2.longitude === 'number') {
          return { lat: data2.latitude, lon: data2.longitude };
        }
      }
    } catch (e2) {}
  }
  return null;
}

/**
 * Fallback to default station with notification
 */
async function fallbackToDefaultStation(message) {
  const fallbackId = getFallbackStationId();
  updateUrlLocation(fallbackId);
  await loadStationDetails(fallbackId, {
    type: 'fallback',
    message: message || 'Please select a monitoring location manually.'
  });
}

/**
 * Returns a safe fallback station ID from available stations
 */
function getFallbackStationId() {
  if (currentLocationId) return currentLocationId;
  if (allLocations && allLocations.length > 0 && allLocations[0].id) {
    return allLocations[0].id;
  }
  return DEFAULT_LOCATION_ID;
}

/**
 * Starts continuous browser location watching with jitter thresholding
 */
function startContinuousGpsTracking() {
  if (!navigator.geolocation || geoWatchId !== null || !isLiveTrackingActive) return;

  const geoOptions = {
    enableHighAccuracy: true,
    timeout: 15000,
    maximumAge: 30000
  };

  geoWatchId = navigator.geolocation.watchPosition(
    async (position) => {
      if (!isLiveTrackingActive || userManuallySelected) return;

      const userLat = position.coords.latitude;
      const userLon = position.coords.longitude;

      if (!isValidCoordinates(userLat, userLon)) return;

      // Update live coordinates readout badge
      const coordsReadout = document.getElementById('liveCoordsReadout');
      if (coordsReadout) {
        coordsReadout.textContent = `[GPS Live: ${userLat.toFixed(4)}° N, ${userLon.toFixed(4)}° E (±${Math.round(position.coords.accuracy || 10)}m)]`;
      }

      // Check distance moved from last known position to filter out minor GPS jitter
      if (lastGpsCoords) {
        const movedKm = haversineDistanceKm(lastGpsCoords.lat, lastGpsCoords.lon, userLat, userLon);
        if (movedKm < MIN_DISTANCE_CHANGE_KM) return;
      }

      lastGpsCoords = { lat: userLat, lon: userLon };

      const locs = await ensureLocationsLoaded();
      const match = findNearestStation(userLat, userLon, locs);

      if (match && match.location && match.location.id !== currentLocationId) {
        const newStation = match.location;
        updateUrlLocation(newStation.id);
        await loadStationDetails(newStation.id, {
          type: 'gps',
          distanceKm: match.distanceKm,
          stationName: newStation.place_name,
          district: newStation.district,
          message: `Live movement tracked: ${newStation.place_name} is now your nearest station (${match.distanceKm.toFixed(1)} km away).`
        });
      }
    },
    (err) => {
      console.warn('Continuous GPS watch notice:', err.message);
    },
    geoOptions
  );
}

/**
 * Stop continuous GPS watching and release resources
 */
function stopContinuousGpsTracking() {
  if (geoWatchId !== null && navigator.geolocation) {
    navigator.geolocation.clearWatch(geoWatchId);
    geoWatchId = null;
  }
}

/**
 * Update URL query parameter without full page reload using history.replaceState()
 */
function updateUrlLocation(locationId) {
  try {
    common.setSelectedLocationId(locationId, true);
  } catch (e) {}
}

/**
 * Starts the periodic data refresh timer for telemetry
 */
function startDataRefresh(locationId) {
  stopDataRefresh();
  refreshTimerId = setInterval(async () => {
    if (currentLocationId && isLiveTrackingActive) {
      await refreshTelemetry(currentLocationId);
    }
  }, REFRESH_INTERVAL_MS);
}

/**
 * Stop any active data refresh timer
 */
function stopDataRefresh() {
  if (refreshTimerId !== null) {
    clearInterval(refreshTimerId);
    refreshTimerId = null;
  }
}

/**
 * Background refresh of dynamic telemetry (weather, prediction, alerts)
 */
async function refreshTelemetry(locationId) {
  try {
    const [weatherRes, predRes, alertsRes] = await Promise.allSettled([
      api.getWeather(locationId),
      api.getPrediction(locationId),
      api.getAlertsByLocation(locationId)
    ]);

    if (weatherRes.status === 'fulfilled') {
      weatherData = weatherRes.value;
      renderChannelProximity(stationData, weatherData);
      renderWeatherCards(weatherData);
      renderPrecipitationAnalytics(weatherData);
    }

    if (predRes.status === 'fulfilled') {
      predictionData = predRes.value;
      renderPredictionEngine(predictionData, stationData, activeAlertsData);
      renderDecisionThreshold(predictionData);
      renderLiveCatchmentAnalysis(predictionData, stationData, weatherData);
    }

    if (alertsRes.status === 'fulfilled') {
      const alerts = alertsRes.value;
      activeAlertsData = (alerts && Array.isArray(alerts.items))
        ? alerts.items.filter((a) => a.status === 'ACTIVE' || a.status === 'ACKNOWLEDGED')
        : [];
      renderActiveAlerts(activeAlertsData);
      renderHeaderBanner(stationData, activeAlertsData);
    }

    updateLiveSyncTimestamp();
  } catch (err) {
    console.warn('Telemetry periodic refresh error:', err);
  }
}

/**
 * Update the live sync time banner tag
 */
function updateLiveSyncTimestamp() {
  const timeEl = document.getElementById('liveFeedSyncTime');
  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  if (timeEl) {
    timeEl.textContent = `LIVE TELEMETRY (Synced ${timeStr})`;
  }
  const badgeEl = document.getElementById('liveAnalysisSyncBadge');
  if (badgeEl) {
    badgeEl.textContent = `Telemetry Engine • Synced ${timeStr}`;
  }
}

/**
 * Fetch and bind all telemetry, GIS, and ML data for a specific station in parallel
 */
async function loadStationDetails(locationId, contextInfo = {}) {
  currentLocationId = locationId;
  const thisRequestId = ++currentRequestId;

  // Sync selector dropdown
  const select = document.getElementById('stationSelect');
  if (select && select.value !== String(locationId)) {
    select.value = String(locationId);
  }

  // Update context toolbar UI
  applyContextToToolbar(contextInfo, locationId);

  // Show loading cues
  setTelemetryLoadingState(true);

  try {
    const [detailsResult, weatherResult] = await Promise.allSettled([
      api.getLocationDetails(locationId),
      api.getWeather(locationId)
    ]);

    if (thisRequestId !== currentRequestId) return;

    // 1. Process Aggregated Location Details
    if (detailsResult.status === 'fulfilled' && detailsResult.value) {
      const details = detailsResult.value;
      
      // Data integrity verification: ensure returned location matches requested location
      const retLocId = details.location ? parseInt(details.location.location_id || details.location.id, 10) : null;
      if (retLocId && retLocId !== parseInt(locationId, 10)) {
        console.error(`[District Integrity Error] Location ID mismatch! Requested: ${locationId}, Returned: ${retLocId}`);
        renderLocationError(`Data integrity error: Location mismatch (Requested ${locationId}, got ${retLocId}).`);
        return;
      }

      stationData = details.location || null;
      predictionData = details.current_prediction || null;
      activeAlertsData = details.active_alerts || [];
      historyData = details.recent_history || [];

      if (stationData) {
        renderBreadcrumbs(stationData);
        renderHeaderBanner(stationData, activeAlertsData);
        renderVulnerabilityMatrix(stationData);
      } else {
        renderLocationError('Unable to load monitoring location details.');
      }

      renderActiveAlerts(activeAlertsData);

      if (predictionData) {
        renderPredictionEngine(predictionData, stationData, activeAlertsData);
        renderDecisionThreshold(predictionData);
      } else {
        renderPredictionError('No current flood prediction is recorded for this location.');
      }

      renderHistoryTable(historyData);
    } else {
      stationData = null;
      predictionData = null;
      activeAlertsData = [];
      historyData = [];
      renderLocationError('Location details are temporarily unavailable.');
    }

    // 2. Process Weather Telemetry
    if (weatherResult.status === 'fulfilled' && weatherResult.value) {
      weatherData = weatherResult.value;
      renderChannelProximity(stationData, weatherData);
      renderWeatherCards(weatherData);
      renderPrecipitationAnalytics(weatherData);
      if (predictionData) {
        renderLiveCatchmentAnalysis(predictionData, stationData, weatherData);
      }
    } else {
      weatherData = null;
      renderWeatherError('Weather telemetry is temporarily unavailable.');
    }

    updateLiveSyncTimestamp();
    startDataRefresh(locationId);

  } catch (err) {
    console.error(`Error loading station ${locationId} details:`, err);
  } finally {
    setTelemetryLoadingState(false);
  }
}

/**
 * Update visual loading indicators across telemetry widgets
 */
function setTelemetryLoadingState(isLoading) {
  const elements = [
    document.getElementById('metricTemp'),
    document.getElementById('metricHumidity'),
    document.getElementById('metricRain'),
    document.getElementById('metricWind'),
    document.getElementById('metricDischarge'),
    document.getElementById('radialGaugeNumber')
  ];

  elements.forEach((el) => {
    if (!el) return;
    if (isLoading) {
      el.classList.add('opacity-50');
    } else {
      el.classList.remove('opacity-50');
    }
  });
}

/**
 * Update the Location Context banner in the UI
 */
function applyContextToToolbar(contextInfo, locationId) {
  const loc = (allLocations && allLocations.find((l) => l.id === locationId)) || stationData;
  const stationName = loc ? loc.place_name : `Station #${locationId}`;
  const districtName = loc ? `${loc.district} District` : '';

  switch (contextInfo.type) {
    case 'gps':
      updateLocationContextUI({
        status: 'gps_match',
        title: `Nearest Station: ${stationName}`,
        subtitle: contextInfo.message || `Auto-detected nearest station from your live coordinates (${districtName}).`,
        icon: 'near_me',
        iconBg: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400',
        distance: contextInfo.distanceKm !== undefined ? `${contextInfo.distanceKm.toFixed(1)} km away` : null
      });
      break;

    case 'denied':
    case 'unsupported':
    case 'fallback':
      updateLocationContextUI({
        status: 'manual_fallback',
        title: `Viewing Station: ${stationName}`,
        subtitle: contextInfo.message || 'Location permission was denied. Please select a monitoring location manually.',
        icon: 'location_off',
        iconBg: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400',
        distance: null
      });
      break;

    case 'manual':
      updateLocationContextUI({
        status: 'manual',
        title: `Monitoring Station: ${stationName}`,
        subtitle: `Manually selected ${districtName} sensor node.`,
        icon: 'tune',
        iconBg: 'bg-secondary-container text-on-secondary-container',
        distance: null
      });
      break;

    case 'url':
    default:
      updateLocationContextUI({
        status: 'default',
        title: `Monitoring Station: ${stationName}`,
        subtitle: `Active sensor node in ${districtName || 'Sri Lanka'}.`,
        icon: 'pin_drop',
        iconBg: 'bg-secondary-container text-on-secondary-container',
        distance: null
      });
      break;
  }
}

/**
 * Set text, badge, and icon in Location Context Toolbar
 */
function updateLocationContextUI({ title, subtitle, icon, iconBg, distance }) {
  const titleEl = document.getElementById('locationContextTitle');
  const subtitleEl = document.getElementById('locationContextSubtitle');
  const iconEl = document.getElementById('locationStatusIcon');
  const iconWrapper = document.getElementById('locationStatusIconWrapper');
  const distBadge = document.getElementById('locationDistanceBadge');

  if (titleEl) titleEl.textContent = title || 'Location Telemetry';
  if (subtitleEl) subtitleEl.textContent = subtitle || '';
  if (iconEl && icon) iconEl.textContent = icon;
  if (iconWrapper && iconBg) iconWrapper.className = `flex items-center justify-center w-9 h-9 rounded-lg shrink-0 ${iconBg}`;

  if (distBadge) {
    if (distance) {
      distBadge.textContent = distance;
      distBadge.classList.remove('hidden');
    } else {
      distBadge.classList.add('hidden');
    }
  }
}

/**
 * Render Live Catchment Inundation Diagnostic Analysis Panel
 */
export function renderLiveCatchmentAnalysis(predRes, loc, weather) {
  const pred = predRes ? (predRes.prediction || predRes) : null;
  const riskObj = pred ? (pred.risk || {}) : {};
  let prob = 0;
  if (riskObj.flood_probability_percent !== undefined) {
    prob = Number(riskObj.flood_probability_percent);
  } else if (pred && pred.flood_probability_percent !== undefined) {
    prob = Number(pred.flood_probability_percent);
  } else if (riskObj.score !== undefined) {
    prob = Number(riskObj.score) * 100;
  } else if (pred && pred.flood_probability !== undefined) {
    prob = Number(pred.flood_probability) * 100;
  }
  const rolling = (weather && weather.rainfall) ? weather.rainfall : (weather ? weather.rolling_aggregations : {});
  const rain7 = rolling ? (rolling.rainfall_7d_mm ?? rolling.precipitation_sum_7d_mm ?? 0) : 0;
  const elevation = loc ? (loc.elevation_m || 10) : 10;
  const distRiver = loc ? (loc.distance_to_river_m || 500) : 500;

  // 1. Watershed Saturation Analysis
  const satRatingEl = document.getElementById('diagSatRating');
  const satDescEl = document.getElementById('diagSatDesc');
  const satIconEl = document.getElementById('diagSatIcon');

  if (satRatingEl && satDescEl) {
    if (rain7 > 75 || prob > 70) {
      satRatingEl.textContent = 'Severe Inundation Load';
      satRatingEl.className = 'font-headline-sm text-headline-sm font-bold text-error';
      satDescEl.textContent = `Extreme antecedent rain accumulation (${rain7.toFixed(1)} mm/7d). Catchment soil matrix at full saturation.`;
      if (satIconEl) satIconEl.className = 'material-symbols-outlined text-[18px] text-error';
    } else if (rain7 > 30 || prob > 40) {
      satRatingEl.textContent = 'Moderate Hydrological Load';
      satRatingEl.className = 'font-headline-sm text-headline-sm font-bold text-warning';
      satDescEl.textContent = `Elevated 7-day precipitation (${rain7.toFixed(1)} mm). Infiltration capacity is moderately constrained.`;
      if (satIconEl) satIconEl.className = 'material-symbols-outlined text-[18px] text-warning';
    } else {
      satRatingEl.textContent = 'Optimal Absorption Load';
      satRatingEl.className = 'font-headline-sm text-headline-sm font-bold text-emerald-500';
      satDescEl.textContent = `Low cumulative rainfall (${rain7.toFixed(1)} mm/7d). Soil absorption buffer within safe operating margins.`;
      if (satIconEl) satIconEl.className = 'material-symbols-outlined text-[18px] text-emerald-500';
    }
  }

  // 2. River Channel Surge Risk Analysis
  const surgeRatingEl = document.getElementById('diagSurgeRating');
  const surgeDescEl = document.getElementById('diagSurgeDesc');
  const surgeIconEl = document.getElementById('diagSurgeIcon');

  if (surgeRatingEl && surgeDescEl) {
    if (distRiver < 400 && elevation < 10) {
      surgeRatingEl.textContent = 'Critical Overflow Reach';
      surgeRatingEl.className = 'font-headline-sm text-headline-sm font-bold text-error';
      surgeDescEl.textContent = `High vulnerability: low elevation (${elevation.toFixed(1)}m ASL) and direct proximity to river channel (${distRiver}m).`;
      if (surgeIconEl) surgeIconEl.className = 'material-symbols-outlined text-[18px] text-error';
    } else if (distRiver < 1000 || elevation < 25) {
      surgeRatingEl.textContent = 'Basin Floodplain Reach';
      surgeRatingEl.className = 'font-headline-sm text-headline-sm font-bold text-secondary';
      surgeDescEl.textContent = `Mid-gradient drainage zone (${distRiver}m from primary canal/river reach, ${elevation.toFixed(1)}m ASL).`;
      if (surgeIconEl) surgeIconEl.className = 'material-symbols-outlined text-[18px] text-secondary';
    } else {
      surgeRatingEl.textContent = 'Elevated Highland Margin';
      surgeRatingEl.className = 'font-headline-sm text-headline-sm font-bold text-on-surface';
      surgeDescEl.textContent = `Topographical buffer present (${elevation.toFixed(1)}m ASL, >${distRiver}m channel clearance). Low flash flood exposure.`;
      if (surgeIconEl) surgeIconEl.className = 'material-symbols-outlined text-[18px] text-on-surface-variant';
    }
  }

  // 3. Operational Directive Synthesis
  const directiveTitleEl = document.getElementById('diagDirectiveTitle');
  const directiveDescEl = document.getElementById('diagDirectiveDesc');
  const directiveIconEl = document.getElementById('diagDirectiveIcon');

  if (directiveTitleEl && directiveDescEl) {
    if (prob >= 65 || (activeAlertsData && activeAlertsData.length > 0)) {
      directiveTitleEl.textContent = 'Evacuation Readiness Alert';
      directiveTitleEl.className = 'font-headline-sm text-headline-sm font-bold text-error';
      directiveDescEl.textContent = 'High inundation risk. Ensure emergency response standby and avoid low-lying canal embankments.';
      if (directiveIconEl) directiveIconEl.className = 'material-symbols-outlined text-[18px] text-error';
    } else if (prob >= 35) {
      directiveTitleEl.textContent = 'Active Precautionary Watch';
      directiveTitleEl.className = 'font-headline-sm text-headline-sm font-bold text-warning';
      directiveDescEl.textContent = 'Maintain situational awareness. Check culverts and monitor hourly synoptic updates.';
      if (directiveIconEl) directiveIconEl.className = 'material-symbols-outlined text-[18px] text-warning';
    } else {
      directiveTitleEl.textContent = 'Routine Telemetry Monitoring';
      directiveTitleEl.className = 'font-headline-sm text-headline-sm font-bold text-emerald-500';
      directiveDescEl.textContent = 'All parameters stable. Continuous background inference active across 64 feature dimensions.';
      if (directiveIconEl) directiveIconEl.className = 'material-symbols-outlined text-[18px] text-emerald-500';
    }
  }
}

/**
 * Render Active Alerts section
 */
function renderActiveAlerts(activeAlerts = []) {
  const section = document.getElementById('stationAlertSection');
  const titleEl = document.getElementById('stationAlertTitle');
  const msgEl = document.getElementById('stationAlertMessage');
  const recEl = document.getElementById('stationAlertRecommendation');
  const timeEl = document.getElementById('stationAlertTime');
  const statusEl = document.getElementById('stationAlertStatus');
  const badgeEl = document.getElementById('stationAlertBadge');
  const cardEl = document.getElementById('stationAlertCard');
  const iconWrapper = document.getElementById('stationAlertIconWrapper');

  if (!section) return;

  if (!activeAlerts || activeAlerts.length === 0) {
    section.classList.remove('hidden');
    if (cardEl) {
      cardEl.className = 'card p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 border border-surface-container bg-surface-container-low/60 rounded-xl';
    }
    if (iconWrapper) {
      iconWrapper.className = 'flex items-center justify-center w-10 h-10 rounded-xl bg-surface-container-high text-secondary shrink-0 mt-0.5';
    }
    if (badgeEl) {
      badgeEl.className = 'px-2.5 py-0.5 rounded-full bg-surface-container-highest text-on-surface font-label-md text-label-md font-bold uppercase tracking-wider';
      badgeEl.textContent = 'Alert Status';
    }
    if (titleEl) titleEl.textContent = 'No active flood alerts for this location.';
    if (msgEl) msgEl.textContent = 'Hydrometeorological indicators are within normal catchment tolerances. Routine telemetry monitoring continues.';
    if (recEl) recEl.textContent = 'Standard monitoring';
    if (timeEl) timeEl.textContent = 'Live System Check';
    if (statusEl) statusEl.textContent = 'NORMAL';
    return;
  }

  const alert = activeAlerts[0];
  const risk = common.getRiskDetails(alert.risk_level || 'HIGH');

  section.classList.remove('hidden');

  if (cardEl) {
    cardEl.className = `card p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 border ${risk.borderClass || 'border-error/40'} bg-surface-container-low rounded-xl`;
  }
  if (iconWrapper) {
    iconWrapper.className = `flex items-center justify-center w-10 h-10 rounded-xl ${risk.badgeBg} shrink-0 mt-0.5`;
  }
  if (badgeEl) {
    badgeEl.className = `px-2.5 py-0.5 rounded-full ${risk.badgeBg} font-label-md text-label-md font-bold uppercase tracking-wider`;
    badgeEl.textContent = `ACTIVE ${alert.risk_level || 'FLOOD'} ALERT`;
  }
  if (titleEl) titleEl.textContent = alert.title || `${alert.risk_level || 'High'} Inundation Risk Warning`;
  if (msgEl) msgEl.textContent = alert.message || 'Elevated flood risk detected based on precipitation and basin saturation features.';
  if (recEl) recEl.textContent = alert.recommendation || 'Initiate standard flood preparedness protocol.';
  if (timeEl) timeEl.textContent = alert.created_at ? common.formatTime(alert.created_at) : 'Active Alert';
  if (statusEl) statusEl.textContent = `STATUS: ${alert.status || 'ACTIVE'}`;
}

/**
 * Render Breadcrumb trail
 */
function renderBreadcrumbs(loc) {
  const districtCrumb = document.getElementById('crumbDistrict');
  const stationCrumb = document.getElementById('crumbStation');

  if (districtCrumb && loc) districtCrumb.textContent = `${loc.district} District`;
  if (stationCrumb && loc) stationCrumb.textContent = loc.place_name;
}

/**
 * Render Header banner with coordinates & elevation
 */
function renderHeaderBanner(loc, activeAlerts = []) {
  if (!loc) return;

  const unitTag = document.getElementById('stationUnitTag');
  const districtTag = document.getElementById('stationDistrictTag');
  const title = document.getElementById('stationTitle');
  const coords = document.getElementById('stationCoords');
  const elevation = document.getElementById('stationElevation');
  const sensorArray = document.getElementById('stationSensorArray');

  if (unitTag) unitTag.textContent = `Catchment Unit ${loc.record_id || 'LK-LOC-' + loc.id}`;
  if (districtTag) districtTag.textContent = `${loc.district} District`;
  if (title) title.innerHTML = `${loc.place_name} Station <span class="font-headline-lg text-headline-lg text-outline font-normal">(${loc.district} Basin)</span>`;
  if (coords) coords.textContent = `${loc.latitude}° N, ${loc.longitude}° E`;
  if (elevation) elevation.textContent = `Elevation: ${common.formatNumber(loc.elevation_m, 1, 'N/A')}m ASL`;
  if (sensorArray) sensorArray.textContent = `Sensor Array ID: ${loc.record_id || 'LK-SEN-' + loc.id}`;
}

/**
 * Radial Probability Gauge & Classification Result
 */
function renderPredictionEngine(predRes, loc, activeAlerts = []) {
  if (!predRes) {
    renderPredictionError('No current flood prediction is recorded for this location.');
    return;
  }

  // Support both canonical prediction object format and legacy nested format
  const pred = predRes.prediction || predRes;
  const riskObj = pred.risk || {};

  // Resolve probability percent & fractional score
  let probPercent = 0;
  let probScore = 0;
  if (riskObj.flood_probability_percent !== undefined) {
    probPercent = Number(riskObj.flood_probability_percent);
    probScore = riskObj.score !== undefined ? Number(riskObj.score) : (probPercent / 100);
  } else if (pred.flood_probability_percent !== undefined) {
    probPercent = Number(pred.flood_probability_percent);
    probScore = pred.flood_probability !== undefined ? Number(pred.flood_probability) : (probPercent / 100);
  } else if (riskObj.score !== undefined) {
    probScore = Number(riskObj.score);
    probPercent = probScore * 100;
  } else if (pred.flood_probability !== undefined) {
    probScore = Number(pred.flood_probability);
    probPercent = probScore * 100;
  }

  const riskLevel = riskObj.level || pred.risk_level || (probScore >= 0.65 ? 'HIGH' : probScore >= 0.35 ? 'MODERATE' : 'LOW');
  const risk = common.getRiskDetails(riskLevel, probScore);
  const predClass = pred.class !== undefined ? pred.class : (pred.prediction_class !== undefined ? pred.prediction_class : (probScore >= 0.5 ? 1 : 0));

  // Risk Badge
  const badgeEl = document.getElementById('detailRiskBadge');
  if (badgeEl) {
    const hasActiveAlert = activeAlerts && activeAlerts.length > 0;
    const alertLabel = hasActiveAlert ? `ACTIVE ${activeAlerts[0].risk_level} ALERT` : risk.label;
    badgeEl.className = `inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full ${risk.badgeBg} font-label-lg text-label-lg font-bold`;
    badgeEl.innerHTML = `<span class="h-2 w-2 rounded-full ${hasActiveAlert ? 'animate-ping' : ''}" style="background-color: ${risk.dotColor}"></span><span>${alertLabel}</span>`;
  }

  // Radial Gauge
  const circleEl = document.getElementById('radialGaugeCircle');
  const numberEl = document.getElementById('radialGaugeNumber');

  if (numberEl) {
    numberEl.innerHTML = `${common.formatNumber(probPercent, 2)}<span class="text-headline-sm font-normal">%</span>`;
  }

  if (circleEl) {
    const totalCircumference = 314.16;
    const offset = totalCircumference - (totalCircumference * (Math.min(Math.max(probPercent, 0), 100) / 100));
    circleEl.style.strokeDasharray = `${totalCircumference}`;
    circleEl.style.strokeDashoffset = `${offset}`;
    circleEl.setAttribute('stroke', risk.dotColor);
  }

  // Classification & Recommendation Block
  const classLabel = document.getElementById('classificationLabel');
  const classDesc = document.getElementById('classificationDesc');
  const dataQuality = document.getElementById('classificationDataQuality');

  if (classLabel) {
    classLabel.innerHTML = `
      <span class="material-symbols-outlined text-[18px]" style="color: ${risk.dotColor}">warning</span>
      <span style="color: ${risk.dotColor}">Class ${predClass} (${predClass === 1 ? 'Flood Hazard Likely within 24-48h' : 'Sub-Hazard / Low Risk'})</span>
    `;
  }

  if (classDesc) {
    const alertRec = (activeAlerts && activeAlerts.length > 0) ? activeAlerts[0].recommendation : null;
    const actionMsg = pred.action ? (pred.action.message || (typeof pred.action === 'string' ? pred.action : null)) : null;
    classDesc.textContent = alertRec || actionMsg || pred.recommendation || 
      `Inference engine evaluates 64 hydro-meteorological features including antecedent rainfall accumulation, elevation (${loc?.elevation_m || 'N/A'}m ASL), and distance to river channels (${loc?.distance_to_river_m || 'N/A'}m).`;
  }

  if (dataQuality) {
    const qualityStatus = predRes?.data_quality?.status || pred?.data_quality_status || 'GOOD';
    const featuresCount = predRes?.data_quality?.features_present_count || pred?.features_used_count || 64;
    dataQuality.textContent = `${qualityStatus} (${featuresCount}/64 Features)`;
  }
}

/**
 * River Channel Proximity Card
 */
function renderChannelProximity(loc, weather) {
  if (!loc) return;
  const channelLoc = document.getElementById('channelLocation');
  const channelDistance = document.getElementById('channelDistance');
  const channelElevation = document.getElementById('channelElevation');

  if (channelLoc) channelLoc.textContent = `${loc.place_name} (${loc.district})`;
  if (channelDistance) channelDistance.textContent = `Distance to River: ${common.formatNumber(loc.distance_to_river_m, 0, 'N/A')}m`;
  if (channelElevation) channelElevation.textContent = `Elevation: ${common.formatNumber(loc.elevation_m, 1, 'N/A')}m ASL`;
}

/**
 * 5 Weather Telemetry Cards
 */
function renderWeatherCards(weather) {
  const current = weather ? weather.current : {};

  const tempEl = document.getElementById('metricTemp');
  const humidityEl = document.getElementById('metricHumidity');
  const rainEl = document.getElementById('metricRain');
  const windEl = document.getElementById('metricWind');
  const dischargeEl = document.getElementById('metricDischarge');

  if (tempEl) tempEl.textContent = common.formatNumber(current.temperature_c, 1, 'N/A');
  if (humidityEl) humidityEl.textContent = common.formatNumber(current.humidity_percent, 0, 'N/A');
  if (rainEl) rainEl.textContent = common.formatNumber(current.precipitation_mm, 1, '0.0');
  if (windEl) windEl.textContent = common.formatNumber(current.wind_speed_kmh, 1, 'N/A');
  if (dischargeEl) dischargeEl.textContent = current.river_discharge_m3s !== undefined ? common.formatNumber(current.river_discharge_m3s, 1, 'N/A') : 'N/A';
}

/**
 * Precipitation Analytics
 */
function renderPrecipitationAnalytics(weather) {
  const rolling = (weather && weather.rainfall) ? weather.rainfall : (weather ? weather.rolling_aggregations : {});

  const rain7El = document.getElementById('detailRain7');
  const rain30El = document.getElementById('detailRain30');
  const maxRainEl = document.getElementById('detailMaxDailyRain');

  const r7 = rolling ? (rolling.rainfall_7d_mm ?? rolling.precipitation_sum_7d_mm) : null;
  const r30 = rolling ? (rolling.monthly_rainfall_mm ?? rolling.precipitation_sum_30d_mm) : null;
  const maxD = rolling ? (rolling.max_daily_rainfall_7d_mm ?? rolling.max_daily_rainfall) : null;

  if (rain7El) rain7El.textContent = `${common.formatNumber(r7, 1, '0.0')} mm`;
  if (rain30El) rain30El.textContent = `${common.formatNumber(r30, 1, '0.0')} mm`;
  if (maxRainEl) maxRainEl.textContent = `${common.formatNumber(maxD, 1, '0.0')} mm`;
}

/**
 * Geospatial Vulnerability Matrix
 */
function renderVulnerabilityMatrix(loc) {
  if (!loc) return;

  const setVal = (id, val, unit = '') => {
    const el = document.getElementById(id);
    if (el) el.textContent = val !== null && val !== undefined ? `${val}${unit}` : 'N/A';
  };

  setVal('vulnElevation', common.formatNumber(loc.elevation_m, 1), ' m');
  setVal('vulnDistanceRiver', common.formatNumber(loc.distance_to_river_m, 0), ' m');
  setVal('vulnPopDensity', common.formatNumber(loc.population_density_per_km2, 0), ' / km²');
  setVal('vulnInfrastructureScore', common.formatNumber(loc.infrastructure_score, 0), ' / 100');
  setVal('vulnHospital', common.formatNumber(loc.nearest_hospital_km, 1), ' km');
  setVal('vulnEvac', common.formatNumber(loc.nearest_evac_km, 1), ' km');
  setVal('vulnBuiltUp', common.formatNumber(loc.built_up_percent, 1), '%');
  setVal('vulnDrainageIndex', common.formatNumber(loc.drainage_index, 2));
}

/**
 * Binary Decision Threshold
 */
function renderDecisionThreshold(predRes) {
  if (!predRes) return;
  const pred = predRes.prediction || predRes;
  const riskObj = pred.risk || {};
  let prob1 = 0;
  if (riskObj.flood_probability_percent !== undefined) {
    prob1 = Number(riskObj.flood_probability_percent);
  } else if (pred.flood_probability_percent !== undefined) {
    prob1 = Number(pred.flood_probability_percent);
  } else if (riskObj.score !== undefined) {
    prob1 = Number(riskObj.score) * 100;
  } else if (pred.flood_probability !== undefined) {
    prob1 = Number(pred.flood_probability) * 100;
  }
  const prob0 = 100 - prob1;

  const class1Val = document.getElementById('splitClass1Val');
  const class0Val = document.getElementById('splitClass0Val');
  const class1Bar = document.getElementById('splitClass1Bar');
  const class0Bar = document.getElementById('splitClass0Bar');

  if (class1Val) class1Val.textContent = `${common.formatNumber(prob1, 2)}%`;
  if (class0Val) class0Val.textContent = `${common.formatNumber(prob0, 2)}%`;
  if (class1Bar) class1Bar.style.width = `${Math.min(Math.max(prob1, 0), 100)}%`;
  if (class0Bar) class0Bar.style.width = `${Math.min(Math.max(prob0, 0), 100)}%`;
}

/**
 * Prediction History Table
 */
function renderHistoryTable(items) {
  const tbody = document.getElementById('districtHistoryTableBody');
  const emptyState = document.getElementById('districtHistoryEmpty');
  if (!tbody) return;

  if (!items || !items.length) {
    tbody.innerHTML = '';
    if (emptyState) emptyState.classList.remove('hidden');
    return;
  }

  if (emptyState) emptyState.classList.add('hidden');

  tbody.innerHTML = items.map((row, idx) => {
    const isLatest = idx === 0;
    const prob = (row.flood_probability * 100);
    const risk = common.getRiskDetails(prob >= 65 ? 'HIGH' : prob >= 35 ? 'MODERATE' : 'LOW', row.flood_probability);
    const timeStr = common.formatTime(row.created_at);

    return `
      <tr class="hover:bg-surface-container-low/50 transition-colors">
        <td class="py-3 px-4 font-data-metric text-data-metric font-semibold text-on-surface flex items-center gap-1.5">
          <span class="h-2 w-2 rounded-full" style="background-color: ${risk.dotColor}"></span>
          ${timeStr} ${isLatest ? '<span class="text-xs text-secondary font-semibold">(Latest)</span>' : ''}
        </td>
        <td class="py-3 px-4 font-data-metric text-data-metric font-bold" style="color: ${risk.textColor}">
          ${common.formatNumber(prob, 2)}%
        </td>
        <td class="py-3 px-4">
          <span class="inline-flex items-center px-2 py-0.5 rounded font-label-md text-label-md font-bold ${risk.badgeBg}">
            Class ${row.prediction_class} (${row.prediction_class === 1 ? 'Flood' : 'Normal'})
          </span>
        </td>
        <td class="py-3 px-4 font-data-timestamp text-data-timestamp text-on-surface-variant">
          ${row.model_name || 'RandomForest'} v${row.model_version || '1.0.0'}
        </td>
        <td class="py-3 px-4">
          <span class="inline-flex items-center gap-1 font-label-md text-label-md text-secondary font-medium">
            <span class="material-symbols-outlined text-[15px]">verified</span>
            ${row.data_quality_status || 'GOOD'} (${row.data_source === 'memory' ? 'Runtime Memory' : 'Database'})
          </span>
        </td>
      </tr>
    `;
  }).join('');
}

/**
 * Graceful error state renderers for individual sections
 */
function renderLocationError(msg) {
  const title = document.getElementById('stationTitle');
  if (title) title.innerHTML = `<span class="text-error font-semibold">${msg}</span>`;
}

function renderWeatherError(msg) {
  const tempEl = document.getElementById('metricTemp');
  const humidityEl = document.getElementById('metricHumidity');
  const rainEl = document.getElementById('metricRain');
  const windEl = document.getElementById('metricWind');
  const dischargeEl = document.getElementById('metricDischarge');

  if (tempEl) tempEl.textContent = 'N/A';
  if (humidityEl) humidityEl.textContent = 'N/A';
  if (rainEl) rainEl.textContent = 'N/A';
  if (windEl) windEl.textContent = 'N/A';
  if (dischargeEl) dischargeEl.textContent = 'N/A';
}

function renderPredictionError(msg) {
  const numberEl = document.getElementById('radialGaugeNumber');
  const classLabel = document.getElementById('classificationLabel');
  const classDesc = document.getElementById('classificationDesc');

  if (numberEl) numberEl.innerHTML = `N/A`;
  if (classLabel) {
    classLabel.innerHTML = `<span class="text-on-surface-variant text-body-sm">${msg}</span>`;
  }
  if (classDesc) {
    classDesc.textContent = msg;
  }
}

function renderAlertsError(msg) {
  const section = document.getElementById('stationAlertSection');
  const titleEl = document.getElementById('stationAlertTitle');
  const msgEl = document.getElementById('stationAlertMessage');

  if (section) section.classList.remove('hidden');
  if (titleEl) titleEl.textContent = 'Alert Service Temporarily Unavailable';
  if (msgEl) msgEl.textContent = msg;
}

/**
 * Setup Export CSV Handler
 */
function setupExportButton() {
  const btn = document.getElementById('btnExportCsv');
  if (!btn) return;

  btn.addEventListener('click', () => {
    if (!stationData) return;
    const rows = [
      ['Attribute', 'Value'],
      ['Record ID', stationData.record_id || ''],
      ['District', stationData.district || ''],
      ['Place Name', stationData.place_name || ''],
      ['Latitude', stationData.latitude || ''],
      ['Longitude', stationData.longitude || ''],
      ['Elevation (m)', stationData.elevation_m !== undefined ? stationData.elevation_m : ''],
      ['Distance to River (m)', stationData.distance_to_river_m !== undefined ? stationData.distance_to_river_m : ''],
      ['Population Density', stationData.population_density_per_km2 !== undefined ? stationData.population_density_per_km2 : ''],
      ['Built-up %', stationData.built_up_percent !== undefined ? stationData.built_up_percent : ''],
      ['Drainage Index', stationData.drainage_index !== undefined ? stationData.drainage_index : ''],
      ['Ambient Temp (°C)', weatherData?.current?.temperature_c !== undefined ? weatherData.current.temperature_c : ''],
      ['Relative Humidity (%)', weatherData?.current?.humidity_percent !== undefined ? weatherData.current.humidity_percent : ''],
      ['7-Day Rain (mm)', weatherData?.rainfall?.rainfall_7d_mm ?? weatherData?.rolling_aggregations?.precipitation_sum_7d_mm ?? ''],
      ['30-Day Rain (mm)', weatherData?.rainfall?.monthly_rainfall_mm ?? weatherData?.rolling_aggregations?.precipitation_sum_30d_mm ?? ''],
      ['Flood Probability (%)', predictionData?.prediction?.flood_probability_percent !== undefined ? predictionData.prediction.flood_probability_percent : ''],
      ['Prediction Class', predictionData?.prediction?.class !== undefined ? predictionData.prediction.class : ''],
      ['Risk Level', predictionData?.prediction?.risk_level || '']
    ];

    const csvContent = "data:text/csv;charset=utf-8," + rows.map((e) => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `station_${stationData.id}_telemetry_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });
}
