"""
Spatial Analysis & Geofencing Engine (core/spatial/spatial_analysis.py)
=====================================================================
Provides personal geofencing, radius proximity searches, geodesic
bounding box analysis, and strict privacy-preserving tracking policies.
- Personal geofencing: alerts on enter/exit of user's own device.
- Explicit refusal of third-party surveillance / unauthorized tracking.
- Proximity analysis against live public feeds (USGS quakes, NOAA weather).
"""

import time
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from core.spatial.spatial_query_engine import spatial_query_engine


@dataclass
class Geofence:
    id: str
    name: str
    latitude: float
    longitude: float
    radius_meters: float
    created_at: float = field(default_factory=time.time)
    notify_on_enter: bool = True
    notify_on_exit: bool = True
    last_state: str = "OUTSIDE"  # INSIDE, OUTSIDE, UNKNOWN


class SpatialAnalysisEngine:
    """Analytical spatial computing and personal geofencing engine."""

    def __init__(self):
        self.geofences: Dict[str, Geofence] = {}
        self.geofence_events: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # 1. GEOFENCING (PERSONAL DEVICE ONLY)
    # ------------------------------------------------------------------
    def create_geofence(
        self,
        name: str,
        latitude: float,
        longitude: float,
        radius_meters: float = 100.0,
        fence_id: Optional[str] = None
    ) -> Dict[str, Any]:
        lat = float(latitude)
        lon = float(longitude)
        rad = float(radius_meters)

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return {"ok": False, "error": f"Invalid coordinates: ({lat}, {lon})"}
        if rad <= 0:
            return {"ok": False, "error": f"Geofence radius must be positive: {rad}m"}

        fid = fence_id or f"fence_{int(time.time()*1000)}"
        fence = Geofence(
            id=fid,
            name=name,
            latitude=lat,
            longitude=lon,
            radius_meters=rad
        )
        self.geofences[fid] = fence
        return {
            "ok": True,
            "geofence": {
                "id": fid,
                "name": name,
                "latitude": lat,
                "longitude": lon,
                "radiusMeters": rad,
                "createdAt": fence.created_at
            }
        }

    def remove_geofence(self, fence_id: str) -> Dict[str, Any]:
        if fence_id in self.geofences:
            del self.geofences[fence_id]
            return {"ok": True, "deletedId": fence_id}
        return {"ok": False, "error": f"Geofence '{fence_id}' not found."}

    def list_geofences(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": f.id,
                "name": f.name,
                "latitude": f.latitude,
                "longitude": f.longitude,
                "radiusMeters": f.radius_meters,
                "lastState": f.last_state,
                "createdAt": f.created_at
            }
            for f in self.geofences.values()
        ]

    def evaluate_geofences(self, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
        """Evaluates all active geofences against user's current position."""
        triggered_events = []

        for fid, fence in self.geofences.items():
            dist_km = spatial_query_engine.haversine_distance_km(
                user_lat, user_lon, fence.latitude, fence.longitude
            )
            dist_m = dist_km * 1000.0
            is_inside = dist_m <= fence.radius_meters
            new_state = "INSIDE" if is_inside else "OUTSIDE"

            if fence.last_state != "UNKNOWN" and fence.last_state != new_state:
                event_type = "ENTER" if new_state == "INSIDE" else "EXIT"
                event = {
                    "fenceId": fid,
                    "fenceName": fence.name,
                    "eventType": event_type,
                    "distanceMeters": round(dist_m, 1),
                    "timestamp": time.time(),
                    "userCoords": [user_lat, user_lon]
                }
                self.geofence_events.append(event)
                triggered_events.append(event)

            fence.last_state = new_state

        return triggered_events

    # ------------------------------------------------------------------
    # 2. PROXIMITY & RADIUS SEARCHES
    # ------------------------------------------------------------------
    def find_entities_within_radius(
        self,
        center_lat: float,
        center_lon: float,
        radius_km: float,
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        results = []
        for ent in entities:
            e_lat = ent.get("latitude") or ent.get("lat")
            e_lon = ent.get("longitude") or ent.get("lon")
            if e_lat is None or e_lon is None:
                continue

            dist_km = spatial_query_engine.haversine_distance_km(
                center_lat, center_lon, float(e_lat), float(e_lon)
            )
            if dist_km <= radius_km:
                results.append({
                    **ent,
                    "distance_km": round(dist_km, 2),
                    "bearing_deg": spatial_query_engine.initial_bearing_deg(
                        center_lat, center_lon, float(e_lat), float(e_lon)
                    )
                })

        return sorted(results, key=lambda x: x["distance_km"])

    # ------------------------------------------------------------------
    # 3. PRIVACY & SAFETY REFUSAL GATEWAY
    # ------------------------------------------------------------------
    def validate_tracking_request(self, target_description: str) -> Dict[str, Any]:
        """Checks if a user request attempts unauthorized surveillance of an external person."""
        desc = target_description.lower().strip()
        unauthorized_indicators = [
            "track my wife", "track my husband", "track my girlfriend", "track my boyfriend",
            "track person", "track someone", "spy on", "find user", "locate user",
            "hack location", "secretly track", "covertly follow", "stalk"
        ]

        for phrase in unauthorized_indicators:
            if phrase in desc:
                return {
                    "allowed": False,
                    "reason": "PRIVACY_POLICY_VIOLATION",
                    "explanation": (
                        "J.A.R.V.I.S. strictly enforces personal privacy. Tracking another individual "
                        "without technical device authorization and explicit consent is strictly prohibited."
                    )
                }

        return {"allowed": True}


spatial_analysis_engine = SpatialAnalysisEngine()
