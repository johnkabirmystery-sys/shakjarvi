/**
 * J.A.R.V.I.S. Spatial Command Bus (frontend/spatial/spatialCommandBus.js)
 * =======================================================================
 * Centralized, verifiable command bus executing spatial operations with strict
 * validation, zero-value preservation, typed lifecycle results, and event emissions.
 *
 * Supported Commands:
 * - fly_to_location / fly_to_coordinates / navigate
 * - zoom_in / zoom_out
 * - set_scene_mode (3D, 2D, Columbus View)
 * - orbit_target / stop_orbit
 * - reset_camera / home_globe
 * - look_at_entity / follow_entity / stop_following
 * - set_camera_orientation
 * - toggle_layer / enable_layer / disable_layer
 * - set_terrain
 * - toggle_buildings / load_tileset / unload_tileset
 * - query_entities
 * - set_visual_style
 * - enter_cockpit / exit_cockpit
 * - add_marker / annotate_map / clear_annotations
 * - center_on_self
 */

import { spatialEventBus } from "./spatialEventBus.js";
import { spatialState } from "./spatialState.js";
import { godsEyeAdapter, REGISTERED_LAYERS, SUPPORTED_VISUAL_STYLES } from "./godsEyeAdapter.js";
import { validateCoordinates, validateHeight } from "./runtime/cameraController.js";
import { spatialLayerRegistry } from "./core/spatialLayerRegistry.js";
import { SpatialAnalytics } from "./analytics/spatialAnalytics.js";

export const COMMAND_STATUS = {
  ACCEPTED: "accepted",
  RUNNING: "running",
  COMPLETED: "completed",
  REJECTED: "rejected",
  FAILED: "failed",
  CANCELLED: "cancelled"
};

class SpatialCommandBus {
  constructor() {
    this.commandCount = 0;
  }

