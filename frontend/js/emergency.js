/**
 * Emergency & Low-Bandwidth Engine for Sri Lanka FloodWatch — Phase 14
 * 
 * Provides an ultra-lightweight, resilient, map-independent emergency interface.
 * Strictly location-isolated, canonical-data consuming, and zero-fake-risk compliant.
 */

import { api } from './api.js';
import { i18n } from './i18n.js';

export const NETWORK_STATES = {
  ONLINE: 'ONLINE',
  SLOW: 'SLOW',
  OFFLINE: 'OFFLINE',
  API_UNAVAILABLE: 'API_UNAVAILABLE',
  PARTIAL_FAILURE: 'PARTIAL_FAILURE',
  RECOVERING: 'RECOVERING'
};

export class EmergencyEngine {
  constructor(options = {}) {
    this.containerId = options.containerId || 'emergency-container';
    this.currentLocationId = options.locationId || localStorage.getItem('floodwatch_selected_location_id') || 'RATNAPURA_001';
    this.currentLang = options.lang || i18n.getLanguage() || 'en';
    this.networkState = NETWORK_STATES.ONLINE;
    this.activeRequestId = 0;
    this.isEmergencyMode = options.isEmergencyMode || false;

    this.initNetworkListeners();
  }

  initNetworkListeners() {
    if (typeof window === 'undefined') return;

    window.addEventListener('online', () => {
      this.networkState = NETWORK_STATES.RECOVERING;
      this.renderNetworkBadge();
      this.refreshCurrentLocation();
    });

    window.addEventListener('offline', () => {
      this.networkState = NETWORK_STATES.OFFLINE;
      this.renderNetworkBadge();
    });
  }

  getCacheKey(locationId, lang) {
    return `floodwatch_emergency_${locationId}_${lang}`;
  }

