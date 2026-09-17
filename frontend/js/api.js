/**
 * Central API Client for Sri Lanka FloodWatch
 * Handles all communication with FastAPI backend endpoints.
 */

const API_CONFIG = {
  // Configurable base URL:
  // 1. window.FLOODWATCH_API_BASE_URL if explicitly set
  // 2. Current origin + '/api/v1' when hosted on web server or FastAPI mount
  // 3. Fallback to local 'http://127.0.0.1:8000/api/v1'
  BASE_URL: (() => {
    if (typeof window !== 'undefined' && window.FLOODWATCH_API_BASE_URL) {
      return window.FLOODWATCH_API_BASE_URL.replace(/\/$/, '');
    }
    if (typeof window !== 'undefined' && window.location && window.location.origin && window.location.origin !== 'null' && !window.location.origin.startsWith('file:')) {
      return (window.location.origin + '/api/v1').replace(/\/$/, '');
    }
    return 'http://127.0.0.1:8000/api/v1';
  })(),
  TIMEOUT_MS: 15000
};

/**
 * Generic fetch wrapper with timeout, error handling, and JSON parsing
 */
async function fetchJson(endpoint, options = {}) {
  const url = `${API_CONFIG.BASE_URL}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options.timeout || API_CONFIG.TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        ...(options.headers || {})
      }
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorDetail = `HTTP ${response.status} ${response.statusText}`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch (e) {
        // Fallback to status text if body is not JSON
      }
      throw new Error(errorDetail);
    }

    return await response.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error(`API request timed out after ${API_CONFIG.TIMEOUT_MS / 1000}s`);
    }
    console.error(`[API Error] ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  /**
   * Health and service status check
   * @returns {Promise<{status: string, service: string, version: string, model_loaded: boolean, database_connected: boolean}>}
   */
  async getHealth() {
    return fetchJson('/health');
  },

  /**
   * Get public client configuration (e.g. CARTO API key, environment settings)
   * @returns {Promise<{status: string, carto_api_key: string, app_env: string, version: string}>}
   */
  async getConfig() {
    return fetchJson('/config');
  },

  /**
   * Get all 33 monitoring stations across Sri Lanka
   * @returns {Promise<{status: string, total: number, locations: Array}>}
   */
  async getLocations() {
    return fetchJson('/locations');
  },

  /**
   * Get single location geospatial attributes by numeric ID
   * @param {number|string} locationId
   * @returns {Promise<Object>}
   */
  async getLocation(locationId) {
    return fetchJson(`/locations/${locationId}`);
  },

  /**
   * Get live weather observations & rolling precipitation aggregations
   * @param {number|string} locationId
   * @returns {Promise<{status: string, location: Object, current: Object, rolling_aggregations: Object, source: string, timestamp: string}>}
   */
  async getWeather(locationId) {
    return fetchJson(`/weather/${locationId}`);
  },

  /**
   * Run real-time ML inference for a location
   * @param {number|string} locationId
   * @returns {Promise<{status: string, ready_for_prediction: boolean, location: Object, prediction: Object}>}
   */
  async getPrediction(locationId) {
    return fetchJson(`/predict/${locationId}`);
  },

  /**
   * Get prediction history for a specific location
   * @param {number|string} locationId
   * @param {number} limit
   * @returns {Promise<{status: string, location_id: number, total: number, items: Array}>}
   */
  async getPredictionHistory(locationId, limit = 50) {
    return fetchJson(`/predictions/${locationId}?limit=${limit}`);
  },

  /**
   * Get latest recorded prediction record
   * @param {number|string} locationId
   * @returns {Promise<Object>}
   */
  async getLatestPrediction(locationId) {
    return fetchJson(`/predictions/${locationId}/latest`);
  },

  /**
   * Get all alerts with optional filtering
   * @param {Object} params - { status, risk_level, district, limit, offset }
   * @returns {Promise<{status: string, total: number, active_count: number, items: Array}>}
   */
  async getAlerts(params = {}) {
    const query = new URLSearchParams();
    if (params.status) query.set('status', params.status);
    if (params.risk_level) query.set('risk_level', params.risk_level);
    if (params.district) query.set('district', params.district);
    if (params.limit) query.set('limit', params.limit);
    if (params.offset) query.set('offset', params.offset);
    const qs = query.toString();
    return fetchJson(`/alerts${qs ? '?' + qs : ''}`);
  },

  /**
   * Get only currently active alerts
   * @param {number} limit
   * @returns {Promise<{status: string, total: number, active_count: number, items: Array}>}
   */
  async getActiveAlerts(limit = 50) {
    return fetchJson(`/alerts/active?limit=${limit}`);
  },

  /**
   * Get single alert details by ID
   * @param {number|string} alertId
   * @returns {Promise<Object>}
   */
  async getAlert(alertId) {
    return fetchJson(`/alerts/${alertId}`);
  },

  /**
   * Get all alerts for a specific location
   * @param {number|string} locationId
   * @returns {Promise<{status: string, location_id: number, total: number, active_count: number, items: Array}>}
   */
  async getAlertsByLocation(locationId) {
    return fetchJson(`/alerts/location/${locationId}`);
  },

  /**
   * Alias for getAlertsByLocation
   */
  async getLocationAlerts(locationId) {
    return this.getAlertsByLocation(locationId);
  },

  /**
   * Acknowledge an active alert
   * @param {number|string} alertId
   * @returns {Promise<Object>}
   */
  async acknowledgeAlert(alertId) {
    return fetchJson(`/alerts/${alertId}/acknowledge`, { method: 'POST' });
  },

  /**
   * Resolve an alert
   * @param {number|string} alertId
   * @returns {Promise<Object>}
   */
  async resolveAlert(alertId) {
    return fetchJson(`/alerts/${alertId}/resolve`, { method: 'POST' });
  },

  /**
   * Trigger alert evaluation for a location
   * @param {number|string} locationId
   * @returns {Promise<Object>}
   */
  async processAlerts(locationId) {
    return fetchJson(`/alerts/process/${locationId}`, { method: 'POST' });
  }
};

// Also attach to window for non-module scripts if needed
if (typeof window !== 'undefined') {
  window.floodWatchApi = api;
}

