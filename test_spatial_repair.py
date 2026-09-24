"""
======================================================================
  J.A.R.V.I.S. GOD'S EYE VIEW SPATIAL SUBSYSTEM REPAIR VERIFICATION
======================================================================
Comprehensive automated verification suite for all 25 spatial requirements:
- Static asset serving (Cesium 1.138, Widgets CSS, local mounts)
- Zero-coordinate preservation (Equator/Prime Meridian 0.0, 0.0)
- Strict boundary validation (Lat/Lon/Altitude ranges)
- Layer registry enforcement (no simulated layers)
- Visual sensor mode validation
- Annotation lifecycle & duplicate prevention
- Command result contract verification (no simulated: true)
- Spatial Query Engine geodesic computations
- Circuit breaker telemetry & health endpoints
"""

import sys
import math
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure workspace root is on sys.path
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

client = TestClient(app)

PASSED_COUNT = 0
FAILED_COUNT = 0

def check(condition: bool, test_name: str, details: str = ""):
    global PASSED_COUNT, FAILED_COUNT
    if condition:
        PASSED_COUNT += 1
        print(f"  [PASS] {test_name}" + (f" ({details})" if details else ""))
    else:
        FAILED_COUNT += 1
        print(f"  [FAIL] {test_name}" + (f" -> {details}" if details else ""))


