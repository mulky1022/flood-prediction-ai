/**
 * Location Details (District Telemetry) Controller
 */

import { api } from './api.js';
import { common } from './common.js';

let currentLocationId = 1;
let stationData = null;
let weatherData = null;
let predictionData = null;
let historyData = [];

document.addEventListener('DOMContentLoaded', async () => {
  common.initHeader('location-details');

  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has('location_id')) {
    currentLocationId = parseInt(urlParams.get('location_id'), 10) || 1;
  }

  setupExportButton();
  await loadStationDetails(currentLocationId);
});

/**
 * Fetch and bind all telemetry, GIS, and ML data
 */
async function loadStationDetails(locationId) {
  try {
    const [location, weather, prediction, history, locationAlerts] = await Promise.all([
      api.getLocation(locationId).catch(e => null),
      api.getWeather(locationId).catch(e => null),
      api.getPrediction(locationId).catch(e => null),
      api.getPredictionHistory(locationId, 10).catch(e => null),
      api.getLocationAlerts(locationId, 5).catch(e => null)
    ]);

    stationData = location;
    weatherData = weather;
    predictionData = prediction;
    historyData = (history && history.items) ? history.items : [];
    const activeAlerts = (locationAlerts && locationAlerts.items) ? locationAlerts.items.filter(a => a.status === 'ACTIVE' || a.status === 'ACKNOWLEDGED') : [];

    renderBreadcrumbs(stationData);
    renderHeaderBanner(stationData, activeAlerts);
    renderPredictionEngine(predictionData, stationData, activeAlerts);

    renderChannelProximity(stationData, weatherData);
    renderWeatherCards(weatherData);
    renderPrecipitationAnalytics(weatherData);
    renderVulnerabilityMatrix(stationData);
    renderDecisionThreshold(predictionData);
    renderHistoryTable(historyData);

  } catch (err) {
    console.error('Error loading station details:', err);
  }
}

/**
 * Breadcrumb trail
 */
function renderBreadcrumbs(loc) {
  const districtCrumb = document.getElementById('crumbDistrict');
  const stationCrumb = document.getElementById('crumbStation');

  if (districtCrumb && loc) districtCrumb.textContent = `${loc.district} District`;
  if (stationCrumb && loc) stationCrumb.textContent = loc.place_name;
}

/**
 * Header banner with coordinates & elevation
 */
function renderHeaderBanner(loc) {
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
  if (elevation) elevation.textContent = `Elevation: ${common.formatNumber(loc.elevation_m, 1)}m ASL`;
  if (sensorArray) sensorArray.textContent = `Sensor Array ID: ${loc.record_id || 'LK-SEN-' + loc.id}`;
}

/**
 * Radial Probability Gauge & Classification Result
 */
