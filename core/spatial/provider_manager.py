"""
Spatial Provider Manager (core/spatial/provider_manager.py)
==========================================================
Manages health, telemetry, circuit-breaking, rate-limits, and provenance
for all live and public geospatial data providers.
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class ProviderInfo:
    id: str
    name: str
    category: str
    status: str = "AVAILABLE"  # LIVE, RECENT, STALE, FALLBACK, UNAVAILABLE
    capabilities: List[str] = field(default_factory=list)
    requires_key: bool = False
    is_configured: bool = True
    rate_limit_per_min: int = 60
    request_count: int = 0
    error_count: int = 0
    consecutive_failures: int = 0
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    last_latency_ms: float = 0.0
    last_error: Optional[str] = None
    freshness_sec: float = 0.0
    fallback_provider_id: Optional[str] = None


class ProviderManager:
    """Isolates and monitors all public and keyed geospatial data feeds."""

    def __init__(self):
        self.providers: Dict[str, ProviderInfo] = {}
        self._register_default_providers()

    def _register_default_providers(self):
        defaults = [
            ProviderInfo(
                id="esri-basemap",
                name="Esri World Imagery",
                category="basemap",
                status="LIVE",
                capabilities=["satellite_imagery", "global_coverage"],
                requires_key=False,
                is_configured=True,
                rate_limit_per_min=600
            ),
            ProviderInfo(
                id="osm-basemap",
                name="OpenStreetMap",
                category="basemap",
                status="AVAILABLE",
                capabilities=["vector_tiles", "roads", "labels"],
                requires_key=False,
                is_configured=True,
                rate_limit_per_min=300
            ),
            ProviderInfo(
                id="google-3d-tiles",
                name="Google Photorealistic 3D Tiles",
                category="basemap",
                status="AVAILABLE",
                capabilities=["photorealistic_3d", "street_mesh", "trees"],
                requires_key=True,
                is_configured=False,
                rate_limit_per_min=120,
                fallback_provider_id="esri-basemap"
            ),
            ProviderInfo(
                id="cesium-ion",
                name="Cesium ion World Terrain / Imagery",
                category="terrain",
                status="AVAILABLE",
                capabilities=["global_elevation", "bathymetry", "bing_aerial"],
                requires_key=True,
                is_configured=False,
                rate_limit_per_min=300
            ),
            ProviderInfo(
                id="nominatim",
                name="Nominatim OpenStreetMap Geocoder",
                category="search",
                status="LIVE",
                capabilities=["geocoding", "reverse_geocoding", "place_search"],
                requires_key=False,
                is_configured=True,
                rate_limit_per_min=60
            ),
            ProviderInfo(
                id="photon",
                name="Photon Komoot Geocoder",
                category="search",
                status="LIVE",
                capabilities=["fast_autocomplete", "geocoding"],
                requires_key=False,
                is_configured=True,
                rate_limit_per_min=120
            ),
            ProviderInfo(
                id="opensky",
                name="OpenSky Network ADS-B",
                category="aviation",
                status="LIVE",
                capabilities=["live_flights", "military_transponders", "altitude"],
                requires_key=False,  # Anonymous tier supported
                is_configured=True,
                rate_limit_per_min=10,
                freshness_sec=10.0
            ),
            ProviderInfo(
                id="aisstream",
                name="AISStream Maritime Vessels",
                category="maritime",
                status="AVAILABLE",
                capabilities=["live_ships", "tankers", "cargo", "coordinates"],
                requires_key=True,
                is_configured=False,
                rate_limit_per_min=120
            ),
            ProviderInfo(
                id="nasa-firms",
                name="NASA FIRMS Thermal Anomalies",
                category="hazard",
                status="AVAILABLE",
                capabilities=["wildfires", "thermal_spots", "brightness"],
                requires_key=True,
                is_configured=False,
                rate_limit_per_min=30
            ),
            ProviderInfo(
                id="usgs-earthquakes",
                name="USGS Real-time Earthquakes",
                category="hazard",
                status="LIVE",
                capabilities=["seismic_events", "magnitude", "depth"],
                requires_key=False,
                is_configured=True,
                rate_limit_per_min=60
            ),
            ProviderInfo(
                id="celestrak",
                name="CelesTrak TLE Satellite Orbits",
                category="space",
                status="LIVE",
                capabilities=["orbital_elements", "starlink", "iss", "debris"],
                requires_key=False,
                is_configured=True,
                rate_limit_per_min=30
            ),
            ProviderInfo(
                id="launch-library-2",
                name="Launch Library 2 Space Missions",
                category="space",
                status="LIVE",
                capabilities=["upcoming_launches", "rocket_pads", "livestreams"],
                requires_key=False,
                is_configured=True,
                rate_limit_per_min=30
            ),
            ProviderInfo(
                id="noaa-gfs",
                name="NOAA GFS Weather & Wind",
                category="weather",
                status="LIVE",
                capabilities=["10m_wind_streamlines", "radar_composite", "clouds"],
                requires_key=False,
                is_configured=True,
                rate_limit_per_min=60
            ),
            ProviderInfo(
                id="radio-browser",
                name="Community Radio Browser",
                category="media",
                status="LIVE",
                capabilities=["live_audio_streams", "station_locations"],
                requires_key=False,
                is_configured=True,
                rate_limit_per_min=60
            )
        ]
        for p in defaults:
            self.providers[p.id] = p

    def record_request_result(
        self,
        provider_id: str,
        success: bool,
        latency_ms: float = 0.0,
        error: Optional[str] = None
    ) -> None:
        if provider_id not in self.providers:
            return

        p = self.providers[provider_id]
        p.request_count += 1
        p.last_latency_ms = round(latency_ms, 1)

        if success:
            p.last_success = time.time()
            p.consecutive_failures = 0
            p.status = "LIVE"
            p.last_error = None
        else:
            p.error_count += 1
            p.consecutive_failures += 1
            p.last_failure = time.time()
            p.last_error = error or "Request failed"

            # Circuit breaker ladder: 3 consecutive fails -> STALE, 5 -> FALLBACK / UNAVAILABLE
            if p.consecutive_failures >= 5:
                p.status = "FALLBACK" if p.fallback_provider_id else "UNAVAILABLE"
            elif p.consecutive_failures >= 3:
                p.status = "STALE"

    def get_provider(self, provider_id: str) -> Optional[ProviderInfo]:
        return self.providers.get(provider_id)

    def get_all_providers(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "status": p.status,
                "capabilities": p.capabilities,
                "requires_key": p.requires_key,
                "is_configured": p.is_configured,
                "last_latency_ms": p.last_latency_ms,
                "error": p.last_error,
                "consecutive_failures": p.consecutive_failures
            }
            for p in self.providers.values()
        ]

    def get_health_summary(self) -> Dict[str, Any]:
        live = sum(1 for p in self.providers.values() if p.status == "LIVE")
        available = sum(1 for p in self.providers.values() if p.status in ["LIVE", "AVAILABLE"])
        unavailable = sum(1 for p in self.providers.values() if p.status in ["UNAVAILABLE", "FALLBACK"])
        return {
            "total_providers": len(self.providers),
            "live": live,
            "available": available,
            "degraded_or_unavailable": unavailable,
            "overall_status": "OPTIMAL" if unavailable <= 2 else "DEGRADED"
        }


provider_manager = ProviderManager()
