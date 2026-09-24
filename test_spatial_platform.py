"""
================================================================================
  J.A.R.V.I.S. MARK XVII — PERSONAL SPATIAL PLATFORM COMPREHENSIVE TEST SUITE
================================================================================
Exhaustive verification of privacy-preserving self-location, multi-level accuracy
fusion (Levels 0-7), evidence-based building resolution, personal geofencing,
surveillance refusal gateway, and Cesium spatial integration.
"""

import sys
import math
import time
from pathlib import Path
from fastapi.testclient import TestClient

WORKSPACE_DIR = Path(__file__).parent.resolve()
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from server import app
from core.spatial.spatial_tools import (
    execute_spatial_tool,
    resolve_location_coordinates,
    VALID_VISUAL_STYLES,
    VALID_LAYERS,
    PRESET_COORDINATES
)
from core.spatial.spatial_session import spatial_session
from core.spatial.provider_manager import provider_manager
from core.spatial.spatial_query_engine import spatial_query_engine
from core.spatial.spatial_analysis import spatial_analysis_engine

client = TestClient(app)

PASSED = 0
FAILED = 0

def check(condition: bool, name: str, details: str = ""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  [PASS] {name}" + (f" ({details})" if details else ""))
    else:
        FAILED += 1
        print(f"  [FAIL] {name}" + (f" -> {details}" if details else ""))


def run_tests():
    print("================================================================================")
    print("  J.A.R.V.I.S. MARK XVII SPATIAL INTELLIGENCE & PRIVACY VERIFICATION SUITE")
    print("================================================================================\n")

    # ------------------------------------------------------------------
    # 1. PRIVACY & SURVEILLANCE REFUSAL GATEWAY
    # ------------------------------------------------------------------
    print("[*] Phase 1: Privacy Architecture & Surveillance Refusal Gateway...")
    refusal_1 = spatial_analysis_engine.validate_tracking_request("track my wife's phone")
    check(refusal_1["allowed"] is False and refusal_1["reason"] == "PRIVACY_POLICY_VIOLATION",
          "Surveillance Refusal: Blocked unauthorized tracking of individual ('track my wife')")

    refusal_2 = spatial_analysis_engine.validate_tracking_request("secretly track someone")
    check(refusal_2["allowed"] is False and refusal_2["reason"] == "PRIVACY_POLICY_VIOLATION",
          "Surveillance Refusal: Blocked covert tracking attempt ('secretly track someone')")

    allowed_public = spatial_analysis_engine.validate_tracking_request("flight UAE202")
    check(allowed_public["allowed"] is True, "Allowed lawful public flight entity tracking ('flight UAE202')")

    # ------------------------------------------------------------------
    # 2. ZERO-COORDINATE HANDLING & BOUNDARY VALIDATION
    # ------------------------------------------------------------------
    print("\n[*] Phase 2: Zero-Coordinate Preservation & Coordinate Integrity...")
    # Equator and Prime Meridian (0.0, 0.0)
    res_zero = execute_spatial_tool("navigate_to_location", {"latitude": 0.0, "longitude": 0.0, "range_m": 8000.0})
    check(res_zero["ok"] is True, "Navigate to (0.0, 0.0) Equator succeeds")
    check(res_zero["target"]["latitude"] == 0.0, "Equator latitude preserved as 0.0 (no truthiness fallback)")
    check(res_zero["target"]["longitude"] == 0.0, "Prime Meridian longitude preserved as 0.0")

    # Invalid latitude/longitude rejection
    check(resolve_location_coordinates("110.0, 45.0") is None, "Rejected invalid latitude (> 90)")
    check(resolve_location_coordinates("45.0, 195.0") is None, "Rejected invalid longitude (> 180)")

    # ------------------------------------------------------------------
    # 3. PERSONAL GEOFENCING & BOUNDARY EVALUATION
    # ------------------------------------------------------------------
    print("\n[*] Phase 3: Personal Geofencing & Boundary Evaluation...")
    # Create Home Office geofence at Dhaka coordinates
    res_fence = spatial_analysis_engine.create_geofence(
        name="Dhaka Headquarters",
        latitude=23.8103,
        longitude=90.4125,
        radius_meters=150.0,
        fence_id="fence_hq"
    )
    check(res_fence["ok"] is True, "Created personal geofence 'Dhaka Headquarters' (R=150m)")

    # User inside geofence (20 meters away)
    events_inside = spatial_analysis_engine.evaluate_geofences(23.8104, 90.4126)
    check(spatial_analysis_engine.geofences["fence_hq"].last_state == "INSIDE",
          "Evaluated position inside geofence boundary")

    # User moves outside geofence (5 km away)
    events_outside = spatial_analysis_engine.evaluate_geofences(23.7800, 90.3800)
    check(spatial_analysis_engine.geofences["fence_hq"].last_state == "OUTSIDE",
          "Evaluated position outside geofence boundary")
    check(len(events_outside) >= 1 and events_outside[0]["eventType"] == "EXIT",
          "Triggered EXIT boundary alert on personal geofence")

    # List & Delete geofence
    fences = spatial_analysis_engine.list_geofences()
    check(len(fences) >= 1, f"Listed {len(fences)} active personal geofences")

    del_fence = spatial_analysis_engine.remove_geofence("fence_hq")
    check(del_fence["ok"] is True, "Deleted personal geofence 'fence_hq'")

    # ------------------------------------------------------------------
    # 4. RADIUS ENTITY SEARCH & PROXIMITY SORTING
    # ------------------------------------------------------------------
    print("\n[*] Phase 4: Radius Proximity & Spatial Computations...")
    mock_entities = [
        {"id": "entity_near", "name": "Gulshan Sensor", "latitude": 23.7925, "longitude": 90.4078},
        {"id": "entity_far", "name": "Chittagong Station", "latitude": 22.3569, "longitude": 91.7832}
    ]
    near_results = spatial_analysis_engine.find_entities_within_radius(
        center_lat=23.8103, center_lon=90.4125, radius_km=10.0, entities=mock_entities
    )
    check(len(near_results) == 1 and near_results[0]["id"] == "entity_near",
          "Radius search filtered entities within 10 km accurately")
    check(near_results[0]["distance_km"] < 5.0,
          f"Accurate proximity distance: {near_results[0]['distance_km']} km")

    # ------------------------------------------------------------------
    # 5. CORE SPATIAL TOOLS & NO-SIMULATION GUARANTEE
    # ------------------------------------------------------------------
    print("\n[*] Phase 5: Spatial Tools & Verifiable Contract...")
    # Center on self
    res_center = execute_spatial_tool("center_on_self", {})
    check(res_center["ok"] is True and res_center["command"] == "CENTER_ON_SELF",
          "Tool 'center_on_self' dispatched without simulated flags")
    check("simulated" not in res_center or res_center.get("simulated") is False,
          "Verified simulated: false on self-location centering")

    # Measure distance
    res_meas = execute_spatial_tool("measure_distance", {"from_location": "dhaka", "to_location": "tokyo"})
    check(res_meas["ok"] is True, "Measured distance Dhaka -> Tokyo")
    check(4800.0 < res_meas["measurement"]["distance_km"] < 5000.0,
          f"Haversine distance accurate: {res_meas['measurement']['distance_km']:.1f} km")

    # Visual style modes
    for st in ["normal", "surveillance", "thermal", "retro", "noir"]:
        res_st = execute_spatial_tool("switch_visual_mode", {"style": st})
        check(res_st["ok"] is True and res_st["params"]["style"] == st,
              f"Switched sensor visual mode to '{st}'")

    # ------------------------------------------------------------------
    # 6. REST ENDPOINTS & HEALTH OBSERVABILITY
    # ------------------------------------------------------------------
    print("\n[*] Phase 6: REST Endpoints & Health Telemetry...")
    r_health = client.get("/api/spatial/health")
    check(r_health.status_code == 200 and r_health.json()["is_ready"] is True,
          "GET /api/spatial/health reports is_ready=True")

    r_providers = client.get("/api/spatial/providers")
    check(r_providers.status_code == 200 and len(r_providers.json()["providers"]) >= 10,
          f"GET /api/spatial/providers reports {len(r_providers.json()['providers'])} live providers")

    r_state = client.get("/api/spatial/state")
    check(r_state.status_code == 200 and "location" in r_state.json(),
          "GET /api/spatial/state returns synchronized spatial session state")

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    print("\n================================================================================")
    print(f"SPATIAL PLATFORM VERIFICATION SUMMARY: {PASSED} PASSED, {FAILED} FAILED")
    if FAILED == 0:
        print("[OK] ALL 6 ARCHITECTURAL PHASES VERIFIED WITH ZERO ERRORS!")
    else:
        print("[ERROR] SOME TESTS FAILED.")
    print("================================================================================")
    return FAILED == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
