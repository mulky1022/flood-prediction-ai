/**
 * Alerts & Prediction History Controller
 * Phase 7: Real Backend Alert and Notification Integration
 */

import { api } from './api.js';
import { common } from './common.js';

let allLocations = [];
let stationEntries = [];
let activeAlertsList = [];
let allAlertsHistory = [];
let filteredEntries = [];

let filterDistrict = '';
let filterRisk = '';
let filterSearch = '';
let filterStatus = '';

document.addEventListener('DOMContentLoaded', async () => {
  common.initHeader('alerts-history');

  setupFiltersAndSearch();
  await loadAlertsAndHistory();
});

/**
 * Setup event listeners for filter dropdowns, search input, and export
 */
function setupFiltersAndSearch() {
  const districtSelect = document.getElementById('filterDistrict');
  const riskSelect = document.getElementById('filterRisk');
  const searchInput = document.getElementById('searchAlerts');
  const exportBtn = document.getElementById('btnExportAuditLog');

  if (districtSelect) {
    districtSelect.addEventListener('change', (e) => {
      filterDistrict = e.target.value.toLowerCase().trim();
      applyFilters();
    });
  }

  if (riskSelect) {
    riskSelect.addEventListener('change', (e) => {
      filterRisk = e.target.value.toLowerCase().trim();
      applyFilters();
    });
  }

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      filterSearch = e.target.value.toLowerCase().trim();
      applyFilters();
    });
  }

  if (exportBtn) {
    exportBtn.addEventListener('click', exportAuditCsv);
  }
}

/**
 * Fetch real alerts from backend and assemble station inferences
 */
async function loadAlertsAndHistory() {
  try {
    // 1. Fetch Locations & Active Alerts in parallel
    const [locRes, activeAlertsRes, allAlertsRes] = await Promise.all([
      api.getLocations().catch(() => ({ locations: [] })),
      api.getActiveAlerts(50).catch(() => ({ items: [] })),
      api.getAlerts({ limit: 100 }).catch(() => ({ items: [] }))
    ]);

    allLocations = locRes.locations || [];
    activeAlertsList = activeAlertsRes.items || [];
    allAlertsHistory = allAlertsRes.items || [];

    populateDistrictFilter(allLocations);

    // 2. Fetch predictions and weather for monitored stations
    const entryPromises = allLocations.map(async (loc) => {
      try {
        const [predData, weatherData] = await Promise.all([
          api.getPrediction(loc.id).catch(() => null),
          api.getWeather(loc.id).catch(() => null)
        ]);

        const pred = predData ? predData.prediction : null;
        const weather = weatherData ? weatherData : null;

        return {
          id: loc.id,
          location: loc,
          prediction: pred,
          weather: weather,
          timestamp: new Date().toISOString()
        };
      } catch (e) {
        return null;
      }
    });

    const entries = await Promise.all(entryPromises);
    stationEntries = entries.filter(Boolean);

    renderKpiSummary(stationEntries, activeAlertsList);
    renderAlertStream(activeAlertsList, stationEntries);
    applyFilters();

  } catch (err) {
    console.error('Error loading alerts and history:', err);
  }
}

/**
 * Populate district filter dropdown
 */
function populateDistrictFilter(locations) {
  const select = document.getElementById('filterDistrict');
  if (!select) return;

  const districts = [...new Set(locations.map(l => l.district))].sort();
  select.innerHTML = '<option value="">All Districts (Colombo, Gampaha, Kalutara...)</option>';

  districts.forEach(dist => {
    const opt = document.createElement('option');
    opt.value = dist;
    opt.textContent = `${dist} District`;
    select.appendChild(opt);
  });
}

/**
 * Render KPI Summary Cards
 */
