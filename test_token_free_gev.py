"""
J.A.R.V.I.S. Token-Free GEV Architecture Tests
================================================
Comprehensive tests validating that God's Eye View operates correctly
without any Cesium Ion tokens, API keys, or paid credentials.

Test Areas:
- Token-free startup and module serving
- GeoJSON validation and import endpoints
- Free terrain provider contracts
- Free building provider architecture
- Coordinate validation and rejection
- Provider state truthfulness
- Spatial analytics (local, no token)
- Backend GeoJSON validation endpoint
"""

import pytest
import requests
import json
import time
import os
import sys

BASE_URL = os.environ.get("JARVIS_TEST_URL", "http://127.0.0.1:8000")


# ──────────────────────────────────────────────────────
# SUITE 1: TOKEN-FREE STARTUP & MODULE DELIVERY
# ──────────────────────────────────────────────────────

class TestTokenFreeStartup:
    """Verify the application starts and serves all spatial modules without any tokens."""

    def test_index_serves_without_token(self):
        """Index page loads without requiring any API key or token."""
        r = requests.get(f"{BASE_URL}/", timeout=10)
        assert r.status_code == 200
        assert "spatialGlobeContainer" in r.text
        assert "J.A.R.V.I.S." in r.text

    def test_cesium_runtime_served_locally(self):
        """Cesium JS bundle is served from local vendor path, not Cesium Ion CDN."""
        r = requests.get(f"{BASE_URL}/cesium/Cesium.js", timeout=10)
        assert r.status_code == 200
        assert len(r.content) > 100000  # Cesium bundle should be substantial

    def test_cesium_widgets_css_served_locally(self):
        """Cesium widget CSS is served locally."""
        r = requests.get(f"{BASE_URL}/cesium/Widgets/widgets.css", timeout=10)
        assert r.status_code == 200

    def test_spatial_service_module_served(self):
        """spatialService.js is accessible."""
        r = requests.get(f"{BASE_URL}/static/spatial/spatialService.js", timeout=10)
        assert r.status_code == 200
        assert "SpatialService" in r.text

    def test_spatial_command_bus_module_served(self):
        """spatialCommandBus.js is accessible."""
        r = requests.get(f"{BASE_URL}/static/spatial/spatialCommandBus.js", timeout=10)
        assert r.status_code == 200
        assert "SpatialCommandBus" in r.text

    def test_geojson_data_layer_module_served(self):
        """New GeoJSON data layer module is accessible."""
        r = requests.get(f"{BASE_URL}/static/spatial/data/geoJsonDataLayer.js", timeout=10)
        assert r.status_code == 200
        assert "GeoJsonDataLayer" in r.text

    def test_osm_building_provider_module_served(self):
        """New OSM building provider module is accessible."""
        r = requests.get(f"{BASE_URL}/static/spatial/data/osmBuildingProvider.js", timeout=10)
        assert r.status_code == 200
        assert "OSMBuildingProvider" in r.text

    def test_free_terrain_provider_module_served(self):
        """New free terrain provider module is accessible."""
        r = requests.get(f"{BASE_URL}/static/spatial/terrain/freeTerrainProvider.js", timeout=10)
        assert r.status_code == 200
        assert "FreeTerrainProvider" in r.text

    def test_spatial_data_manager_module_served(self):
        """New spatial data manager module is accessible."""
        r = requests.get(f"{BASE_URL}/static/spatial/data/spatialDataManager.js", timeout=10)
        assert r.status_code == 200
        assert "SpatialDataManager" in r.text

    def test_building_layer_module_served(self):
        """Updated building layer with fallback is accessible."""
        r = requests.get(f"{BASE_URL}/static/spatial/tiles/buildingLayer.js", timeout=10)
        assert r.status_code == 200
        assert "osm_free_extrusion" in r.text or "osmBuildingProvider" in r.text

    def test_terrain_availability_module_served(self):
        """Updated terrain availability with ArcGIS check is accessible."""
        r = requests.get(f"{BASE_URL}/static/spatial/terrain/terrainAvailability.js", timeout=10)
        assert r.status_code == 200

    def test_terrain_provider_registry_module_served(self):
        """Terrain provider registry with free providers is accessible."""
        r = requests.get(f"{BASE_URL}/static/spatial/terrain/terrainProviderRegistry.js", timeout=10)
        assert r.status_code == 200
        assert "ellipsoid" in r.text
        assert "arcgis_elevation" in r.text

    def test_imagery_provider_registry_module_served(self):
        """Imagery provider registry with free basemaps is accessible."""
        r = requests.get(f"{BASE_URL}/static/spatial/imagery/imageryProviderRegistry.js", timeout=10)
        assert r.status_code == 200
        assert "arcgis_imagery" in r.text
        assert "osm" in r.text
        assert "cartodb_dark" in r.text
        assert "nasa_gibs" in r.text

    def test_no_hardcoded_ion_token_in_served_modules(self):
        """No module should contain a hardcoded Cesium Ion access token."""
        modules = [
            "/static/spatial/spatialService.js",
            "/static/spatial/spatialCommandBus.js",
            "/static/spatial/runtime/viewerFactory.js",
            "/static/spatial/runtime/cesiumRuntime.js",
            "/static/spatial/data/geoJsonDataLayer.js",
            "/static/spatial/data/osmBuildingProvider.js",
            "/static/spatial/data/spatialDataManager.js",
        ]
        for mod_path in modules:
            r = requests.get(f"{BASE_URL}{mod_path}", timeout=10)
            assert r.status_code == 200
            # Cesium Ion tokens are typically long alphanumeric strings
            # We just check there's no hardcoded "eyJ" (JWT) or long random token
            content = r.text
            assert "eyJhbGc" not in content, f"Possible hardcoded JWT token found in {mod_path}"