  getCachedEmergencyData(locationId, lang) {
    try {
      const key = this.getCacheKey(locationId, lang);
      const raw = localStorage.getItem(key);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      // Verify location isolation in cache
      if (parsed && parsed.data && parsed.data.location && parsed.data.location.id === locationId) {
        return parsed;
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  saveCachedEmergencyData(locationId, lang, data) {
    try {
      if (!data || !data.location || data.location.id !== locationId) return;
      const key = this.getCacheKey(locationId, lang);
      const cachePayload = {
        data: data,
        cachedAt: new Date().toISOString()
      };
      localStorage.setItem(key, JSON.stringify(cachePayload));
    } catch (e) {
      console.warn('[Emergency Engine] Cache write failed:', e);
    }
  }

  async fetchAndRender(locationId, options = {}) {
    const targetLocId = locationId || this.currentLocationId;
    this.currentLocationId = targetLocId;
    const targetLang = options.lang || i18n.getLanguage() || 'en';
    this.currentLang = targetLang;

    const requestId = ++this.activeRequestId;

    // Check navigator online signal first
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      this.networkState = NETWORK_STATES.OFFLINE;
      this.renderOfflineOrCacheState(targetLocId, targetLang, requestId);
      return;
    }

    const startTime = Date.now();
    try {
      const response = await api.getEmergencyData(targetLocId, targetLang);
      const duration = Date.now() - startTime;

      // Check race condition — discard if user changed location while request was in-flight
      if (requestId !== this.activeRequestId) {
        return;
      }

      if (duration > 3000) {
        this.networkState = NETWORK_STATES.SLOW;
      } else {
        this.networkState = NETWORK_STATES.ONLINE;
      }

      if (response && response.status === 'success' && response.location && response.location.id === targetLocId) {
        this.saveCachedEmergencyData(targetLocId, targetLang, response);
        this.renderEmergencyUI(response, 'CURRENT', requestId);
      } else {
        this.renderOfflineOrCacheState(targetLocId, targetLang, requestId, 'API_INVALID');
      }
    } catch (err) {
      if (requestId !== this.activeRequestId) return;
      console.warn('[Emergency Engine] API request failed:', err.message);

      this.networkState = err.message.includes('timed out') ? NETWORK_STATES.SLOW : NETWORK_STATES.API_UNAVAILABLE;
      this.renderOfflineOrCacheState(targetLocId, targetLang, requestId, 'API_FAILED');
    }
  }

  renderOfflineOrCacheState(locationId, lang, requestId, failureReason = '') {
    if (requestId !== this.activeRequestId) return;

    const cachedPayload = this.getCachedEmergencyData(locationId, lang);
    if (cachedPayload && cachedPayload.data) {
      // We have safe cached data for exact location
      this.renderEmergencyUI(cachedPayload.data, 'LAST_KNOWN', requestId, cachedPayload.cachedAt);
    } else {
      // NO CACHE + OFFLINE/UNAVAILABLE -> NEVER SHOW FAKE LOW RISK
      this.renderUnavailableUI(locationId, requestId);
    }
  }

  refreshCurrentLocation() {
    this.fetchAndRender(this.currentLocationId, { lang: this.currentLang });
  }

  renderNetworkBadge() {
    const badgeEl = document.getElementById('emergency-network-badge');
    if (!badgeEl) return;

    let badgeClass = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
    let labelKey = 'emergency.net_online';

    switch (this.networkState) {
      case NETWORK_STATES.SLOW:
        badgeClass = 'bg-amber-500/20 text-amber-300 border-amber-500/30';
        labelKey = 'emergency.net_slow';
        break;
      case NETWORK_STATES.OFFLINE:
        badgeClass = 'bg-rose-500/20 text-rose-300 border-rose-500/30';
        labelKey = 'emergency.net_offline';
        break;
      case NETWORK_STATES.API_UNAVAILABLE:
        badgeClass = 'bg-rose-600/20 text-rose-400 border-rose-600/30';
        labelKey = 'emergency.net_unavailable';
        break;
      case NETWORK_STATES.RECOVERING:
        badgeClass = 'bg-blue-500/20 text-blue-300 border-blue-500/30';
        labelKey = 'emergency.net_recovering';
        break;
    }

    badgeEl.className = `inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${badgeClass}`;
    badgeEl.innerText = i18n.t(labelKey);
  }

  renderEmergencyUI(data, dataState, requestId, cachedAtStr = null) {
    if (requestId !== this.activeRequestId) return;

    const container = document.getElementById(this.containerId);
    if (!container) return;

    const loc = data.location || {};
    const pred = data.prediction;
    const action = data.action;
    const warning = data.official_warning;
    const emergency = data.emergency || {};

    const locName = i18n.getStationName(loc.id, loc.name);

    // Banner for stale or last known data
    let bannerHtml = '';
    if (dataState === 'LAST_KNOWN') {
      const cachedTime = cachedAtStr ? new Date(cachedAtStr).toLocaleTimeString() : (data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : '');
      bannerHtml = `
        <div class="mb-4 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-sm flex items-start gap-3" role="alert">
          <svg class="w-5 h-5 text-amber-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
          <div>
            <div class="font-bold text-amber-300">${i18n.t('emergency.last_known_banner')}</div>
            <div class="text-xs text-amber-300/80 mt-1">Last retrieved: ${cachedTime || 'Previously cached'}</div>
          </div>
        </div>
      `;
    } else if (pred && pred.freshness_status === 'STALE') {
      bannerHtml = `
        <div class="mb-4 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-sm flex items-start gap-3" role="alert">
          <svg class="w-5 h-5 text-amber-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          <div>
            <div class="font-bold text-amber-300">${i18n.t('emergency.stale_banner')}</div>
          </div>
        </div>
      `;
    }

    // Prediction Risk Card
    let riskHtml = '';
    if (pred && pred.risk_level) {
      let riskColor = 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400';
      let riskLabel = i18n.t('risk.low');
      const rLevel = pred.risk_level.toUpperCase();

      if (rLevel === 'CRITICAL') {
        riskColor = 'border-purple-500/40 bg-purple-900/30 text-purple-300';
        riskLabel = i18n.t('risk.critical');
      } else if (rLevel === 'HIGH') {
        riskColor = 'border-rose-500/40 bg-rose-900/30 text-rose-300';
        riskLabel = i18n.t('risk.high');
      } else if (rLevel === 'MODERATE') {
        riskColor = 'border-amber-500/40 bg-amber-900/30 text-amber-300';
        riskLabel = i18n.t('risk.moderate');
      }

      const updatedTime = pred.prediction_time ? new Date(pred.prediction_time).toLocaleString() : 'N/A';
      const validUntil = pred.valid_until ? new Date(pred.valid_until).toLocaleString() : 'N/A';

      riskHtml = `
        <div class="rounded-2xl border p-5 ${riskColor} shadow-lg mb-4">
          <div class="text-xs uppercase tracking-wider font-semibold opacity-75 mb-1">${i18n.t('homepage.current_risk')} (ML Estimate)</div>
          <div class="text-3xl font-extrabold tracking-tight mb-2" id="emergency-risk-title">${riskLabel}</div>
          <div class="text-xs opacity-80 space-y-1">
            <div>${i18n.t('common.updated')}: <span class="font-mono">${updatedTime}</span></div>
            <div>${i18n.t('common.valid_until')}: <span class="font-mono">${validUntil}</span></div>
            ${pred.prediction_id ? `<div class="font-mono text-[10px] opacity-60">ID: ${pred.prediction_id}</div>` : ''}
          </div>
        </div>
      `;
    } else {
      riskHtml = `
        <div class="rounded-2xl border border-slate-700 bg-slate-800/60 p-5 text-slate-300 mb-4">
          <div class="text-xs uppercase tracking-wider font-semibold text-slate-400 mb-1">${i18n.t('homepage.current_risk')}</div>
          <div class="text-lg font-bold text-slate-300">${i18n.t('emergency.partial_prediction_failed')}</div>
        </div>
      `;
    }

    // Action Card
    let actionHtml = '';
    if (action && action.message) {
      actionHtml = `
        <div class="rounded-2xl border border-slate-700 bg-slate-800/80 p-5 text-slate-100 shadow-md mb-4">
          <div class="text-xs uppercase tracking-wider font-semibold text-sky-400 mb-1">${i18n.t('homepage.what_to_do')}</div>
          <div class="text-base font-semibold leading-snug">${action.message}</div>
        </div>
      `;
    }

    // Official Warning Card
    let warningHtml = '';
    if (warning) {
      let warnBadge = 'bg-slate-700 text-slate-300';
      if (warning.status === 'ACTIVE') warnBadge = 'bg-rose-500/20 text-rose-300 border-rose-500/40';
      else if (warning.status === 'EXPIRED') warnBadge = 'bg-amber-500/20 text-amber-300 border-amber-500/40';

      warningHtml = `
        <div class="rounded-2xl border border-slate-700 bg-slate-800/80 p-5 text-slate-100 shadow-md mb-4">
          <div class="flex items-center justify-between mb-2">
            <div class="text-xs uppercase tracking-wider font-semibold text-amber-400">${i18n.t('official.warning_title')}</div>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-bold border ${warnBadge}">${warning.status}</span>
          </div>
          <div class="text-lg font-bold text-slate-100 mb-1">${warning.title || i18n.t('official.no_warning')}</div>
          ${warning.message ? `<div class="text-sm text-slate-300 mb-3">${warning.message}</div>` : ''}
          <div class="text-xs text-slate-400 space-y-1">
            <div>${i18n.t('official.issued_by')}: <span class="text-slate-200">${warning.source_name || 'DMC / Irrigation Dept'}</span></div>
            ${warning.issued_at ? `<div>${i18n.t('official.issued_at')}: <span class="font-mono text-slate-300">${new Date(warning.issued_at).toLocaleString()}</span></div>` : ''}
            ${warning.source_url ? `<a href="${warning.source_url}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 text-sky-400 hover:underline mt-2 font-semibold text-xs">${i18n.t('official.view_source')} &rarr;</a>` : ''}
          </div>
        </div>
      `;
    } else {
      warningHtml = `
        <div class="rounded-2xl border border-slate-700 bg-slate-800/60 p-5 text-slate-300 mb-4">
          <div class="text-xs uppercase tracking-wider font-semibold text-slate-400 mb-1">${i18n.t('official.warning_title')}</div>
          <div class="text-sm text-slate-300">${i18n.t('emergency.partial_warning_failed')}</div>
        </div>
      `;
    }

    // Emergency DMC 117 Card
    const hotlineHtml = `
      <div class="rounded-2xl border border-rose-500/50 bg-gradient-to-br from-rose-950/60 to-rose-900/30 p-5 text-rose-100 shadow-xl mb-4">
        <div class="text-xs uppercase tracking-wider font-semibold text-rose-400 mb-1">${i18n.t('safety.emergency_hotline')}</div>
        <div class="text-xl font-black text-white mb-2">Disaster Management Centre (DMC)</div>
        <div class="text-xs text-rose-200/80 mb-4">${emergency.safety_guidance || i18n.t('homepage.dmc_contact')}</div>
        <a href="tel:117" class="inline-flex items-center justify-center w-full py-3 px-6 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-black text-lg shadow-lg active:scale-95 transition-all gap-2" role="button" aria-label="Call DMC Hotline 117">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1.001 1.001 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
          CALL DMC 117
        </a>
      </div>
    `;

    // Controls & Retry
    const controlsHtml = `
      <div class="flex items-center justify-between gap-3 pt-2">
        <button id="emergency-retry-btn" class="flex-1 py-3 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 font-bold text-sm flex items-center justify-center gap-2 active:scale-95 transition-all">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
          ${i18n.t('common.retry')}
        </button>
      </div>
    `;

    container.innerHTML = `
      <div class="max-w-md mx-auto p-4 sm:p-6 text-left">
        <!-- Header Location Header -->
        <div class="flex items-center justify-between mb-4">
          <div>
            <div class="text-xs uppercase tracking-wider text-slate-400 font-bold">${i18n.t('homepage.select_area')}</div>
            <div class="text-2xl font-black text-white" id="emergency-location-title">${locName}</div>
            <div class="text-xs text-slate-400 font-medium">${loc.district || ''} District, ${loc.province || ''}</div>
          </div>
          <div id="emergency-network-badge"></div>
        </div>

        ${bannerHtml}
        ${riskHtml}
        ${actionHtml}
        ${warningHtml}
        ${hotlineHtml}
        ${controlsHtml}
      </div>
    `;

    this.renderNetworkBadge();

    const retryBtn = document.getElementById('emergency-retry-btn');
    if (retryBtn) {
      retryBtn.addEventListener('click', () => this.refreshCurrentLocation());
    }
  }

  renderUnavailableUI(locationId, requestId) {
    if (requestId !== this.activeRequestId) return;

    const container = document.getElementById(this.containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="max-w-md mx-auto p-6 text-left">
        <div class="flex items-center justify-between mb-4">
          <div>
            <div class="text-xs uppercase tracking-wider text-slate-400 font-bold">${i18n.t('homepage.select_area')}</div>
            <div class="text-xl font-bold text-white">${locationId}</div>
          </div>
          <div id="emergency-network-badge"></div>
        </div>

        <!-- Explicit Unavailable Card - NO FAKE LOW RISK -->
        <div class="rounded-2xl border border-rose-500/40 bg-rose-950/30 p-6 text-rose-100 mb-6">
          <svg class="w-10 h-10 text-rose-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
          <div class="text-lg font-black text-rose-200 mb-2">${i18n.t('emergency.unavailable_title')}</div>
          <div class="text-sm text-rose-300/80 mb-4">${i18n.t('emergency.unavailable_msg')}</div>
        </div>

        <!-- DMC 117 Hotline -->
        <div class="rounded-2xl border border-rose-500/50 bg-rose-900/30 p-5 text-rose-100 mb-6">
          <div class="text-xs uppercase tracking-wider font-semibold text-rose-400 mb-1">${i18n.t('safety.emergency_hotline')}</div>
          <div class="text-lg font-bold text-white mb-3">Disaster Management Centre</div>
          <a href="tel:117" class="inline-flex items-center justify-center w-full py-3 px-6 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-black text-lg shadow-lg active:scale-95 transition-all gap-2" role="button">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1.001 1.001 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
            CALL DMC 117
          </a>
        </div>

        <button id="emergency-retry-btn" class="w-full py-3 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 font-bold text-sm flex items-center justify-center gap-2 active:scale-95 transition-all">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
          ${i18n.t('common.retry')}
        </button>
      </div>
    `;

    this.renderNetworkBadge();

    const retryBtn = document.getElementById('emergency-retry-btn');
    if (retryBtn) {
      retryBtn.addEventListener('click', () => this.refreshCurrentLocation());
    }
  }
}
