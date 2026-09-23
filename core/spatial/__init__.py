"""
J.A.R.V.I.S. Spatial Intelligence Subsystem (core/spatial)
=========================================================
Deep integration of God's Eye View with Jarvis Core.
Provides spatial awareness, 3D geospatial intelligence, live public data
orchestration, entity tracking, spatial querying, and agent routing.
"""

from .spatial_service import spatial_service, SpatialService
from .spatial_session import spatial_session, SpatialSession
from .spatial_query_engine import spatial_query_engine, SpatialQueryEngine
from .provider_manager import provider_manager, ProviderManager
from .spatial_tools import SPATIAL_TOOLS, execute_spatial_tool

__all__ = [
    "spatial_service",
    "SpatialService",
    "spatial_session",
    "SpatialSession",
    "spatial_query_engine",
    "SpatialQueryEngine",
    "provider_manager",
    "ProviderManager",
    "SPATIAL_TOOLS",
    "execute_spatial_tool",
]
