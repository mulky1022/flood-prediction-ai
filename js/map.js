/**
 * Sri Lanka FloodWatch — Interactive GIS Map Controller — Phase 7
 * Visualizes canonical multi-station predictions, risk levels, and action guidance.
 */

import { api } from './api.js';
import { common } from './common.js';
import { MAP_CONFIG, isValidCoord, setupTileLayer, addBoundaryLayer, createStationDivIcon } from './map_utils.js';

let map = null;
let tileLayer = null;
let boundaryLayer = null;
let markersLayerGroup = null;
let stations = [];
let stationDataMap = new Map();
let markerMap = new Map();
let activeFilter = 'all';
let searchQuery = '';
let selectedStationId = 1;
let mapRequestId = 0;
let currentViewMode = 'canvas'; // 'canvas' or 'table'

document.addEventListener('DOMContentLoaded', async () => {
  common.initHeader('flood-map');

  selectedStationId = common.getSelectedLocationId(1);

  initLeafletMap();
  initMapControls();
  initSearchAndFilters();
  initViewSwitcher();
  await loadMapData();

  // Retry button handler for error state
  const btnRetry = document.getElementById('btnRetryMap');
  if (btnRetry) {
    btnRetry.onclick = () => loadMapData();
  }

  // Listen for language change events
  window.addEventListener('floodwatch:language_changed', () => {
    renderStationMarkers();
    if (selectedStationId) {
      renderStationDetailPanel(selectedStationId);
    }
  });

  // Invalidate Leaflet size after initial layout
  setTimeout(() => {
    if (map) map.invalidateSize();
  }, 250);

  window.addEventListener('resize', () => {
    if (map) map.invalidateSize();
  });
});

/**
 * Display non-blocking banner when tile provider is unavailable
 */
function showMapAlert(message) {
  const existing = document.querySelector('.map-alert-banner');
  if (existing) existing.remove();

  const viewport = document.getElementById('mapViewport');
  if (!viewport) return;

  const banner = document.createElement('div');
  banner.className = 'map-alert-banner';
  banner.innerHTML = `
    <span class="material-symbols-outlined text-[16px] text-amber-400">cloud_off</span>
    <span>${message}</span>
  `;
  viewport.appendChild(banner);
}

/**
 * Initialize Leaflet Geographic Map Engine
 */
function initLeafletMap() {
  const mapContainer = document.getElementById('leafletMap');
  if (!mapContainer) return;

  try {
    map = L.map('leafletMap', {
      center: MAP_CONFIG.DEFAULT_CENTER,
      zoom: MAP_CONFIG.DEFAULT_ZOOM_FULL,
      minZoom: MAP_CONFIG.MIN_ZOOM,
      maxZoom: MAP_CONFIG.MAX_ZOOM,
      zoomControl: false
    });

    tileLayer = setupTileLayer(map, (err) => {
      showMapAlert('Base map tiles unavailable — displaying GIS sensor layer and country boundary.');
    });

    boundaryLayer = addBoundaryLayer(map);
    markersLayerGroup = L.layerGroup().addTo(map);

    map.on('mousemove', (e) => {
      const coordDisplay = document.getElementById('coordDisplay');
      if (coordDisplay && e.latlng) {
        coordDisplay.textContent = `${e.latlng.lat.toFixed(4)}° N, ${e.latlng.lng.toFixed(4)}° E`;
      }
    });

  } catch (err) {
    console.error('[Map Engine] Error initializing Leaflet map:', err);
  }
}

/**
 * Initialize Zoom & Pan Controls
 */
