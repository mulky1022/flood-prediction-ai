/**
 * Live Dashboard Controller for Sri Lanka FloodWatch — Phase 6 Redesign
 * Consumes canonical prediction, risk, and action from Unified Prediction API.
 */

import { api } from './api.js';
import { common } from './common.js';
import { MAP_CONFIG, isValidCoord, setupTileLayer, addBoundaryLayer, createStationDivIcon } from './map_utils.js';

let allLocations = [];
let currentLocationId = 1;
let dashboardRequestId = 0;
let refreshInterval = null;
let countdownSeconds = 300; // 5 minutes

// Mini GIS Map Variables
let miniMap = null;
let miniMapMarkersGroup = null;
let miniMapStationDataMap = new Map();

document.addEventListener('DOMContentLoaded', async () => {
  common.initHeader('live-dashboard');
  
  // Resolve location via central state (URL -> localStorage -> default ID 1)
  currentLocationId = common.getSelectedLocationId(1);

  initDashboardMiniMap();
  await loadLocations();
  await updateDashboardData(currentLocationId);
  await loadRecentPredictions();
  
  startAutoRefresh();

  // Retry button handler for error state
  const btnRetry = document.getElementById('btnRetryDashboard');
  if (btnRetry) {
    btnRetry.onclick = () => updateDashboardData(currentLocationId);
  }

  // Listen for global location change events
  window.addEventListener('floodwatch:location_changed', (e) => {
    if (e.detail && e.detail.location_id && e.detail.location_id !== currentLocationId) {
      currentLocationId = e.detail.location_id;
      const selectEl = document.getElementById('locationSelect');
      if (selectEl) selectEl.value = String(currentLocationId);
      updateDashboardData(currentLocationId);
    }
  });

  // Listen for global language change events
  window.addEventListener('floodwatch:language_changed', () => {
    populateLocationDropdown(allLocations);
    updateDashboardData(currentLocationId);
  });
});

/**
 * Initialize Geographic Leaflet Mini-Map for Dashboard Preview
 */
function initDashboardMiniMap() {
  const container = document.getElementById('dashboardMiniMap');
  if (!container) return;

  try {
    miniMap = L.map('dashboardMiniMap', {
      center: MAP_CONFIG.DEFAULT_CENTER,
      zoom: MAP_CONFIG.DEFAULT_ZOOM_MINI,
      minZoom: MAP_CONFIG.MIN_ZOOM,
      maxZoom: MAP_CONFIG.MAX_ZOOM,
      zoomControl: false,
      attributionControl: false
    });

    setupTileLayer(miniMap);
    addBoundaryLayer(miniMap);
    miniMapMarkersGroup = L.layerGroup().addTo(miniMap);

    // Initial fit to Sri Lanka bounds with padding
    miniMap.fitBounds(MAP_CONFIG.SRI_LANKA_BOUNDS, { padding: [15, 15] });

    setTimeout(() => {
      if (miniMap) miniMap.invalidateSize();
    }, 250);

    window.addEventListener('resize', () => {
      if (miniMap) miniMap.invalidateSize();
    });
  } catch (err) {
    console.error('[Dashboard] Error initializing mini GIS map:', err);
  }
}

function populateLocationDropdown(locations) {
  const selectEl = document.getElementById('locationSelect');
  if (!selectEl || !locations.length) return;
  selectEl.innerHTML = '';
  locations.forEach(loc => {
    const opt = document.createElement('option');
    opt.value = loc.id;
    const locName = common.i18n ? common.i18n.getLocationName(loc) : loc.place_name;
    opt.textContent = `${loc.district} — ${locName}`;
    if (loc.id === currentLocationId) {
      opt.selected = true;
    }
    selectEl.appendChild(opt);
  });
}

/**
 * Load all 33 monitoring stations into selector dropdown and mini-map
 */
async function loadLocations() {
  const selectEl = document.getElementById('locationSelect');
  if (!selectEl) return;

  try {
    const data = await api.getLocations();
    allLocations = data.locations || [];

    populateLocationDropdown(allLocations);

    selectEl.addEventListener('change', (e) => {
      currentLocationId = parseInt(e.target.value, 10);
      common.setSelectedLocationId(currentLocationId, true);
      updateDashboardData(currentLocationId);
    });

    // Setup action buttons with selected location ID
    updateActionLinks(currentLocationId);
    selectEl.addEventListener('change', () => updateActionLinks(currentLocationId));

    // Pre-fetch predictions for mini-map markers
    loadMiniMapPredictions();

  } catch (err) {
    console.error('[Dashboard] Failed to load locations:', err);
    selectEl.innerHTML = '<option value="1">Colombo (Kelani Basin)</option>';
  }
}

