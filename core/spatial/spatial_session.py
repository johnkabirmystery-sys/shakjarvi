"""
Spatial Session Manager (core/spatial/spatial_session.py)
=========================================================
Maintains live spatial context, selected entities, active missions,
temporary annotations, and cross-agent context handoffs.
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class SpatialLocation:
    name: str = "World Overview"
    latitude: float = 20.0
    longitude: float = 0.0
    altitude: float = 20000000.0  # meters
    view_mode: str = "globe"
    bbox: Optional[List[float]] = None
    confidence: float = 1.0
    match_type: str = "EXACT"


@dataclass
class TrackedEntity:
    id: str
    layer_id: str
    name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_m: float = 0.0
    heading_deg: float = 0.0
    speed_kts: float = 0.0
    provider: str = "unknown"
    freshness_sec: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class SpatialSession:
    def __init__(self):
        self.location: SpatialLocation = SpatialLocation()
        self.tracked_entity: Optional[TrackedEntity] = None
        self.selected_entity: Optional[Dict[str, Any]] = None
        self.active_layers: List[str] = ["flights"]
        self.active_map_source: str = "esri-imagery"
        self.active_visual_style: str = "normal"
        self.in_cockpit: bool = False
        self.active_mission: Optional[Dict[str, Any]] = None
        self.temporary_annotations: List[Dict[str, Any]] = []
        self.command_history: List[Dict[str, Any]] = []
        self.last_updated: float = time.time()

    def update_location(
        self,
        name: str,
        latitude: float,
        longitude: float,
        altitude: float = 10000.0,
        view_mode: str = "overview",
        bbox: Optional[List[float]] = None,
        confidence: float = 1.0,
        match_type: str = "CITY"
    ) -> SpatialLocation:
        self.location = SpatialLocation(
            name=name,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            view_mode=view_mode,
            bbox=bbox,
            confidence=confidence,
            match_type=match_type
        )
        self.last_updated = time.time()
        return self.location

    def set_tracked_entity(
        self,
        entity_id: str,
        layer_id: str,
        name: str = "",
        latitude: float = 0.0,
        longitude: float = 0.0,
        altitude_m: float = 0.0,
        heading_deg: float = 0.0,
        speed_kts: float = 0.0,
        provider: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ) -> TrackedEntity:
        self.tracked_entity = TrackedEntity(
            id=entity_id,
            layer_id=layer_id,
            name=name or entity_id,
            latitude=latitude,
            longitude=longitude,
            altitude_m=altitude_m,
            heading_deg=heading_deg,
            speed_kts=speed_kts,
            provider=provider,
            metadata=metadata or {},
            timestamp=time.time()
        )
        self.last_updated = time.time()
        return self.tracked_entity

    def clear_tracked_entity(self) -> None:
        self.tracked_entity = None
        self.in_cockpit = False
        self.last_updated = time.time()

    def toggle_layer(self, layer_id: str) -> bool:
        if layer_id in self.active_layers:
            self.active_layers.remove(layer_id)
            return False
        else:
            self.active_layers.append(layer_id)
            return True

    def enable_layer(self, layer_id: str) -> None:
        if layer_id not in self.active_layers:
            self.active_layers.append(layer_id)
        self.last_updated = time.time()

    def disable_layer(self, layer_id: str) -> None:
        if layer_id in self.active_layers:
            self.active_layers.remove(layer_id)
        self.last_updated = time.time()

    def add_annotation(self, annotation: Dict[str, Any]) -> None:
        annotation["id"] = annotation.get("id", f"ann_{int(time.time()*1000)}")
        annotation["created_at"] = time.time()
        self.temporary_annotations.append(annotation)
        self.last_updated = time.time()

    def clear_annotations(self) -> int:
        count = len(self.temporary_annotations)
        self.temporary_annotations.clear()
        self.last_updated = time.time()
        return count

    def get_summary_context(self) -> str:
        """Returns a concise text summary of active spatial state for LLM prompt injection."""
        loc = self.location
        loc_str = f"{loc.name} ({loc.latitude:.4f}, {loc.longitude:.4f})" if loc.name != "World Overview" else "Global Earth Overview"
        layers_str = ", ".join(self.active_layers) if self.active_layers else "None"
        
        tracking_str = "None"
        if self.tracked_entity:
            t = self.tracked_entity
            tracking_str = f"{t.name or t.id} [{t.layer_id}] (Alt: {int(t.altitude_m)}m, Speed: {int(t.speed_kts)} kts)"
            if self.in_cockpit:
                tracking_str += " [COCKPIT ACTIVE]"

        return (
            f"- Spatial Target: {loc_str}\n"
            f"- Active Layers: {layers_str}\n"
            f"- Tracked Entity: {tracking_str}\n"
            f"- Visual Mode: {self.active_visual_style.upper()} | Basemap: {self.active_map_source}"
        )

    def export_handoff_context(self, target_agent: str = "") -> Dict[str, Any]:
        """Provides machine-readable spatial context for agent-to-agent delegation."""
        return {
            "target_agent": target_agent,
            "location": {
                "name": self.location.name,
                "latitude": self.location.latitude,
                "longitude": self.location.longitude,
                "altitude": self.location.altitude,
                "bbox": self.location.bbox,
                "match_type": self.location.match_type
            },
            "tracked_entity": {
                "id": self.tracked_entity.id,
                "layer_id": self.tracked_entity.layer_id,
                "name": self.tracked_entity.name,
                "altitude_m": self.tracked_entity.altitude_m,
                "speed_kts": self.tracked_entity.speed_kts,
                "provider": self.tracked_entity.provider
            } if self.tracked_entity else None,
            "active_layers": list(self.active_layers),
            "visual_style": self.active_visual_style,
            "exported_at": time.time()
        }

    def import_handoff_context(self, context: Dict[str, Any]) -> None:
        if "location" in context:
            l = context["location"]
            self.update_location(
                name=l.get("name", "Unknown"),
                latitude=float(l.get("latitude", 0.0)),
                longitude=float(l.get("longitude", 0.0)),
                altitude=float(l.get("altitude", 10000.0)),
                bbox=l.get("bbox")
            )
        if "active_layers" in context:
            self.active_layers = list(context["active_layers"])
        self.last_updated = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "location": {
                "name": self.location.name,
                "latitude": self.location.latitude,
                "longitude": self.location.longitude,
                "altitude": self.location.altitude,
                "view_mode": self.location.view_mode,
                "bbox": self.location.bbox,
                "confidence": self.location.confidence,
                "match_type": self.location.match_type
            },
            "tracked_entity": {
                "id": self.tracked_entity.id,
                "layer_id": self.tracked_entity.layer_id,
                "name": self.tracked_entity.name,
                "latitude": self.tracked_entity.latitude,
                "longitude": self.tracked_entity.longitude,
                "altitude_m": self.tracked_entity.altitude_m,
                "heading_deg": self.tracked_entity.heading_deg,
                "speed_kts": self.tracked_entity.speed_kts,
                "provider": self.tracked_entity.provider,
                "freshness_sec": round(time.time() - self.tracked_entity.timestamp, 1)
            } if self.tracked_entity else None,
            "active_layers": self.active_layers,
            "active_map_source": self.active_map_source,
            "active_visual_style": self.active_visual_style,
            "in_cockpit": self.in_cockpit,
            "annotations_count": len(self.temporary_annotations),
            "last_updated": self.last_updated
        }


spatial_session = SpatialSession()