function renderKpiSummary(entries, activeAlerts) {
  let highCount = 0, modCount = 0, lowCount = 0;
  const highPoints = [];
  const modPoints = [];
  const lowPoints = [];

  // Categorize based on active alerts if present, or inference entries
  entries.forEach(item => {
    const pred = item.prediction;
    const prob = pred ? pred.flood_probability : 0;
    const risk = common.getRiskDetails(pred ? pred.risk_level : 'LOW', prob);

    if (risk.key === 'critical' || risk.key === 'high') {
      highCount++;
      if (highPoints.length < 3) highPoints.push(item.location.place_name.split(' ')[0]);
    } else if (risk.key === 'moderate') {
      modCount++;
      if (modPoints.length < 5) modPoints.push(item.location.place_name.split(' ')[0]);
    } else {
      lowCount++;
      if (lowPoints.length < 6) lowPoints.push(item.location.place_name.split(' ')[0]);
    }
  });

  const kpiHighCount = document.getElementById('kpiHighCount');
  const kpiHighList = document.getElementById('kpiHighList');
  const kpiModCount = document.getElementById('kpiModCount');
  const kpiModList = document.getElementById('kpiModList');
  const kpiLowCount = document.getElementById('kpiLowCount');
  const kpiLowList = document.getElementById('kpiLowList');

  if (kpiHighCount) kpiHighCount.textContent = String(highCount).padStart(2, '0');
  if (kpiHighList) {
    kpiHighList.innerHTML = highPoints.map(p => `<span class="bg-surface-container px-1.5 py-0.5 rounded text-on-surface font-medium">${p}</span>`).join('') || '<span class="text-xs text-outline">None active</span>';
  }

  if (kpiModCount) kpiModCount.textContent = String(modCount).padStart(2, '0');
  if (kpiModList) kpiModList.textContent = modPoints.join(', ') || 'None';

  if (kpiLowCount) kpiLowCount.textContent = String(lowCount).padStart(2, '0');
  if (kpiLowList) kpiLowList.textContent = lowPoints.join(', ') || 'All standard baselines';
}

/**
 * Render Active Alert Stream from real backend active alerts
 */
function renderAlertStream(activeAlerts, entries) {
  const container = document.getElementById('activeAlertStreamGrid');
  const alertCountBadge = document.getElementById('alertCountBadge');
  if (!container) return;

  // Use real active alerts from backend
  if (alertCountBadge) {
    alertCountBadge.textContent = `${activeAlerts.length} Active Operational Alerts`;
  }

  if (!activeAlerts.length) {
    // If no explicit persistent alerts, check for elevated inferences in live stream
    const elevatedInferences = entries.filter(item => {
      const pred = item.prediction;
      return pred && (pred.flood_probability >= 0.35 || pred.risk_level === 'HIGH' || pred.risk_level === 'CRITICAL');
    });

    if (!elevatedInferences.length) {
      container.innerHTML = `
        <div class="col-span-2 p-6 bg-surface-container-lowest rounded-xl text-center text-on-surface-variant font-body-md border border-surface-container">
          <div class="flex flex-col items-center gap-2">
            <span class="material-symbols-outlined text-emerald-600 text-[28px]">verified</span>
            <span class="font-semibold text-on-surface">No active flood risk alerts at this time.</span>
            <span class="text-xs text-on-surface-variant">All monitored Sri Lankan river basins are currently operating within normal baseline limits.</span>
          </div>
        </div>
      `;
      return;
    }

    // Render elevated inferences as provisional stream
    container.innerHTML = elevatedInferences.slice(0, 4).map(item => renderProvisionalAlertCard(item)).join('');
    return;
  }

  // Render real active alerts
  container.innerHTML = activeAlerts.slice(0, 6).map(alert => renderRealAlertCard(alert)).join('');
}

/**
 * Render an individual real active alert card with interactive actions
 */