function renderPredictionEngine(predRes, loc, activeAlerts = []) {
  const pred = predRes ? predRes.prediction : null;
  const probPercent = pred ? (pred.flood_probability_percent || pred.flood_probability * 100) : 0;
  const risk = common.getRiskDetails(pred ? pred.risk_level : 'LOW', pred ? pred.flood_probability : 0);

  // Risk Badge
  const badgeEl = document.getElementById('detailRiskBadge');
  if (badgeEl) {
    const hasActiveAlert = activeAlerts && activeAlerts.length > 0;
    const alertLabel = hasActiveAlert ? `ACTIVE ${activeAlerts[0].risk_level} ALERT` : risk.label;
    badgeEl.className = `inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full ${risk.badgeBg} font-label-lg text-label-lg font-bold`;
    badgeEl.innerHTML = `<span class="h-2 w-2 rounded-full ${hasActiveAlert ? 'animate-ping' : ''}" style="background-color: ${risk.dotColor}"></span><span>${alertLabel}</span>`;
  }

  // Radial Gauge (circumference for r=50 is ~314.16)
  const circleEl = document.getElementById('radialGaugeCircle');
  const numberEl = document.getElementById('radialGaugeNumber');

  if (numberEl) {
    numberEl.innerHTML = `${common.formatNumber(probPercent, 2)}<span class="text-headline-sm font-normal">%</span>`;
  }

  if (circleEl) {
    const totalCircumference = 314.16;
    const offset = totalCircumference - (totalCircumference * (Math.min(probPercent, 100) / 100));
    circleEl.style.strokeDasharray = `${totalCircumference}`;
    circleEl.style.strokeDashoffset = `${offset}`;
    circleEl.setAttribute('stroke', risk.dotColor);
  }

  // Classification & Recommendation Block
  const classLabel = document.getElementById('classificationLabel');
  const classDesc = document.getElementById('classificationDesc');
  const dataQuality = document.getElementById('classificationDataQuality');

  if (classLabel && pred) {
    classLabel.innerHTML = `
      <span class="material-symbols-outlined text-[18px]" style="color: ${risk.dotColor}">warning</span>
      <span style="color: ${risk.dotColor}">Class ${pred.class} (${pred.class === 1 ? 'Flood Hazard Likely within 24-48h' : 'Sub-Hazard / Low Risk'})</span>
    `;
  }

  if (classDesc && pred) {
    const alertRec = (activeAlerts && activeAlerts.length > 0) ? activeAlerts[0].recommendation : null;
    classDesc.textContent = alertRec || pred.recommendation || 
      `Inference engine evaluates 64 hydro-meteorological features including antecedent rainfall accumulation, elevation (${loc?.elevation_m || 4.5}m ASL), and distance to river channels (${loc?.distance_to_river_m || 200}m).`;
  }

  if (dataQuality && pred) {
    dataQuality.textContent = `${pred.data_quality_status || 'GOOD'} (${pred.features_used_count || 64}/64 Features)`;
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
  if (channelDistance) channelDistance.textContent = `Distance to River: ${common.formatNumber(loc.distance_to_river_m, 0)}m`;
  if (channelElevation) channelElevation.textContent = `Elevation: ${common.formatNumber(loc.elevation_m, 1)}m ASL`;
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

  if (tempEl) tempEl.textContent = common.formatNumber(current.temperature_c, 1, '--');
  if (humidityEl) humidityEl.textContent = common.formatNumber(current.humidity_percent, 0, '--');
  if (rainEl) rainEl.textContent = common.formatNumber(current.precipitation_mm, 1, '0.0');
  if (windEl) windEl.textContent = common.formatNumber(current.wind_speed_kmh, 1, '--');
  if (dischargeEl) dischargeEl.textContent = current.river_discharge_m3s !== undefined ? common.formatNumber(current.river_discharge_m3s, 1) : 'N/A';
}

/**
 * Precipitation Analytics
 */
function renderPrecipitationAnalytics(weather) {
  const rolling = weather ? weather.rolling_aggregations : {};

  const rain7El = document.getElementById('detailRain7');
  const rain30El = document.getElementById('detailRain30');
  const maxRainEl = document.getElementById('detailMaxDailyRain');

  if (rain7El) rain7El.textContent = `${common.formatNumber(rolling.precipitation_sum_7d_mm, 1, '0.0')} mm`;
  if (rain30El) rain30El.textContent = `${common.formatNumber(rolling.precipitation_sum_30d_mm, 1, '0.0')} mm`;
  if (maxRainEl) maxRainEl.textContent = `${common.formatNumber(rolling.max_daily_rainfall_7d_mm, 1, '0.0')} mm`;
}

/**
 * Geospatial Vulnerability Matrix
 */
function renderVulnerabilityMatrix(loc) {
  if (!loc) return;

  const setVal = (id, val, unit = '') => {
    const el = document.getElementById(id);
    if (el) el.textContent = val !== null && val !== undefined ? `${val}${unit}` : 'Not available';
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
  const pred = predRes ? predRes.prediction : null;
  const prob1 = pred ? (pred.flood_probability_percent || pred.flood_probability * 100) : 0;
  const prob0 = 100 - prob1;

  const class1Val = document.getElementById('splitClass1Val');
  const class0Val = document.getElementById('splitClass0Val');
  const class1Bar = document.getElementById('splitClass1Bar');
  const class0Bar = document.getElementById('splitClass0Bar');

  if (class1Val) class1Val.textContent = `${common.formatNumber(prob1, 2)}%`;
  if (class0Val) class0Val.textContent = `${common.formatNumber(prob0, 2)}%`;
  if (class1Bar) class1Bar.style.width = `${Math.min(prob1, 100)}%`;
  if (class0Bar) class0Bar.style.width = `${Math.min(prob0, 100)}%`;
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
      ['Elevation (m)', stationData.elevation_m || ''],
      ['Distance to River (m)', stationData.distance_to_river_m || ''],
      ['Population Density', stationData.population_density_per_km2 || ''],
      ['Built-up %', stationData.built_up_percent || ''],
      ['Drainage Index', stationData.drainage_index || ''],
      ['Ambient Temp (°C)', weatherData?.current?.temperature_c || ''],
      ['Relative Humidity (%)', weatherData?.current?.humidity_percent || ''],
      ['7-Day Rain (mm)', weatherData?.rolling_aggregations?.precipitation_sum_7d_mm || ''],
      ['30-Day Rain (mm)', weatherData?.rolling_aggregations?.precipitation_sum_30d_mm || ''],
      ['Flood Probability (%)', predictionData?.prediction?.flood_probability_percent || ''],
      ['Prediction Class', predictionData?.prediction?.class || ''],
      ['Risk Level', predictionData?.prediction?.risk_level || '']
    ];

    const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `station_${stationData.id}_telemetry_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });
}