  async dispatch(command = {}) {
    const startedAt = new Date().toISOString();
    const startMs = performance.now();
    this.commandCount++;

    const commandId = command.commandId || `cmd_${Date.now()}_${this.commandCount}`;
    const rawType = command.type || command.action || "";
    const type = String(rawType).toUpperCase().trim();
    const params = command.params || command.target || command.payload || {};

    if (!type) {
      const errorResult = {
        ok: false,
        commandId,
        type: "UNKNOWN",
        status: COMMAND_STATUS.REJECTED,
        error: {
          code: "MISSING_COMMAND_TYPE",
          message: "Command 'type' or 'action' property is required."
        },
        data: null,
        startedAt,
        completedAt: new Date().toISOString()
      };
      spatialEventBus.emit("spatial.command.rejected", errorResult);
      spatialEventBus.emit("spatial.command.failed", errorResult);
      return errorResult;
    }

    spatialEventBus.emit("spatial.command.accepted", { commandId, type, params, startedAt });
    spatialEventBus.emit("spatial.command.started", { commandId, type, params });

    try {
      let data = null;

      // -------------------------------------------------------------
      // 1. NAVIGATION & CAMERA FLIGHT
      // -------------------------------------------------------------
      if (type === "FLY_TO_COORDINATES" || type === "FLY_TO_LOCATION" || type === "NAVIGATE") {
        const lat = Number(params.latitude);
        const lon = Number(params.longitude);
        const height = Number.isFinite(params.height)
          ? Number(params.height)
          : (Number.isFinite(params.altitude) ? Number(params.altitude) : (Number.isFinite(params.rangeM) ? Number(params.rangeM) : 15000.0));
        const duration = Number.isFinite(params.duration) ? Number(params.duration) : 2.0;

        if (!validateCoordinates(lat, lon)) {
          throw {
            code: "INVALID_COORDINATES",
            message: `Invalid coordinates: latitude=${params.latitude}, longitude=${params.longitude}. Latitude must be [-90, 90], Longitude [-180, 180].`
          };
        }

        if (!validateHeight(height)) {
          throw {
            code: "INVALID_HEIGHT",
            message: `Invalid height/altitude: ${height}. Must be a finite non-negative number <= 50,000,000m.`
          };
        }

        // Delegate to spatialService cameraController if attached, or fallback to godsEyeAdapter
        if (window.spatialService?.cameraController?.viewer) {
          const flightRes = await window.spatialService.cameraController.flyToCoordinates({
            latitude: lat,
            longitude: lon,
            height,
            heading: params.heading,
            pitch: params.pitch,
            roll: params.roll,
            duration
          });
          if (!flightRes.ok) throw { code: "FLIGHT_FAILED", message: flightRes.error || "Camera flight aborted." };
          data = {
            latitude: lat,
            longitude: lon,
            height,
            name: params.name || params.query,
            ...flightRes
          };
        } else {
          const adapterRes = await godsEyeAdapter.executeNativeAction("fly_to_location", {
            latitude: lat,
            longitude: lon,
            rangeM: height,
            name: params.name || params.query
          });
          if (!adapterRes.ok) throw { code: "ADAPTER_FAILED", message: adapterRes.error };
          data = adapterRes;
        }

        spatialState.setCamera({
          latitude: lat,
          longitude: lon,
          height,
          locationName: params.name || params.query || "Target"
        });
      }

      // -------------------------------------------------------------
      // 2. ZOOM & GLOBE RESET
      // -------------------------------------------------------------
      else if (type === "RESET_CAMERA" || type === "HOME_GLOBE" || type === "ZOOM_TO_GLOBE" || type === "RESET_VIEW") {
        if (window.spatialService?.cameraController?.viewer) {
          data = await window.spatialService.cameraController.resetCamera();
        } else {
          data = await godsEyeAdapter.executeNativeAction("zoom_to_globe", {});
        }
        spatialState.setCamera({
          latitude: 20.0,
          longitude: 0.0,
          height: 20000000.0,
          locationName: "World Overview"
        });
      }

      else if (type === "ZOOM_IN") {
        if (window.spatialService?.cameraController?.viewer) {
          data = window.spatialService.cameraController.zoom("in", params.amount);
        } else {
          data = await godsEyeAdapter.executeNativeAction("adjust_camera_zoom", { direction: "in" });
        }
      }

      else if (type === "ZOOM_OUT") {
        if (window.spatialService?.cameraController?.viewer) {
          data = window.spatialService.cameraController.zoom("out", params.amount);
        } else {
          data = await godsEyeAdapter.executeNativeAction("adjust_camera_zoom", { direction: "out" });
        }
      }

      // -------------------------------------------------------------
      // 3. SCENE MODE (3D, 2D, COLUMBUS VIEW)
      // -------------------------------------------------------------
      else if (type === "SET_SCENE_MODE") {
        const mode = params.mode || params.sceneMode || "3D";
        if (window.spatialService?.sceneModeController?.viewer) {
          const modeRes = await window.spatialService.sceneModeController.setSceneMode(mode, params.duration);
          if (!modeRes.ok) throw { code: "SCENE_MODE_ERROR", message: modeRes.error };
          data = modeRes;
        } else {
          throw { code: "NOT_INITIALIZED", message: "SceneModeController is not ready." };
        }
      }

      // -------------------------------------------------------------
      // 4. CAMERA ORIENTATION & ORBIT
      // -------------------------------------------------------------
      else if (type === "SET_CAMERA_ORIENTATION") {
        if (window.spatialService?.cameraController?.viewer) {
          data = window.spatialService.cameraController.setOrientation({
            heading: params.heading,
            pitch: params.pitch,
            roll: params.roll
          });
        } else {
          throw { code: "NOT_INITIALIZED", message: "CameraController is not ready." };
        }
      }

      else if (type === "ORBIT_TARGET") {
        if (window.spatialService?.cameraController?.viewer) {
          data = window.spatialService.cameraController.startOrbit(params.targetCartesian, params.speedDegPerSec);
        } else {
          throw { code: "NOT_INITIALIZED", message: "CameraController is not ready." };
        }
      }

      else if (type === "STOP_ORBIT") {
        if (window.spatialService?.cameraController?.viewer) {
          data = window.spatialService.cameraController.stopOrbit();
        } else {
          data = { ok: true, status: "orbit_stopped" };
        }
      }

      // -------------------------------------------------------------
      // 5. ENTITY TRACKING & FOLLOWING
      // -------------------------------------------------------------
      else if (type === "TRACK_ENTITY" || type === "FOLLOW_ENTITY") {
        const entityId = String(params.entityId || "").trim();
        if (!entityId) {
          throw { code: "MISSING_PARAMETER", message: "Parameter 'entityId' is required for tracking." };
        }

        const res = await godsEyeAdapter.executeNativeAction("track_entity", {
          entityId,
          layerId: params.layerId || "flights"
        });
        if (!res.ok) throw { code: "TRACKING_FAILED", message: res.error };
        data = res;
        spatialState.setTracking(entityId, params.layerId || "flights", params.name || entityId);
      }

      else if (type === "UNTRACK_ENTITY" || type === "STOP_TRACKING" || type === "STOP_FOLLOWING") {
        const res = await godsEyeAdapter.executeNativeAction("stop_tracking", {});
        data = res;
        spatialState.setTracking(null, null);
      }

      // -------------------------------------------------------------
      // 6. LAYER MANAGEMENT
      // -------------------------------------------------------------
      else if (type === "ENABLE_LAYER" || type === "DISABLE_LAYER") {
        const layerId = String(params.layerId || "").toLowerCase().trim();
        const visible = type === "ENABLE_LAYER";

        if (spatialLayerRegistry.has(layerId)) {
          const regRes = visible ? spatialLayerRegistry.enable(layerId) : spatialLayerRegistry.disable(layerId);
          if (!regRes.ok) throw { code: "LAYER_ERROR", message: regRes.error };
        }

        const res = await godsEyeAdapter.executeNativeAction("set_layer_visibility", {
          layerId,
          visible
        });
        if (!res.ok) throw { code: "LAYER_FAILED", message: res.error };
        data = res;
        spatialState.setLayerVisibility(layerId, visible);
      }

      else if (type === "TOGGLE_LAYER") {
        const layerId = String(params.layerId || "").toLowerCase().trim();
        const currentState = Boolean(spatialState.getState().layers[layerId]);
        const nextState = !currentState;

        if (spatialLayerRegistry.has(layerId)) {
          nextState ? spatialLayerRegistry.enable(layerId) : spatialLayerRegistry.disable(layerId);
        }

        const res = await godsEyeAdapter.executeNativeAction("set_layer_visibility", {
          layerId,
          visible: nextState
        });
        if (!res.ok) throw { code: "LAYER_FAILED", message: res.error };
        data = res;
        spatialState.setLayerVisibility(layerId, nextState);
      }

      // -------------------------------------------------------------
      // 7. TERRAIN & 3D TILES
      // -------------------------------------------------------------
      else if (type === "SET_TERRAIN") {
        const providerName = params.provider || "ellipsoid";
        if (window.spatialService?.terrainManager) {
          const tRes = await window.spatialService.terrainManager.setTerrain(providerName, params);
          data = tRes;
        } else {
          throw { code: "NOT_INITIALIZED", message: "TerrainManager is not available." };
        }
      }

      else if (type === "TOGGLE_BUILDINGS") {
        if (window.spatialService?.buildingLayer) {
          const res = await window.spatialService.buildingLayer.toggle();
          if (!res.ok) throw { code: "BUILDINGS_FAILED", message: res.error || "3D Buildings unavailable without valid token" };
          data = { visible: window.spatialService.buildingLayer.isEnabled, ...res };
        } else {
          throw { code: "NOT_INITIALIZED", message: "BuildingLayer is not available." };
        }
      }

      else if (type === "LOAD_TILESET") {
        const tilesetId = params.id || `tileset_${Date.now()}`;
        if (window.spatialService?.tilesetManager && typeof params.factory === "function") {
          const res = await window.spatialService.tilesetManager.load(tilesetId, params.factory, params);
          if (!res.ok) throw { code: "TILESET_FAILED", message: res.error };
          data = res;
        } else {
          throw { code: "INVALID_REQUEST", message: "TilesetManager or factory function unavailable." };
        }
      }

      else if (type === "UNLOAD_TILESET") {
        if (window.spatialService?.tilesetManager && params.id) {
          data = window.spatialService.tilesetManager.remove(params.id);
        } else {
          throw { code: "INVALID_REQUEST", message: "Tileset ID required to unload." };
        }
      }

      // -------------------------------------------------------------
      // 8. SPATIAL ANALYTICS & QUERIES
      // -------------------------------------------------------------
      else if (type === "QUERY_ENTITIES") {
        const entities = params.entities || [];
        if (params.geometry?.type === "Circle") {
          data = SpatialAnalytics.queryWithinRadius(
            entities,
            params.geometry.center.latitude,
            params.geometry.center.longitude,
            params.geometry.radiusMeters
          );
        } else if (params.geometry?.type === "BoundingBox") {
          data = SpatialAnalytics.queryWithinBoundingBox(
            entities,
            params.geometry.minLat,
            params.geometry.minLon,
            params.geometry.maxLat,
            params.geometry.maxLon
          );
        } else {
          data = {
            ok: true,
            results: entities,
            count: entities.length,
            queryId: `query_${Date.now()}`,
            generatedAt: new Date().toISOString(),
            dataStatus: "complete"
          };
        }
      }

      // -------------------------------------------------------------
      // 9. SENSOR MODES & VISUAL STYLES
      // -------------------------------------------------------------
      else if (type === "SET_VISUAL_STYLE") {
        const style = String(params.style || "normal").toLowerCase().trim();
        const res = await godsEyeAdapter.executeNativeAction("set_visual_style", { style });
        if (!res.ok) throw { code: "STYLE_FAILED", message: res.error };
        data = res;
        spatialState.setVisualStyle(style);
      }

      else if (type === "ENTER_COCKPIT") {
        const res = await godsEyeAdapter.executeNativeAction("control_cockpit", { mode: "enter" });
        if (!res.ok) throw { code: "COCKPIT_FAILED", message: res.error };
        data = res;
        spatialState.setCockpit(true);
      }

      else if (type === "EXIT_COCKPIT") {
        const res = await godsEyeAdapter.executeNativeAction("control_cockpit", { mode: "exit" });
        if (!res.ok) throw { code: "COCKPIT_FAILED", message: res.error };
        data = res;
        spatialState.setCockpit(false);
      }

      // -------------------------------------------------------------
      // 10. ANNOTATIONS & MARKERS
      // -------------------------------------------------------------
      else if (type === "ADD_MARKER" || type === "ANNOTATE_MAP") {
        const lat = Number(params.latitude);
        const lon = Number(params.longitude);

        if (!validateCoordinates(lat, lon)) {
          throw { code: "INVALID_COORDINATES", message: `Invalid marker coordinates (${params.latitude}, ${params.longitude})` };
        }

        const res = await godsEyeAdapter.executeNativeAction("annotate_map", params);
        if (!res.ok) throw { code: "ANNOTATION_FAILED", message: res.error };
        data = res;
        spatialState.addAnnotation(res.annotation || params);
      }

      else if (type === "CLEAR_ANNOTATIONS") {
        const res = await godsEyeAdapter.executeNativeAction("clear_annotations", {});
        data = res;
        spatialState.clearAnnotations();
      }

      else if (type === "CENTER_ON_SELF") {
        const res = await godsEyeAdapter.executeNativeAction("center_on_self", {});
        if (!res.ok) throw { code: "SELF_LOCATION_FAILED", message: res.error };
        data = res;
      }

      // Fallback direct dispatch
      else {
        data = await godsEyeAdapter.executeNativeAction(type.toLowerCase(), params);
      }

      const completedAt = new Date().toISOString();
      const elapsedMs = Math.round(performance.now() - startMs);

      const commandResult = {
        ok: true,
        commandId,
        type,
        status: COMMAND_STATUS.COMPLETED,
        data,
        startedAt,
        completedAt,
        diagnostics: { elapsedMs }
      };

      spatialEventBus.emit("spatial.command.completed", commandResult);
      return commandResult;

    } catch (err) {
      const completedAt = new Date().toISOString();
      const elapsedMs = Math.round(performance.now() - startMs);

      const errorObj = typeof err === "object" && err !== null ? {
        code: err.code || "EXECUTION_ERROR",
        message: err.message || String(err),
        retryable: Boolean(err.retryable)
      } : {
        code: "EXECUTION_ERROR",
        message: String(err),
        retryable: false
      };

      const failureResult = {
        ok: false,
        commandId,
        type,
        status: COMMAND_STATUS.FAILED,
        error: errorObj,
        data: null,
        startedAt,
        completedAt,
        diagnostics: { elapsedMs }
      };

      spatialEventBus.emit("spatial.command.failed", failureResult);
      console.warn(`[SpatialCommandBus] Command ${type} (${commandId}) failed:`, errorObj.message);
      return failureResult;
    }
  }
}

export const spatialCommandBus = new SpatialCommandBus();
if (typeof window !== "undefined") {
  window.spatialCommandBus = spatialCommandBus;
}