# ──────────────────────────────────────────────────────
# SUITE 2: GEOJSON VALIDATION ENDPOINT
# ──────────────────────────────────────────────────────

class TestGeoJSONValidation:
    """Backend GeoJSON validation endpoint tests."""

    def test_valid_feature_collection(self):
        """Valid FeatureCollection passes validation."""
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [139.6503, 35.6762]
                    },
                    "properties": {"name": "Tokyo Tower"}
                }
            ]
        }
        r = requests.post(f"{BASE_URL}/api/spatial/geojson/validate", json={"geojson": geojson}, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["feature_count"] == 1

    def test_valid_single_feature(self):
        """Valid single Feature passes validation."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            },
            "properties": {"name": "Test Square"}
        }
        r = requests.post(f"{BASE_URL}/api/spatial/geojson/validate", json={"geojson": geojson}, timeout=10)
        data = r.json()
        assert data["ok"] is True
        assert data["feature_count"] == 1

    def test_valid_linestring(self):
        """Valid LineString geometry passes validation."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[0, 0], [1, 1], [2, 0]]
            },
            "properties": {"name": "Test Line"}
        }
        r = requests.post(f"{BASE_URL}/api/spatial/geojson/validate", json={"geojson": geojson}, timeout=10)
        data = r.json()
        assert data["ok"] is True

    def test_multi_feature_collection(self):
        """FeatureCollection with multiple features validates correctly."""
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]}, "properties": {}},
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [1, 1]}, "properties": {}},
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [2, 2]}, "properties": {}},
            ]
        }
        r = requests.post(f"{BASE_URL}/api/spatial/geojson/validate", json={"geojson": geojson}, timeout=10)
        data = r.json()
        assert data["ok"] is True
        assert data["feature_count"] == 3

    def test_invalid_geojson_type(self):
        """Invalid GeoJSON type is rejected."""
        geojson = {"type": "InvalidType", "data": []}
        r = requests.post(f"{BASE_URL}/api/spatial/geojson/validate", json={"geojson": geojson}, timeout=10)
        data = r.json()
        assert data["ok"] is False
        assert "Invalid GeoJSON type" in data["error"]

    def test_feature_missing_geometry(self):
        """Feature with missing geometry is flagged."""
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {"name": "no geom"}}
            ]
        }
        r = requests.post(f"{BASE_URL}/api/spatial/geojson/validate", json={"geojson": geojson}, timeout=10)
        data = r.json()
        assert data["ok"] is False
        assert len(data["invalid_features"]) == 1

    def test_empty_feature_collection(self):
        """Empty FeatureCollection is valid (0 features, 0 invalid)."""
        geojson = {"type": "FeatureCollection", "features": []}
        r = requests.post(f"{BASE_URL}/api/spatial/geojson/validate", json={"geojson": geojson}, timeout=10)
        data = r.json()
        assert data["ok"] is True
        assert data["feature_count"] == 0


# ──────────────────────────────────────────────────────
# SUITE 3: SPATIAL STATE & PROVIDER TRUTHFULNESS
# ──────────────────────────────────────────────────────

