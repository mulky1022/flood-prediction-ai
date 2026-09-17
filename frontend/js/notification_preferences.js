/**
 * Sri Lanka FloodWatch — Notification Preference Store & UI Manager
 * Handles client device identity, server-side preference persistence,
 * risk threshold configuration, station filters, and accessible modal controls.
 */

import { api } from './api.js';
import { notificationSound } from './notification_sound.js';
import { locationTracker } from './location_tracker.js';
import { notificationEngine } from './notification_engine.js';

const STORAGE_KEY = 'floodwatch_notification_prefs';
const DEVICE_ID_KEY = 'floodwatch_device_id';

/**
 * Retrieves or generates a persistent unique device/client ID
 */
export function getOrCreateDeviceId() {
  if (typeof localStorage === 'undefined') {
    return 'anon_device_' + Math.random().toString(36).substring(2, 10);
  }
  let deviceId = localStorage.getItem(DEVICE_ID_KEY);
  if (!deviceId) {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      deviceId = 'dev_' + crypto.randomUUID();
    } else {
      deviceId = 'dev_' + Date.now().toString(36) + '_' + Math.random().toString(36).substring(2, 8);
    }
    localStorage.setItem(DEVICE_ID_KEY, deviceId);
  }
  return deviceId;
}

const DEFAULT_PREFERENCES = {
  id: null,
  device_id: getOrCreateDeviceId(),
  selected_location_id: null, // null = All Monitored Stations
  selected_location_name: 'All Monitored Stations',
  selected_district: 'Island-wide',
  risk_threshold: 35.0, // 35% threshold default (MODERATE)
  alert_levels: {
    LOW: false,
    MODERATE: true,
    HIGH: true,
    CRITICAL: true
  },
  notification_channels: ['in_app'],
  notifications_enabled: true,
  tracking_enabled: false,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
};

class NotificationPreferenceStore {
  constructor() {
    this.deviceId = getOrCreateDeviceId();
    this.preferences = this.loadLocal();
    this.listeners = [];
    this.unreadAlertsCount = 0;
  }

  /**
   * Load cached preferences from localStorage
   */
  loadLocal() {
    try {
      if (typeof localStorage !== 'undefined') {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw);
          return {
            ...DEFAULT_PREFERENCES,
            ...parsed,
            device_id: this.deviceId,
            alert_levels: {
              ...DEFAULT_PREFERENCES.alert_levels,
              ...(parsed.alert_levels || {})
            }
          };
        }
      }
    } catch (e) {
      console.warn('[NotificationPrefs] Could not parse stored preferences:', e);
    }
    return { ...DEFAULT_PREFERENCES, device_id: this.deviceId };
  }

  /**
   * Fetch saved preferences from the backend API
   */
  async syncWithBackend() {
    try {
      const res = await api.getPreferences(this.deviceId);
      if (res && res.items && res.items.length > 0) {
        const serverPref = res.items[0];
        const thresh = parseFloat(serverPref.risk_threshold) || 35.0;
        this.preferences = {
          ...this.preferences,
          id: serverPref.id,
          device_id: this.deviceId,
          selected_location_id: serverPref.location_id,
          selected_location_name: serverPref.location_name || 'All Monitored Stations',
          selected_district: serverPref.district || 'Island-wide',
          risk_threshold: thresh,
          notifications_enabled: serverPref.is_active,
          alert_levels: {
            LOW: thresh <= 20.0,
            MODERATE: thresh <= 50.0,
            HIGH: thresh <= 75.0,
            CRITICAL: true
          },
          notification_channels: serverPref.notification_channels || ['in_app'],
          updated_at: serverPref.updated_at
        };
        this.saveLocal(this.preferences);
        this.notify();
      }
    } catch (err) {
      console.warn('[NotificationPrefs] Could not fetch server preferences, using local cache:', err);
    }

    // Also sync unread triggered alerts count for badge
    await this.updateUnreadCount();
  }

  /**
   * Save preferences to backend and localStorage
   */
  async save(newPrefs) {
    const thresh = newPrefs.risk_threshold !== undefined ? parseFloat(newPrefs.risk_threshold) : this.preferences.risk_threshold;
    
    this.preferences = {
      ...this.preferences,
      ...newPrefs,
      risk_threshold: thresh,
      alert_levels: {
        LOW: thresh <= 20.0,
        MODERATE: thresh <= 50.0,
        HIGH: thresh <= 75.0,
        CRITICAL: true
      },
      updated_at: new Date().toISOString()
    };

    this.saveLocal(this.preferences);
    this.notify();

    // Persist to backend database
    try {
      const payload = {
        device_id: this.deviceId,
        location_id: this.preferences.selected_location_id,
        risk_threshold: this.preferences.risk_threshold,
        notification_channels: this.preferences.notification_channels || ['in_app'],
        is_active: this.preferences.notifications_enabled
      };
      const res = await api.savePreference(payload);
      if (res && res.preference) {
        this.preferences.id = res.preference.id;
        this.saveLocal(this.preferences);
      }
      return { status: 'success', preference: this.preferences };
    } catch (err) {
      console.error('[NotificationPrefs] Backend save error:', err);
      return { status: 'local_only', preference: this.preferences };
    }
  }

  saveLocal(prefs) {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
      }
    } catch (e) {
      console.error('[NotificationPrefs] Failed to persist local preferences:', e);
    }
  }

  get() {
    return { ...this.preferences };
  }

  subscribe(fn) {
    this.listeners.push(fn);
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== fn);
    };
  }

  notify() {
    const data = this.get();
    this.listeners.forEach(fn => {
      try {
        fn(data);
      } catch (e) {
        console.error('[NotificationPrefs] Listener error:', e);
      }
    });

    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('floodwatch:notification_prefs_changed', { detail: data }));
    }
  }

  async updateUnreadCount() {
    try {
      const res = await api.getTriggeredAlerts({ device_id: this.deviceId, status: 'UNREAD', limit: 50 });
      this.unreadAlertsCount = (res && res.unread_count !== undefined) ? res.unread_count : 0;
      notificationUI.updateHeaderBadge(this.unreadAlertsCount);
    } catch (e) {
      // Quiet fallback
    }
  }
}