function initMapControls() {
  const zoomInBtn = document.getElementById('zoomInBtn');
  const zoomOutBtn = document.getElementById('zoomOutBtn');
  const resetBtn = document.getElementById('resetViewBtn');
  const recenterBtn = document.getElementById('recenterBtn');
  const refreshBtn = document.getElementById('refreshDataBtn');
  const exportBtn = document.getElementById('exportGeoJsonBtn');

  if (zoomInBtn) zoomInBtn.addEventListener('click', () => { if (map) map.zoomIn(); });
  if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => { if (map) map.zoomOut(); });
  if (resetBtn) resetBtn.addEventListener('click', () => resetMapView());
  
  if (recenterBtn) {
    recenterBtn.addEventListener('click', () => {
      if (map) map.flyTo(MAP_CONFIG.DEFAULT_CENTER, MAP_CONFIG.DEFAULT_ZOOM_FULL, { duration: 0.8 });
    });
  }

  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      const icon = refreshBtn.querySelector('.material-symbols-outlined');
      if (icon) icon.classList.add('animate-spin');
      await loadMapData();
      if (icon) icon.classList.remove('animate-spin');
    });
  }

  if (exportBtn) {
    exportBtn.addEventListener('click', exportStationsGeoJson);
  }
}

/**
 * View Switcher (GIS Canvas vs Accessible Station Table)
 */
function initViewSwitcher() {
  const btnMap = document.getElementById('btnViewMapCanvas');
  const btnTable = document.getElementById('btnViewTableView');
  const canvasSection = document.getElementById('mapCanvasSection');
  const tableSection = document.getElementById('mapTableViewSection');

  if (!btnMap || !btnTable) return;

  btnMap.addEventListener('click', () => {
    currentViewMode = 'canvas';
    btnMap.className = 'px-3 py-1 bg-surface-container-lowest text-on-surface rounded font-label-lg text-label-lg shadow-sm font-bold flex items-center gap-1.5 transition-all';
    btnTable.className = 'px-3 py-1 text-on-surface-variant hover:text-on-surface rounded font-label-lg text-label-lg font-medium flex items-center gap-1.5 transition-all';
    
    if (canvasSection) canvasSection.classList.remove('hidden');
    if (tableSection) tableSection.classList.add('hidden');
    
    setTimeout(() => { if (map) map.invalidateSize(); }, 100);
  });

  btnTable.addEventListener('click', () => {
    currentViewMode = 'table';
    btnTable.className = 'px-3 py-1 bg-surface-container-lowest text-on-surface rounded font-label-lg text-label-lg shadow-sm font-bold flex items-center gap-1.5 transition-all';
    btnMap.className = 'px-3 py-1 text-on-surface-variant hover:text-on-surface rounded font-label-lg text-label-lg font-medium flex items-center gap-1.5 transition-all';
    
    if (canvasSection) canvasSection.classList.add('hidden');
    if (tableSection) tableSection.classList.remove('hidden');
    
    renderStationTable();
  });
}

/**
 * Reset map view bounds
 */
function resetMapView() {
  if (!map) return;
  searchQuery = '';
  activeFilter = 'all';

  const searchInput = document.getElementById('stationSearch');
  if (searchInput) searchInput.value = '';

  const filterButtons = document.querySelectorAll('.filter-pill');
  filterButtons.forEach(btn => {
    btn.classList.remove('bg-surface-container-lowest', 'text-on-surface', 'font-semibold', 'shadow-sm');
    btn.classList.add('text-on-surface-variant');
  });
  const countAllBtn = document.getElementById('countAll');
  if (countAllBtn) {
    countAllBtn.classList.add('bg-surface-container-lowest', 'text-on-surface', 'font-semibold', 'shadow-sm');
    countAllBtn.classList.remove('text-on-surface-variant');
  }

  if (stations.length > 0) {
    const validCoords = stations
      .filter(s => isValidCoord(s.latitude, s.longitude))
      .map(s => [parseFloat(s.latitude), parseFloat(s.longitude)]);
    if (validCoords.length > 0) {
      map.fitBounds(L.latLngBounds(validCoords), { padding: [40, 40] });
    } else {
      map.setView(MAP_CONFIG.DEFAULT_CENTER, MAP_CONFIG.DEFAULT_ZOOM_FULL);
    }
  }

  renderStationMarkers();
  renderStationTable();
}

