/**
 * J.A.R.V.I.S. Spatial Command Bus (frontend/spatial/spatialCommandBus.js)
 * =======================================================================
 * Centralized, verifiable command bus executing spatial operations.
 * Guaranteed return contract: { ok, commandId, state, result, error, diagnostics }
 */

import { spatialEventBus } from "./spatialEventBus.js";
import { spatialState } from "./spatialState.js";
import { godsEyeAdapter } from "./godsEyeAdapter.js";

class SpatialCommandBus {
  constructor() {
    this.commandCount = 0;
  }

  async dispatch(command) {
    const start = performance.now();
    this.commandCount++;
    const commandId = command.commandId || `cmd_${Date.now()}_${this.commandCount}`;
    const type = (command.type || command.action || "").toUpperCase();
    const params = command.params || command.target || {};

    spatialEventBus.emit("spatial.command.started", { commandId, type, params });

    try {
      let result = null;

      switch (type) {
        case "NAVIGATE":
        case "FLY_TO_LOCATION":
          result = await godsEyeAdapter.executeNativeAction("fly_to_location", {
            latitude: params.latitude,
            longitude: params.longitude,
            rangeM: params.rangeM || params.altitude || 15000,
            viewMode: params.viewMode || "overview",
            query: params.name || params.query
          });
          spatialState.setCamera({
            latitude: params.latitude,
            longitude: params.longitude,
            locationName: params.name || "Target"
          });
          break;

        case "HOME_GLOBE":
        case "ZOOM_TO_GLOBE":
        case "RESET_VIEW":
          result = await godsEyeAdapter.executeNativeAction("zoom_to_globe", {});
          spatialState.setCamera({ locationName: "World Overview" });
          break;

        case "ZOOM_IN":
          result = await godsEyeAdapter.executeNativeAction("adjust_camera_zoom", { direction: "in" });
          break;

        case "ZOOM_OUT":
          result = await godsEyeAdapter.executeNativeAction("adjust_camera_zoom", { direction: "out" });
          break;

        case "TRACK_ENTITY":
          result = await godsEyeAdapter.executeNativeAction("track_entity", {
            entityId: params.entityId,
            layerId: params.layerId
          });
          spatialState.setTracking(params.entityId, params.layerId, params.name || params.entityId);
          break;

        case "UNTRACK_ENTITY":
        case "STOP_TRACKING":
          result = await godsEyeAdapter.executeNativeAction("stop_tracking", {});
          spatialState.setTracking(null, null);
          break;

        case "ENABLE_LAYER":
          result = await godsEyeAdapter.executeNativeAction("set_layer_visibility", {
            layerId: params.layerId,
            visible: true
          });
          spatialState.setLayerVisibility(params.layerId, true);
          break;

        case "DISABLE_LAYER":
          result = await godsEyeAdapter.executeNativeAction("set_layer_visibility", {
            layerId: params.layerId,
            visible: false
          });
          spatialState.setLayerVisibility(params.layerId, false);
          break;

        case "TOGGLE_LAYER": {
          const currentState = spatialState.getState().layers[params.layerId];
          const nextState = !currentState;
          result = await godsEyeAdapter.executeNativeAction("set_layer_visibility", {
            layerId: params.layerId,
            visible: nextState
          });
          spatialState.setLayerVisibility(params.layerId, nextState);
          break;
        }

        case "SET_VISUAL_STYLE":
          result = await godsEyeAdapter.executeNativeAction("set_visual_style", {
            style: params.style
          });
          spatialState.setVisualStyle(params.style);
          break;

        case "ENTER_COCKPIT":
          result = await godsEyeAdapter.executeNativeAction("control_cockpit", { mode: "enter" });
          spatialState.setCockpit(true);
          break;

        case "EXIT_COCKPIT":
          result = await godsEyeAdapter.executeNativeAction("control_cockpit", { mode: "exit" });
          spatialState.setCockpit(false);
          break;

        case "CLEAR_ANNOTATIONS":
          result = await godsEyeAdapter.executeNativeAction("clear_annotations", {});
          spatialState.clearAnnotations();
          break;

        case "ADD_MARKER":
        case "ANNOTATE_MAP":
          result = await godsEyeAdapter.executeNativeAction("annotate_map", params);
          spatialState.addAnnotation(params);
          break;

        case "SET_MAP_SOURCE":
          result = await godsEyeAdapter.executeNativeAction("set_map_stack", {
            stackId: params.sourceId || params.stackId
          });
          spatialState.setMapSource(params.sourceId || params.stackId);
          break;

        default:
          result = await godsEyeAdapter.executeNativeAction(type.toLowerCase(), params);
          break;
      }

      const elapsed = Math.round(performance.now() - start);
      const responsePayload = {
        ok: result ? (result.ok !== false) : true,
        commandId,
        type,
        state: spatialState.getState(),
        result,
        error: result?.error || null,
        diagnostics: { elapsedMs: elapsed }
      };

      spatialEventBus.emit("spatial.command.completed", responsePayload);
      return responsePayload;

    } catch (err) {
      const elapsed = Math.round(performance.now() - start);
      const errorPayload = {
        ok: false,
        commandId,
        type,
        state: spatialState.getState(),
        result: null,
        error: String(err.message || err),
        diagnostics: { elapsedMs: elapsed }
      };

      spatialEventBus.emit("spatial.command.failed", errorPayload);
      console.error(`[SpatialCommandBus] Command ${type} (${commandId}) failed:`, err);
      return errorPayload;
    }
  }
}

export const spatialCommandBus = new SpatialCommandBus();
if (typeof window !== "undefined") {
  window.__jarvisSpatialCommandBus = spatialCommandBus;
}
