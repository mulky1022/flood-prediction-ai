"""
Location Service for Sri Lanka Static Geographic & Environmental Data.

Loads and queries validated static location records from data/locations.json.
Provides accessors for district filtering, ID lookup, and full-text search.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("LocationService")

# Base directory relative path resolution
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "locations.json"

_LOCATIONS_CACHE: Optional[List[Dict[str, Any]]] = None


def load_locations(data_file: Optional[Union[str, Path]] = None, reload: bool = False) -> List[Dict[str, Any]]:
    """
    Loads all static location records from the JSON dataset into memory cache.
    """
    global _LOCATIONS_CACHE

    if _LOCATIONS_CACHE is not None and not reload and data_file is None:
        return _LOCATIONS_CACHE

    file_to_load = Path(data_file) if data_file else DATA_PATH

    if not file_to_load.exists():
        logger.error(f"Locations data file not found at: {file_to_load}")
        raise FileNotFoundError(f"Locations data file not found: {file_to_load}")

    try:
        with open(file_to_load, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(f"Expected JSON array in {file_to_load}, got {type(data)}")

        if data_file is None:
            _LOCATIONS_CACHE = data

        return data

    except Exception as e:
        logger.error(f"Error loading location data: {e}", exc_info=True)
        raise RuntimeError(f"Failed to load locations: {e}")


def get_all_locations() -> List[Dict[str, Any]]:
    """
    Returns a copy of all static location records.
    """
    locations = load_locations()
    return list(locations)


def get_location_by_id(location_id: Union[int, str]) -> Optional[Dict[str, Any]]:
    """
    Looks up a location by its integer 'id' or string 'record_id'.
    """
    locations = load_locations()

    for loc in locations:
        if isinstance(location_id, int) and loc.get("id") == location_id:
            return loc
        elif str(loc.get("id")) == str(location_id):
            return loc
        elif str(loc.get("record_id", "")).lower() == str(location_id).lower():
            return loc

    return None


def get_locations_by_district(district: str) -> List[Dict[str, Any]]:
    """
    Returns all location records belonging to the specified district (case-insensitive).
    """
    if not district:
        return []

    target_district = district.strip().lower()
    locations = load_locations()

    return [
        loc for loc in locations
        if str(loc.get("district", "")).strip().lower() == target_district
    ]


def search_locations(query: str) -> List[Dict[str, Any]]:
    """
    Searches locations by place_name, district, or record_id matching the query.
    """
    if not query:
        return []

    q = query.strip().lower()
    locations = load_locations()

    results = []
    for loc in locations:
        place_match = q in str(loc.get("place_name", "")).lower()
        district_match = q in str(loc.get("district", "")).lower()
        id_match = q in str(loc.get("record_id", "")).lower()

        if place_match or district_match or id_match:
            results.append(loc)

    return results
