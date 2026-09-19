/**
 * Sri Lanka FloodWatch — Centralized Open-Source Map & GIS Configuration
 * 100% Free & Open-Source GIS basemaps:
 * 1. Humanitarian OpenStreetMap (HOT) - Disaster & Flood Risk Mapping
 * 2. OpenStreetMap Standard (OSM) - Comprehensive Geographic & Hydrological Base
 * NO API keys required, NO watermarks, 100% Open Access.
 */

export const MAP_CONFIG = {
  DEFAULT_CENTER: [7.8731, 80.7718], // Sri Lanka Centroid (Lat, Lon)
  DEFAULT_ZOOM_FULL: 8,
  DEFAULT_ZOOM_MINI: 7,
  MIN_ZOOM: 6,
  MAX_ZOOM: 19,
  SRI_LANKA_BOUNDS: [[5.85, 79.50], [9.90, 81.95]],
  
  // Primary Basemap: Humanitarian OpenStreetMap (HOT)
  PRIMARY_TILES: {
    name: 'Humanitarian OSM (HOT)',
    url: 'https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
    options: {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors, Tiles style by <a href="https://www.hotosm.org/" target="_blank" rel="noopener">Humanitarian OpenStreetMap Team</a> hosted by <a href="https://openstreetmap.fr/" target="_blank" rel="noopener">OSM France</a>',
      subdomains: 'abc',
      maxZoom: 19,
      detectRetina: false
    }
  },
  
  // Secondary / Standard Basemap: OpenStreetMap Standard (OSM)
  STANDARD_TILES: {
    name: 'OpenStreetMap Standard',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    options: {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
      maxZoom: 19,
      detectRetina: false
    }
  },
  
  // Fallback: OpenStreetMap Standard
  FALLBACK_TILES: {
    name: 'OpenStreetMap Standard (Fallback)',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    options: {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
      maxZoom: 19
    }
  }
};

/**
 * Returns the active open-source tile layer configuration (HOT by default)
 */
export function getOpenSourceTileLayer(type = 'hot') {
  if (type === 'osm' || type === 'standard') {
    return MAP_CONFIG.STANDARD_TILES;
  }
  return MAP_CONFIG.PRIMARY_TILES;
}
