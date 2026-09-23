"""
Spatial Query Engine (core/spatial/spatial_query_engine.py)
==========================================================
Deterministic spatial mathematics, geometric calculations, and computational
filtering. Keeps massive raw geospatial datasets out of the LLM context by
computing counts, top-k, nearest-k, distance, bearing, and area server-side.
"""

import math
import time
from typing import List, Dict, Any, Tuple, Optional


class SpatialQueryEngine:
    """Provides high-performance, deterministic geospatial analytics."""

    EARTH_RADIUS_KM = 6371.0
    KM_TO_NM = 0.539957

    @staticmethod
    def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates great-circle distance between two points in kilometers."""
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return SpatialQueryEngine.EARTH_RADIUS_KM * c

    @staticmethod
    def haversine_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates great-circle distance in nautical miles."""
        return SpatialQueryEngine.haversine_distance_km(lat1, lon1, lat2, lon2) * SpatialQueryEngine.KM_TO_NM

    @staticmethod
    def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates initial compass bearing from point 1 to point 2 (0° - 360°)."""
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dlambda = math.radians(lon2 - lon1)

        x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
        y = math.sin(dlambda) * math.cos(phi2)
        initial_bearing = math.atan2(y, x)
        compass_bearing = (math.degrees(initial_bearing) + 360.0) % 360.0
        return round(compass_bearing, 1)

    @staticmethod
    def polygon_area_sq_km(coordinates: List[Tuple[float, float]]) -> float:
        """
        Calculates spherical area of a closed polygon in square kilometers.
        Coordinates given as list of (lat, lon).
        """
        if len(coordinates) < 3:
            return 0.0

        coords = list(coordinates)
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        total = 0.0
        for i in range(len(coords) - 1):
            lat1, lon1 = coords[i]
            lat2, lon2 = coords[i + 1]
            total += math.radians(lon2 - lon1) * (2.0 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2)))

        area = abs(total * (SpatialQueryEngine.EARTH_RADIUS_KM ** 2) / 2.0)
        return round(area, 2)

    @staticmethod
    def point_in_polygon(lat: float, lon: float, polygon: List[Tuple[float, float]]) -> bool:
        """Ray-casting algorithm to test whether (lat, lon) is inside a polygon."""
        n = len(polygon)
        if n < 3:
            return False

        inside = False
        p1lat, p1lon = polygon[0]
        for i in range(n + 1):
            p2lat, p2lon = polygon[i % n]
            if min(p1lat, p2lat) < lat <= max(p1lat, p2lat):
                if lon <= max(p1lon, p2lon):
                    if p1lat != p2lat:
                        xinters = (lat - p1lat) * (p2lon - p1lon) / (p2lat - p1lat) + p1lon
                    if p1lon == p2lon or lon <= xinters:
                        inside = not inside
            p1lat, p1lon = p2lat, p2lon
        return inside

    @classmethod
    def filter_within_radius(
        cls,
        center_lat: float,
        center_lon: float,
        radius_km: float,
        entities: List[Dict[str, Any]],
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Filters entities within radius and calculates exact distance."""
        results = []
        for e in entities:
            lat = e.get("latitude") or e.get("lat")
            lon = e.get("longitude") or e.get("lon")
            if lat is None or lon is None:
                continue

            dist = cls.haversine_distance_km(center_lat, center_lon, float(lat), float(lon))
            if dist <= radius_km:
                item = dict(e)
                item["distance_km"] = round(dist, 2)
                item["distance_nm"] = round(dist * cls.KM_TO_NM, 2)
                results.append(item)

        results.sort(key=lambda x: x["distance_km"])
        return results[:limit]

    @classmethod
    def aggregate_and_summarize(
        cls,
        category: str,
        entities: List[Dict[str, Any]],
        center_lat: float,
        center_lon: float,
        radius_km: float,
        source: str = "public_feed"
    ) -> Dict[str, Any]:
        """
        Creates a bounded, LLM-safe summary package containing aggregate stats
        and top-5 nearest entities without bloating prompt token windows.
        """
        filtered = cls.filter_within_radius(center_lat, center_lon, radius_km, entities, limit=50)
        total_count = len(filtered)

        top_nearest = []
        for item in filtered[:5]:
            top_nearest.append({
                "id": item.get("id") or item.get("callsign") or item.get("mmsi") or "Unknown",
                "name": item.get("name") or item.get("callsign") or item.get("label") or "Unnamed",
                "distance_km": item.get("distance_km"),
                "altitude_m": item.get("altitude_m") or item.get("altitude") or item.get("baro_altitude"),
                "speed_kts": item.get("speed_kts") or item.get("velocity"),
                "heading": item.get("heading") or item.get("true_track")
            })

        # Calculate category statistics
        altitudes = [
            float(e["altitude_m"]) for e in filtered
            if e.get("altitude_m") is not None and str(e["altitude_m"]).replace('.', '', 1).isdigit()
        ]
        avg_alt = round(sum(altitudes) / len(altitudes), 0) if altitudes else None

        speeds = [
            float(e["speed_kts"]) for e in filtered
            if e.get("speed_kts") is not None and str(e["speed_kts"]).replace('.', '', 1).isdigit()
        ]
        avg_speed = round(sum(speeds) / len(speeds), 1) if speeds else None

        return {
            "category": category,
            "total_count": total_count,
            "radius_km": radius_km,
            "center": {"latitude": center_lat, "longitude": center_lon},
            "nearest_entities": top_nearest,
            "metrics": {
                "average_altitude_m": avg_alt,
                "average_speed_kts": avg_speed,
                "max_altitude_m": max(altitudes) if altitudes else None,
                "max_speed_kts": max(speeds) if speeds else None,
            },
            "provenance": {
                "source": source,
                "freshness_sec": 12.0,
                "timestamp": time.time(),
                "status": "LIVE" if total_count > 0 else "AVAILABLE"
            }
        }


spatial_query_engine = SpatialQueryEngine()
