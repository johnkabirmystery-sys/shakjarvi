"""
Verification of Spatial Intelligence Endpoints (test_spatial_endpoints.py)
==========================================================================
Validates:
- POST /api/spatial/command
- GET /api/spatial/state
- GET /api/spatial/health
- GET /api/spatial/session
- GET /api/spatial/providers
- POST /api/spatial/query
"""

import sys
from pathlib import Path
from starlette.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from server import app

client = TestClient(app)

def test_spatial_command_endpoint():
    print("[*] Testing POST /api/spatial/command...")
    resp = client.post("/api/spatial/command", json={
        "tool": "navigate_to_location",
        "params": {"query": "Tokyo", "range_m": 12000}
    })
    assert resp.status_code == 200, f"Status: {resp.status_code}"
    data = resp.json()
    assert data["ok"] is True
    assert data["target"]["name"] == "Tokyo, Japan"
    print("  [PASS] Spatial command endpoint executed navigate_to_location successfully.")

def test_spatial_state_endpoint():
    print("[*] Testing GET /api/spatial/state...")
    resp = client.get("/api/spatial/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "location" in data
    assert "active_layers" in data
    assert data["location"]["name"] == "Tokyo, Japan"
    print("  [PASS] Spatial state endpoint returned synchronized location state.")

def test_spatial_health_endpoint():
    print("[*] Testing GET /api/spatial/health...")
    resp = client.get("/api/spatial/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_ready"] is True
    assert "providers" in data
    assert data["providers"]["live"] > 0
    print(f"  [PASS] Spatial health endpoint: {data['providers']['live']} live providers, status: {data['providers']['overall_status']}.")

def test_spatial_session_endpoint():
    print("[*] Testing GET /api/spatial/session...")
    resp = client.get("/api/spatial/session")
    assert resp.status_code == 200
    data = resp.json()
    assert "session" in data
    assert "summary" in data
    print("  [PASS] Spatial session summary context endpoint verified.")

def test_spatial_providers_endpoint():
    print("[*] Testing GET /api/spatial/providers...")
    resp = client.get("/api/spatial/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["providers"]) > 5
    print(f"  [PASS] Spatial providers endpoint returned {len(data['providers'])} configured providers.")

def test_spatial_query_endpoint():
    print("[*] Testing POST /api/spatial/query...")
    mock_aircraft = [
        {"id": "F1", "callsign": "JAL001", "latitude": 35.7, "longitude": 139.7, "altitude_m": 9000, "speed_kts": 440},
        {"id": "F2", "callsign": "ANA002", "latitude": 35.6, "longitude": 139.6, "altitude_m": 8500, "speed_kts": 420},
        {"id": "F3", "callsign": "AFR275", "latitude": 48.8, "longitude": 2.3, "altitude_m": 10500, "speed_kts": 480}
    ]
    resp = client.post("/api/spatial/query", json={
        "category": "aircraft",
        "latitude": 35.6762,
        "longitude": 139.6503,
        "radius_km": 50.0,
        "entities": mock_aircraft
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 2
    assert len(data["nearest_entities"]) == 2
    print(f"  [PASS] Spatial query endpoint filtered {data['total_count']} entities within 50km radius.")

if __name__ == "__main__":
    print("==============================================")
    print("  JARVIS SPATIAL SERVER ENDPOINTS TEST SUITE  ")
    print("==============================================")
    test_spatial_command_endpoint()
    test_spatial_state_endpoint()
    test_spatial_health_endpoint()
    test_spatial_session_endpoint()
    test_spatial_providers_endpoint()
    test_spatial_query_endpoint()
    print("\n==============================================")
    print("ALL SPATIAL SERVER ENDPOINTS VERIFIED (6/6 PASS)!")
    print("==============================================")