function updateActionLinks(id) {
  const viewMapBtn = document.getElementById('btnViewOnMap');
  const viewDetailsBtn = document.getElementById('btnViewDetails');

  if (viewMapBtn) viewMapBtn.onclick = () => window.location.href = `map.html?location_id=${id}`;
  if (viewDetailsBtn) viewDetailsBtn.onclick = () => window.location.href = `district.html?location_id=${id}`;
}

/**
 * Pre-fetch map predictions for mini-map station markers
 */
async function loadMiniMapPredictions() {
  try {
    const res = await api.getMapPredictions();
    if (res && res.predictions) {
      res.predictions.forEach(p => {
        miniMapStationDataMap.set(p.location_id, p);
      });
    }
    renderMiniMapStations(allLocations);
  } catch (e) {
    console.warn('[Dashboard] Could not preload map prediction metrics:', e);
    renderMiniMapStations(allLocations);
  }
}

/**
 * Render dynamic station points on the Sri Lanka Mini Geographic Map
 */
function renderMiniMapStations(locations) {
  if (!miniMap || !miniMapMarkersGroup || !locations.length) return;

  miniMapMarkersGroup.clearLayers();

  const validLocations = locations.filter(loc => isValidCoord(loc.latitude, loc.longitude));

  validLocations.forEach(loc => {
    const isSelected = loc.id === currentLocationId;
    const pred = miniMapStationDataMap.get(loc.id);
    const prob = pred ? (pred.flood_probability_percent !== undefined ? pred.flood_probability_percent / 100 : (pred.flood_probability || 0)) : 0;
    const riskLevel = pred ? (pred.risk_level || (pred.risk ? pred.risk.level : 'LOW')) : 'LOW';
    const riskDetails = common.getRiskDetails(riskLevel, prob);
    const displayName = common.i18n ? common.i18n.getLocationName(loc) : loc.place_name;

    const icon = createStationDivIcon(riskDetails, isSelected, true);
    const marker = L.marker([parseFloat(loc.latitude), parseFloat(loc.longitude)], { icon });

    marker.bindTooltip(`
      <div class="flex items-center gap-1.5 font-sans">
        <span class="w-2 h-2 rounded-full" style="background-color: ${riskDetails.dotColor}"></span>
        <span class="font-semibold">${displayName}</span>
        <span class="text-xs" style="color: ${riskDetails.dotColor}">(${common.formatNumber(prob * 100, 0)}%)</span>
      </div>
    `, {
      direction: 'top',
      offset: [0, -10],
      className: 'leaflet-tooltip-dark'
    });

    marker.on('click', () => {
      window.selectLocation(loc.id);
    });

    miniMapMarkersGroup.addLayer(marker);
  });
}

// Global selector bridge for station interaction
window.selectLocation = (id) => {
  const selectEl = document.getElementById('locationSelect');
  if (selectEl) {
    selectEl.value = id;
    selectEl.dispatchEvent(new Event('change'));
  }
};

/**
 * Fetch and bind all telemetry & prediction data for selected location
 * Enforces race-condition protection and location identity verification.
 */
async function updateDashboardData(locationId) {
  // 1. Increment request counter to prevent out-of-order race conditions
  const currentRequestId = ++dashboardRequestId;
  
  showState('LOADING');
  updateActionLinks(locationId);

  try {
    // 2. Fetch canonical current prediction, weather observations, and official warnings concurrently
    const [predictionRes, locationRes, weatherRes, officialWarningRes] = await Promise.all([
      api.getCurrentPrediction(locationId).catch(err => ({ error: err })),
      api.getLocation(locationId).catch(err => null),
      api.getWeather(locationId).catch(err => null),
      api.getOfficialWarning(locationId).catch(err => null)
    ]);

    // 3. Race condition guard: ignore stale responses if location selection changed during fetch
    if (currentRequestId !== dashboardRequestId) {
      console.warn(`[Dashboard] Ignoring stale response for request ${currentRequestId} (active request: ${dashboardRequestId})`);
      return;
    }

    // 4. Handle prediction fetch errors
    if (predictionRes && predictionRes.error) {
      const err = predictionRes.error;
      const errMsg = (err.message || '').toLowerCase();
      
      if (errMsg.includes('404') || errMsg.includes('not found') || errMsg.includes('location_not_found')) {
        const locName = (locationRes && (common.i18n ? common.i18n.getLocationName(locationRes) : locationRes.place_name)) || `Location ID ${locationId}`;
        showState('MISSING', { locationName: locName });
      } else {
        showState('ERROR', { message: err.message || 'Unable to connect to prediction service.' });
      }
      return;
    }

    // 5. Data integrity verification: ensure returned prediction location matches requested location
    if (predictionRes && predictionRes.location) {
      const returnedLocId = parseInt(predictionRes.location.location_id, 10);
      if (returnedLocId !== parseInt(locationId, 10)) {
        console.error(`[Dashboard Integrity Error] Location ID mismatch! Requested: ${locationId}, Returned: ${returnedLocId}`);
        showState('ERROR', { message: `Data integrity error: Received data for location ${returnedLocId} when requesting ${locationId}.` });
        return;
      }
    }

    // 6. Check freshness status
    const isStale = predictionRes.is_stale || predictionRes.status === 'STALE';

    // 7. Render canonical dashboard content and official government warning
    renderDashboardView(predictionRes, locationRes, weatherRes, officialWarningRes, isStale);
    renderMiniMapStations(allLocations);

    // Show appropriate state
    showState(isStale ? 'STALE' : 'CURRENT');

    // Reset auto-refresh countdown
    countdownSeconds = 300;

  } catch (err) {
    if (currentRequestId === dashboardRequestId) {
      console.error('[Dashboard] Error updating dashboard:', err);
      showState('ERROR', { message: err.message || 'Unexpected error loading prediction.' });
    }
  }
}

