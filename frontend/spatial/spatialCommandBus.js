/**
 * J.A.R.V.I.S. Spatial Command Bus (frontend/spatial/spatialCommandBus.js)
 * =======================================================================
 * Centralized, verifiable command bus executing spatial operations.
 * Guaranteed return contract:
 * {
 *   ok: boolean,
 *   executed: boolean,
 *   simulated: false,
 *   commandId: string,
 *   type: string,
 *   result: object|null,
 *   error: string|null,
 *   diagnostics: { elapsedMs: number }
 * }
 */

import { spatialEventBus } from "./spatialEventBus.js";
import { spatialState } from "./spatialState.js";
import { godsEyeAdapter, REGISTERED_LAYERS, SUPPORTED_VISUAL_STYLES } from "./godsEyeAdapter.js";

class SpatialCommandBus {
  constructor() {
    this.commandCount = 0;
  }

  async dispatch(command) {
    const start = performance.now();
    this.commandCount++;
    const commandId = command.commandId || `cmd_${Date.now()}_${this.commandCount}`;
    const type = String(command.type || command.action || "").toUpperCase().trim();
    const params = command.params || command.target || {};

    if (!type) {
      const elapsed = Math.round(performance.now() - start);
      const errPayload = {
        ok: false,
        executed: false,
        simulated: false,
        commandId,
        type: "UNKNOWN",
        result: null,
        error: "Command type or action is missing.",
        diagnostics: { elapsedMs: elapsed }
      };
      spatialEventBus.emit("spatial.command.failed", errPayload);
      return errPayload;
    }

    spatialEventBus.emit("spatial.command.started", { commandId, type, params });

    try {
      let result = null;

      // -------------------------------------------------------------
      // 1. NAVIGATION & CAMERA COMMANDS
      // -------------------------------------------------------------
      if (type === "NAVIGATE" || type === "FLY_TO_LOCATION") {
        const lat = Number(params.latitude);
        const lon = Number(params.longitude);
        const rangeM = Number.isFinite(params.rangeM) ? Number(params.rangeM) : (Number.isFinite(params.altitude) ? Number(params.altitude) : 15000);

        if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
          throw new Error(`Invalid latitude value: ${params.latitude}. Must be between -90 and 90.`);
        }
        if (!Number.isFinite(lon) || lon < -180 || lon > 180) {
          throw new Error(`Invalid longitude value: ${params.longitude}. Must be between -180 and 180.`);
        }
        if (!Number.isFinite(rangeM) || rangeM < 0) {
          throw new Error(`Invalid altitude/range value: ${rangeM}. Must be non-negative.`);
        }

        result = await godsEyeAdapter.executeNativeAction("fly_to_location", {
          latitude: lat,
          longitude: lon,
          rangeM,
          viewMode: params.viewMode || "overview",
          query: params.name || params.query
        });

        if (result?.ok) {
          spatialState.setCamera({
            latitude: lat,
            longitude: lon,
            height: rangeM,
            locationName: params.name || params.query || "Target"
          });
        }
      }

      else if (type === "HOME_GLOBE" || type === "ZOOM_TO_GLOBE" || type === "RESET_VIEW") {
        result = await godsEyeAdapter.executeNativeAction("zoom_to_globe", {});
        if (result?.ok) {
          spatialState.setCamera({
            latitude: 20.0,
            longitude: 0.0,
            height: 20000000.0,
            locationName: "World Overview"
          });
        }
      }

      else if (type === "ZOOM_IN") {
        result = await godsEyeAdapter.executeNativeAction("adjust_camera_zoom", { direction: "in" });
      }

      else if (type === "ZOOM_OUT") {
        result = await godsEyeAdapter.executeNativeAction("adjust_camera_zoom", { direction: "out" });
      }

      // -------------------------------------------------------------
      // 2. ENTITY TRACKING COMMANDS
      // -------------------------------------------------------------
      else if (type === "TRACK_ENTITY") {
        const entityId = String(params.entityId || "").trim();
        if (!entityId) {
          throw new Error("Parameter 'entityId' is required for entity tracking.");
        }

        result = await godsEyeAdapter.executeNativeAction("track_entity", {
          entityId,
          layerId: params.layerId || "flights"
        });

        if (result?.ok) {
          spatialState.setTracking(entityId, params.layerId || "flights", params.name || entityId);
        }
      }

      else if (type === "UNTRACK_ENTITY" || type === "STOP_TRACKING") {
        result = await godsEyeAdapter.executeNativeAction("stop_tracking", {});
        if (result?.ok) {
          spatialState.setTracking(null, null);
        }
      }

      // -------------------------------------------------------------
      // 3. LAYER VISIBILITY COMMANDS
      // -------------------------------------------------------------
      else if (type === "ENABLE_LAYER" || type === "DISABLE_LAYER") {
        const layerId = String(params.layerId || "").toLowerCase().trim();
        const visible = type === "ENABLE_LAYER";

        if (!REGISTERED_LAYERS.has(layerId)) {
          throw new Error(`Unrecognized layer ID '${layerId}'. Registered layers: ${Array.from(REGISTERED_LAYERS).join(", ")}`);
        }

        result = await godsEyeAdapter.executeNativeAction("set_layer_visibility", {
          layerId,
          visible
        });

        if (result?.ok) {
          spatialState.setLayerVisibility(layerId, visible);
        }
      }

      else if (type === "TOGGLE_LAYER") {
        const layerId = String(params.layerId || "").toLowerCase().trim();
        if (!REGISTERED_LAYERS.has(layerId)) {
          throw new Error(`Unrecognized layer ID '${layerId}'. Registered layers: ${Array.from(REGISTERED_LAYERS).join(", ")}`);
        }

        const currentState = Boolean(spatialState.getState().layers[layerId]);
        const nextState = !currentState;

        result = await godsEyeAdapter.executeNativeAction("set_layer_visibility", {
          layerId,
          visible: nextState
        });

        if (result?.ok) {
          spatialState.setLayerVisibility(layerId, nextState);
        }
      }

      // -------------------------------------------------------------
      // 4. SENSOR VISUAL STYLES
      // -------------------------------------------------------------
      else if (type === "SET_VISUAL_STYLE") {
        const style = String(params.style || "normal").toLowerCase().trim();
        if (!SUPPORTED_VISUAL_STYLES.has(style)) {
          throw new Error(`Unsupported visual style '${style}'. Supported: ${Array.from(SUPPORTED_VISUAL_STYLES).join(", ")}`);
        }

        result = await godsEyeAdapter.executeNativeAction("set_visual_style", { style });

        if (result?.ok) {
          spatialState.setVisualStyle(style);
        }
      }

      // -------------------------------------------------------------
      // 5. COCKPIT MODE
      // -------------------------------------------------------------
      else if (type === "ENTER_COCKPIT") {
        result = await godsEyeAdapter.executeNativeAction("control_cockpit", { mode: "enter" });
        if (result?.ok) {
          spatialState.setCockpit(true);
        }
      }

      else if (type === "EXIT_COCKPIT") {
        result = await godsEyeAdapter.executeNativeAction("control_cockpit", { mode: "exit" });
        if (result?.ok) {
          spatialState.setCockpit(false);
        }
      }

      // -------------------------------------------------------------
      // 6. ANNOTATIONS
      // -------------------------------------------------------------
      else if (type === "CLEAR_ANNOTATIONS") {
        result = await godsEyeAdapter.executeNativeAction("clear_annotations", {});
        if (result?.ok) {
          spatialState.clearAnnotations();
        }
      }

      else if (type === "ADD_MARKER" || type === "ANNOTATE_MAP") {
        const lat = Number(params.latitude);
        const lon = Number(params.longitude);

        if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
          throw new Error(`Invalid latitude for marker: ${params.latitude}`);
        }
        if (!Number.isFinite(lon) || lon < -180 || lon > 180) {
          throw new Error(`Invalid longitude for marker: ${params.longitude}`);
        }

        result = await godsEyeAdapter.executeNativeAction("annotate_map", params);
        if (result?.ok) {
          spatialState.addAnnotation(result.annotation || params);
        }
      }