function renderRealAlertCard(alert) {
  const loc = alert.location || { place_name: `Location ${alert.location_id}`, district: 'Sri Lanka' };
  const probPct = common.formatNumber(alert.flood_probability_percent || alert.flood_probability * 100, 2);
  const risk = common.getRiskDetails(alert.risk_level, alert.flood_probability);

  const stripeClass = risk.key === 'critical' ? 'alert-stripe-crit' :
                      risk.key === 'high' ? 'alert-stripe-high' :
                      risk.key === 'moderate' ? 'alert-stripe-mod' : 'alert-stripe-low';

  const isAcknowledged = alert.status === 'ACKNOWLEDGED';

  return `
    <div class="alert-card" id="alert-card-${alert.id}">
      <div class="${stripeClass}"></div>
      <div class="flex flex-col gap-2 pl-2">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded font-label-md text-label-md font-bold uppercase tracking-wider flex items-center gap-1 ${risk.badgeBg}">
              <span class="w-1.5 h-1.5 rounded-full" style="background-color: ${risk.dotColor}"></span>
              ${risk.label}
            </span>
            <span class="px-1.5 py-0.5 rounded text-xs font-semibold ${isAcknowledged ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'}">
              ${alert.status}
            </span>
            <span class="font-data-timestamp text-data-timestamp text-outline">|</span>
            <span class="font-data-timestamp text-data-timestamp text-on-surface-variant font-medium">${common.formatTime(alert.updated_at || alert.created_at)}</span>
          </div>
          <span class="font-data-display text-data-display font-bold" style="color: ${risk.textColor}">${probPct}%</span>
        </div>

        <div class="flex flex-col">
          <h3 class="font-headline-sm text-headline-sm text-on-surface font-bold">${loc.place_name}</h3>
          <span class="font-label-md text-label-md text-secondary font-medium uppercase">${loc.district} Catchment Area</span>
        </div>

        <div class="bg-surface-container-low p-2.5 rounded-lg flex flex-col gap-1.5">
          <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
            ${alert.message || 'Elevated flood risk probability detected.'}
          </p>
          ${alert.recommendation ? `
            <div class="text-xs text-on-surface bg-surface-container/60 p-1.5 rounded flex items-start gap-1">
              <span class="material-symbols-outlined text-secondary text-[14px] mt-0.5">info</span>
              <span><strong>Action:</strong> ${alert.recommendation}</span>
            </div>
          ` : ''}
        </div>
      </div>

      <div class="flex items-center justify-between pt-2 pl-2 border-t border-surface-container gap-2">
        <div class="flex items-center gap-1 font-data-timestamp text-data-timestamp text-on-surface-variant">
          <span class="material-symbols-outlined text-[15px]">notifications</span>
          <span>Notif: ${alert.notification_status || 'NOT_REQUIRED'}</span>
        </div>
        <div class="flex items-center gap-1.5">
          ${!isAcknowledged ? `
            <button class="btn btn-secondary btn-sm" onclick="window.handleAcknowledgeAlert(${alert.id})">
              <span>Ack</span>
            </button>
          ` : ''}
          <button class="btn btn-secondary btn-sm" onclick="window.handleResolveAlert(${alert.id})">
            <span>Resolve</span>
          </button>
          <a class="btn btn-primary btn-sm" href="district.html?location_id=${alert.location_id}">
            <span>Details</span>
            <span class="material-symbols-outlined text-[14px]">arrow_forward</span>
          </a>
        </div>
      </div>
    </div>
  `;
}

/**
 * Render provisional alert card from real-time elevated inference
 */