/**
 * Manage explicit dashboard state visibility (LOADING, ERROR, MISSING, STALE, CURRENT)
 */
function showState(stateName, meta = {}) {
  const loadingEl = document.getElementById('dashboardLoadingState');
  const errorEl = document.getElementById('dashboardErrorState');
  const missingEl = document.getElementById('dashboardMissingState');
  const staleEl = document.getElementById('dashboardStaleBanner');
  const contentEl = document.getElementById('dashboardContentArea');

  // Hide all state banners by default
  if (loadingEl) loadingEl.classList.add('hidden');
  if (errorEl) errorEl.classList.add('hidden');
  if (missingEl) missingEl.classList.add('hidden');
  if (staleEl) staleEl.classList.add('hidden');

  const loadingMsg = document.getElementById('loadingStateMessage');
  const errorMsg = document.getElementById('errorMessageText');
  const missingText = document.getElementById('missingStateText');

  const i18n = common.i18n;

  if (stateName === 'LOADING') {
    if (contentEl) contentEl.classList.add('opacity-50', 'pointer-events-none');
    if (loadingEl) {
      loadingEl.classList.remove('hidden');
      if (loadingMsg) loadingMsg.textContent = i18n ? i18n.t('common.loading') : `Checking current flood risk for location...`;
    }
  } else if (stateName === 'ERROR') {
    if (contentEl) contentEl.classList.add('hidden');
    if (errorEl) {
      errorEl.classList.remove('hidden');
      if (errorMsg) errorMsg.textContent = meta.message || (i18n ? i18n.t('state.error_banner') : 'The prediction server could not be reached.');
    }
  } else if (stateName === 'MISSING') {
    if (contentEl) contentEl.classList.add('hidden');
    if (missingEl) {
      missingEl.classList.remove('hidden');
      if (missingText) missingText.textContent = i18n ? i18n.t('state.missing_banner') : `No current flood prediction is available for ${meta.locationName || 'the selected location'}.`;
    }
  } else if (stateName === 'STALE') {
    if (contentEl) contentEl.classList.remove('hidden', 'opacity-50', 'pointer-events-none');
    if (staleEl) {
      staleEl.classList.remove('hidden');
      const staleText = document.getElementById('staleBannerText');
      if (staleText) {
        staleText.textContent = i18n ? i18n.t('state.stale_banner') : `This prediction may be outdated. Next update cycle pending.`;
      }
    }
  } else if (stateName === 'CURRENT') {
    if (contentEl) contentEl.classList.remove('hidden', 'opacity-50', 'pointer-events-none');
  }
}

/**
 * Render the Canonical Dashboard View from Phase 3/5 API Response
 */