export const notificationPrefs = new NotificationPreferenceStore();

/**
 * UI Component for Notification Preference Modal & Header Control
 */
export const notificationUI = {
  isModalRendered: false,
  locationsCache: [],

  async init() {
    this.injectHeaderButton();
    this.injectModal();
    await this.loadLocationsDropdown();
    await notificationPrefs.syncWithBackend();
    this.syncUI();

    // Re-sync on store changes
    notificationPrefs.subscribe(() => {
      this.syncUI();
    });

    // Check unread triggered alerts periodically (every 30s)
    setInterval(() => {
      notificationPrefs.updateUnreadCount();
    }, 30000);
  },

  injectHeaderButton() {
    if (document.getElementById('headerNotificationBtn')) return;

    const header = document.querySelector('.site-header');
    if (!header) return;

    const rightContainer = header.querySelector('.header-container > div:last-child');
    if (!rightContainer) return;

    const btn = document.createElement('button');
    btn.id = 'headerNotificationBtn';
    btn.className = 'notification-trigger-btn relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-surface-container bg-surface-container-low hover:bg-surface-container-high transition-all text-xs font-semibold cursor-pointer';
    btn.setAttribute('aria-label', 'Open Notification Preferences');
    btn.title = 'Flood Risk Notification & Alert Preferences';
    btn.innerHTML = `
      <span id="headerNotificationIcon" class="material-symbols-outlined text-[18px] text-on-surface-variant">notifications</span>
      <span id="headerNotificationLabel" class="hidden sm:inline text-on-surface-variant">Alerts</span>
      <span id="headerNotificationBadge" class="hidden min-w-[18px] h-[18px] px-1 bg-rose-600 text-white text-[10px] font-bold rounded-full flex items-center justify-center -ml-0.5">0</span>
    `;

    btn.onclick = () => this.openModal();

    const themeBtn = document.getElementById('themeToggleBtn');
    if (themeBtn) {
      rightContainer.insertBefore(btn, themeBtn);
    } else {
      rightContainer.appendChild(btn);
    }
  },

  updateHeaderBadge(count) {
    const badge = document.getElementById('headerNotificationBadge');
    const icon = document.getElementById('headerNotificationIcon');
    const label = document.getElementById('headerNotificationLabel');
    const prefs = notificationPrefs.get();

    if (badge) {
      if (count > 0) {
        badge.textContent = count > 99 ? '99+' : String(count);
        badge.classList.remove('hidden');
        badge.classList.add('flex');
        if (icon) icon.className = 'material-symbols-outlined text-[18px] text-rose-500 animate-pulse';
        if (label) label.className = 'hidden sm:inline font-bold text-rose-600 dark:text-rose-400';
      } else {
        badge.classList.add('hidden');
        badge.classList.remove('flex');
        if (icon) {
          icon.className = prefs.notifications_enabled
            ? 'material-symbols-outlined text-[18px] text-secondary'
            : 'material-symbols-outlined text-[18px] text-on-surface-variant';
        }
        if (label) {
          label.className = 'hidden sm:inline text-on-surface-variant';
        }
      }
    }
  },

  injectModal() {
    if (document.getElementById('notificationPrefModal')) return;

    const modalHtml = `
      <div id="notificationPrefBackdrop" class="notification-modal-backdrop fixed inset-0 bg-black/60 backdrop-blur-sm z-50 opacity-0 pointer-events-none transition-opacity duration-200 flex items-center justify-center p-4">
        <div id="notificationPrefModal" class="notification-modal-card bg-surface w-full max-w-lg rounded-2xl border border-surface-container shadow-2xl overflow-hidden transform scale-95 transition-transform duration-200" role="dialog" aria-modal="true" aria-labelledby="prefModalTitle">
          
          <!-- Modal Header -->
          <div class="px-6 py-5 border-b border-surface-container flex items-center justify-between bg-surface-container-low">
            <div class="flex items-center gap-3">
              <div id="modalBellIconWrapper" class="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center text-secondary">
                <span id="modalBellIcon" class="material-symbols-outlined text-[24px]">notifications_active</span>
              </div>
              <div>
                <h3 id="prefModalTitle" class="font-display-md text-base font-bold text-on-surface">Flood Alert Preferences</h3>
                <p class="text-xs text-on-surface-variant">Set automated flood-risk notification threshold &amp; stations</p>
              </div>
            </div>
            <button id="closePrefModalBtn" class="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container hover:text-on-surface transition-colors cursor-pointer" aria-label="Close modal">
              <span class="material-symbols-outlined text-[20px]">close</span>
            </button>
          </div>

          <!-- Modal Body -->
          <div class="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
            
            <!-- Master Notification Switch -->
            <div class="p-3.5 rounded-xl border border-surface-container bg-surface-container-low flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <span class="material-symbols-outlined text-secondary text-[22px]">radar</span>
                <div>
                  <div class="text-xs font-bold text-on-surface">Live Risk Monitoring</div>
                  <div class="text-[11px] text-on-surface-variant">Evaluate each station inference against your threshold</div>
                </div>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" id="prefMasterToggle" class="sr-only peer" checked />
                <div class="w-11 h-6 bg-surface-container-highest peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-secondary"></div>
              </label>
            </div>

            <!-- Station / District Selector -->
            <div>
              <label for="prefLocationSelect" class="block text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-2 flex items-center justify-between">
                <span class="flex items-center gap-1.5">
                  <span class="material-symbols-outlined text-[16px] text-secondary">location_on</span>
                  <span>Target Station / District</span>
                </span>
                <button id="btnAutoDetectLocation" type="button" class="text-[11px] text-secondary hover:underline flex items-center gap-1 font-semibold cursor-pointer">
                  <span class="material-symbols-outlined text-[14px]">my_location</span>
                  <span>Use GPS Station</span>
                </button>
              </label>
              <select id="prefLocationSelect" class="w-full bg-surface-container-low border border-surface-container-high rounded-xl px-3.5 py-2.5 text-sm font-medium text-on-surface focus:ring-2 focus:ring-secondary focus:border-transparent outline-none transition-all cursor-pointer">
                <option value="all">🌟 All Monitored Stations (Island-wide, ~33 Stations)</option>
              </select>
              <p class="text-[11px] text-on-surface-variant mt-1.5">
                Choose a specific catchment station or select All Stations to receive alerts across all Sri Lanka.
              </p>
            </div>

            <!-- Flood Risk Threshold Selector -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="block text-xs font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-1.5">
                  <span class="material-symbols-outlined text-[16px] text-secondary">tune</span>
                  <span>Risk Alert Threshold</span>
                </label>
                <span id="thresholdValueBadge" class="text-xs font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 font-mono">
                  &ge; 35% (MODERATE)
                </span>
              </div>

              <!-- Preset Pills -->
              <div class="grid grid-cols-3 gap-2 mb-3">
                <button type="button" data-thresh="35" class="thresh-preset-btn py-2 px-3 rounded-xl border border-amber-500/30 bg-amber-50 dark:bg-amber-950/30 text-xs font-bold text-amber-700 dark:text-amber-300 hover:bg-amber-100 transition-all cursor-pointer text-center">
                  ⚠️ Moderate<br><span class="text-[10px] font-normal">&ge; 35%</span>
                </button>
                <button type="button" data-thresh="65" class="thresh-preset-btn py-2 px-3 rounded-xl border border-orange-500/30 bg-surface-container-low text-xs font-bold text-on-surface-variant hover:bg-orange-50 dark:hover:bg-orange-950/30 transition-all cursor-pointer text-center">
                  🚨 High<br><span class="text-[10px] font-normal">&ge; 65%</span>
                </button>
                <button type="button" data-thresh="80" class="thresh-preset-btn py-2 px-3 rounded-xl border border-rose-500/30 bg-surface-container-low text-xs font-bold text-on-surface-variant hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-all cursor-pointer text-center">
                  🛑 Critical<br><span class="text-[10px] font-normal">&ge; 80%</span>
                </button>
              </div>

              <!-- Custom Threshold Slider -->
              <div class="space-y-1">
                <input type="range" id="prefThresholdSlider" min="15" max="90" step="5" value="35" class="w-full accent-secondary cursor-pointer" />
                <div class="flex justify-between text-[10px] text-on-surface-variant font-mono">
                  <span>15% (Sensitive)</span>
                  <span>50% (Balanced)</span>
                  <span>90% (Urgent Only)</span>
                </div>
              </div>
            </div>

            <!-- Audio & Alert Testing -->
            <div class="pt-2 border-t border-surface-container">
              <div class="flex items-center justify-between gap-2">
                <button id="btnTestSoundHigh" type="button" class="flex-1 py-2 px-3 rounded-xl border border-surface-container bg-surface-container-low hover:bg-surface-container text-xs font-semibold text-on-surface flex items-center justify-center gap-1.5 transition-colors cursor-pointer">
                  <span>🔊 Test Chime</span>
                </button>
                <button id="btnTestSoundCrit" type="button" class="flex-1 py-2 px-3 rounded-xl border border-rose-500/30 bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-100 text-xs font-semibold text-rose-700 dark:text-rose-300 flex items-center justify-center gap-1.5 transition-colors cursor-pointer">
                  <span>🚨 Test Siren</span>
                </button>
              </div>
            </div>

            <!-- Status Banner -->
            <div id="prefStatusBanner" class="p-3 rounded-xl bg-surface-container text-xs text-on-surface-variant flex items-start gap-2.5">
              <span class="material-symbols-outlined text-[18px] text-secondary shrink-0 mt-0.5">info</span>
              <span id="prefStatusText">Alerts trigger automatically when live inferences exceed your chosen threshold.</span>
            </div>

            <!-- Action Buttons: Save & Cancel -->
            <div class="flex items-center gap-3 pt-2">
              <button id="btnCancelPrefModal" type="button" class="flex-1 py-2.5 px-4 rounded-xl border border-surface-container text-xs font-bold text-on-surface hover:bg-surface-container transition-colors cursor-pointer">
                Cancel
              </button>
              <button id="btnSavePrefModal" type="button" class="flex-1 py-2.5 px-4 rounded-xl bg-secondary hover:bg-secondary/90 text-white text-xs font-bold shadow-md transition-all flex items-center justify-center gap-1.5 cursor-pointer">
                <span class="material-symbols-outlined text-[16px]">save</span>
                <span>Save Preferences</span>
              </button>
            </div>

          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    this.attachModalEvents();
  },

  attachModalEvents() {
    const backdrop = document.getElementById('notificationPrefBackdrop');
    const closeBtn = document.getElementById('closePrefModalBtn');
    const cancelBtn = document.getElementById('btnCancelPrefModal');
    const saveBtn = document.getElementById('btnSavePrefModal');
    const locSelect = document.getElementById('prefLocationSelect');
    const masterToggle = document.getElementById('prefMasterToggle');
    const slider = document.getElementById('prefThresholdSlider');
    const autoGpsBtn = document.getElementById('btnAutoDetectLocation');
    const testHighBtn = document.getElementById('btnTestSoundHigh');
    const testCritBtn = document.getElementById('btnTestSoundCrit');

    const closeModal = () => this.closeModal();

    if (closeBtn) closeBtn.onclick = closeModal;
    if (cancelBtn) cancelBtn.onclick = closeModal;

    if (backdrop) {
      backdrop.onclick = (e) => {
        if (e.target === backdrop) closeModal();
      };
    }

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && backdrop && !backdrop.classList.contains('opacity-0')) {
        closeModal();
      }
    });

    // Slider input change
    if (slider) {
      slider.oninput = (e) => {
        const val = parseFloat(e.target.value);
        this.updateThresholdDisplay(val);
      };
    }

    // Preset threshold buttons
    document.querySelectorAll('.thresh-preset-btn').forEach(btn => {
      btn.onclick = () => {
        const t = parseFloat(btn.dataset.thresh);
        if (slider) slider.value = String(t);
        this.updateThresholdDisplay(t);
      };
    });

    // Auto-detect GPS button
    if (autoGpsBtn) {
      autoGpsBtn.onclick = async () => {
        autoGpsBtn.innerHTML = `<span class="material-symbols-outlined text-[14px] animate-spin">sync</span><span>Detecting GPS...</span>`;
        try {
          const res = await locationTracker.getCurrentPosition();
          if (res && res.nearestStation && res.nearestStation.location) {
            const st = res.nearestStation.location;
            if (locSelect) locSelect.value = String(st.id);
            autoGpsBtn.innerHTML = `<span class="material-symbols-outlined text-[14px] text-emerald-500">check</span><span>${st.place_name}</span>`;
          }
        } catch (err) {
          autoGpsBtn.innerHTML = `<span class="material-symbols-outlined text-[14px] text-rose-500">error</span><span>GPS Unavailable</span>`;
        }
        setTimeout(() => {
          if (autoGpsBtn) {
            autoGpsBtn.innerHTML = `<span class="material-symbols-outlined text-[14px]">my_location</span><span>Use GPS Station</span>`;
          }
        }, 4000);
      };
    }

    // Test Audio
    if (testHighBtn) {
      testHighBtn.onclick = async () => {
        notificationSound.initContext();
        await notificationEngine.triggerTestNotification('HIGH');
      };
    }

    if (testCritBtn) {
      testCritBtn.onclick = async () => {
        notificationSound.initContext();
        await notificationEngine.triggerTestNotification('CRITICAL');
      };
    }

    // Save Button
    if (saveBtn) {
      saveBtn.onclick = async () => {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span class="material-symbols-outlined text-[16px] animate-spin">sync</span><span>Saving...</span>`;

        const isEnabled = masterToggle ? masterToggle.checked : true;
        const locVal = locSelect ? locSelect.value : 'all';
        const locId = locVal === 'all' ? null : parseInt(locVal, 10);
        const threshVal = slider ? parseFloat(slider.value) : 35.0;

        let locName = 'All Monitored Stations';
        let district = 'Island-wide';
        if (locId && locSelect) {
          const selectedOpt = locSelect.options[locSelect.selectedIndex];
          if (selectedOpt) {
            const parts = selectedOpt.textContent.split('—').map(s => s.trim());
            district = parts[0] || '';
            locName = parts[1] || selectedOpt.textContent;
          }
        }

        await notificationPrefs.save({
          selected_location_id: locId,
          selected_location_name: locName,
          selected_district: district,
          risk_threshold: threshVal,
          notifications_enabled: isEnabled
        });

        if (isEnabled) {
          notificationSound.initContext();
          notificationSound.playConfirmationChime();
        }

        saveBtn.disabled = false;
        saveBtn.innerHTML = `<span class="material-symbols-outlined text-[16px]">check</span><span>Saved!</span>`;
        
        setTimeout(() => {
          this.closeModal();
          this.showSaveToast(locName, threshVal);
          if (saveBtn) {
            saveBtn.innerHTML = `<span class="material-symbols-outlined text-[16px]">save</span><span>Save Preferences</span>`;
          }
        }, 500);
      };
    }
  },

  updateThresholdDisplay(val) {
    const badge = document.getElementById('thresholdValueBadge');
    if (badge) {
      let label = 'MODERATE';
      let cls = 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20';
      if (val >= 80) {
        label = 'CRITICAL';
        cls = 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20';
      } else if (val >= 65) {
        label = 'HIGH';
        cls = 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20';
      } else if (val <= 20) {
        label = 'LOW';
        cls = 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20';
      }
      badge.textContent = `≥ ${val}% (${label})`;
      badge.className = `text-xs font-bold px-2 py-0.5 rounded border font-mono ${cls}`;
    }

    // Update preset button active states
    document.querySelectorAll('.thresh-preset-btn').forEach(btn => {
      const t = parseFloat(btn.dataset.thresh);
      if (Math.abs(t - val) < 5) {
        btn.classList.add('ring-2', 'ring-secondary');
      } else {
        btn.classList.remove('ring-2', 'ring-secondary');
      }
    });
  },

  showSaveToast(locationName, threshold) {
    let toast = document.getElementById('prefSavedToast');
    if (toast) toast.remove();

    const html = `
      <div id="prefSavedToast" class="fixed bottom-6 right-6 z-[9999] bg-surface border border-secondary/30 shadow-2xl rounded-2xl p-4 flex items-center gap-3 animate-fade-in max-w-sm">
        <div class="w-8 h-8 rounded-xl bg-secondary/10 flex items-center justify-center text-secondary shrink-0">
          <span class="material-symbols-outlined text-[20px]">notifications_active</span>
        </div>
        <div class="flex-1 text-xs">
          <div class="font-bold text-on-surface">Preferences Saved to Database</div>
          <div class="text-on-surface-variant mt-0.5">${locationName} · Threshold ≥ ${threshold}%</div>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
    setTimeout(() => {
      const t = document.getElementById('prefSavedToast');
      if (t) t.remove();
    }, 4500);
  },

  async loadLocationsDropdown() {
    const select = document.getElementById('prefLocationSelect');
    if (!select) return;

    try {
      const data = await api.getLocations();
      this.locationsCache = data.locations || [];
      
      select.innerHTML = '<option value="all">🌟 All Monitored Stations (Island-wide, ~33 Stations)</option>';
      this.locationsCache.forEach(loc => {
        const opt = document.createElement('option');
        opt.value = loc.id;
        opt.textContent = `${loc.district} — ${loc.place_name}`;
        select.appendChild(opt);
      });
    } catch (e) {
      console.warn('[NotificationUI] Failed to load stations from API:', e);
    }
  },

  syncUI() {
    const prefs = notificationPrefs.get();

    // 1. Header icon sync
    const headerIcon = document.getElementById('headerNotificationIcon');
    const headerLabel = document.getElementById('headerNotificationLabel');
    if (headerIcon) {
      headerIcon.textContent = prefs.notifications_enabled ? 'notifications_active' : 'notifications_off';
      headerIcon.className = prefs.notifications_enabled 
        ? 'material-symbols-outlined text-[18px] text-secondary' 
        : 'material-symbols-outlined text-[18px] text-on-surface-variant';
    }
    if (headerLabel) {
      headerLabel.textContent = prefs.notifications_enabled ? 'Alerts ON' : 'Alerts OFF';
    }

    // 2. Modal controls sync
    const masterToggle = document.getElementById('prefMasterToggle');
    const locSelect = document.getElementById('prefLocationSelect');
    const slider = document.getElementById('prefThresholdSlider');

    if (masterToggle) masterToggle.checked = Boolean(prefs.notifications_enabled);
    if (locSelect) {
      locSelect.value = prefs.selected_location_id ? String(prefs.selected_location_id) : 'all';
    }
    if (slider) {
      slider.value = String(prefs.risk_threshold || 35);
      this.updateThresholdDisplay(prefs.risk_threshold || 35);
    }

    const statusText = document.getElementById('prefStatusText');
    if (statusText) {
      if (prefs.notifications_enabled) {
        statusText.textContent = `Monitoring active for ${prefs.selected_location_name || 'All Stations'}. Alerts trigger at ≥ ${prefs.risk_threshold}%.`;
      } else {
        statusText.textContent = 'Notifications are currently disabled. Toggle switch above to activate live flood alerts.';
      }
    }
  },

  openModal() {
    this.syncUI();
    const backdrop = document.getElementById('notificationPrefBackdrop');
    const modal = document.getElementById('notificationPrefModal');
    if (!backdrop || !modal) return;

    backdrop.classList.remove('pointer-events-none', 'opacity-0');
    backdrop.classList.add('pointer-events-auto', 'opacity-100');
    modal.classList.remove('scale-95');
    modal.classList.add('scale-100');
  },

  closeModal() {
    const backdrop = document.getElementById('notificationPrefBackdrop');
    const modal = document.getElementById('notificationPrefModal');
    if (!backdrop || !modal) return;

    backdrop.classList.remove('pointer-events-auto', 'opacity-100');
    backdrop.classList.add('pointer-events-none', 'opacity-0');
    modal.classList.remove('scale-100');
    modal.classList.add('scale-95');
  }
};

// Global helper for opening settings modal from anywhere in the app
if (typeof window !== 'undefined') {
  window.openNotificationSettings = () => notificationUI.openModal();
  window.notificationUI = notificationUI;
  window.notificationPrefs = notificationPrefs;
}

// Auto-initialize UI on DOMContentLoaded
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => notificationUI.init());
  } else {
    notificationUI.init();
  }
}