function renderProvisionalAlertCard(item) {
  const loc = item.location;
  const pred = item.prediction;
  const weather = item.weather;
  const probPct = common.formatNumber(pred.flood_probability_percent || pred.flood_probability * 100, 2);
  const risk = common.getRiskDetails(pred.risk_level, pred.flood_probability);
  const rain7 = weather?.rolling_aggregations?.precipitation_sum_7d_mm;
  const rain30 = weather?.rolling_aggregations?.precipitation_sum_30d_mm;
  const discharge = weather?.current?.river_discharge_m3s;

  const stripeClass = risk.key === 'critical' ? 'alert-stripe-crit' :
                      risk.key === 'high' ? 'alert-stripe-high' :
                      risk.key === 'moderate' ? 'alert-stripe-mod' : 'alert-stripe-low';

  return `
    <div class="alert-card">
      <div class="${stripeClass}"></div>
      <div class="flex flex-col gap-2 pl-2">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded font-label-md text-label-md font-bold uppercase tracking-wider flex items-center gap-1 ${risk.badgeBg}">
              <span class="w-1.5 h-1.5 rounded-full" style="background-color: ${risk.dotColor}"></span>
              ${risk.label}
            </span>
            <span class="font-data-timestamp text-data-timestamp text-outline">|</span>
            <span class="font-data-timestamp text-data-timestamp text-on-surface-variant font-medium">${common.formatTime()}</span>
          </div>
          <span class="font-data-display text-data-display font-bold" style="color: ${risk.textColor}">${probPct}%</span>
        </div>

        <div class="flex flex-col">
          <h3 class="font-headline-sm text-headline-sm text-on-surface font-bold">${loc.place_name}</h3>
          <span class="font-label-md text-label-md text-secondary font-medium uppercase">${loc.district} Catchment Area</span>
        </div>

        <div class="bg-surface-container-low p-2.5 rounded-lg flex flex-col gap-1.5">
          <div class="flex items-center justify-between font-label-md text-label-md">
            <span class="text-on-surface-variant">Basin Runoff Profile</span>
            <span class="font-semibold" style="color: ${risk.textColor}">${risk.label} Status</span>
          </div>
          <div class="w-full h-2 bg-surface-container rounded-full overflow-hidden flex">
            <div class="h-full rounded-full transition-all duration-500" style="width: ${Math.min(probPct, 100)}%; background-color: ${risk.dotColor}"></div>
          </div>
          <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
            7d Rain: <strong>${common.formatNumber(rain7, 1, '0.0')} mm</strong> • 30d Rain: <strong>${common.formatNumber(rain30, 1, '0.0')} mm</strong> • Discharge: <strong>${discharge !== undefined ? common.formatNumber(discharge, 1) + ' m³/s' : 'N/A'}</strong>
          </p>
        </div>
      </div>

      <div class="flex items-center justify-between pt-1 pl-2 border-t border-surface-container">
        <div class="flex items-center gap-1 font-data-timestamp text-data-timestamp text-on-surface-variant">
          <span class="material-symbols-outlined text-[15px]">analytics</span>
          <span>Model: RandomForest v1.0.0</span>
        </div>
        <a class="btn btn-secondary btn-sm" href="district.html?location_id=${loc.id}">
          <span>View Details</span>
          <span class="material-symbols-outlined text-[16px]">arrow_forward</span>
        </a>
      </div>
    </div>
  `;
}

// Global action handlers for alerts
window.handleAcknowledgeAlert = async (alertId) => {
  try {
    await api.acknowledgeAlert(alertId);
    await loadAlertsAndHistory();
  } catch (e) {
    alert(`Could not acknowledge alert: ${e.message}`);
  }
};

window.handleResolveAlert = async (alertId) => {
  try {
    await api.resolveAlert(alertId);
    await loadAlertsAndHistory();
  } catch (e) {
    alert(`Could not resolve alert: ${e.message}`);
  }
};

/**
 * Filter and render Comprehensive Inference History Table
 */
function applyFilters() {
  filteredEntries = stationEntries.filter(item => {
    const loc = item.location;
    const pred = item.prediction;
    if (!loc) return false;

    // Filter by district
    if (filterDistrict && !loc.district.toLowerCase().includes(filterDistrict)) {
      return false;
    }

    // Filter by risk
    if (filterRisk) {
      const risk = common.getRiskDetails(pred ? pred.risk_level : 'LOW', pred ? pred.flood_probability : 0);
      if (filterRisk === 'high' && risk.key !== 'high' && risk.key !== 'critical') return false;
      if (filterRisk === 'moderate' && risk.key !== 'moderate') return false;
      if (filterRisk === 'low' && risk.key !== 'low') return false;
    }

    // Filter by search
    if (filterSearch) {
      const matchDistrict = (loc.district || '').toLowerCase().includes(filterSearch);
      const matchPlace = (loc.place_name || '').toLowerCase().includes(filterSearch);
      if (!matchDistrict && !matchPlace) return false;
    }

    return true;
  });

  renderHistoryTable(filteredEntries);
}

/**
 * Render History Table
 */
