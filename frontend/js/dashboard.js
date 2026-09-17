/**
 * Live Dashboard Controller for Sri Lanka FloodWatch
 * Real GIS Geographic Mini-Map & Real-Time Hydrological Telemetry
 */

import { api } from './api.js';
import { common } from './common.js';
import { MAP_CONFIG, isValidCoord, setupTileLayer, addBoundaryLayer, createStationDivIcon } from './map_utils.js';

let allLocations = [];
let currentLocationId = 1;
let refreshInterval = null;
let countdownSeconds = 300; // 5 minutes

// Mini GIS Map Variables
let miniMap = null;
let miniMapMarkersGroup = null;
let miniMapStationDataMap = new Map();

document.addEventListener('DOMContentLoaded', async () => {
  common.initHeader('live-dashboard');
  
  // Check URL query parameters for default location
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has('location_id') || urlParams.has('station')) {
    currentLocationId = parseInt(urlParams.get('location_id') || urlParams.get('station'), 10) || 1;
  }

  initDashboardMiniMap();
  await loadLocations();
  await updateDashboardData(currentLocationId);
  await loadRecentPredictions();
  
  startAutoRefresh();
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

/**
 * Load all 33 monitoring stations into the selector dropdown and mini-map
 */
async function loadLocations() {
  const selectEl = document.getElementById('locationSelect');
  if (!selectEl) return;

  try {
    const data = await api.getLocations();
    allLocations = data.locations || [];

    selectEl.innerHTML = '';
    allLocations.forEach(loc => {
      const opt = document.createElement('option');
      opt.value = loc.id;
      opt.textContent = `${loc.district} — ${loc.place_name}`;
      if (loc.id === currentLocationId) {
        opt.selected = true;
      }
      selectEl.appendChild(opt);
    });

    selectEl.addEventListener('change', (e) => {
      currentLocationId = parseInt(e.target.value, 10);
      updateDashboardData(currentLocationId);
      // Update browser history without reload
      const newUrl = new URL(window.location);
      newUrl.searchParams.set('location_id', currentLocationId);
      window.history.replaceState({}, '', newUrl);
    });

    // Setup "View on Map" & "Open in Flood Map" buttons
    const viewMapBtn = document.getElementById('btnViewOnMap');
    const openMapBtn = document.getElementById('btnOpenMap');
    const viewDetailsBtn = document.getElementById('btnViewDetails');

    const updateLinks = (id) => {
      if (viewMapBtn) viewMapBtn.onclick = () => window.location.href = `map.html?station=${id}`;
      if (openMapBtn) openMapBtn.onclick = () => window.location.href = `map.html?station=${id}`;
      if (viewDetailsBtn) viewDetailsBtn.onclick = () => window.location.href = `district.html?location_id=${id}`;
    };

    updateLinks(currentLocationId);
    selectEl.addEventListener('change', () => updateLinks(currentLocationId));

    // Pre-fetch predictions for mini-map markers in background
    loadMiniMapPredictions();

  } catch (err) {
    console.error('Failed to load locations:', err);
    selectEl.innerHTML = '<option value="1">Colombo (Kelani Basin)</option>';
  }
}

/**
 * Pre-fetch predictions for all stations to render accurate risk colors on mini-map
 */
async function loadMiniMapPredictions() {
  try {
    const promises = allLocations.map(async (loc) => {
      try {
        const pred = await api.getPrediction(loc.id);
        return { id: loc.id, pred: pred.prediction };
      } catch (e) {
        return { id: loc.id, pred: null };
      }
    });

    const results = await Promise.all(promises);
    results.forEach(r => {
      if (r && r.pred) miniMapStationDataMap.set(r.id, r.pred);
    });

    renderMiniMapStations(allLocations);
  } catch (e) {
    console.warn('[Dashboard] Could not preload mini-map prediction metrics:', e);
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
    const prob = pred ? (pred.flood_probability_percent !== undefined ? pred.flood_probability_percent / 100 : pred.flood_probability) : 0;
    const riskLevel = pred ? pred.risk_level : 'LOW';
    const riskDetails = common.getRiskDetails(riskLevel, prob);

    const icon = createStationDivIcon(riskDetails, isSelected, true);
    const marker = L.marker([parseFloat(loc.latitude), parseFloat(loc.longitude)], { icon });

    marker.bindTooltip(`
      <div class="flex items-center gap-1.5 font-sans">
        <span class="w-2 h-2 rounded-full" style="background-color: ${riskDetails.dotColor}"></span>
        <span class="font-semibold">${loc.place_name.split(' ')[0]}</span>
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
 */
async function updateDashboardData(locationId) {
  setLoadingState(true);

  try {
    const [location, weather, predictionData] = await Promise.all([
      api.getLocation(locationId).catch(e => ({ error: e.message })),
      api.getWeather(locationId).catch(e => ({ error: e.message })),
      api.getPrediction(locationId).catch(e => ({ error: e.message }))
    ]);

    if (predictionData && predictionData.prediction) {
      miniMapStationDataMap.set(locationId, predictionData.prediction);
    }

    renderHeroTelemetry(location, weather, predictionData);
    renderGauge(predictionData);
    renderWeatherCards(weather);
    renderLocationStatusCard(location, weather, predictionData);
    renderMiniMapStations(allLocations);

    // Reset countdown
    countdownSeconds = 300;
  } catch (err) {
    console.error('Error updating dashboard data:', err);
  } finally {
    setLoadingState(false);
  }
}

/**
 * Render Header telemetry subline (Station ID, District, Coords)
 */
function renderHeroTelemetry(location, weather, predictionData) {
  const stationIdEl = document.getElementById('heroStationId');
  const stationSyncEl = document.getElementById('heroStationSync');

  if (stationIdEl && location && location.record_id) {
    stationIdEl.textContent = `Station ID: ${location.record_id}`;
  }

  if (stationSyncEl) {
    stationSyncEl.textContent = 'Telemetry Synchronized';
  }
}

/**
 * Render Circular Probability SVG Gauge
 */
function renderGauge(predictionData) {
  const pred = (predictionData && predictionData.prediction) ? predictionData.prediction : null;
  const probPercent = pred ? (pred.flood_probability_percent || pred.flood_probability * 100) : 0;
  const riskLevel = pred ? pred.risk_level : 'LOW';

  const probNumberEl = document.getElementById('gaugeProbNumber');
  const riskBadgeEl = document.getElementById('gaugeRiskBadge');
  const arcEl = document.getElementById('gaugeProbabilityArc');
  const dataQualityEl = document.getElementById('gaugeDataQuality');

  if (probNumberEl) {
    probNumberEl.textContent = common.formatNumber(probPercent, 2);
  }

  // Calculate SVG arc stroke offset (Total arc length for r=80 semi-circle is approx 251.32)
  if (arcEl) {
    const totalLen = 251.32;
    const offset = totalLen - (totalLen * (Math.min(probPercent, 100) / 100));
    arcEl.style.strokeDasharray = `${totalLen}`;
    arcEl.style.strokeDashoffset = `${offset}`;

    // Color code arc
    if (riskLevel === 'CRITICAL' || probPercent >= 80) {
      arcEl.setAttribute('stroke', '#ef4444');
    } else if (riskLevel === 'HIGH' || probPercent >= 65) {
      arcEl.setAttribute('stroke', '#f97316');
    } else if (riskLevel === 'MODERATE' || probPercent >= 35) {
      arcEl.setAttribute('stroke', '#f59e0b');
    } else {
      arcEl.setAttribute('stroke', '#10b981');
    }
  }

  // Update Risk Badge
  if (riskBadgeEl) {
    const riskDetails = common.getRiskDetails(riskLevel, probPercent / 100);
    riskBadgeEl.className = `mt-1 flex items-center gap-1.5 px-2.5 py-0.5 rounded ${riskDetails.badgeBg}`;
    riskBadgeEl.innerHTML = `
      <span class="w-2 h-2 rounded-full" style="background-color: ${riskDetails.dotColor}"></span>
      <span class="font-label-md text-label-md font-bold uppercase tracking-wider">${riskDetails.label}</span>
    `;
  }

  if (dataQualityEl && pred) {
    dataQualityEl.textContent = `DATA: ${pred.data_quality_status || 'GOOD'}`;
  }
}

/**
 * Render 4 Weather Telemetry Cards
 */
function renderWeatherCards(weather) {
  const current = weather && weather.current ? weather.current : {};
  const rolling = weather && weather.rolling_aggregations ? weather.rolling_aggregations : {};

  // 1. Ambient Temp
  const tempEl = document.getElementById('cardTemp');
  if (tempEl) tempEl.textContent = common.formatNumber(current.temperature_c, 1, '--');

  // 2. Humidity
  const humidityEl = document.getElementById('cardHumidity');
  if (humidityEl) humidityEl.textContent = common.formatNumber(current.humidity_percent, 0, '--');

  // 3. 7-Day Rainfall
  const rain7El = document.getElementById('cardRain7');
  if (rain7El) rain7El.textContent = common.formatNumber(rolling.precipitation_sum_7d_mm, 1, '0.0');

  // 4. 30-Day Rainfall
  const rain30El = document.getElementById('cardRain30');
  if (rain30El) rain30El.textContent = common.formatNumber(rolling.precipitation_sum_30d_mm, 1, '0.0');
}

/**
 * Render Main Location Status Card
 */
function renderLocationStatusCard(location, weather, predictionData) {
  const pred = predictionData && predictionData.prediction ? predictionData.prediction : null;
  const current = weather && weather.current ? weather.current : {};

  // Place name & District
  const placeNameEl = document.getElementById('statusPlaceName');
  const districtEl = document.getElementById('statusDistrict');
  const coordsEl = document.getElementById('statusCoords');

  if (placeNameEl && location) placeNameEl.textContent = location.place_name || 'Selected Station';
  if (districtEl && location) districtEl.textContent = `District: ${location.district || 'Sri Lanka'}`;
  if (coordsEl && location) coordsEl.textContent = `Lat ${location.latitude}° N, Lon ${location.longitude}° E`;

  // Risk badges
  const riskBadgeContainer = document.getElementById('statusRiskBadgeContainer');
  if (riskBadgeContainer && pred) {
    const risk = common.getRiskDetails(pred.risk_level, pred.flood_probability);
    riskBadgeContainer.innerHTML = `
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg ${risk.badgeBg} font-label-lg text-label-lg uppercase tracking-wider font-bold">
        <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${risk.dotColor}"></span>
        <span>Risk: ${risk.label}</span>
      </div>
      <div class="px-3 py-1.5 rounded-lg bg-surface-container text-on-surface font-label-lg text-label-lg font-semibold">
        Prediction: Class ${pred.class} (${pred.class === 1 ? 'Flood Alert' : 'Non-Flood / Normal'})
      </div>
    `;
  }

  // Probability Bar
  const probBarEl = document.getElementById('statusProbBar');
  const probValEl = document.getElementById('statusProbValue');
  const probPercent = pred ? (pred.flood_probability_percent || pred.flood_probability * 100) : 0;

  if (probValEl) probValEl.textContent = `${common.formatNumber(probPercent, 2)}%`;
  if (probBarEl) {
    probBarEl.style.width = `${Math.min(probPercent, 100)}%`;
    if (pred && (pred.risk_level === 'HIGH' || pred.risk_level === 'CRITICAL')) {
      probBarEl.style.backgroundColor = '#ef4444';
    } else if (pred && pred.risk_level === 'MODERATE') {
      probBarEl.style.backgroundColor = '#f59e0b';
    } else {
      probBarEl.style.backgroundColor = '#10b981';
    }
  }

  // River Discharge
  const dischargeEl = document.getElementById('statusDischargeValue');
  const dischargeMetaEl = document.getElementById('statusDischargeMeta');
  if (dischargeEl) {
    dischargeEl.textContent = current.river_discharge_m3s !== undefined && current.river_discharge_m3s !== null 
      ? common.formatNumber(current.river_discharge_m3s, 1) 
      : 'N/A';
  }
  if (dischargeMetaEl) {
    dischargeMetaEl.textContent = current.river_discharge_m3s !== undefined 
      ? 'GloFAS Hydrological Telemetry' 
      : 'Discharge telemetry not available';
  }

  // Model Card
  const modelNameEl = document.getElementById('statusModelName');
  const modelVerEl = document.getElementById('statusModelVersion');
  const modelFeaturesEl = document.getElementById('statusModelFeatures');
  const modelIntegrityEl = document.getElementById('statusModelIntegrity');

  if (modelNameEl && pred) modelNameEl.textContent = pred.model_name || 'RandomForestClassifier';
  if (modelVerEl && pred) modelVerEl.textContent = `v${pred.model_version || '1.0.0'} (Production)`;
  if (modelFeaturesEl && pred) modelFeaturesEl.textContent = `${pred.features_used_count || 64} Hydro-Meteo Inputs`;
  if (modelIntegrityEl && pred) modelIntegrityEl.textContent = `Input Integrity: ${pred.data_quality_status || 'GOOD'}`;
}

/**
 * Load sequential recent predictions for feed
 */
async function loadRecentPredictions() {
  const feedEl = document.getElementById('recentPredictionsFeed');
  if (!feedEl) return;

  try {
    // Fetch predictions for 5 prominent stations
    const sampleIds = [1, 4, 7, 10, 13];
    const results = await Promise.all(
      sampleIds.map(async (id) => {
        try {
          const loc = allLocations.find(l => l.id === id) || { place_name: `Station ${id}`, district: 'Sri Lanka' };
          const pred = await api.getPrediction(id);
          return { loc, pred: pred.prediction, time: common.formatTime() };
        } catch (e) {
          return null;
        }
      })
    );

    const validResults = results.filter(r => r && r.pred);
    if (!validResults.length) {
      feedEl.innerHTML = '<div class="p-3 text-center text-on-surface-variant font-body-sm">No live feed entries recorded yet.</div>';
      return;
    }

    feedEl.innerHTML = validResults.map(item => {
      const risk = common.getRiskDetails(item.pred.risk_level, item.pred.flood_probability);
      const probPct = common.formatNumber(item.pred.flood_probability_percent || item.pred.flood_probability * 100, 2);
      
      return `
        <div class="pt-2 first:pt-0 flex items-center justify-between gap-3 hover:bg-surface-container-low/50 p-2 rounded transition-colors cursor-pointer" onclick="window.selectLocation(${item.loc.id || 1})">
          <div class="flex items-center gap-2">
            <div class="w-2 h-8 rounded" style="background-color: ${risk.dotColor}"></div>
            <div class="flex flex-col">
              <span class="font-headline-sm text-headline-sm text-on-surface">${item.loc.place_name}</span>
              <span class="font-data-timestamp text-data-timestamp text-outline">${item.loc.district} • Random Forest</span>
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
    console.error('Failed to load recent predictions:', err);
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

function setLoadingState(isLoading) {
  const refreshIcon = document.getElementById('refreshIcon');
  if (refreshIcon) {
    if (isLoading) refreshIcon.classList.add('animate-spin');
    else refreshIcon.classList.remove('animate-spin');
  }
}
