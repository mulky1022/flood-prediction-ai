/**
 * Sri Lanka FloodWatch — Unified Open-Source Map Utilities & Centralized GIS Engine
 * Standardized for both Dashboard Map Preview and Full Flood Monitoring Map.
 * Powered by Humanitarian OpenStreetMap (HOT) & OpenStreetMap Standard.
 */

import { SRI_LANKA_BOUNDARY_GEOJSON } from './sri_lanka_boundary.js';
import { MAP_CONFIG, getOpenSourceTileLayer } from './map-config.js';

export { MAP_CONFIG, getOpenSourceTileLayer };

/**
 * Validate geographic coordinate bounds (WGS 84 / EPSG:4326)
 */
export function isValidCoord(lat, lon) {
  const numLat = parseFloat(lat);
  const numLon = parseFloat(lon);
  return !isNaN(numLat) && !isNaN(numLon) && numLat >= -90 && numLat <= 90 && numLon >= -180 && numLon <= 180;
}

/**
 * Initialize base map tile layer using 100% Free Open-Source Humanitarian OSM & OSM Standard
 * @param {L.Map} mapInstance 
 * @param {Function} onTileError 
 * @returns {L.TileLayer}
 */
export function setupTileLayer(mapInstance, onTileError = null) {
  let activeLayer = null;
  let fallbackAttempted = false;

  const primaryTiles = MAP_CONFIG.PRIMARY_TILES;

  const tryFallback = () => {
    if (fallbackAttempted) {
      if (onTileError) onTileError('BASE_MAP_UNAVAILABLE');
      return;
    }
    fallbackAttempted = true;
    console.warn('[Map Engine] Primary Humanitarian OSM (HOT) tile layer failed. Attempting OpenStreetMap Standard fallback...');

    if (activeLayer && mapInstance.hasLayer(activeLayer)) {
      mapInstance.removeLayer(activeLayer);
    }

    const fallbackLayer = L.tileLayer(MAP_CONFIG.FALLBACK_TILES.url, MAP_CONFIG.FALLBACK_TILES.options);
    fallbackLayer.on('tileerror', () => {
      console.error('[Map Engine] Fallback OpenStreetMap tile layer failed.');
      if (onTileError) onTileError('BASE_MAP_UNAVAILABLE');
    });
    fallbackLayer.addTo(mapInstance);
    activeLayer = fallbackLayer;
  };

  activeLayer = L.tileLayer(primaryTiles.url, primaryTiles.options);
  activeLayer.on('tileerror', () => {
    tryFallback();
  });

  activeLayer.addTo(mapInstance);
  console.info('[Map Engine] Initialized 100% Free Open-Source Humanitarian OSM (HOT) Basemap.');
  return activeLayer;
}

/**
 * Add Sri Lanka country boundary polygon to map
 * Ensures geographic country outline is clearly visible.
 * @param {L.Map} mapInstance 
 * @param {Object} customStyle 
 * @returns {L.GeoJSON}
 */
export function addBoundaryLayer(mapInstance, customStyle = {}) {
  const defaultStyle = {
    color: '#0284c7',
    weight: 2,
    opacity: 0.9,
    fillColor: '#0369a1',
    fillOpacity: 0.1,
    dashArray: '3, 4'
  };

  try {
    const boundaryLayer = L.geoJSON(SRI_LANKA_BOUNDARY_GEOJSON, {
      style: { ...defaultStyle, ...customStyle },
      interactive: false
    }).addTo(mapInstance);
    return boundaryLayer;
  } catch (err) {
    console.warn('[Map Engine] Could not load Sri Lanka boundary GeoJSON layer:', err);
    return null;
  }
}

/**
 * Generate custom Leaflet DivIcon for a monitoring station
 * @param {Object} riskDetails { dotColor, key }
 * @param {boolean} isSelected 
 * @param {boolean} isMini 
 * @returns {L.DivIcon}
 */
export function createStationDivIcon(riskDetails, isSelected = false, isMini = false) {
  const isHighOrCrit = riskDetails.key === 'critical' || riskDetails.key === 'high';
  const size = isMini ? (isSelected ? 24 : 18) : (isSelected ? 36 : 28);
  const half = size / 2;

  const pulseRing = (isHighOrCrit && !isMini) 
    ? `<div class="marker-pulse-ring" style="background-color: ${riskDetails.dotColor}; opacity: 0.4;"></div>` 
    : '';

  const outerRing = !isMini
    ? `<div class="marker-outer-ring" style="background-color: ${riskDetails.dotColor};"></div>`
    : '';

  const dotSize = isMini ? (isSelected ? '8px' : '6px') : (isSelected ? '14px' : '10px');

  const html = `
    <div class="leaflet-station-marker ${isSelected ? 'selected-marker' : ''} ${isMini ? 'mini-marker' : ''}">
      <div class="marker-pin-wrapper">
        ${pulseRing}
        ${outerRing}
        <div class="marker-inner-dot" style="background-color: ${riskDetails.dotColor}; width: ${dotSize}; height: ${dotSize};"></div>
      </div>
    </div>
  `;

  return L.divIcon({
    html: html,
    className: 'custom-station-icon-wrapper',
    iconSize: [size, size],
    iconAnchor: [half, half],
    popupAnchor: [0, -half]
  });
}