function renderDashboardView(predRes, locationRes, weatherRes, officialWarningRes, isStale) {
  const loc = predRes.location || locationRes || {};
  const risk = predRes.risk || { level: 'LOW', score: 0.0, flood_probability_percent: 0.0 };
  const action = predRes.action || { code: 'SAFE', message: 'Normal conditions. No immediate flood risk detected.' };
  const cond = predRes.conditions || {};
  const currentWx = (weatherRes && weatherRes.current) ? weatherRes.current : {};
  const rainfallWx = (weatherRes && weatherRes.rainfall) ? weatherRes.rainfall : {};

  const i18n = common.i18n;

  // Localize Static Section Headings and Labels
  if (i18n) {
    const lblWarnTitle = document.getElementById('lblOfficialWarningTitle');
    if (lblWarnTitle) lblWarnTitle.innerHTML = `<span class="material-symbols-outlined text-[18px]">campaign</span> ${i18n.t('official.warning_title').toUpperCase()}`;
    const lblNoticeTitle = document.getElementById('lblNoticeTitle');
    if (lblNoticeTitle) lblNoticeTitle.textContent = i18n.t('official.notice_title');
    const lblDisclaimer = document.getElementById('lblOfficialDisclaimer');
    if (lblDisclaimer) lblDisclaimer.textContent = i18n.t('official.disclaimer');
    const lblSafetyTitle = document.getElementById('lblSafetyTitle');
    if (lblSafetyTitle) lblSafetyTitle.textContent = i18n.t('safety.title');
    const lblSafetySubtitle = document.getElementById('lblSafetySubtitle');
    if (lblSafetySubtitle) lblSafetySubtitle.textContent = i18n.t('safety.subtitle');
    const lblCallDMC117 = document.getElementById('lblCallDMC117');
    if (lblCallDMC117) lblCallDMC117.textContent = i18n.t('safety.dmc_117');
    const lblTip1 = document.getElementById('lblSafetyTip1');
    if (lblTip1) lblTip1.textContent = i18n.t('safety.tip1');
    const lblTip2 = document.getElementById('lblSafetyTip2');
    if (lblTip2) lblTip2.textContent = i18n.t('safety.tip2');
    const lblTip3 = document.getElementById('lblSafetyTip3');
    if (lblTip3) lblTip3.textContent = i18n.t('safety.tip3');
    const lblTip4 = document.getElementById('lblSafetyTip4');
    if (lblTip4) lblTip4.textContent = i18n.t('safety.tip4');
    const lblViewSource = document.getElementById('lblViewOfficialSource');
    if (lblViewSource) lblViewSource.textContent = i18n.t('official.view_source');
  }

  // 1. Location Header & Identity
  const nameEl = document.getElementById('heroLocationName');
  const districtEl = document.getElementById('heroLocationDistrict');
  const stationRecordEl = document.getElementById('heroStationRecordId');
  const updatedTimeEl = document.getElementById('heroUpdatedTime');

  const localizedName = i18n ? i18n.getLocationName(loc) : (loc.name || loc.place_name || 'Location');
  if (nameEl) nameEl.textContent = localizedName.toUpperCase();
  if (districtEl) districtEl.textContent = `${i18n ? i18n.t('common.district') : 'District'}: ${loc.district || 'Sri Lanka'}`;
  if (stationRecordEl) stationRecordEl.textContent = `${i18n ? i18n.t('common.station_id') : 'Station ID'}: ${loc.record_id || `LK-LOC-${String(loc.location_id || currentLocationId).padStart(3, '0')}`}`;
  if (updatedTimeEl) updatedTimeEl.textContent = `${i18n ? i18n.t('common.updated') : 'Updated'}: ${common.formatTime(predRes.prediction_time)}`;

  // 2. Circular Gauge & Focal Visualizer
  const probPercent = risk.flood_probability_percent !== undefined 
    ? risk.flood_probability_percent 
    : (risk.score ? risk.score * 100 : 0.0);

  const gaugeNumEl = document.getElementById('gaugeProbNumber');
  const gaugeArcEl = document.getElementById('gaugeProbabilityArc');
  const gaugeBadgeEl = document.getElementById('gaugeRiskBadge');
  const gaugeFreshnessEl = document.getElementById('gaugeFreshnessStatus');

  if (gaugeNumEl) gaugeNumEl.textContent = common.formatNumber(probPercent, 2);

  if (gaugeArcEl) {
    const totalLen = 251.32;
    const offset = totalLen - (totalLen * (Math.min(probPercent, 100) / 100));
    gaugeArcEl.style.strokeDasharray = `${totalLen}`;
    gaugeArcEl.style.strokeDashoffset = `${offset}`;

    const riskDetails = common.getRiskDetails(risk.level, probPercent / 100);
    gaugeArcEl.setAttribute('stroke', riskDetails.dotColor);
  }

  if (gaugeBadgeEl) {
    const riskDetails = common.getRiskDetails(risk.level, probPercent / 100);
    gaugeBadgeEl.className = `mt-1 flex items-center gap-1.5 px-2.5 py-0.5 rounded ${riskDetails.badgeBg}`;
    gaugeBadgeEl.innerHTML = `
      <span class="w-2 h-2 rounded-full" style="background-color: ${riskDetails.dotColor}"></span>
      <span class="font-label-md text-label-md font-bold uppercase tracking-wider">${riskDetails.label}</span>
    `;
  }

  if (gaugeFreshnessEl) {
    gaugeFreshnessEl.textContent = isStale ? (i18n ? i18n.t('state.stale') : 'STALE') : (i18n ? i18n.t('state.current') : 'CURRENT');
    gaugeFreshnessEl.className = `bg-surface-container px-1.5 py-0.5 rounded font-semibold ${isStale ? 'text-amber-400' : 'text-emerald-400'}`;
  }

  // 3. Primary Risk Card
  const riskHeaderEl = document.getElementById('riskLocationHeader');
  const primaryRiskLevelEl = document.getElementById('primaryRiskLevel');
  const primaryRiskBadgeEl = document.getElementById('primaryRiskBadge');
  const primaryValidityEl = document.getElementById('primaryValidity');
  const primaryRiskScoreEl = document.getElementById('primaryRiskScore');
  const riskFreshnessTagEl = document.getElementById('riskFreshnessTag');

  if (riskHeaderEl) riskHeaderEl.textContent = localizedName.toUpperCase();

  const riskDetails = common.getRiskDetails(risk.level, probPercent / 100);
  if (primaryRiskLevelEl) {
    primaryRiskLevelEl.textContent = `${riskDetails.label.toUpperCase()}`;
    primaryRiskLevelEl.style.color = riskDetails.dotColor;
  }

  if (primaryRiskBadgeEl) {
    primaryRiskBadgeEl.className = `px-3 py-1 rounded-lg ${riskDetails.badgeBg} text-sm font-bold uppercase tracking-wider flex items-center gap-1.5`;
    primaryRiskBadgeEl.innerHTML = `
      <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${riskDetails.dotColor}"></span>
      <span>${riskDetails.label}</span>
    `;
  }

  if (primaryValidityEl) {
    if (predRes.valid_from && predRes.valid_until) {
      primaryValidityEl.textContent = `${i18n ? i18n.t('common.valid_until') : 'Valid Until'}: ${common.formatTime(predRes.valid_until)}`;
    } else {
      primaryValidityEl.textContent = `${i18n ? i18n.t('common.valid_until') : 'Valid'}: Next 12 Hours`;
    }
  }

  if (primaryRiskScoreEl) {
    primaryRiskScoreEl.textContent = `${common.formatNumber(risk.score || (probPercent / 100), 4)} (${common.formatNumber(probPercent, 2)}%)`;
  }

  if (riskFreshnessTagEl) {
    riskFreshnessTagEl.textContent = isStale ? (i18n ? i18n.t('state.stale') : 'STALE') : (i18n ? i18n.t('state.current') : 'CURRENT');
    riskFreshnessTagEl.className = `px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${isStale ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}`;
  }

  // 4. Primary Action Card ("WHAT TO DO NOW")
  const actionCodeEl = document.getElementById('primaryActionCode');
  const actionMsgEl = document.getElementById('primaryActionMessage');

  if (actionCodeEl) {
    actionCodeEl.textContent = action.code || 'SAFE';
    if (action.code === 'EVACUATE') {
      actionCodeEl.className = 'px-2.5 py-0.5 rounded text-xs font-extrabold uppercase tracking-wider bg-rose-600 text-white animate-pulse';
    } else if (action.code === 'PREPARE') {
      actionCodeEl.className = 'px-2.5 py-0.5 rounded text-xs font-extrabold uppercase tracking-wider bg-amber-600 text-white';
    } else if (action.code === 'MONITOR') {
      actionCodeEl.className = 'px-2.5 py-0.5 rounded text-xs font-extrabold uppercase tracking-wider bg-amber-500/20 text-amber-300';
    } else {
      actionCodeEl.className = 'px-2.5 py-0.5 rounded text-xs font-extrabold uppercase tracking-wider bg-emerald-500/20 text-emerald-300';
    }
  }

  if (actionMsgEl) {
    actionMsgEl.textContent = i18n ? i18n.getActionMessage(action.code) : (action.message || 'Normal conditions.');
  }

  // 5. Official Government Warning Card (Phase 13)
  renderOfficialWarningCard(officialWarningRes);

  // 6. Conditions Grid (Live Open-Meteo Telemetry & In-situ Sensing)
  const condRainfallEl = document.getElementById('condRainfall');
  const condWaterLevelEl = document.getElementById('condWaterLevel');
  const condWaterLevelMetaEl = document.getElementById('condWaterLevelMeta');
  const condTrendEl = document.getElementById('condTrend');
  const cardTempEl = document.getElementById('cardTemp');
  const cardHumidityEl = document.getElementById('cardHumidity');

  // Real-time 24h precipitation from Open-Meteo takes priority
  let rainfallVal = 0.0;
  if (rainfallWx.rainfall_24h_forecast_mm !== undefined && rainfallWx.rainfall_24h_forecast_mm !== null) {
    rainfallVal = rainfallWx.rainfall_24h_forecast_mm;
  } else if (rainfallWx.rainfall_24h_mm !== undefined && rainfallWx.rainfall_24h_mm !== null) {
    rainfallVal = rainfallWx.rainfall_24h_mm;
  } else if (currentWx.precipitation_mm !== undefined && currentWx.precipitation_mm !== null && currentWx.precipitation_mm > 0) {
    rainfallVal = currentWx.precipitation_mm;
  } else if (cond.rainfall_mm_24h !== undefined && cond.rainfall_mm_24h > 0) {
    rainfallVal = cond.rainfall_mm_24h;
  } else if (currentWx.precipitation_mm !== undefined && currentWx.precipitation_mm !== null) {
    rainfallVal = currentWx.precipitation_mm;
  } else if (rainfallWx.rainfall_7d_mm) {
    rainfallVal = rainfallWx.rainfall_7d_mm / 7.0;
  } else if (cond.rainfall_mm_24h !== undefined) {
    rainfallVal = cond.rainfall_mm_24h;
  }
  if (condRainfallEl) condRainfallEl.textContent = common.formatNumber(rainfallVal, 1, '0.0');

  // Ambient Weather (Temp & Humidity) from live Open-Meteo observation
  const tempVal = (currentWx.temperature_c !== undefined && currentWx.temperature_c !== null)
    ? currentWx.temperature_c
    : cond.temperature_c;
  if (cardTempEl) cardTempEl.textContent = common.formatNumber(tempVal, 1, '--');

  const humVal = (currentWx.humidity_percent !== undefined && currentWx.humidity_percent !== null)
    ? currentWx.humidity_percent
    : cond.humidity_percent;
  if (cardHumidityEl) cardHumidityEl.textContent = common.formatNumber(humVal, 0, '--');

  // Water Trend based on real rainfall dynamics & stream conditions
  let trendVal = cond.water_level_trend;
  const r7 = rainfallWx.rainfall_7d_mm || 0;
  if (!trendVal || trendVal === 'Steady') {
    if (r7 > 100 || rainfallVal > 20) {
      trendVal = 'Rising';
    } else if (r7 < 20 && rainfallVal < 2) {
      trendVal = 'Falling';
    } else {
      trendVal = 'Steady';
    }
  }
  if (condTrendEl) {
    condTrendEl.textContent = trendVal;
    if (trendVal === 'Rising') {
      condTrendEl.className = 'font-data-display text-2xl text-rose-400 font-bold';
    } else if (trendVal === 'Falling') {
      condTrendEl.className = 'font-data-display text-2xl text-emerald-400 font-bold';
    } else {
      condTrendEl.className = 'font-data-display text-2xl text-on-surface font-bold';
    }
  }

  // Water Level / River Proximity / Discharge
  if (cond.water_level_m !== undefined && cond.water_level_m > 0) {
    if (condWaterLevelEl) condWaterLevelEl.textContent = common.formatNumber(cond.water_level_m, 1, 'N/A');
  } else if (currentWx.river_discharge_m3s !== undefined && currentWx.river_discharge_m3s !== null) {
    if (condWaterLevelEl) condWaterLevelEl.textContent = common.formatNumber(currentWx.river_discharge_m3s, 1, 'N/A');
  } else if (cond.river_discharge_m3s !== undefined && cond.river_discharge_m3s !== null) {
    if (condWaterLevelEl) condWaterLevelEl.textContent = common.formatNumber(cond.river_discharge_m3s, 1, 'N/A');
  } else {
    const distM = (locationRes && locationRes.distance_to_river_m) || (loc && loc.distance_to_river_m);
    if (distM !== undefined && distM !== null) {
      if (condWaterLevelEl) condWaterLevelEl.textContent = common.formatNumber(distM, 0, 'N/A');
      const unitEl = condWaterLevelEl?.nextElementSibling;
      if (unitEl) unitEl.textContent = 'm';
      if (condWaterLevelMetaEl) condWaterLevelMetaEl.textContent = 'Distance to river channel';
    } else {
      if (condWaterLevelEl) condWaterLevelEl.textContent = 'Normal';
    }
  }

  // 7. Secondary Technical Details (Collapsible)
  const statusModelNameEl = document.getElementById('statusModelName');
  const statusModelVersionEl = document.getElementById('statusModelVersion');
  const statusModelFeaturesEl = document.getElementById('statusModelFeatures');
  const statusPredictionIdEl = document.getElementById('statusPredictionId');

  if (statusModelNameEl) statusModelNameEl.textContent = predRes.model_name || 'RandomForestClassifier';
  if (statusModelVersionEl) statusModelVersionEl.textContent = `v${predRes.model_version || '1.0.0'} (Production)`;
  if (statusModelFeaturesEl) statusModelFeaturesEl.textContent = `${predRes.features_used_count || 64} Hydro-Meteo Features`;
  if (statusPredictionIdEl) statusPredictionIdEl.textContent = predRes.prediction_id ? `#${predRes.prediction_id}` : 'Live Engine Output';
}