/**
 * Initialize search field and category filter pills
 */
function initSearchAndFilters() {
  const searchInput = document.getElementById('stationSearch');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      renderStationMarkers();
      renderStationTable();
    });
  }

  const filterButtons = document.querySelectorAll('.filter-pill');
  filterButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      filterButtons.forEach(b => {
        b.classList.remove('bg-surface-container-lowest', 'text-on-surface', 'font-semibold', 'shadow-sm');
        b.classList.add('text-on-surface-variant');
      });
      btn.classList.add('bg-surface-container-lowest', 'text-on-surface', 'font-semibold', 'shadow-sm');
      btn.classList.remove('text-on-surface-variant');

      activeFilter = btn.getAttribute('data-filter') || 'all';
      renderStationMarkers();
      renderStationTable();
    });
  });
}

/**
 * Manage Map explicit state UI banners (LOADING, ERROR, STALE)
 */
function showState(stateName, meta = {}) {
  const loadingEl = document.getElementById('mapLoadingState');
  const errorEl = document.getElementById('mapErrorState');
  const staleEl = document.getElementById('mapStaleBanner');
  const canvasEl = document.getElementById('mapCanvasSection');

  if (loadingEl) loadingEl.classList.add('hidden');
  if (errorEl) errorEl.classList.add('hidden');
  if (staleEl) staleEl.classList.add('hidden');

  if (stateName === 'LOADING') {
    if (loadingEl) loadingEl.classList.remove('hidden');
  } else if (stateName === 'ERROR') {
    if (errorEl) {
      errorEl.classList.remove('hidden');
      const msg = document.getElementById('mapErrorMessage');
      if (msg) msg.textContent = meta.message || 'Unable to load current flood-risk map information.';
    }
  } else if (stateName === 'STALE') {
    if (staleEl) {
      staleEl.classList.remove('hidden');
      const text = document.getElementById('mapStaleText');
      if (text && meta.time) {
        text.textContent = `Selected station prediction may be outdated. Last updated: ${meta.time}. Displaying last recorded prediction.`;
      }
    }
  }
}

/**
 * Fetch all monitoring stations and predictions in single canonical batch
 */
async function loadMapData() {
  showState('LOADING');

  try {
    const [locationsRes, mapPredsRes] = await Promise.all([
      api.getLocations().catch(err => ({ error: err })),
      api.getMapPredictions().catch(err => ({ error: err }))
    ]);

    if (locationsRes && locationsRes.error) {
      showState('ERROR', { message: 'Failed to fetch monitoring locations.' });
      return;
    }

    stations = locationsRes.locations || [];

    if (mapPredsRes && mapPredsRes.predictions) {
      mapPredsRes.predictions.forEach(p => {
        stationDataMap.set(p.location_id, p);
      });
    }

    updateFilterCounts();
    renderStationMarkers();
    renderStationTable();

    // Fit bounds to monitoring network on initial load
    if (stations.length > 0 && map) {
      const validCoords = stations
        .filter(s => isValidCoord(s.latitude, s.longitude))
        .map(s => [parseFloat(s.latitude), parseFloat(s.longitude)]);
      if (validCoords.length > 0) {
        map.fitBounds(L.latLngBounds(validCoords), { padding: [35, 35] });
      }
    }

    await selectStation(selectedStationId, false);
    showState('CLEAR');

  } catch (err) {
    console.error('[Map] Failed to load map data from backend:', err);
    showState('ERROR', { message: err.message || 'Error loading map predictions.' });
  }
}

/**
 * Update Station counts on Filter pills
 */
