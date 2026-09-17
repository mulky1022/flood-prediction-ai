/**
 * Sri Lanka FloodWatch — Interactive GIS Map Controller
 * Real Leaflet Geographic Map Engine with Live Multi-Station Inference Overlays
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

document.addEventListener('DOMContentLoaded', async () => {
  common.initHeader('flood-map');

  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has('station') || urlParams.has('location_id')) {
    selectedStationId = parseInt(urlParams.get('station') || urlParams.get('location_id'), 10) || 1;
  }

  initLeafletMap();
  initMapControls();
  initSearchAndFilters();
  await loadMapData();

  // Invalidate size after initial layout
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
 * Initialize Leaflet Geographic Map
 */
function initLeafletMap() {
  const mapContainer = document.getElementById('leafletMap');
  if (!mapContainer) {
    console.error('Leaflet map container (#leafletMap) not found.');
    return;
  }

  try {
    map = L.map('leafletMap', {
      center: MAP_CONFIG.DEFAULT_CENTER,
      zoom: MAP_CONFIG.DEFAULT_ZOOM_FULL,
      minZoom: MAP_CONFIG.MIN_ZOOM,
      maxZoom: MAP_CONFIG.MAX_ZOOM,
      zoomControl: false // Handled via Stitch custom controls
    });

    // Setup base tile layer with fallback & error reporting
    tileLayer = setupTileLayer(map, (err) => {
      showMapAlert('Base map tiles unavailable — displaying GIS sensor layer and country boundary.');
    });

    // Add Sri Lanka country boundary
    boundaryLayer = addBoundaryLayer(map);

    markersLayerGroup = L.layerGroup().addTo(map);

    // Track mouse move for live coordinate readout
    map.on('mousemove', (e) => {
      const coordDisplay = document.getElementById('coordDisplay');
      if (coordDisplay && e.latlng) {
        coordDisplay.textContent = `${e.latlng.lat.toFixed(4)}° N, ${e.latlng.lng.toFixed(4)}° E`;
      }
    });

  } catch (err) {
    console.error('Error initializing Leaflet map:', err);
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

  if (zoomInBtn) {
    zoomInBtn.addEventListener('click', () => {
      if (map) map.zoomIn();
    });
  }

  if (zoomOutBtn) {
    zoomOutBtn.addEventListener('click', () => {
      if (map) map.zoomOut();
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      resetMapView();
    });
  }

  if (recenterBtn) {
    recenterBtn.addEventListener('click', () => {
      if (map) {
        map.flyTo(MAP_CONFIG.DEFAULT_CENTER, MAP_CONFIG.DEFAULT_ZOOM_FULL, { duration: 0.8 });
      }
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
 * Reset map view bounds to encapsulate all monitoring stations
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
      const bounds = L.latLngBounds(validCoords);
      map.fitBounds(bounds, { padding: [40, 40] });
    } else {
      map.setView(MAP_CONFIG.DEFAULT_CENTER, MAP_CONFIG.DEFAULT_ZOOM_FULL);
    }
  } else {
    map.setView(MAP_CONFIG.DEFAULT_CENTER, MAP_CONFIG.DEFAULT_ZOOM_FULL);
  }

  renderStationMarkers();
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
    });
  });
}

/**
 * Fetch all locations and predict risk for key stations
 */
async function loadMapData() {
  try {
    const data = await api.getLocations();
    stations = data.locations || [];

    // Pre-fetch predictions in parallel for all stations
    const predictionPromises = stations.map(async (loc) => {
      try {
        const pred = await api.getPrediction(loc.id);
        return { id: loc.id, pred: pred.prediction };
      } catch (e) {
        return { id: loc.id, pred: null };
      }
    });

    const predictions = await Promise.all(predictionPromises);
    predictions.forEach(item => {
      if (item && item.pred) {
        stationDataMap.set(item.id, item.pred);
      }
    });

    updateFilterCounts();
    renderStationMarkers();

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

  } catch (err) {
    console.error('Failed to load map data from backend:', err);
  }
}

/**
 * Update Station counts on Filter pills
 */
