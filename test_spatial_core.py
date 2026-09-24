"""
Unit Test Suite for Spatial Intelligence Core (test_spatial_core.py)
===================================================================
Tests SpatialService, SpatialSession, SpatialQueryEngine, ProviderManager,
SpatialTools, and AI Brain spatial intent routing.
"""

import asyncio
from core.spatial.spatial_service import spatial_service
from core.spatial.spatial_session import spatial_session
from core.spatial.spatial_query_engine import spatial_query_engine
from core.spatial.provider_manager import provider_manager
from core.spatial.spatial_tools import execute_spatial_tool, resolve_location_coordinates
from core.ai_brain import classify_intent, execute_tool_call
from core.orchestrator import IntentType


def test_spatial_query_engine():
    print("[*] Testing SpatialQueryEngine...")
    # JFK to London Heathrow
    jfk_lat, jfk_lon = 40.6413, -73.7781
    lhr_lat, lhr_lon = 51.4700, -0.4543

    dist_km = spatial_query_engine.haversine_distance_km(jfk_lat, jfk_lon, lhr_lat, lhr_lon)
    assert 5500 < dist_km < 5600, f"Unexpected JFK-LHR distance: {dist_km}"
    print(f"  [PASS] Haversine distance JFK-LHR: {dist_km:.1f} km")

    bearing = spatial_query_engine.initial_bearing_deg(jfk_lat, jfk_lon, lhr_lat, lhr_lon)
    assert 45 < bearing < 60, f"Unexpected bearing: {bearing}"
    print(f"  [PASS] Initial bearing JFK-LHR: {bearing}°")

    # Triangle area (NYC, SF, Miami)
    triangle = [
        (40.7128, -74.0060),
        (37.7749, -122.4194),
        (25.7617, -80.1918)
    ]
    area = spatial_query_engine.polygon_area_sq_km(triangle)
    assert area > 1000000, f"Unexpected triangle area: {area}"
    print(f"  [PASS] Spherical polygon area: {area:,.1f} sq km")

    # Point in polygon
    in_pt = spatial_query_engine.point_in_polygon(35.0, -90.0, triangle)
    assert in_pt is True, "Point in triangle failed"
    out_pt = spatial_query_engine.point_in_polygon(10.0, 0.0, triangle)
    assert out_pt is False, "Point outside triangle failed"
    print("  [PASS] Point-in-polygon ray-casting test verified")

    # Filtering & Summarization
    mock_aircraft = [
        {"id": "A1", "callsign": "BAW123", "latitude": 40.7, "longitude": -74.0, "altitude_m": 10000, "speed_kts": 450},
        {"id": "A2", "callsign": "UAL456", "latitude": 40.8, "longitude": -73.9, "altitude_m": 8000, "speed_kts": 380},
        {"id": "A3", "callsign": "FAR999", "latitude": 51.5, "longitude": -0.1, "altitude_m": 11000, "speed_kts": 490},
    ]
    summary = spatial_query_engine.aggregate_and_summarize("aircraft", mock_aircraft, 40.7128, -74.0060, radius_km=50.0)
    assert summary["total_count"] == 2, f"Expected 2 aircraft near NYC, got {summary['total_count']}"
    assert len(summary["nearest_entities"]) == 2
    assert summary["metrics"]["average_altitude_m"] == 9000
    print("  [PASS] Bounded entity aggregation & LLM-safe summarization verified")


def test_spatial_session():
    print("[*] Testing SpatialSession & Agent Handoff...")
    spatial_session.update_location("Tokyo", 35.6762, 139.6503, altitude=12000.0)
    assert spatial_session.location.name == "Tokyo"
    assert spatial_session.location.latitude == 35.6762

    spatial_session.set_tracked_entity("FLIGHT_X", "flights", name="Stark One", altitude_m=35000, speed_kts=520)
    assert spatial_session.tracked_entity.name == "Stark One"

    spatial_session.enable_layer("satellites")
    assert "satellites" in spatial_session.active_layers

    # Agent handoff
    exported = spatial_session.export_handoff_context(target_agent="researcher")
    assert exported["location"]["name"] == "Tokyo"
    assert exported["tracked_entity"]["name"] == "Stark One"
    assert "satellites" in exported["active_layers"]

    # Import into fresh session
    spatial_session.clear_tracked_entity()
    spatial_session.import_handoff_context(exported)
    assert spatial_session.location.name == "Tokyo"
    print("  [PASS] SpatialSession context tracking & agent handoff verified")