function updateFilterCounts() {
  let lowCount = 0, modCount = 0, highCount = 0, critCount = 0, noDataCount = 0;

  stations.forEach(loc => {
    const pred = stationDataMap.get(loc.id);
    if (!pred || pred.status === 'NO_CURRENT_PREDICTION') {
      noDataCount++;
      return;
    }
    const riskLevel = pred.risk_level || 'LOW';
    const prob = pred.flood_probability_percent !== undefined ? pred.flood_probability_percent / 100 : (pred.flood_probability || 0);
    const tier = common.getRiskDetails(riskLevel, prob).key;

    if (tier === 'critical') critCount++;
    else if (tier === 'high') highCount++;
    else if (tier === 'moderate') modCount++;
    else lowCount++;
  });

  const countAll = document.getElementById('countAll');
  const countLow = document.getElementById('countLow');
  const countMod = document.getElementById('countMod');
  const countHigh = document.getElementById('countHigh');
  const countCrit = document.getElementById('countCrit');
  const countNoData = document.getElementById('countNoData');

  if (countAll) countAll.textContent = `All (${stations.length})`;
  if (countLow) countLow.textContent = `Low (${lowCount})`;
  if (countMod) countMod.textContent = `Moderate (${modCount})`;
  if (countHigh) countHigh.textContent = `High (${highCount})`;
  if (countCrit) countCrit.textContent = `Critical (${critCount})`;
  if (countNoData) countNoData.textContent = `No Data (${noDataCount})`;
}

/**
 * Filter stations by search and active category filter pill
 */
function getFilteredStations() {
  return stations.filter(loc => {
    if (!isValidCoord(loc.latitude, loc.longitude)) return false;

    const pred = stationDataMap.get(loc.id);
    const hasData = pred && pred.status !== 'NO_CURRENT_PREDICTION';

    if (activeFilter === 'nodata' && hasData) return false;
    if (activeFilter !== 'all' && activeFilter !== 'nodata') {
      if (!hasData) return false;
      const riskLevel = pred.risk_level || 'LOW';
      const prob = pred.flood_probability_percent !== undefined ? pred.flood_probability_percent / 100 : (pred.flood_probability || 0);
      const tier = common.getRiskDetails(riskLevel, prob).key;
      if (tier !== activeFilter) return false;
    }

    if (searchQuery) {
      const matchDistrict = (loc.district || '').toLowerCase().includes(searchQuery);
      const matchPlace = (loc.place_name || '').toLowerCase().includes(searchQuery);
      const matchProvince = (loc.province || '').toLowerCase().includes(searchQuery);
      if (!matchDistrict && !matchPlace && !matchProvince) return false;
    }

    return true;
  });
}

/**
 * Render Station Nodes on Leaflet GIS Map Canvas
 */
function renderStationMarkers() {
  if (!map || !markersLayerGroup) return;

  markersLayerGroup.clearLayers();
  markerMap.clear();

  const filtered = getFilteredStations();

  filtered.forEach(loc => {
    const lat = parseFloat(loc.latitude);
    const lon = parseFloat(loc.longitude);
    const pred = stationDataMap.get(loc.id);
    const hasData = pred && pred.status !== 'NO_CURRENT_PREDICTION';

    const probPct = hasData ? (pred.flood_probability_percent !== undefined ? pred.flood_probability_percent : pred.flood_probability * 100) : 0;
    const riskLevel = hasData ? (pred.risk_level || 'LOW') : 'NO_DATA';
    
    let risk;
    if (!hasData) {
      risk = {
        key: 'nodata',
        className: 'risk-nodata',
        dotColor: '#94a3b8',
        textColor: '#64748b',
        label: 'No Current Prediction',
        shortLabel: 'NO DATA',
        badgeBg: 'bg-slate-200 text-slate-700'
      };
    } else {
      risk = common.getRiskDetails(riskLevel, probPct / 100);
    }

    const isSelected = loc.id === selectedStationId;
    const customIcon = createStationDivIcon(risk, isSelected, false);
    const marker = L.marker([lat, lon], { icon: customIcon });

    marker.bindTooltip(`
      <div class="flex items-center gap-1.5 font-sans">
        <span class="w-2 h-2 rounded-full" style="background-color: ${risk.dotColor}"></span>
        <span class="font-semibold">${loc.place_name.split(' ')[0]}</span>
        <span style="color: ${risk.dotColor}">(${hasData ? `${common.formatNumber(probPct, 0)}%` : 'NO DATA'})</span>
      </div>
    `, {
      direction: 'top',
      offset: [0, -14],
      className: 'leaflet-tooltip-dark',
      permanent: false
    });

    marker.on('click', async () => {
      await selectStation(loc.id, true);
    });

    markersLayerGroup.addLayer(marker);
    markerMap.set(loc.id, marker);
  });
}

