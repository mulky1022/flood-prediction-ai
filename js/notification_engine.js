/**
 * Sri Lanka FloodWatch — Real-Time Notification & Alert Dispatch Engine
 * Bridges Notification Preferences, LocationTracker, Open-Meteo ML Inferences,
 * Web Audio Ringtone Synthesis, and System Notifications.
 */

import { api } from './api.js';
import { notificationPrefs, getOrCreateDeviceId } from './notification_preferences.js';
import { locationTracker } from './location_tracker.js';
import { notificationSound } from './notification_sound.js';

class FloodNotificationEngine {
  constructor() {
    this.pollIntervalId = null;
    this.seenTriggeredAlertIds = new Set();
    this.isPolling = false;
    this.isInitialized = false;

    if (typeof setTimeout !== 'undefined') {
      setTimeout(() => this.init(), 0);
    }
  }

  /**
   * Initializes listeners to preference and location changes
   */
  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;

    if (typeof notificationPrefs !== 'undefined') {
      notificationPrefs.subscribe((prefs) => {
        if (prefs.notifications_enabled) {
          this.startMonitoring();
        } else {
          this.stopMonitoring();
        }
      });
    }

    locationTracker.subscribe((locData) => {
      const prefs = notificationPrefs.get();
      if (prefs.notifications_enabled && locData.nearestStation && locData.nearestStation.location) {
        const station = locData.nearestStation.location;
        if (prefs.selected_location_id !== null && station.id !== prefs.selected_location_id) {
          // If user had selected specific station or wanted tracking
        }
      }
    });

