/**
 * J.A.R.V.I.S. God's Eye View Adapter (frontend/spatial/godsEyeAdapter.js)
 * ======================================================================
 * Translates Jarvis-level spatial commands into native GEV / Cesium APIs.
 * Isolates Cesium internals so that Jarvis agents interact only with stable schemas.
 */

import { spatialEventBus } from "./spatialEventBus.js";
import { spatialState } from "./spatialState.js";
import { spatialPerformanceGovernor } from "./spatialPerformanceGovernor.js";

class GodsEyeAdapter {
  constructor() {
    this.viewer = null;
    this.actionRunner = null;
    this.isInitialized = false;
    this.cameraListener = null;
  }

  attachViewer(viewer, actionRunner = null) {
    if (!viewer) return;
    this.viewer = viewer;
    this.actionRunner = actionRunner;
    this.isInitialized = true;

    this._setupCameraListeners();
    this._setupEntitySelection();

    spatialEventBus.emit("spatial.ready", {
      hasViewer: true,
      hasActionRunner: Boolean(actionRunner)
    });
    console.log("[GodsEyeAdapter] Cesium Viewer successfully linked to Jarvis Spatial Gateway.");
  }

  _setupCameraListeners() {
    if (!this.viewer?.camera) return;

    // Listen to camera move end to update state without per-frame overhead
    this.cameraListener = () => {
      try {
        const camera = this.viewer.camera;
        const cartographic = camera.positionCartographic;
        if (cartographic && window.Cesium) {
          const lat = window.Cesium.Math.toDegrees(cartographic.latitude);
          const lon = window.Cesium.Math.toDegrees(cartographic.longitude);
          const height = cartographic.height;
          const heading = window.Cesium.Math.toDegrees(camera.heading);
          const pitch = window.Cesium.Math.toDegrees(camera.pitch);

          spatialState.setCamera({
            latitude: parseFloat(lat.toFixed(4)),
            longitude: parseFloat(lon.toFixed(4)),
            height: Math.round(height),
            heading: Math.round(heading),
            pitch: Math.round(pitch)
          });
        }
      } catch (err) {}
    };

    this.viewer.camera.moveEnd.addEventListener(this.cameraListener);
  }

  _setupEntitySelection() {
    // Listen for GEV native custom events
    window.addEventListener("gev:entity-selected", (e) => {
      const detail = e.detail;
      if (detail) {
        spatialState.setSelection(
          detail.id || detail.callsign || "unknown",
          detail.layerId || "entity",
          detail.provider || "public_feed",
          detail
        );
      }
    });

    window.addEventListener("gev:awareness-subject-selected", (e) => {
      const detail = e.detail;
      if (detail) {
        spatialState.setTracking(
          detail.id || detail.callsign,
          detail.layerId || "flights",
          detail.callsign || detail.name,
          detail
        );
      }
    });
  }

  async executeNativeAction(actionName, args = {}) {
    if (this.actionRunner && typeof this.actionRunner === "function") {
      try {
        const res = await this.actionRunner(actionName, args);
        return res;
      } catch (err) {
        console.warn(`[GodsEyeAdapter] Action '${actionName}' failed in runner:`, err);
      }
    }

    // Direct fallback execution if action runner is absent or pending
    return this._fallbackDirectExecution(actionName, args);
  }

  _fallbackDirectExecution(actionName, args = {}) {
    if (!this.viewer) {
      return { ok: false, error: "Cesium Viewer not yet attached" };
    }

    const Cesium = window.Cesium;
    if (!Cesium) {
      return { ok: false, error: "Cesium global library not loaded" };
    }

    try {
      if (actionName === "fly_to_location") {
        const lat = args.latitude || 20.0;
        const lon = args.longitude || 0.0;
        const range = args.rangeM || 15000.0;

        this.viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(lon, lat, range),
          duration: 2.0
        });
        return { ok: true, action: actionName, destination: { lat, lon, range } };
      }

      if (actionName === "zoom_to_globe") {
        this.viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(0.0, 20.0, 20000000.0),
          duration: 2.5
        });
        return { ok: true, action: actionName };
      }

      if (actionName === "adjust_camera_zoom") {
        const zoomOut = args.direction === "out";
        const factor = zoomOut ? 1.5 : 0.65;
        this.viewer.camera.zoomIn(this.viewer.camera.positionCartographic.height * (1 - factor));
        return { ok: true, action: actionName, zoomOut };
      }

      return { ok: true, action: actionName, simulated: true };
    } catch (err) {
      return { ok: false, error: String(err) };
    }
  }

  destroy() {
    if (this.viewer && this.cameraListener) {
      try {
        this.viewer.camera.moveEnd.removeEventListener(this.cameraListener);
      } catch (e) {}
    }
    this.viewer = null;
    this.actionRunner = null;
    this.isInitialized = false;
    spatialEventBus.emit("spatial.destroyed");
  }
}

export const godsEyeAdapter = new GodsEyeAdapter();
if (typeof window !== "undefined") {
  window.__jarvisGodsEyeAdapter = godsEyeAdapter;
}
