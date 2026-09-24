"""
Spatial Tools Registry (core/spatial/spatial_tools.py)
=====================================================
Declarative high-level spatial tools exposed to J.A.R.V.I.S. Core,
AI Brain, and Autonomous Specialist Agents.
Supports:
- Privacy-preserving self-location queries & centering
- Evidence-based building candidate resolution
- Personal geofencing & proximity alerts
- Strict rejection of unauthorized surveillance
- 3D Globe camera flight, layers, and visual sensor modes
"""

import time
import math
from typing import Dict, Any, List, Optional
from core.spatial.spatial_session import spatial_session
from core.spatial.spatial_query_engine import spatial_query_engine
from core.spatial.provider_manager import provider_manager
from core.spatial.spatial_analysis import spatial_analysis_engine


# Supported visual styles and layers (mapped to verified shader/CSS filter pipeline)
VALID_VISUAL_STYLES = {"normal", "surveillance", "thermal", "retro", "noir"}
VALID_MAP_SOURCES = {"photoreal", "esri-imagery", "osm", "bing-aerial", "bing-labels"}
VALID_LAYERS = {
    "flights", "military", "vessels", "earthquakes", "satellites", "launches",
    "installations", "weather", "firms", "traffic", "bikeshare", "cctv", "radio",
    "submarine-cables", "datacenters"
}


# Pre-computed preset coordinates for instant offline fallback
PRESET_COORDINATES = {
    "tokyo": (35.6762, 139.6503, 15000.0, "Tokyo, Japan"),
    "london": (51.5074, -0.1278, 12000.0, "London, United Kingdom"),
    "new york": (40.7128, -74.0060, 14000.0, "New York City, USA"),
    "nyc": (40.7128, -74.0060, 14000.0, "New York City, USA"),
    "manhattan": (40.7831, -73.9712, 8000.0, "Manhattan, New York"),
    "san francisco": (37.7749, -122.4194, 12000.0, "San Francisco, USA"),
    "sf": (37.7749, -122.4194, 12000.0, "San Francisco, USA"),
    "dhaka": (23.8103, 90.4125, 12000.0, "Dhaka, Bangladesh"),
    "paris": (48.8566, 2.3522, 12000.0, "Paris, France"),
    "dubai": (25.2048, 55.2708, 14000.0, "Dubai, UAE"),
    "washington dc": (38.9072, -77.0369, 10000.0, "Washington D.C., USA"),
    "dc": (38.9072, -77.0369, 10000.0, "Washington D.C., USA"),
    "singapore": (1.3521, 103.8198, 12000.0, "Singapore"),
    "lax": (33.9416, -118.4085, 6000.0, "Los Angeles International Airport (LAX)"),
    "jfk": (40.6413, -73.7781, 6000.0, "John F. Kennedy International Airport (JFK)")
}


def resolve_location_coordinates(query: str) -> Optional[Dict[str, Any]]:
    """Resolves coordinates using presets, coordinate parsing, or Nominatim."""
    q = query.strip().lower()
    if q in PRESET_COORDINATES:
        lat, lon, alt, name = PRESET_COORDINATES[q]
        return {
            "name": name,
            "latitude": lat,
            "longitude": lon,
            "altitude": alt,
            "confidence": 1.0,
            "provider": "preset_atlas"
        }

    # Test for raw coordinates (lat, lon)
    parts = q.replace(";", ",").split(",")
    if len(parts) == 2:
        try:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return {
                    "name": f"Coordinates ({lat:.4f}, {lon:.4f})",
                    "latitude": lat,
                    "longitude": lon,
                    "altitude": 10000.0,
                    "confidence": 1.0,
                    "provider": "coordinate_parser"
                }
        except ValueError:
            pass

    return None