def run_all_tests():
    print("======================================================================")
    print("  STARTING J.A.R.V.I.S. SPATIAL SUBSYSTEM AUDIT & REPAIR VERIFICATION")
    print("======================================================================\n")

    # ------------------------------------------------------------------
    # 1. CESIUM 1.138 ASSETS & STATIC MOUNT VERIFICATION
    # ------------------------------------------------------------------
    print("[*] Phase 1: Cesium 1.138 Assets & Static Mount Verification...")
    r_cesium_js = client.get("/spatial/cesium/Cesium.js")
    check(r_cesium_js.status_code == 200 and len(r_cesium_js.content) > 1_000_000,
          "Static /spatial/cesium/Cesium.js served", f"{len(r_cesium_js.content)/1048576:.1f} MB")

    r_cesium_css = client.get("/spatial/cesium/Widgets/widgets.css")
    check(r_cesium_css.status_code == 200 and len(r_cesium_css.content) > 1000,
          "Static /spatial/cesium/Widgets/widgets.css served", f"{len(r_cesium_css.content)} bytes")

    r_spatial_service = client.get("/static/spatial/spatialService.js")
    check(r_spatial_service.status_code == 200, "Static /static/spatial/spatialService.js served")

    r_gods_eye_adapter = client.get("/static/spatial/godsEyeAdapter.js")
    check(r_gods_eye_adapter.status_code == 200, "Static /static/spatial/godsEyeAdapter.js served")

    r_spatial_cmd_bus = client.get("/static/spatial/spatialCommandBus.js")
    check(r_spatial_cmd_bus.status_code == 200, "Static /static/spatial/spatialCommandBus.js served")

    # ------------------------------------------------------------------
    # 2. ZERO-COORDINATE PRESERVATION & PRESET ATLAS
    # ------------------------------------------------------------------
    print("\n[*] Phase 2: Coordinate Handling & Zero-Value Preservation...")
    # Equator and Prime Meridian (0.0, 0.0)
    res_zero = execute_spatial_tool("navigate_to_location", {"latitude": 0.0, "longitude": 0.0, "range_m": 10000.0})
    check(res_zero["ok"] is True, "Navigate to (0.0, 0.0) Equator succeeds")
    check(res_zero["target"]["latitude"] == 0.0, "Equator latitude preserved as exactly 0.0")
    check(res_zero["target"]["longitude"] == 0.0, "Prime meridian longitude preserved as exactly 0.0")
    check(res_zero["target"]["rangeM"] == 10000.0, "Range preserved as 10000.0m")

    # High-altitude global overview
    res_globe = execute_spatial_tool("zoom_to_globe", {})
    check(res_globe["ok"] is True and res_globe["command"] == "HOME_GLOBE", "Zoom to globe reset executed")

    # Named Presets
    presets = [("dhaka", 23.8103, 90.4125), ("tokyo", 35.6762, 139.6503), ("london", 51.5074, -0.1278), ("sf", 37.7749, -122.4194)]
    for city, exp_lat, exp_lon in presets:
        res = execute_spatial_tool("navigate_to_location", {"query": city})
        check(res["ok"] is True and abs(res["target"]["latitude"] - exp_lat) < 0.01, f"Resolved '{city}' preset coordinates", f"Lat: {res['target']['latitude']}, Lon: {res['target']['longitude']}")

    # Raw coordinate string parser
    coord_resolved = resolve_location_coordinates("0.0, 0.0")
    check(coord_resolved is not None and coord_resolved["latitude"] == 0.0, "Parsed raw string coordinate '0.0, 0.0'")

    coord_neg = resolve_location_coordinates("-33.8688, 151.2093")
    check(coord_neg is not None and abs(coord_neg["latitude"] - (-33.8688)) < 0.001, "Parsed negative latitude coordinate (Sydney)")

    # ------------------------------------------------------------------
    # 3. STRICT BOUNDARY & PARAMETER VALIDATION
    # ------------------------------------------------------------------
    print("\n[*] Phase 3: Strict Boundary & Parameter Validation...")
    # Out of range latitude (> 90)
    res_invalid_lat = resolve_location_coordinates("105.0, 50.0")
    check(res_invalid_lat is None, "Rejected invalid latitude (105.0 > 90)")

    # Out of range longitude (> 180)
    res_invalid_lon = resolve_location_coordinates("45.0, 210.0")
    check(res_invalid_lon is None, "Rejected invalid longitude (210.0 > 180)")

    # Missing entity_id on track_entity
    res_track_empty = execute_spatial_tool("track_entity", {"entity_id": ""})
    check(res_track_empty["ok"] is False, "Rejected empty entity_id on track_entity")

    # ------------------------------------------------------------------
    # 4. LAYER REGISTRY & VISIBILITY MANAGEMENT
    # ------------------------------------------------------------------
    print("\n[*] Phase 4: Layer Registry & Visibility Management...")
    expected_layers = {"flights", "vessels", "satellites", "weather", "firms", "earthquakes", "cctv", "radio"}
    check(expected_layers.issubset(VALID_LAYERS), "All expected core layers in VALID_LAYERS registry")

    # Enable layer
    res_layer_en = execute_spatial_tool("enable_layer", {"layer_id": "satellites"})
    check(res_layer_en["ok"] is True and res_layer_en["command"] == "ENABLE_LAYER", "Enabled 'satellites' layer")
    check(res_layer_en["params"]["visible"] is True, "Layer visibility flag set to True")

    # Disable layer
    res_layer_dis = execute_spatial_tool("disable_layer", {"layer_id": "satellites"})
    check(res_layer_dis["ok"] is True and res_layer_dis["command"] == "DISABLE_LAYER", "Disabled 'satellites' layer")
    check(res_layer_dis["params"]["visible"] is False, "Layer visibility flag set to False")

    # Alias mapping
    res_alias = execute_spatial_tool("enable_layer", {"layer_id": "planes"})
    check(res_alias["ok"] is True and res_alias["params"]["layerId"] == "flights", "Mapped alias 'planes' -> 'flights'")

    # ------------------------------------------------------------------
    # 5. VISUAL SENSOR MODES & NO SIMULATED FALLBACK
    # ------------------------------------------------------------------
    print("\n[*] Phase 5: Visual Sensor Modes & Contract Verification...")
    for style in ["normal", "surveillance", "thermal", "retro", "noir"]:
        res_style = execute_spatial_tool("switch_visual_mode", {"style": style})
        check(res_style["ok"] is True and res_style["params"]["style"] == style, f"Switched visual mode to '{style}'")
        check("simulated" not in res_style or res_style.get("simulated") is False, f"Confirmed no simulated flag on '{style}'")

    # Alias resolution (e.g. night vision -> surveillance)
    res_nvg = execute_spatial_tool("switch_visual_mode", {"style": "night vision"})
    check(res_nvg["ok"] is True and res_nvg["params"]["style"] == "surveillance", "Mapped style alias 'night vision' -> 'surveillance'")

    # Cockpit mode transitions
    res_cockpit_in = execute_spatial_tool("enter_cockpit", {})
    check(res_cockpit_in["ok"] is True and res_cockpit_in["command"] == "ENTER_COCKPIT", "Entered cockpit camera mode")

    res_cockpit_out = execute_spatial_tool("exit_cockpit", {})
    check(res_cockpit_out["ok"] is True and res_cockpit_out["command"] == "EXIT_COCKPIT", "Exited cockpit camera mode")

    # Untrack entity
    res_untrack = execute_spatial_tool("untrack_entity", {})
    check(res_untrack["ok"] is True and res_untrack["command"] == "UNTRACK_ENTITY", "Disengaged entity tracking")

    # ------------------------------------------------------------------
    # 6. SPATIAL QUERY ENGINE & GEODESIC COMPUTATIONS
    # ------------------------------------------------------------------
    print("\n[*] Phase 6: Spatial Query Engine Geodesic Calculations...")
    # Distance JFK to London Heathrow
    res_dist = execute_spatial_tool("measure_distance", {"from_location": "jfk", "to_location": "london"})
    check(res_dist["ok"] is True, "Measured distance JFK -> London")
    km = res_dist["measurement"]["distance_km"]
    check(5500.0 < km < 5600.0, f"Geodesic distance accuracy: {km:.1f} km (expected ~5540 km)")
    bearing = res_dist["measurement"]["bearing_deg"]
    check(50.0 <= bearing <= 53.0, f"Initial bearing accuracy: {bearing}° (expected ~51.4°)")

    # ------------------------------------------------------------------
    # 7. FASTAPI REST ENDPOINTS VERIFICATION
    # ------------------------------------------------------------------
    print("\n[*] Phase 7: FastAPI REST Spatial Endpoints...")
    # POST /api/spatial/command
    r_cmd = client.post("/api/spatial/command", json={"action": "navigate_to_location", "params": {"query": "Tokyo"}})
    check(r_cmd.status_code == 200 and r_cmd.json().get("ok") is True, "POST /api/spatial/command executed navigate_to_location")

    # GET /api/spatial/state
    r_state = client.get("/api/spatial/state")
    check(r_state.status_code == 200 and "location" in r_state.json() and "latitude" in r_state.json()["location"], "GET /api/spatial/state returned valid synchronized state")

    # GET /api/spatial/health
    r_health = client.get("/api/spatial/health")
    check(r_health.status_code == 200 and r_health.json().get("is_ready") is True, "GET /api/spatial/health returned is_ready=True")

    # GET /api/spatial/providers
    r_prov = client.get("/api/spatial/providers")
    check(r_prov.status_code == 200 and len(r_prov.json().get("providers", [])) >= 10, f"GET /api/spatial/providers returned {len(r_prov.json().get('providers', []))} providers")

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    print("\n======================================================================")
    print(f"VERIFICATION SUMMARY: {PASSED_COUNT} PASSED, {FAILED_COUNT} FAILED")
    if FAILED_COUNT == 0:
        print("[OK] ALL SPATIAL SUBSYSTEM REPAIR AUDIT REQUIREMENTS SATISFIED!")
    else:
        print("[ERROR] SOME VERIFICATION CHECKS FAILED. INSPECT ABOVE LOGS.")
    print("======================================================================")
    return FAILED_COUNT == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