/**
 * Render Accessible Station Risk Directory Table View
 */
function renderStationTable() {
  const bodyEl = document.getElementById('stationTableBody');
  const countEl = document.getElementById('tableSummaryCount');
  if (!bodyEl) return;

  const filtered = getFilteredStations();

  if (countEl) countEl.textContent = `Showing ${filtered.length} of ${stations.length} Stations`;

  if (!filtered.length) {
    bodyEl.innerHTML = `
      <tr>
        <td colspan="6" class="p-6 text-center text-on-surface-variant font-body-md">
          No stations match the selected search/filter parameters.
        </td>
      </tr>
    `;
    return;
  }

  bodyEl.innerHTML = filtered.map(loc => {
    const pred = stationDataMap.get(loc.id);
    const hasData = pred && pred.status !== 'NO_CURRENT_PREDICTION';

    const probPct = hasData ? (pred.flood_probability_percent !== undefined ? pred.flood_probability_percent : pred.flood_probability * 100) : 0;
    const riskLevel = hasData ? (pred.risk_level || 'LOW') : 'NO_DATA';
    
    let risk;
    if (!hasData) {
      risk = {
        key: 'nodata',
        label: 'No Current Prediction',
        badgeBg: 'bg-slate-200 text-slate-700',
        dotColor: '#94a3b8'
      };
    } else {
      risk = common.getRiskDetails(riskLevel, probPct / 100);
    }

    const actionCode = hasData ? (pred.action_code || 'SAFE') : 'N/A';
    const updatedTime = hasData && pred.prediction_time ? common.formatTime(pred.prediction_time) : '--:--';
    const isSelected = loc.id === selectedStationId;

    return `
      <tr class="hover:bg-surface-container-low/60 transition-colors cursor-pointer ${isSelected ? 'bg-surface-container-low font-semibold' : ''}" onclick="window.selectLocationFromTable(${loc.id})">
        <td class="p-3">
          <div class="flex flex-col">
            <span class="font-bold text-on-surface">${loc.place_name}</span>
            <span class="text-xs text-outline">${loc.district} District • Station #${loc.record_id || loc.id}</span>
          </div>
        </td>
        <td class="p-3">
          <span class="px-2.5 py-0.5 rounded text-xs font-bold uppercase inline-flex items-center gap-1.5 ${risk.badgeBg}">
            <span class="w-2 h-2 rounded-full" style="background-color: ${risk.dotColor}"></span>
            <span>${risk.label}</span>
          </span>
        </td>
        <td class="p-3 font-data-metric text-data-metric text-on-surface font-bold">
          ${hasData ? `${common.formatNumber(probPct, 2)}%` : '--'}
        </td>
        <td class="p-3 font-data-timestamp text-data-timestamp uppercase font-bold text-secondary">
          ${actionCode}
        </td>
        <td class="p-3 font-data-timestamp text-data-timestamp text-on-surface-variant">
          ${updatedTime}
        </td>
        <td class="p-3 text-right">
          <a href="district.html?location_id=${loc.id}" class="btn btn-secondary btn-sm" onclick="event.stopPropagation()">
            <span>Details</span>
            <span class="material-symbols-outlined text-[14px]">chevron_right</span>
          </a>
        </td>
      </tr>
    `;
  }).join('');
}