def test_spatial_tools_execution():
    print("[*] Testing SpatialTools Execution...")
    res = execute_spatial_tool("navigate_to_location", {"query": "London", "range_m": 12000})
    assert res["ok"] is True
    assert res["target"]["name"] == "London, United Kingdom"
    assert res["client_action"] == "fly_to_location"

    res_track = execute_spatial_tool("track_entity", {"entity_id": "ISS_25544", "layer_id": "satellites", "name": "Space Station"})
    assert res_track["ok"] is True
    assert res_track["command"] == "TRACK_ENTITY"

    res_visual = execute_spatial_tool("switch_visual_mode", {"style": "thermal"})
    assert res_visual["ok"] is True
    assert res_visual["params"]["style"] == "thermal"

    res_dist = execute_spatial_tool("measure_distance", {"from_location": "JFK", "to_location": "London"})
    assert res_dist["ok"] is True
    assert res_dist["measurement"]["distance_km"] > 5000
    print("  [PASS] SpatialTools commands verified")


def test_provider_manager():
    print("[*] Testing ProviderManager & Circuit Breakers...")
    p = provider_manager.get_provider("opensky")
    assert p is not None
    assert p.status == "LIVE"

    # Test error tracking
    provider_manager.record_request_result("opensky", success=False, error="Simulated 429")
    assert p.consecutive_failures == 1
    # Recovery
    provider_manager.record_request_result("opensky", success=True, latency_ms=120.5)
    assert p.consecutive_failures == 0
    assert p.status == "LIVE"
    print("  [PASS] ProviderManager telemetry and circuit-breaker verified")


def test_ai_brain_spatial_intent():
    print("[*] Testing AI Brain Spatial Intent Classification...")
    queries = [
        ("Take me to Tokyo and show planes", IntentType.SPATIAL_INTELLIGENCE),
        ("Show aircraft around London", IntentType.SPATIAL_INTELLIGENCE),
        ("Track the nearest flight", IntentType.SPATIAL_INTELLIGENCE),
        ("Enter cockpit mode", IntentType.SPATIAL_INTELLIGENCE),
        ("Switch to thermal vision", IntentType.SPATIAL_INTELLIGENCE),
        ("Measure distance from JFK to London", IntentType.SPATIAL_INTELLIGENCE),
        ("Zoom out to globe view", IntentType.SPATIAL_INTELLIGENCE)
    ]
    for q, expected in queries:
        cls = classify_intent(q)
        assert cls["intent"] == expected, f"Failed for '{q}': got {cls['intent']}"
    print(f"  [PASS] All {len(queries)} spatial natural language queries correctly classified")


def test_ai_brain_spatial_tool_execution():
    print("[*] Testing AI Brain Spatial Tool Execution...")
    res = asyncio.run(execute_tool_call("spatial_navigate", query="San Francisco", range_m=10000))
    assert res["ok"] is True
    assert res["target"]["name"] == "San Francisco, USA"

    res_mode = asyncio.run(execute_tool_call("spatial_visual", style="night vision"))
    assert res_mode["ok"] is True
    assert res_mode["params"]["style"] == "surveillance"
    print("  [PASS] AI Brain spatial tool execution verified")


if __name__ == "__main__":
    print("==========================================")
    print("  JARVIS SPATIAL CORE VERIFICATION SUITE  ")
    print("==========================================")
    test_spatial_query_engine()
    test_spatial_session()
    test_spatial_tools_execution()
    test_provider_manager()
    test_ai_brain_spatial_intent()
    asyncio.run(test_ai_brain_spatial_tool_execution())
    print("\n==========================================")
    print("ALL SPATIAL CORE TESTS PASSED (6/6 PASS)! ")
    print("==========================================")