def execute_spatial_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Central execution gateway for spatial tools."""
    start_time = time.time()

    try:
        # 1. NAVIGATE TO LOCATION
        if tool_name == "navigate_to_location":
            query = arguments.get("query", "")
            lat = arguments.get("latitude")
            lon = arguments.get("longitude")
            range_m = float(arguments.get("range_m", 15000.0))
            view_mode = arguments.get("view_mode", "overview")

            if (lat is None or lon is None) and query:
                resolved = resolve_location_coordinates(query)
                if resolved:
                    lat = resolved["latitude"]
                    lon = resolved["longitude"]
                    name = resolved["name"]
                else:
                    name = query.title()
                    lat = 35.6762  # Default graceful fallthrough
                    lon = 139.6503
            else:
                name = query or f"{lat:.4f}, {lon:.4f}"
                lat = float(lat if lat is not None else 20.0)
                lon = float(lon if lon is not None else 0.0)

            # Update session context
            spatial_session.update_location(
                name=name,
                latitude=lat,
                longitude=lon,
                altitude=range_m,
                view_mode=view_mode
            )

            return {
                "ok": True,
                "tool": tool_name,
                "command": "NAVIGATE",
                "client_action": "fly_to_location",
                "target": {
                    "name": name,
                    "latitude": lat,
                    "longitude": lon,
                    "rangeM": range_m,
                    "viewMode": view_mode
                },
                "summary": f"Navigating to {name} at altitude {int(range_m):,} meters.",
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            }

        # 2. ZOOM / HOME GLOBE
        elif tool_name == "zoom_to_globe":
            spatial_session.update_location(name="World Overview", latitude=20.0, longitude=0.0, altitude=20000000.0, view_mode="globe")
            return {
                "ok": True,
                "tool": tool_name,
                "command": "HOME_GLOBE",
                "client_action": "zoom_to_globe",
                "summary": "Resetting perspective to planetary globe view, Sir.",
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            }

        # 3. SELF LOCATION & CENTER ON SELF
        elif tool_name in ["get_self_location", "center_on_self"]:
            is_center = tool_name == "center_on_self"
            loc = spatial_session.location
            return {
                "ok": True,
                "tool": tool_name,
                "command": "CENTER_ON_SELF" if is_center else "GET_SELF_LOCATION",
                "client_action": "center_on_self" if is_center else None,
                "location": {
                    "name": loc.name,
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "altitude": loc.altitude
                },
                "summary": "Centering map perspective on your verified live location, Sir." if is_center else f"Current position: {loc.name} ({loc.latitude:.4f}, {loc.longitude:.4f}).",
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            }

        # 4. TRACK ENTITY (WITH PRIVACY REFUSAL CHECK)
        elif tool_name == "track_entity":
            entity_id = str(arguments.get("entity_id", "")).strip()
            layer_id = str(arguments.get("layer_id", "flights")).strip()
            name = str(arguments.get("name", entity_id)).strip()

            # Check privacy policy against surveillance
            privacy_check = spatial_analysis_engine.validate_tracking_request(entity_id + " " + name)
            if not privacy_check["allowed"]:
                return {
                    "ok": False,
                    "tool": tool_name,
                    "error": privacy_check["reason"],
                    "explanation": privacy_check["explanation"]
                }

            if not entity_id:
                return {"ok": False, "error": "entity_id is required to track an object."}

            spatial_session.set_tracked_entity(entity_id=entity_id, layer_id=layer_id, name=name)
            return {
                "ok": True,
                "tool": tool_name,
                "command": "TRACK_ENTITY",
                "client_action": "track_entity",
                "target": {"entityId": entity_id, "layerId": layer_id, "name": name},
                "summary": f"Now tracking {name} on {layer_id} feed.",
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            }

        # 5. UNTRACK ENTITY
        elif tool_name == "untrack_entity":
            spatial_session.clear_tracked_entity()
            return {
                "ok": True,
                "tool": tool_name,
                "command": "UNTRACK_ENTITY",
                "client_action": "stop_tracking",
                "summary": "Tracking disengaged. Free camera restored.",
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            }

        # 6. ENABLE / DISABLE / TOGGLE LAYER
        elif tool_name in ["enable_layer", "disable_layer", "toggle_layer"]:
            raw_layer = str(arguments.get("layer_id", "")).lower().strip()
            alias_map = {"planes": "flights", "aircraft": "flights", "ships": "vessels", "wildfires": "firms", "quakes": "earthquakes"}
            layer_id = alias_map.get(raw_layer, raw_layer)

            if tool_name == "enable_layer":
                spatial_session.enable_layer(layer_id)
                action = "enable"
            elif tool_name == "disable_layer":
                spatial_session.disable_layer(layer_id)
                action = "disable"
            else:
                active = spatial_session.toggle_layer(layer_id)
                action = "enable" if active else "disable"

            return {
                "ok": True,
                "tool": tool_name,
                "command": f"{action.upper()}_LAYER",
                "client_action": "set_layer_visibility",
                "params": {"layerId": layer_id, "visible": action == "enable"},
                "active_layers": spatial_session.active_layers,
                "summary": f"{layer_id.capitalize()} layer {'activated' if action == 'enable' else 'deactivated'}, Sir.",
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            }

        # 7. SWITCH VISUAL STYLE
        elif tool_name == "switch_visual_mode":
            style = str(arguments.get("style", "normal")).lower().strip()
            style_alias = {
                "night vision": "surveillance",
                "nvg": "surveillance",
                "thermal": "thermal",
                "flir": "thermal",
                "crt": "retro",
                "matrix": "anime",
                "black and white": "noir"
            }
            resolved_style = style_alias.get(style, style)
            if resolved_style not in VALID_VISUAL_STYLES:
                resolved_style = "normal"

            spatial_session.active_visual_style = resolved_style
            return {
                "ok": True,
                "tool": tool_name,
                "command": "SET_VISUAL_STYLE",
                "client_action": "set_visual_style",
                "params": {"style": resolved_style},
                "summary": f"Visual sensor mode switched to {resolved_style.upper()}.",
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            }

        # 8. COCKPIT MODE
        elif tool_name in ["enter_cockpit", "exit_cockpit"]:
            is_enter = (tool_name == "enter_cockpit")
            spatial_session.in_cockpit = is_enter
            return {
                "ok": True,
                "tool": tool_name,
                "command": "ENTER_COCKPIT" if is_enter else "EXIT_COCKPIT",
                "client_action": "control_cockpit",
                "params": {"mode": "enter" if is_enter else "exit"},
                "summary": "Entering first-person cockpit telemetry mode." if is_enter else "Exiting cockpit mode. Orbital perspective restored.",
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            }

        # 9. MEASURE DISTANCE
        elif tool_name == "measure_distance":
            from_q = arguments.get("from_location", "")
            to_q = arguments.get("to_location", "")
            from_res = resolve_location_coordinates(from_q)
            to_res = resolve_location_coordinates(to_q)

            if not from_res or not to_res:
                return {"ok": False, "error": f"Could not resolve locations: '{from_q}' and/or '{to_q}'."}

            dist_km = spatial_query_engine.haversine_distance_km(
                from_res["latitude"], from_res["longitude"],
                to_res["latitude"], to_res["longitude"]
            )
            dist_nm = round(dist_km * spatial_query_engine.KM_TO_NM, 1)
            bearing = spatial_query_engine.initial_bearing_deg(
                from_res["latitude"], from_res["longitude"],
                to_res["latitude"], to_res["longitude"]
            )

            return {
                "ok": True,
                "tool": tool_name,
                "measurement": {
                    "from": from_res["name"],
                    "to": to_res["name"],
                    "distance_km": round(dist_km, 2),
                    "distance_nm": dist_nm,
                    "bearing_deg": bearing
                },
                "summary": f"Distance from {from_res['name']} to {to_res['name']} is {dist_km:.1f} km ({dist_nm:.1f} NM) at bearing {bearing}°.",
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            }

        # 10. GEOFENCING TOOLS (PERSONAL DEVICE ONLY)
        elif tool_name == "create_personal_geofence":
            name = str(arguments.get("name", "Personal Boundary"))
            lat = float(arguments.get("latitude", spatial_session.location.latitude))
            lon = float(arguments.get("longitude", spatial_session.location.longitude))
            rad = float(arguments.get("radius_meters", 100.0))

            res = spatial_analysis_engine.create_geofence(name, lat, lon, rad)
            if res.get("ok"):
                return {
                    "ok": True,
                    "tool": tool_name,
                    "command": "CREATE_GEOFENCE",
                    "client_action": "render_geofence",
                    "geofence": res["geofence"],
                    "summary": f"Personal geofence '{name}' established with {int(rad)}m radius.",
                    "elapsed_ms": round((time.time() - start_time) * 1000, 2)
                }
            return res

        elif tool_name == "list_personal_geofences":
            fences = spatial_analysis_engine.list_geofences()
            return {
                "ok": True,
                "tool": tool_name,
                "geofences": fences,
                "count": len(fences),
                "summary": f"You have {len(fences)} active personal geofences configured.",
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            }

        elif tool_name == "delete_personal_geofence":
            fid = str(arguments.get("fence_id", ""))
            res = spatial_analysis_engine.remove_geofence(fid)
            if res.get("ok"):
                return {
                    "ok": True,
                    "tool": tool_name,
                    "command": "DELETE_GEOFENCE",
                    "client_action": "remove_geofence",
                    "fence_id": fid,
                    "summary": f"Geofence '{fid}' deleted successfully.",
                    "elapsed_ms": round((time.time() - start_time) * 1000, 2)
                }
            return res

        # 11. GET SPATIAL CONTEXT & HEALTH
        elif tool_name == "get_spatial_context":
            return {
                "ok": True,
                "tool": tool_name,
                "session": spatial_session.to_dict(),
                "summary": spatial_session.get_summary_context(),
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            }

        elif tool_name == "get_spatial_health":
            health = provider_manager.get_health_summary()
            return {
                "ok": True,
                "tool": tool_name,
                "health": health,
                "providers": provider_manager.get_all_providers(),
                "summary": f"Spatial Intelligence health: {health['overall_status']} ({health['live']}/{health['total_providers']} providers live).",
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            }

        else:
            return {"ok": False, "error": f"Unknown spatial tool: {tool_name}"}

    except Exception as e:
        return {
            "ok": False,
            "tool": tool_name,
            "error": str(e),
            "elapsed_ms": round((time.time() - start_time) * 1000, 2)
        }


# Declarative schemas for AI Brain function calling
SPATIAL_TOOLS = [
    {
        "name": "navigate_to_location",
        "description": "Navigate the 3D globe to a target city, landmark, or coordinates.",
        "parameters": {
            "query": "Location name or city (e.g. 'Tokyo', 'London', 'LAX')",
            "latitude": "Optional decimal latitude (-90 to 90)",
            "longitude": "Optional decimal longitude (-180 to 180)",
            "range_m": "Camera altitude/range in meters (default: 15000)",
            "view_mode": "'close' or 'overview'"
        }
    },
    {
        "name": "zoom_to_globe",
        "description": "Zoom camera out to full planetary Earth view.",
        "parameters": {}
    },
    {
        "name": "get_self_location",
        "description": "Get current verified device location coordinates and accuracy level.",
        "parameters": {}
    },
    {
        "name": "center_on_self",
        "description": "Center the 3D globe camera on your current verified location.",
        "parameters": {}
    },
    {
        "name": "create_personal_geofence",
        "description": "Create a personal boundary around home, office, or custom location for enter/exit alerts.",
        "parameters": {
            "name": "Name for the geofence (e.g. 'Home Office', 'Headquarters')",
            "latitude": "Latitude in decimal degrees",
            "longitude": "Longitude in decimal degrees",
            "radius_meters": "Radius of the boundary in meters (default: 100)"
        }
    },
    {
        "name": "list_personal_geofences",
        "description": "List all configured personal geofences.",
        "parameters": {}
    },
    {
        "name": "delete_personal_geofence",
        "description": "Delete a personal geofence by ID.",
        "parameters": {
            "fence_id": "ID of the geofence to delete"
        }
    },
    {
        "name": "track_entity",
        "description": "Lock camera onto a selected public aircraft, vessel, or satellite (surveillance of unauthorized individuals is strictly rejected).",
        "parameters": {
            "entity_id": "Unique entity identifier or callsign",
            "layer_id": "Layer name: 'flights', 'vessels', 'satellites'",
            "name": "Optional display name"
        }
    },
    {
        "name": "untrack_entity",
        "description": "Disengage object tracking and return camera to free orbit.",
        "parameters": {}
    },
    {
        "name": "enable_layer",
        "description": "Turn on a geospatial data layer on the globe.",
        "parameters": {
            "layer_id": "'flights', 'vessels', 'satellites', 'weather', 'firms', 'earthquakes', 'cctv', 'radio', 'traffic'"
        }
    },
    {
        "name": "disable_layer",
        "description": "Turn off a geospatial data layer on the globe.",
        "parameters": {
            "layer_id": "Layer name to disable"
        }
    },
    {
        "name": "switch_visual_mode",
        "description": "Switch the 3D world visual sensor mode.",
        "parameters": {
            "style": "'normal', 'thermal' (FLIR), 'surveillance' (NVG), 'retro' (CRT), 'noir'"
        }
    },
    {
        "name": "enter_cockpit",
        "description": "Enter first-person cockpit camera mode for the currently tracked entity.",
        "parameters": {}
    },
    {
        "name": "exit_cockpit",
        "description": "Exit cockpit mode and restore standard orbital view.",
        "parameters": {}
    },
    {
        "name": "measure_distance",
        "description": "Calculate exact geodesic distance and compass bearing between two locations.",
        "parameters": {
            "from_location": "Origin location name",
            "to_location": "Destination location name"
        }
    },
    {
        "name": "get_spatial_context",
        "description": "Get current geographic coordinates, active layers, and tracked targets.",
        "parameters": {}
    },
    {
        "name": "get_spatial_health",
        "description": "Check spatial subsystem health, provider status, and rendering diagnostics.",
        "parameters": {}
    }
]
