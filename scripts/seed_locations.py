"""
Seed script to insert/upsert Phase 2 locations.json into Supabase.
"""

import json
import sys
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.supabase_service import get_supabase_service


def seed():
    print("=" * 60)
    print("Sri Lanka FloodWatch — Seeding Supabase Locations")
    print("=" * 60)

    locations_path = PROJECT_ROOT / "data" / "locations.json"
    if not locations_path.exists():
        print(f"ERROR: data/locations.json not found at {locations_path}")
        sys.exit(1)

    with open(locations_path, "r", encoding="utf-8") as f:
        locations_data = json.load(f)

    print(f"Loaded {len(locations_data)} location records from data/locations.json.")

    db_service = get_supabase_service()
    result = db_service.upsert_locations(locations_data)

    print(f"Seed Result: {result.get('status')}")
    print(f"Message: {result.get('message')}")
    print(f"Record Count: {result.get('count', len(locations_data))}")

    print("\n" + "=" * 60)
    print("LOCATION SEEDING COMPLETED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = seed()
    sys.exit(0 if success else 1)