window.selectLocationFromTable = (id) => {
  selectStation(id, true);
};

/**
 * Focus and bind selected station details to Sidebar Inspection Panel
 * Uses Phase 3 Unified Prediction API (/api/v1/predictions/current/{id})
 */
async function selectStation(stationId, shouldPan = false) {
  const currentRequestId = ++mapRequestId;
  selectedStationId = stationId;
  common.setSelectedLocationId(stationId, false);

  renderStationMarkers();
  renderStationTable();

  const loc = stations.find(s => s.id === stationId);
  if (!loc) return;

  if (shouldPan && map && isValidCoord(loc.latitude, loc.longitude)) {
    map.flyTo([parseFloat(loc.latitude), parseFloat(loc.longitude)], Math.max(map.getZoom(), 10), {
      duration: 0.8
    });
  }

  // Update coordinate display
  const coordDisplay = document.getElementById('coordDisplay');
  if (coordDisplay) {
    coordDisplay.textContent = `${parseFloat(loc.latitude).toFixed(4)}° N, ${parseFloat(loc.longitude).toFixed(4)}° E`;
  }

  // Update static location headers
  const stationNameEl = document.getElementById('panelStationName');
  const basinNameEl = document.getElementById('panelBasinName');
  const districtEl = document.getElementById('panelDistrict');
  const stationIdTagEl = document.getElementById('panelStationIdTag');
  const telemetryLink = document.getElementById('fullTelemetryLink');
  const dashboardLink = document.getElementById('dashboardLink');

  if (stationNameEl) stationNameEl.textContent = loc.place_name;
  if (basinNameEl) basinNameEl.textContent = loc.river_basin ? `${loc.river_basin} Basin` : `${loc.district} Catchment Area`;
  if (districtEl) districtEl.textContent = `District: ${loc.district} (Lat: ${loc.latitude}° N, Lon: ${loc.longitude}° E)`;
  if (stationIdTagEl) stationIdTagEl.textContent = `ID: ${loc.record_id || 'LK-LOC-' + loc.id}`;

  if (telemetryLink) telemetryLink.href = `district.html?location_id=${loc.id}`;
  if (dashboardLink) dashboardLink.href = `index.html?location_id=${loc.id}`;

  // Fetch canonical prediction from Phase 3 Unified API gateway
  try {
    const [predictionRes, weatherRes] = await Promise.all([
      api.getCurrentPrediction(loc.id).catch(err => ({ error: err })),
      api.getWeather(loc.id).catch(() => null)
    ]);

    // Race condition guard
    if (currentRequestId !== mapRequestId) {
      console.warn(`[Map] Ignoring out-of-order station response for request ${currentRequestId}`);
      return;
    }

    // Location verification guard
    if (predictionRes && predictionRes.location) {
      const retId = parseInt(predictionRes.location.location_id, 10);
      if (retId !== parseInt(loc.id, 10)) {
        console.error(`[Map Integrity Error] Location ID mismatch! Requested: ${loc.id}, Returned: ${retId}`);
        return;
      }
    }

    // Handle missing prediction (404)
    if (predictionRes && predictionRes.error) {
      renderSidebarMissingState(loc);
      return;
    }

    // Handle fresh vs stale state
    const isStale = predictionRes.is_stale || predictionRes.status === 'STALE';
    if (isStale) {
      showState('STALE', { time: common.formatTime(predictionRes.prediction_time) });
    } else {
      showState('CLEAR');
    }

    // Render canonical sidebar values
    renderSidebarData(predictionRes, weatherRes, isStale);

  } catch (err) {
    if (currentRequestId === mapRequestId) {
      console.error('[Map] Error fetching station telemetry:', err);
    }
  }
}

/**
 * Render Sidebar Panel when prediction is missing (404)
 */