      // -------------------------------------------------------------
      // 7. MAP SOURCE
      // -------------------------------------------------------------
      else if (type === "SET_MAP_SOURCE") {
        const sourceId = params.sourceId || params.stackId;
        result = await godsEyeAdapter.executeNativeAction("set_map_stack", { stackId: sourceId });
        if (result?.ok) {
          spatialState.setMapSource(sourceId);
        }
      }

      // -------------------------------------------------------------
      // 8. UNKNOWN / FALLBACK DIRECT DISPATCH
      // -------------------------------------------------------------
      else {
        result = await godsEyeAdapter.executeNativeAction(type.toLowerCase(), params);
      }

      const elapsed = Math.round(performance.now() - start);
      const isOk = Boolean(result && result.ok !== false);

      const responsePayload = {
        ok: isOk,
        executed: isOk,
        simulated: false,
        commandId,
        type,
        result: isOk ? result : null,
        error: isOk ? null : (result?.error || "Execution failed"),
        diagnostics: { elapsedMs: elapsed }
      };

      if (isOk) {
        spatialEventBus.emit("spatial.command.completed", responsePayload);
      } else {
        spatialEventBus.emit("spatial.command.failed", responsePayload);
      }

      return responsePayload;

    } catch (err) {
      const elapsed = Math.round(performance.now() - start);
      const errorPayload = {
        ok: false,
        executed: false,
        simulated: false,
        commandId,
        type,
        result: null,
        error: String(err.message || err),
        diagnostics: { elapsedMs: elapsed }
      };

      spatialEventBus.emit("spatial.command.failed", errorPayload);
      console.error(`[SpatialCommandBus] Command ${type} (${commandId}) validation/execution failure:`, err);
      return errorPayload;
    }
  }
}

export const spatialCommandBus = new SpatialCommandBus();
if (typeof window !== "undefined") {
  window.__jarvisSpatialCommandBus = spatialCommandBus;
}