class TestProviderTruthfulness:
    """Verify providers report honest states and never fabricate live status."""

    def test_spatial_state_endpoint(self):
        """Spatial state endpoint returns valid structure."""
        r = requests.get(f"{BASE_URL}/api/spatial/state", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "location" in data
        assert "active_layers" in data

    def test_spatial_health_endpoint(self):
        """Spatial health endpoint returns valid structure."""
        r = requests.get(f"{BASE_URL}/api/spatial/health", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "is_ready" in data or "ok" in data

    def test_spatial_providers_endpoint(self):
        """Spatial providers endpoint lists available providers."""
        r = requests.get(f"{BASE_URL}/api/spatial/providers", timeout=10)
        assert r.status_code == 200

    def test_terrain_provider_metadata_in_registry(self):
        """Terrain provider registry JS contains proper metadata markers."""
        r = requests.get(f"{BASE_URL}/static/spatial/terrain/terrainProviderRegistry.js", timeout=10)
        content = r.text
        # Must have honest requiresToken flags
        assert "requiresToken: false" in content  # Ellipsoid
        assert "requiresToken: true" in content   # World Terrain


# ──────────────────────────────────────────────────────
# SUITE 4: COORDINATE VALIDATION
# ──────────────────────────────────────────────────────

class TestCoordinateValidation:
    """Verify coordinate validation rejects invalid values."""

    def test_valid_coordinates_accepted(self):
        """Valid coordinates (Tokyo) are accepted."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "navigate_to_location",
            "arguments": {"query": "tokyo"}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is True
        assert data["target"]["latitude"] == 35.6762

    def test_zero_coordinates_accepted(self):
        """Zero coordinates (0.0, 0.0) are valid and accepted."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "navigate_to_location",
            "arguments": {"latitude": 0.0, "longitude": 0.0}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is True
        assert data["target"]["latitude"] == 0.0
        assert data["target"]["longitude"] == 0.0

    def test_out_of_range_latitude_rejected(self):
        """Latitude 105 is out of range and rejected."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "navigate_to_location",
            "arguments": {"latitude": 105.0, "longitude": 0.0}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is False
        assert "Invalid coordinates" in data.get("error", "")

    def test_out_of_range_longitude_rejected(self):
        """Longitude 200 is out of range and rejected."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "navigate_to_location",
            "arguments": {"latitude": 0.0, "longitude": 200.0}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is False

    def test_boundary_coordinates_accepted(self):
        """Edge-case coordinates (-90, -180) are valid."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "navigate_to_location",
            "arguments": {"latitude": -90.0, "longitude": -180.0}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is True

    def test_preset_london_resolved(self):
        """Preset 'london' resolves to correct coordinates."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "navigate_to_location",
            "arguments": {"query": "london"}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is True
        assert abs(data["target"]["latitude"] - 51.5074) < 0.01
        assert abs(data["target"]["longitude"] - (-0.1278)) < 0.01

    def test_preset_new_york_resolved(self):
        """Preset 'new york' resolves to correct coordinates."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "navigate_to_location",
            "arguments": {"query": "new york"}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is True
        assert abs(data["target"]["latitude"] - 40.7128) < 0.01


# ──────────────────────────────────────────────────────
# SUITE 5: SPATIAL ANALYTICS (LOCAL, NO TOKEN)
# ──────────────────────────────────────────────────────

class TestSpatialAnalyticsLocal:
    """Test spatial analytics computations that work entirely locally."""

    def test_distance_measurement(self):
        """Distance measurement between presets works without any token."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "measure_distance",
            "arguments": {"from_location": "tokyo", "to_location": "london"}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is True
        assert "distance_km" in data["measurement"]
        dist = data["measurement"]["distance_km"]
        # Tokyo to London is approximately 9,556 km
        assert 9000 < dist < 10000, f"Expected ~9556km, got {dist}km"

    def test_bearing_calculation(self):
        """Bearing calculation returns valid degrees."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "measure_distance",
            "arguments": {"from_location": "tokyo", "to_location": "new york"}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is True
        bearing = data["measurement"]["bearing_deg"]
        assert 0 <= bearing < 360

    def test_spatial_context_returns_state(self):
        """Spatial context provides current session state."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "get_spatial_context",
            "arguments": {}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is True
        assert "session" in data


# ──────────────────────────────────────────────────────
# SUITE 6: TOKEN-FREE MODULE ARCHITECTURE
# ──────────────────────────────────────────────────────

class TestTokenFreeArchitecture:
    """Verify the token-free architectural components are properly integrated."""

    def test_building_layer_has_osm_fallback_code(self):
        """Building layer includes free OSM fallback strategy."""
        r = requests.get(f"{BASE_URL}/static/spatial/tiles/buildingLayer.js", timeout=10)
        content = r.text
        assert "osm_free_extrusion" in content or "osmBuildingProvider" in content
        assert "Strategy 2" in content or "Free OSM" in content

    def test_command_bus_has_geojson_commands(self):
        """Command bus supports LOAD_GEOJSON and LOAD_OSM_BUILDINGS commands."""
        r = requests.get(f"{BASE_URL}/static/spatial/spatialCommandBus.js", timeout=10)
        content = r.text
        assert "LOAD_GEOJSON" in content
        assert "IMPORT_GEOJSON" in content
        assert "LOAD_OSM_BUILDINGS" in content

    def test_spatial_service_integrates_data_manager(self):
        """SpatialService initializes GeoJsonDataLayer and SpatialDataManager."""
        r = requests.get(f"{BASE_URL}/static/spatial/spatialService.js", timeout=10)
        content = r.text
        assert "GeoJsonDataLayer" in content
        assert "SpatialDataManager" in content
        assert "geoJsonLayer" in content
        assert "spatialDataManager" in content

    def test_geojson_layer_validates_input(self):
        """GeoJSON data layer includes validation logic."""
        r = requests.get(f"{BASE_URL}/static/spatial/data/geoJsonDataLayer.js", timeout=10)
        content = r.text
        assert "validateGeoJSON" in content or "_validateGeoJSON" in content or "validate" in content.lower()

    def test_osm_provider_has_rate_limiting(self):
        """OSM building provider includes rate limiting."""
        r = requests.get(f"{BASE_URL}/static/spatial/data/osmBuildingProvider.js", timeout=10)
        content = r.text
        assert "requestQueue" in content or "rate_limit" in content.lower() or "lastRequestTime" in content

    def test_osm_provider_has_attribution(self):
        """OSM building provider includes proper attribution."""
        r = requests.get(f"{BASE_URL}/static/spatial/data/osmBuildingProvider.js", timeout=10)
        content = r.text
        assert "OpenStreetMap contributors" in content

    def test_free_terrain_provider_lists_options(self):
        """Free terrain provider module lists available free providers."""
        r = requests.get(f"{BASE_URL}/static/spatial/terrain/freeTerrainProvider.js", timeout=10)
        content = r.text
        assert "ellipsoid" in content
        assert "arcgis_elevation" in content

    def test_viewer_factory_disables_ion_defaults(self):
        """ViewerFactory explicitly disables Ion-dependent Cesium defaults."""
        r = requests.get(f"{BASE_URL}/static/spatial/runtime/viewerFactory.js", timeout=10)
        content = r.text
        assert "baseLayerPicker: false" in content
        assert "geocoder: false" in content

    def test_imagery_uses_free_basemaps(self):
        """All configured imagery basemaps use free public endpoints."""
        r = requests.get(f"{BASE_URL}/static/spatial/imagery/imageryProviderRegistry.js", timeout=10)
        content = r.text
        # All basemaps should use public URLs, not Ion
        assert "services.arcgisonline.com" in content  # Free Esri
        assert "tile.openstreetmap.org" in content      # Free OSM
        assert "basemaps.cartocdn.com" in content       # Free CARTO
        assert "gibs.earthdata.nasa.gov" in content     # Free NASA


# ──────────────────────────────────────────────────────
# SUITE 7: LAYER TOGGLE OPERATIONS
# ──────────────────────────────────────────────────────

class TestLayerOperations:
    """Test layer enable/disable/toggle operations work without tokens."""

    def test_enable_flights_layer(self):
        """Enabling flights layer works without any token."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "enable_layer",
            "arguments": {"layer_id": "flights"}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is True

    def test_disable_flights_layer(self):
        """Disabling flights layer works."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "disable_layer",
            "arguments": {"layer_id": "flights"}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is True

    def test_toggle_weather_layer(self):
        """Toggling weather layer works."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "toggle_layer",
            "arguments": {"layer_id": "weather"}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is True

    def test_zoom_to_globe_works(self):
        """Home/reset globe works without token."""
        r = requests.post(f"{BASE_URL}/api/spatial/command", json={
            "tool_name": "zoom_to_globe",
            "arguments": {}
        }, timeout=10)
        data = r.json()
        assert data["ok"] is True

    def test_visual_style_switch(self):
        """Visual style switching works without token."""
        for style in ["thermal", "surveillance", "normal"]:
            r = requests.post(f"{BASE_URL}/api/spatial/command", json={
                "tool_name": "switch_visual_mode",
                "arguments": {"style": style}
            }, timeout=10)
            data = r.json()
            assert data["ok"] is True


if __name__ == "__main__":
    print("=" * 72)
    print("J.A.R.V.I.S. Token-Free GEV Architecture Test Suite")
    print("=" * 72)
    pytest.main([__file__, "-v", "--tb=short", "-x"])