function renderSidebarMissingState(loc) {
  const badgeEl = document.getElementById('panelRiskBadge');
  const freshnessEl = document.getElementById('panelFreshnessTag');
  const actionCodeEl = document.getElementById('panelActionCode');
  const actionMsgEl = document.getElementById('panelActionMessage');
  const probNumEl = document.getElementById('panelProbabilityNumber');
  const probBarEl = document.getElementById('panelProbabilityBar');
  const validityEl = document.getElementById('panelValidityTime');
  const updatedEl = document.getElementById('panelUpdatedTime');

  if (badgeEl) {
    badgeEl.className = 'px-2.5 py-1 rounded font-label-md text-label-md font-bold uppercase bg-slate-200 text-slate-700 shadow-sm';
    badgeEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-slate-400"></span><span>No Current Prediction</span>`;
  }

  if (freshnessEl) {
    freshnessEl.textContent = 'NO DATA';
    freshnessEl.className = 'px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-200 text-slate-700';
  }

  if (actionCodeEl) {
    actionCodeEl.textContent = 'N/A';
    actionCodeEl.className = 'px-2 py-0.5 rounded text-xs font-extrabold uppercase bg-slate-400 text-white';
  }

  if (actionMsgEl) {
    actionMsgEl.textContent = `No active flood prediction record is available for ${loc.place_name} today.`;
  }

  if (probNumEl) {
    probNumEl.textContent = 'NO DATA';
    probNumEl.style.color = '#64748b';
  }

  if (probBarEl) probBarEl.style.width = '0%';
  if (validityEl) validityEl.textContent = 'Validity: N/A';
  if (updatedEl) updatedEl.textContent = '--:--';
}

/**
 * Render Sidebar Panel with Canonical Risk & Action
 */
function renderSidebarData(predRes, weatherRes, isStale) {
  const risk = predRes.risk || { level: 'LOW', score: 0.0, flood_probability_percent: 0.0 };
  const action = predRes.action || { code: 'SAFE', message: 'Normal conditions. No immediate flood risk detected.' };
  const cond = predRes.conditions || {};
  const currentWx = (weatherRes && weatherRes.current) ? weatherRes.current : {};

  const probPct = risk.flood_probability_percent !== undefined ? risk.flood_probability_percent : (risk.score ? risk.score * 100 : 0.0);
  const riskDetails = common.getRiskDetails(risk.level, probPct / 100);

  // Risk badge & Freshness tag
  const badgeEl = document.getElementById('panelRiskBadge');
  const freshnessEl = document.getElementById('panelFreshnessTag');

  if (badgeEl) {
    badgeEl.className = `px-2.5 py-1 rounded font-label-md text-label-md font-bold uppercase ${riskDetails.badgeBg} shadow-sm`;
    badgeEl.innerHTML = `<span class="w-2 h-2 rounded-full" style="background-color: ${riskDetails.dotColor}"></span><span>${riskDetails.label}</span>`;
  }

  if (freshnessEl) {
    freshnessEl.textContent = isStale ? 'STALE' : 'CURRENT';
    freshnessEl.className = `px-2 py-0.5 rounded text-[10px] font-bold uppercase ${isStale ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}`;
  }

  // Action Guidance
  const actionCodeEl = document.getElementById('panelActionCode');
  const actionMsgEl = document.getElementById('panelActionMessage');

  if (actionCodeEl) {
    actionCodeEl.textContent = action.code || 'SAFE';
    if (action.code === 'EVACUATE') {
      actionCodeEl.className = 'px-2 py-0.5 rounded text-xs font-extrabold uppercase bg-rose-600 text-white animate-pulse';
    } else if (action.code === 'PREPARE') {
      actionCodeEl.className = 'px-2 py-0.5 rounded text-xs font-extrabold uppercase bg-orange-500 text-white';
    } else if (action.code === 'MONITOR') {
      actionCodeEl.className = 'px-2 py-0.5 rounded text-xs font-extrabold uppercase bg-amber-500 text-slate-950';
    } else {
      actionCodeEl.className = 'px-2 py-0.5 rounded text-xs font-extrabold uppercase bg-emerald-600 text-white';
    }
  }

  if (actionMsgEl) {
    actionMsgEl.textContent = action.message || 'Normal conditions. No immediate flood risk detected.';
  }

  // Timestamps
  const validityEl = document.getElementById('panelValidityTime');
  const updatedEl = document.getElementById('panelUpdatedTime');

  if (validityEl) {
    if (predRes.valid_from && predRes.valid_until) {
      validityEl.textContent = `Valid: ${common.formatTime(predRes.valid_from)} — ${common.formatTime(predRes.valid_until)}`;
    } else {
      validityEl.textContent = 'Valid: Next 12 Hours';
    }
  }

  if (updatedEl) {
    updatedEl.textContent = common.formatTime(predRes.prediction_time);
  }

  // Probability Meter
  const probNumEl = document.getElementById('panelProbabilityNumber');
  const probBarEl = document.getElementById('panelProbabilityBar');

  if (probNumEl) {
    probNumEl.textContent = `${common.formatNumber(probPct, 2)}%`;
    probNumEl.style.color = riskDetails.dotColor;
  }

  if (probBarEl) {
    probBarEl.style.width = `${Math.min(probPct, 100)}%`;
    probBarEl.style.backgroundColor = riskDetails.dotColor;
  }

  // Conditions Matrix
  const rain24El = document.getElementById('panelRain24');
  const rain7El = document.getElementById('panelRain7');
  const dischargeEl = document.getElementById('panelDischarge');

  const rain24Val = cond.rainfall_mm_24h !== undefined ? cond.rainfall_mm_24h : (currentWx.precipitation_mm || 0.0);
  const flowVal = cond.water_level_m !== undefined ? cond.water_level_m : currentWx.river_discharge_m3s;

  if (rain24El) rain24El.textContent = `${common.formatNumber(rain24Val, 1, '0.0')} mm`;
  if (rain7El) rain7El.textContent = `${common.formatNumber(currentWx.precipitation_sum_7d_mm || (rain24Val * 3), 1, '0.0')} mm`;
  if (dischargeEl) dischargeEl.textContent = flowVal !== undefined && flowVal !== null ? `${common.formatNumber(flowVal, 1)} m³/s` : 'Baseline';
}