/**
 * Render Official Government Warning Card (Phase 13)
 */
function renderOfficialWarningCard(warningRes) {
  const stateTagEl = document.getElementById('officialWarningStateTag');
  const titleEl = document.getElementById('officialWarningTitle');
  const msgEl = document.getElementById('officialWarningMessage');
  const authorityEl = document.getElementById('officialWarningAuthority');
  const timeEl = document.getElementById('officialWarningTime');
  const linkEl = document.getElementById('officialWarningSourceLink');
  const cardEl = document.getElementById('officialWarningCard');

  const i18n = common.i18n;

  if (!warningRes || warningRes.state === 'UNAVAILABLE' || warningRes.status === 'error') {
    if (stateTagEl) {
      stateTagEl.textContent = i18n ? i18n.t('official.unavailable') : 'UNAVAILABLE';
      stateTagEl.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-rose-500/20 text-rose-400 border border-rose-500/30';
    }
    if (titleEl) titleEl.textContent = i18n ? i18n.t('official.unavailable') : 'Warning Data Unavailable';
    if (msgEl) msgEl.textContent = i18n ? i18n.t('official.unavailable') : 'Official government warning information is temporarily unavailable.';
    if (authorityEl) authorityEl.textContent = 'Authority: Disaster Management Centre (DMC)';
    if (timeEl) timeEl.textContent = '';
    if (linkEl) linkEl.classList.add('hidden');
    if (cardEl) cardEl.className = 'lg:col-span-12 card flex flex-col justify-between gap-4 border-l-4 border-l-rose-500 bg-rose-950/20';
    return;
  }

  if (warningRes.state === 'ACTIVE' && warningRes.warning) {
    const w = warningRes.warning;
    if (stateTagEl) {
      stateTagEl.textContent = `${w.severity || 'ACTIVE'} WARNING`;
      stateTagEl.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-amber-500/30 text-amber-300 border border-amber-500/50 animate-pulse';
    }
    if (titleEl) titleEl.textContent = w.title || (i18n ? i18n.t('official.warning_title') : 'Official Government Warning');
    if (msgEl) msgEl.textContent = w.message || '';
    if (authorityEl) authorityEl.textContent = `${i18n ? i18n.t('official.issued_by') : 'Authority'}: ${w.source_name || 'Disaster Management Centre (DMC)'}`;
    if (timeEl) timeEl.textContent = `${i18n ? i18n.t('official.issued_at') : 'Issued'}: ${common.formatTime(w.issued_at)}`;

    if (linkEl && w.source_url) {
      linkEl.href = w.source_url;
      linkEl.classList.remove('hidden');
    } else if (linkEl) {
      linkEl.classList.add('hidden');
    }
    if (cardEl) cardEl.className = 'lg:col-span-12 card flex flex-col justify-between gap-4 border-l-4 border-l-amber-500 bg-amber-950/30';

  } else if (warningRes.state === 'EXPIRED' && warningRes.warning) {
    const w = warningRes.warning;
    if (stateTagEl) {
      stateTagEl.textContent = i18n ? i18n.t('official.expired') : 'EXPIRED';
      stateTagEl.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-slate-500/20 text-slate-400 border border-slate-500/30';
    }
    if (titleEl) titleEl.textContent = w.title || (i18n ? i18n.t('official.expired') : 'Warning Expired');
    if (msgEl) msgEl.textContent = i18n ? i18n.t('official.expired') : 'This official government warning has expired.';
    if (authorityEl) authorityEl.textContent = `${i18n ? i18n.t('official.issued_by') : 'Authority'}: ${w.source_name || 'DMC'}`;
    if (timeEl) timeEl.textContent = `${i18n ? i18n.t('official.valid_until') : 'Expired'}: ${common.formatTime(w.valid_until)}`;
    if (linkEl) linkEl.classList.add('hidden');
    if (cardEl) cardEl.className = 'lg:col-span-12 card flex flex-col justify-between gap-4 border-l-4 border-l-slate-500 bg-slate-900/20';

  } else {
    // NO_ACTIVE_WARNING
    if (stateTagEl) {
      stateTagEl.textContent = i18n ? i18n.t('official.no_warning') : 'NO ACTIVE WARNING';
      stateTagEl.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
    }
    if (titleEl) titleEl.textContent = i18n ? i18n.t('official.no_warning') : 'No Active Official Warning';
    if (msgEl) msgEl.textContent = i18n ? i18n.t('official.no_warning') : 'No active official government warning has been reported for this area.';
    if (authorityEl) authorityEl.textContent = 'Authority: Disaster Management Centre (DMC)';
    if (timeEl) timeEl.textContent = '';
    if (linkEl) linkEl.classList.add('hidden');
    if (cardEl) cardEl.className = 'lg:col-span-12 card flex flex-col justify-between gap-4 border-l-4 border-l-emerald-500 bg-emerald-950/10';
  }
}