    // Auto-start if enabled
    const currentPrefs = notificationPrefs.get();
    if (currentPrefs.notifications_enabled) {
      this.startMonitoring();
    }
  }

  /**
   * Requests browser notification permission
   */
  async requestPermission() {
    if (typeof window === 'undefined' || !('Notification' in window)) {
      return 'unsupported';
    }

    if (Notification.permission === 'granted') {
      return 'granted';
    }

    if (Notification.permission !== 'denied') {
      const permission = await Notification.requestPermission();
      return permission;
    }

    return Notification.permission;
  }

  /**
   * Start live polling & telemetry monitoring
   */
  async startMonitoring() {
    if (this.isPolling) return;
    this.isPolling = true;

    // 1. Request Permission
    await this.requestPermission();

    // 2. Unlock Audio
    notificationSound.initContext();

    // 3. Initial immediate check for triggered alerts
    await this.checkTriggeredAlerts();

    // 4. Periodic polling (every 20 seconds)
    if (this.pollIntervalId) clearInterval(this.pollIntervalId);
    this.pollIntervalId = setInterval(() => {
      const p = notificationPrefs.get();
      if (p.notifications_enabled) {
        this.checkTriggeredAlerts();
      }
    }, 20000);
  }

  /**
   * Stop monitoring and cleanup timers
   */
  stopMonitoring() {
    this.isPolling = false;
    if (this.pollIntervalId) {
      clearInterval(this.pollIntervalId);
      this.pollIntervalId = null;
    }
  }

  /**
   * Check backend for unread triggered alerts matching user's device/preferences
   */
  async checkTriggeredAlerts() {
    const deviceId = getOrCreateDeviceId();
    try {
      const res = await api.getTriggeredAlerts({ device_id: deviceId, status: 'UNREAD', limit: 10 });
      if (res && res.items && res.items.length > 0) {
        for (const item of res.items) {
          if (!this.seenTriggeredAlertIds.has(item.id)) {
            this.seenTriggeredAlertIds.add(item.id);
            await this.dispatchFloodAlert({
              id: item.id,
              location: {
                id: item.location_id,
                place_name: item.location_name || `Station ${item.location_id}`,
                district: item.district || 'Sri Lanka'
              },
              risk_level: item.risk_level,
              flood_probability: item.flood_probability,
              prob_pct: (item.flood_probability_percent || item.flood_probability * 100).toFixed(1),
              threshold_crossed: item.threshold_crossed,
              title: item.title,
              message: item.message
            });
          }
        }
      }
      // Update badge
      notificationPrefs.updateUnreadCount();
    } catch (err) {
      console.warn('[NotificationEngine] Error checking triggered alerts:', err);
    }
  }

  /**
   * Dispatches system notification, plays audio ringtone, and shows in-app banner
   */
  async dispatchFloodAlert({ id, location, risk_level, flood_probability, prob_pct, threshold_crossed, title, message }) {
    const placeName = location.place_name || 'Monitored Station';
    const district = location.district || 'Sri Lanka';
    const timeStr = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

    const alertTitle = title || `🚨 FLOOD ALERT — ${risk_level} RISK (${placeName})`;
    const fullMessage = message || `Station ${placeName} (${district}) probability of ${prob_pct}% exceeded threshold.`;

    // 1. Play synthesized emergency audio tone
    await notificationSound.playAlertTone(risk_level);

    // 2. Dispatch browser system notification
    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
      try {
        const notif = new Notification(alertTitle, {
          body: `${fullMessage}\nTime: ${timeStr}`,
          icon: '/assets/logo.png',
          badge: '/assets/logo.png',
          tag: `floodwatch-alert-${location.id || 1}-${id || Date.now()}`,
          requireInteraction: risk_level === 'CRITICAL' || risk_level === 'HIGH'
        });

        notif.onclick = () => {
          window.focus();
          if (id) api.markTriggeredAlertRead(id).catch(() => null);
          window.location.href = `district.html?location_id=${location.id || 1}`;
        };
      } catch (err) {
        console.warn('[NotificationEngine] Native Notification constructor failed:', err);
      }
    }

    // 3. Render In-App Floating Visual Banner
    this.showInAppBanner({
      id,
      title: alertTitle,
      placeName,
      district,
      risk_level,
      prob_pct,
      threshold_crossed: threshold_crossed || 35,
      timeStr,
      locationId: location.id || 1
    });
  }

  /**
   * Renders high-visibility in-app toast/banner
   */
  showInAppBanner(data) {
    if (typeof document === 'undefined') return;

    let banner = document.getElementById('liveFloodAlertToast');
    if (banner) banner.remove();

    const isUrgent = data.risk_level === 'CRITICAL' || data.risk_level === 'HIGH';
    const bgClass = data.risk_level === 'CRITICAL' 
      ? 'bg-rose-600 text-white' 
      : data.risk_level === 'HIGH' 
      ? 'bg-orange-600 text-white' 
      : data.risk_level === 'MODERATE'
      ? 'bg-amber-500 text-white'
      : 'bg-emerald-600 text-white';

    const toastHtml = `
      <div id="liveFloodAlertToast" class="fixed top-5 right-5 z-[9999] max-w-md w-full shadow-2xl rounded-2xl overflow-hidden animate-bounce-short border-2 border-white/20 transition-all duration-300">
        <div class="${bgClass} p-4">
          <div class="flex items-start justify-between gap-3">
            <div class="flex items-center gap-2.5">
              <span class="text-2xl animate-pulse">🚨</span>
              <div>
                <h4 class="font-bold text-sm leading-tight">${data.title}</h4>
                <p class="text-xs opacity-90">📍 ${data.placeName}, ${data.district}</p>
              </div>
            </div>
            <button id="closeAlertToastBtn" class="text-white/80 hover:text-white p-1 cursor-pointer" aria-label="Close">
              <span class="material-symbols-outlined text-[18px]">close</span>
            </button>
          </div>

          <div class="mt-2.5 pt-2 border-t border-white/20 text-xs flex items-center justify-between">
            <span>Probability: <strong>${data.prob_pct}%</strong> (Threshold ≥ ${data.threshold_crossed}%)</span>
            <span class="opacity-80">${data.timeStr}</span>
          </div>

          <div class="mt-3 flex items-center gap-2">
            <a href="district.html?location_id=${data.locationId}" id="btnToastViewStation" class="flex-1 text-center py-2 px-3 bg-white text-on-surface font-bold text-xs rounded-xl shadow hover:bg-white/90 transition-colors">
              View Station Telemetry
            </a>
            <button id="btnToastAcknowledge" type="button" class="py-2 px-3 bg-black/30 hover:bg-black/40 text-white font-bold text-xs rounded-xl transition-colors cursor-pointer">
              Mark Read
            </button>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', toastHtml);

    const closeBtn = document.getElementById('closeAlertToastBtn');
    const ackBtn = document.getElementById('btnToastAcknowledge');
    const viewBtn = document.getElementById('btnToastViewStation');

    const dismissToast = () => {
      if (data.id) api.markTriggeredAlertRead(data.id).catch(() => null);
      const t = document.getElementById('liveFloodAlertToast');
      if (t) t.remove();
      notificationPrefs.updateUnreadCount();
    };

    if (closeBtn) closeBtn.onclick = dismissToast;
    if (ackBtn) ackBtn.onclick = dismissToast;
    if (viewBtn) {
      viewBtn.onclick = () => {
        if (data.id) api.markTriggeredAlertRead(data.id).catch(() => null);
      };
    }

    // Auto-dismiss non-urgent after 20s
    if (!isUrgent) {
      setTimeout(() => {
        const t = document.getElementById('liveFloodAlertToast');
        if (t) t.remove();
      }, 20000);
    }
  }

  /**
   * Test notification trigger for manual verification
   */
  async triggerTestNotification(severity = 'HIGH') {
    notificationSound.initContext();
    const prefs = notificationPrefs.get();
    const locId = prefs.selected_location_id || 1;
    let loc = {
      id: locId,
      place_name: prefs.selected_location_name || 'Kolonnawa (Kelani River Lower)',
      district: prefs.selected_district || 'Colombo'
    };

    try {
      const fetched = await api.getLocation(locId);
      if (fetched && fetched.location) loc = fetched.location;
    } catch (e) {}

    await this.dispatchFloodAlert({
      id: null,
      location: loc,
      risk_level: severity,
      flood_probability: severity === 'CRITICAL' ? 0.912 : 0.755,
      prob_pct: severity === 'CRITICAL' ? '91.2' : '75.5',
      threshold_crossed: prefs.risk_threshold || 35.0,
      title: `🚨 FLOOD ALERT — ${severity} RISK (${loc.place_name})`,
      message: `Simulated test notification: Web audio ringtone and flood alert pipeline verified.`
    });
  }
}

export const notificationEngine = new FloodNotificationEngine();

if (typeof window !== 'undefined') {
  window.floodNotificationEngine = notificationEngine;
}