function renderHistoryTable(entries) {
  const tbody = document.getElementById('historyTableBody');
  const emptyEl = document.getElementById('historyTableEmpty');
  if (!tbody) return;

  if (!entries.length) {
    tbody.innerHTML = '';
    if (emptyEl) emptyEl.classList.remove('hidden');
    return;
  }

  if (emptyEl) emptyEl.classList.add('hidden');

  tbody.innerHTML = entries.map(item => {
    const loc = item.location;
    const pred = item.prediction;
    const weather = item.weather;
    const prob = pred ? (pred.flood_probability_percent || pred.flood_probability * 100) : 0;
    const risk = common.getRiskDetails(pred ? pred.risk_level : 'LOW', pred ? pred.flood_probability : 0);
    const rain7 = weather?.rolling_aggregations?.precipitation_sum_7d_mm;

    return `
      <tr class="hover:bg-surface-container-low/60 transition-colors">
        <td class="py-3 px-4 font-data-timestamp text-data-timestamp text-on-surface-variant font-medium">
          ${common.formatTime(item.timestamp)}
        </td>
        <td class="py-3 px-4">
          <div class="flex flex-col">
            <span class="font-headline-sm text-headline-sm text-on-surface font-semibold">${loc.place_name}</span>
            <span class="font-label-md text-label-md text-on-surface-variant">${loc.district} Catchment</span>
          </div>
        </td>
        <td class="py-3 px-4 font-medium">${loc.district}</td>
        <td class="py-3 px-4 font-data-metric text-data-metric">${common.formatNumber(rain7, 1, '0.0')} mm</td>
        <td class="py-3 px-4 font-data-metric text-data-metric font-bold" style="color: ${risk.textColor}">
          ${common.formatNumber(prob, 2)}%
        </td>
        <td class="py-3 px-4">
          <span class="px-2 py-0.5 rounded font-label-md text-label-md font-bold inline-flex items-center gap-1 ${risk.badgeBg}">
            <span class="w-1.5 h-1.5 rounded-full" style="background-color: ${risk.dotColor}"></span>
            Class ${pred ? pred.class : 0} (${pred?.class === 1 ? 'Flood' : 'Normal'})
          </span>
        </td>
        <td class="py-3 px-4 font-data-timestamp text-data-timestamp text-on-surface-variant">
          RandomForest v1.0.0 / 64 feats
        </td>
        <td class="py-3 px-4">
          <span class="px-1.5 py-0.5 rounded bg-surface-container text-secondary font-label-md text-label-md font-semibold">
            ${pred?.data_quality_status || 'GOOD'}
          </span>
        </td>
        <td class="py-3 px-4 text-right">
          <a class="btn btn-secondary btn-sm" href="district.html?location_id=${loc.id}">Inspect</a>
        </td>
      </tr>
    `;
  }).join('');
}

/**
 * Export Audit Log as CSV
 */
function exportAuditCsv() {
  const rows = [
    ['Timestamp', 'Place Name', 'District', 'Latitude', 'Longitude', '7-Day Rain (mm)', '30-Day Rain (mm)', 'River Discharge (m3/s)', 'Flood Probability (%)', 'Class', 'Risk Level', 'Data Quality']
  ];

  filteredEntries.forEach(item => {
    const loc = item.location;
    const pred = item.prediction;
    const weather = item.weather;

    rows.push([
      item.timestamp,
      `"${loc.place_name}"`,
      loc.district,
      loc.latitude,
      loc.longitude,
      weather?.rolling_aggregations?.precipitation_sum_7d_mm || '0.0',
      weather?.rolling_aggregations?.precipitation_sum_30d_mm || '0.0',
      weather?.current?.river_discharge_m3s !== undefined ? weather.current.river_discharge_m3s : 'N/A',
      pred ? pred.flood_probability_percent || (pred.flood_probability * 100).toFixed(2) : '',
      pred ? pred.class : '',
      pred ? pred.risk_level : '',
      pred ? pred.data_quality_status : 'GOOD'
    ]);
  });

  const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `floodwatch_audit_log_${Date.now()}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