/**
 * Load sequential recent predictions feed for sidebar stream
 */
async function loadRecentPredictions() {
  const feedEl = document.getElementById('recentPredictionsFeed');
  if (!feedEl) return;

  try {
    const sampleIds = [1, 4, 7, 10, 13];
    const results = await Promise.all(
      sampleIds.map(async (id) => {
        try {
          const loc = allLocations.find(l => l.id === id) || { place_name: `Station ${id}`, district: 'Sri Lanka' };
          const pred = await api.getCurrentPrediction(id);
          return { loc, pred, time: common.formatTime(pred.prediction_time) };
        } catch (e) {
          return null;
        }
      })
    );

    const validResults = results.filter(r => r && r.pred && r.pred.risk);
    if (!validResults.length) {
      feedEl.innerHTML = '<div class="p-3 text-center text-on-surface-variant font-body-sm">No live feed entries recorded yet.</div>';
      return;
    }

    feedEl.innerHTML = validResults.map(item => {
      const riskLevel = item.pred.risk.level || 'LOW';
      const prob = item.pred.risk.score || 0.0;
      const risk = common.getRiskDetails(riskLevel, prob);
      const probPct = common.formatNumber(item.pred.risk.flood_probability_percent || prob * 100, 2);
      
      return `
        <div class="pt-2 first:pt-0 flex items-center justify-between gap-3 hover:bg-surface-container-low/50 p-2 rounded transition-colors cursor-pointer" onclick="window.selectLocation(${item.loc.id || 1})">
          <div class="flex items-center gap-2">
            <div class="w-2 h-8 rounded" style="background-color: ${risk.dotColor}"></div>
            <div class="flex flex-col">
              <span class="font-headline-sm text-headline-sm text-on-surface">${item.loc.place_name || item.loc.district}</span>
              <span class="font-data-timestamp text-data-timestamp text-outline">${item.loc.district || 'Basin'} • Phase 5 Engine</span>
            </div>
          </div>
          <div class="flex flex-col items-end gap-1">
            <div class="flex items-center gap-1.5">
              <span class="font-data-metric text-data-metric font-bold text-on-surface">${probPct}%</span>
              <span class="px-1.5 py-0.5 rounded font-label-md text-label-md font-bold ${risk.badgeBg}">${risk.shortLabel}</span>
            </div>
            <span class="font-data-timestamp text-data-timestamp text-on-surface-variant">${item.time}</span>
          </div>
        </div>
      `;
    }).join('');

  } catch (err) {
    console.error('[Dashboard] Failed to load recent predictions:', err);
  }
}

/**
 * Start 5-minute auto-refresh cycle
 */
function startAutoRefresh() {
  if (refreshInterval) clearInterval(refreshInterval);

  const timerEl = document.getElementById('pipelineCountdown');
  
  refreshInterval = setInterval(() => {
    countdownSeconds--;
    if (countdownSeconds <= 0) {
      updateDashboardData(currentLocationId);
      loadRecentPredictions();
      countdownSeconds = 300;
    }

    if (timerEl) {
      const mins = String(Math.floor(countdownSeconds / 60)).padStart(2, '0');
      const secs = String(countdownSeconds % 60).padStart(2, '0');
      timerEl.textContent = `${mins}:${secs}`;
    }
  }, 1000);
}
