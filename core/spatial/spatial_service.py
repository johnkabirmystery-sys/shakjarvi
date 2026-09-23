"""
Spatial Intelligence Service (core/spatial/spatial_service.py)
==============================================================
Central orchestration service coordinating God's Eye View capabilities,
client command queuing, state synchronization, and fail-safe recovery.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from core.spatial.spatial_session import spatial_session, SpatialSession
from core.spatial.spatial_query_engine import spatial_query_engine, SpatialQueryEngine
from core.spatial.provider_manager import provider_manager, ProviderManager
from core.spatial.spatial_tools import execute_spatial_tool, SPATIAL_TOOLS


class SpatialService:
    """Singleton service bridging Jarvis Core with God's Eye View subsystem."""

    def __init__(self):
        self.session: SpatialSession = spatial_session
        self.query_engine: SpatialQueryEngine = spatial_query_engine
        self.providers: ProviderManager = provider_manager
        self.broadcast_callback: Optional[Callable[[Dict[str, Any]], Any]] = None
        self.is_ready: bool = True
        self.degraded_mode: bool = False
        self.command_queue: List[Dict[str, Any]] = []
        self._startup_time = time.time()

    def set_broadcast_callback(self, cb: Callable[[Dict[str, Any]], Any]):
        self.broadcast_callback = cb

    async def broadcast_spatial_event(self, event_type: str, data: Dict[str, Any]):
        """Dispatches spatial events to active WebSocket clients."""
        payload = {
            "type": "spatial_event",
            "event": event_type,
            "data": data,
            "timestamp": time.time()
        }
        if self.broadcast_callback:
            try:
                res = self.broadcast_callback(payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                print(f"[SpatialService] Broadcast error: {e}")

    async def execute_command(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a spatial tool and broadcasts client actions to the HUD."""
        result = execute_spatial_tool(tool_name, args)

        # If tool generated a client action, dispatch to frontend command bus
        if result.get("ok") and "client_action" in result:
            await self.broadcast_spatial_event(
                event_type="command",
                data={
                    "action": result["client_action"],
                    "params": result.get("params") or result.get("target") or {},
                    "commandId": f"cmd_{int(time.time()*1000)}"
                }
            )

        return result

    def get_health(self) -> Dict[str, Any]:
        """Provides complete health metrics for /api/spatial/health."""
        p_health = self.providers.get_health_summary()
        return {
            "service": "Jarvis Spatial Intelligence (God's Eye View)",
            "uptime_seconds": round(time.time() - self._startup_time, 1),
            "is_ready": self.is_ready,
            "degraded_mode": self.degraded_mode,
            "providers": p_health,
            "session": self.session.to_dict(),
            "capabilities": {
                "3d_globe": True,
                "photoreal_tiles": True,
                "flight_tracking": True,
                "maritime_tracking": True,
                "satellite_orbits": True,
                "thermal_anomalies": True,
                "weather_radar_wind": True,
                "cockpit_mode": True,
                "annotations": True,
                "measurements": True
            }
        }


spatial_service = SpatialService()