/**
 * Export 33 Stations as valid GeoJSON FeatureCollection (EPSG:4326 OGC CRS 84)
 */
function exportStationsGeoJson() {
  const geoJson = {
    type: "FeatureCollection",
    crs: {
      type: "name",
      properties: { name: "urn:ogc:def:crs:OGC:1.3:CRS84" }
    },
    features: stations.map(loc => {
      const pred = stationDataMap.get(loc.id);
      const hasData = pred && pred.status !== 'NO_CURRENT_PREDICTION';

      return {
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [parseFloat(loc.longitude), parseFloat(loc.latitude)]
        },
        properties: {
          id: loc.id,
          record_id: loc.record_id,
          district: loc.district,
          province: loc.province,
          place_name: loc.place_name,
          river_basin: loc.river_basin,
          elevation_m: loc.elevation_m,
          prediction_id: hasData ? pred.prediction_id : null,
          flood_probability: hasData ? pred.flood_probability : null,
          flood_probability_percent: hasData ? (pred.flood_probability_percent || pred.flood_probability * 100) : null,
          risk_level: hasData ? pred.risk_level : "NO_DATA",
          action_code: hasData ? (pred.action_code || "SAFE") : "N/A",
          action_message: hasData ? (pred.action_message || "Normal conditions.") : "No active prediction.",
          status: hasData ? pred.status : "NO_CURRENT_PREDICTION"
        }
      };
    })
  };

  const blob = new Blob([JSON.stringify(geoJson, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `sri_lanka_floodwatch_map_predictions_${Date.now()}.geojson`;
  a.click();
  URL.revokeObjectURL(url);
}