function updateFilterCounts() {
  let lowCount = 0, modCount = 0, highCount = 0, critCount = 0;

  stations.forEach(loc => {
    const pred = stationDataMap.get(loc.id);
    const riskLevel = pred ? pred.risk_level : 'LOW';
    const prob = pred ? (pred.flood_probability_percent !== undefined ? pred.flood_probability_percent / 100 : pred.flood_probability) : 0;
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

  if (countAll) countAll.textContent = `All (${stations.length})`;
  if (countLow) countLow.textContent = `Low (${lowCount})`;
  if (countMod) countMod.textContent = `Moderate (${modCount})`;
  if (countHigh) countHigh.textContent = `High (${highCount})`;
  if (countCrit) countCrit.textContent = `Critical (${critCount})`;
}

/**
 * Render Station Nodes as Leaflet Custom HTML DivIcons
 */
function renderStationMarkers() {
  if (!map || !markersLayerGroup) return;

  markersLayerGroup.clearLayers();
  markerMap.clear();

  const filteredStations = stations.filter(loc => {
    if (!isValidCoord(loc.latitude, loc.longitude)) return false;

    const pred = stationDataMap.get(loc.id);
    const riskLevel = pred ? pred.risk_level : 'LOW';
    const prob = pred ? (pred.flood_probability_percent !== undefined ? pred.flood_probability_percent / 100 : pred.flood_probability) : 0;
    const tier = common.getRiskDetails(riskLevel, prob).key;

    // Filter by risk tier
    if (activeFilter !== 'all' && tier !== activeFilter) {
      return false;
    }

    // Filter by search query
    if (searchQuery) {
      const matchDistrict = (loc.district || '').toLowerCase().includes(searchQuery);
      const matchPlace = (loc.place_name || '').toLowerCase().includes(searchQuery);
      const matchProvince = (loc.province || '').toLowerCase().includes(searchQuery);
      if (!matchDistrict && !matchPlace && !matchProvince) return false;
    }

    return true;
  });

  filteredStations.forEach(loc => {
    const lat = parseFloat(loc.latitude);
    const lon = parseFloat(loc.longitude);
    const pred = stationDataMap.get(loc.id);
    const probPct = pred ? (pred.flood_probability_percent !== undefined ? pred.flood_probability_percent : pred.flood_probability * 100) : 0;
    const risk = common.getRiskDetails(pred ? pred.risk_level : 'LOW', probPct / 100);
    const isSelected = loc.id === selectedStationId;

    const customIcon = createStationDivIcon(risk, isSelected, false);
    const marker = L.marker([lat, lon], { icon: customIcon });

    // Dark styled tooltip
    marker.bindTooltip(`
      <div class="flex items-center gap-1.5 font-sans">
        <span class="w-2 h-2 rounded-full" style="background-color: ${risk.dotColor}"></span>
        <span>${loc.place_name.split(' ')[0]}</span>
        <span style="color: ${risk.dotColor}">(${common.formatNumber(probPct, 0)}%)</span>
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
 * Focus and bind selected station details to Sidebar
 */
async function selectStation(stationId, shouldPan = false) {
  selectedStationId = stationId;

  // Update marker visual styles
  renderStationMarkers();

  const loc = stations.find(s => s.id === stationId);
  if (!loc) return;

  if (shouldPan && map && isValidCoord(loc.latitude, loc.longitude)) {
    map.flyTo([parseFloat(loc.latitude), parseFloat(loc.longitude)], Math.max(map.getZoom(), 10), {
      duration: 0.8
    });

    if (window.innerWidth < 1024) {
      setTimeout(() => {
        const panel = document.getElementById('panelStationName');
        if (panel) {
          panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }, 400);
    }
  }

  // Update coordinate display
  const coordDisplay = document.getElementById('coordDisplay');
  if (coordDisplay) {
    coordDisplay.textContent = `${parseFloat(loc.latitude).toFixed(4)}° N, ${parseFloat(loc.longitude).toFixed(4)}° E`;
  }

  // Update sidebar static elements
  const stationNameEl = document.getElementById('panelStationName');
  const basinNameEl = document.getElementById('panelBasinName');
  const districtEl = document.getElementById('panelDistrict');
  const stationIdTagEl = document.getElementById('panelStationIdTag');

  if (stationNameEl) stationNameEl.textContent = loc.place_name;
  if (basinNameEl) basinNameEl.textContent = loc.river_basin ? `${loc.river_basin} Basin` : `${loc.district} Catchment Area`;
  if (districtEl) districtEl.textContent = `${loc.district} District (Lat: ${loc.latitude}° N, Lon: ${loc.longitude}° E)`;
  if (stationIdTagEl) stationIdTagEl.textContent = `ID: ${loc.record_id || 'LK-LOC-' + loc.id}`;

  // Link to details page
  const fullTelemetryLink = document.getElementById('fullTelemetryLink');
  if (fullTelemetryLink) {
    fullTelemetryLink.href = `district.html?location_id=${loc.id}`;
  }

  // Fetch fresh telemetry & prediction for selected station
  try {
    const [weather, predData] = await Promise.all([
      api.getWeather(loc.id).catch(() => null),
      api.getPrediction(loc.id).catch(() => null)
    ]);

    const pred = predData ? predData.prediction : null;
    const current = weather ? (weather.current || {}) : {};
    const rolling = weather ? (weather.rainfall || weather.rolling_aggregations || {}) : {};

    // Risk Badge
    const badgeEl = document.getElementById('panelRiskBadge');
    if (badgeEl) {
      const risk = common.getRiskDetails(pred ? pred.risk_level : 'LOW', pred ? (pred.flood_probability_percent !== undefined ? pred.flood_probability_percent / 100 : pred.flood_probability) : 0);
      badgeEl.className = `px-2.5 py-1 rounded font-label-md text-label-md font-bold uppercase ${risk.badgeBg} flex items-center gap-1.5 shadow-sm`;
      badgeEl.innerHTML = `<span class="w-2 h-2 rounded-full" style="background-color: ${risk.dotColor}"></span><span>${risk.label}</span>`;
    }

    // Probability readout & progress bar
    const probNumberEl = document.getElementById('panelProbabilityNumber');
    const probBarEl = document.getElementById('panelProbabilityBar');
    const probPct = pred ? (pred.flood_probability_percent !== undefined ? pred.flood_probability_percent : pred.flood_probability * 100) : 0;

    if (probNumberEl) {
      probNumberEl.textContent = `${common.formatNumber(probPct, 2)}%`;
      const risk = common.getRiskDetails(pred ? pred.risk_level : 'LOW', probPct / 100);
      probNumberEl.style.color = risk.textColor;
    }

    if (probBarEl) {
      probBarEl.style.width = `${Math.min(probPct, 100)}%`;
    }

    // Risk drivers
    const rain7El = document.getElementById('panelRain7');
    const rain30El = document.getElementById('panelRain30');
    const dischargeEl = document.getElementById('panelDischarge');

    const val7d = rolling.rainfall_7d_mm !== undefined ? rolling.rainfall_7d_mm : rolling.precipitation_sum_7d_mm;
    const val30d = rolling.monthly_rainfall_mm !== undefined ? rolling.monthly_rainfall_mm : rolling.precipitation_sum_30d_mm;

    if (rain7El) rain7El.textContent = `${common.formatNumber(val7d, 1, '0.0')} mm`;
    if (rain30El) rain30El.textContent = `${common.formatNumber(val30d, 1, '0.0')} mm`;
    if (dischargeEl) dischargeEl.textContent = current.river_discharge_m3s !== undefined ? `${common.formatNumber(current.river_discharge_m3s, 1)} m³/s` : 'Normal Baseline';

    // Atmospheric metrics
    const tempEl = document.getElementById('panelTemp');
    const humidityEl = document.getElementById('panelHumidity');
    const windEl = document.getElementById('panelWind');

    if (tempEl) tempEl.textContent = `${common.formatNumber(current.temperature_c, 1, '--')}°C`;
    if (humidityEl) humidityEl.textContent = `${common.formatNumber(current.humidity_percent, 0, '--')}%`;
    if (windEl) windEl.textContent = `${common.formatNumber(current.wind_speed_kmh, 1, '--')} km/h`;

  } catch (e) {
    console.error('Error fetching station details:', e);
  }
}

/**
 * Export 33 Stations as valid GeoJSON FeatureCollection
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
          flood_probability: pred ? pred.flood_probability : null,
          flood_probability_percent: pred ? (pred.flood_probability_percent || pred.flood_probability * 100) : null,
          risk_level: pred ? pred.risk_level : null
        }
      };
    })
  };

  const blob = new Blob([JSON.stringify(geoJson, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `sri_lanka_floodwatch_stations_${Date.now()}.geojson`;
  a.click();
  URL.revokeObjectURL(url);
}
