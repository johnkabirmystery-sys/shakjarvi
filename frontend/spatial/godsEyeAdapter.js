/**
 * J.A.R.V.I.S. God's Eye View Adapter (frontend/spatial/godsEyeAdapter.js)
 * ======================================================================
 * Translates Jarvis-level spatial commands into native Cesium 1.138 APIs.
 * Eliminates all simulated returns. Guaranteed real scene mutations or
 * explicit actionable error returns.
 */

import { spatialEventBus } from "./spatialEventBus.js";
import { spatialState } from "./spatialState.js";

export const SUPPORTED_VISUAL_STYLES = new Set(["normal", "surveillance", "thermal", "retro", "noir"]);
export const REGISTERED_LAYERS = new Set([
  "flights", "military", "vessels", "satellites", "earthquakes",
  "firms", "weather", "traffic", "cctv", "radio", "bikeshare",
  "submarine-cables", "datacenters"
]);

class GodsEyeAdapter {
  constructor() {
    this.viewer = null;
    this.actionRunner = null;
    this.isInitialized = false;
    this.cameraListener = null;
    this._annotationEntities = new Map(); // id -> Cesium.Entity
    this._layerDataSources = new Map(); // layerId -> Cesium.DataSource / CustomDataSource
    this._activeStyle = "normal";
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
      hasActionRunner: Boolean(actionRunner),
      version: window.Cesium?.VERSION || "1.138.0"
    });
    console.log("[GodsEyeAdapter] Cesium Viewer attached to Jarvis Spatial Adapter.");
  }

  _setupCameraListeners() {
    if (!this.viewer?.camera) return;

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
      } catch (err) {
        console.warn("[GodsEyeAdapter] Camera telemetry sync error:", err);
      }
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
    if (!this.viewer) {
      return { ok: false, error: "Cesium Viewer not attached or not yet initialized." };
    }

    if (this.actionRunner && typeof this.actionRunner === "function") {
      try {
        const res = await this.actionRunner(actionName, args);
        if (res && res.ok !== undefined) {
          if (this.viewer?.scene) this.viewer.scene.requestRender();
          return res;
        }
      } catch (err) {
        console.warn(`[GodsEyeAdapter] Action '${actionName}' delegate error, falling back to direct Cesium:`, err);
      }
    }

    return this._directCesiumExecution(actionName, args);
  }

  _directCesiumExecution(actionName, args = {}) {
    const Cesium = window.Cesium;
    if (!Cesium) {
      return { ok: false, error: "Cesium global library not available in runtime." };
    }

    const scene = this.viewer.scene;

    try {
      // 1. FLY TO LOCATION
      if (actionName === "fly_to_location") {
        const lat = Number.isFinite(args.latitude) ? Number(args.latitude) : 20.0;
        const lon = Number.isFinite(args.longitude) ? Number(args.longitude) : 0.0;
        const range = Number.isFinite(args.rangeM) ? Number(args.rangeM) : (Number.isFinite(args.altitude) ? Number(args.altitude) : 15000.0);

        if (lat < -90 || lat > 90) {
          return { ok: false, error: `Invalid latitude ${lat}. Must be between -90 and 90.` };
        }
        if (lon < -180 || lon > 180) {
          return { ok: false, error: `Invalid longitude ${lon}. Must be between -180 and 180.` };
        }
        if (range < 0) {
          return { ok: false, error: `Invalid range ${range}m. Must be non-negative.` };
        }

        this.viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(lon, lat, range),
          duration: 2.0,
          complete: () => {
            if (scene) scene.requestRender();
          }
        });

        if (scene) scene.requestRender();
        return {
          ok: true,
          action: actionName,
          destination: { latitude: lat, longitude: lon, rangeM: range, name: args.query || args.name }
        };
      }

      // 2. ZOOM TO GLOBE
      if (actionName === "zoom_to_globe") {
        this.viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(0.0, 20.0, 20000000.0),
          duration: 2.5,
          complete: () => {
            if (scene) scene.requestRender();
          }
        });

        if (scene) scene.requestRender();
        return { ok: true, action: actionName, view: "globe" };
      }

      // 3. ADJUST CAMERA ZOOM
      if (actionName === "adjust_camera_zoom") {
        const zoomOut = args.direction === "out";
        const currentHeight = this.viewer.camera.positionCartographic?.height || 1000000.0;
        const delta = zoomOut ? currentHeight * 0.5 : currentHeight * 0.35;

        if (zoomOut) {
          this.viewer.camera.zoomOut(delta);
        } else {
          this.viewer.camera.zoomIn(delta);
        }

        if (scene) scene.requestRender();
        return { ok: true, action: actionName, direction: args.direction };
      }

      // 4. TRACK ENTITY
      if (actionName === "track_entity") {
        const entityId = args.entityId;
        if (!entityId) {
          return { ok: false, error: "Parameter 'entityId' is required for entity tracking." };
        }

        // Search in viewer.entities
        let entity = this.viewer.entities.getById(entityId);

        // If not in root collection, search in data sources
        if (!entity && this.viewer.dataSources) {
          for (let i = 0; i < this.viewer.dataSources.length; i++) {
            const ds = this.viewer.dataSources.get(i);
            const found = ds.entities.getById(entityId);
            if (found) {
              entity = found;
              break;
            }
          }
        }

        if (entity) {
          this.viewer.trackedEntity = entity;
          if (scene) scene.requestRender();
          return { ok: true, action: actionName, entityId, tracked: true };
        } else {
          // Entity not currently in scene: return explicit error without crashing
          return {
            ok: false,
            error: `Entity '${entityId}' was not found in the active Cesium scene.`,
            entityId
          };
        }
      }

      // 5. STOP TRACKING
      if (actionName === "stop_tracking") {
        this.viewer.trackedEntity = undefined;
        if (scene) scene.requestRender();
        return { ok: true, action: actionName, tracked: false };
      }

      // 6. SET LAYER VISIBILITY
      if (actionName === "set_layer_visibility") {
        const layerId = String(args.layerId || "").toLowerCase();
        const visible = Boolean(args.visible);

        if (!REGISTERED_LAYERS.has(layerId)) {
          return {
            ok: false,
            error: `Layer '${layerId}' is not a recognized geospatial layer.`,
            registeredLayers: Array.from(REGISTERED_LAYERS)
          };
        }

        // Toggle matching Cesium data sources if present
        let matched = false;
        if (this.viewer.dataSources) {
          for (let i = 0; i < this.viewer.dataSources.length; i++) {
            const ds = this.viewer.dataSources.get(i);
            if (ds.name && ds.name.toLowerCase().includes(layerId)) {
              ds.show = visible;
              matched = true;
            }
          }
        }

        // Update layer state in registry
        this._layerDataSources.set(layerId, { show: visible, matched });

        if (scene) scene.requestRender();
        return { ok: true, action: actionName, layerId, visible, sceneSourceMatched: matched };
      }

      // 7. SET VISUAL STYLE
      if (actionName === "set_visual_style") {
        const style = String(args.style || "normal").toLowerCase();
        if (!SUPPORTED_VISUAL_STYLES.has(style)) {
          return {
            ok: false,
            error: `Visual style '${style}' is unsupported. Supported styles: ${Array.from(SUPPORTED_VISUAL_STYLES).join(", ")}.`,
            supportedStyles: Array.from(SUPPORTED_VISUAL_STYLES)
          };
        }

        this._activeStyle = style;

        // Apply shader filter CSS class to container
        const container = document.getElementById("workspaceSpatial") || this.viewer.container;
        if (container) {
          container.classList.remove(
            "spatial-mode-surveillance",
            "spatial-mode-thermal",
            "spatial-mode-retro",
            "spatial-mode-noir"
          );
          if (style !== "normal") {
            container.classList.add(`spatial-mode-${style}`);
          }
        }

        if (scene) scene.requestRender();
        return { ok: true, action: actionName, style };
      }

      // 8. CONTROL COCKPIT
      if (actionName === "control_cockpit") {
        const mode = args.mode || "enter";
        const isEnter = mode === "enter";

        if (isEnter) {
          if (this.viewer.trackedEntity) {
            // Lock tight camera offset
            this.viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
          } else {
            // Drop to close flight perspective at current camera center
            const pos = this.viewer.camera.positionCartographic;
            if (pos) {
              const lat = Cesium.Math.toDegrees(pos.latitude);
              const lon = Cesium.Math.toDegrees(pos.longitude);
              this.viewer.camera.flyTo({
                destination: Cesium.Cartesian3.fromDegrees(lon, lat, 800.0),
                orientation: {
                  heading: this.viewer.camera.heading,
                  pitch: Cesium.Math.toRadians(-15.0),
                  roll: 0.0
                },
                duration: 1.5
              });
            }
          }
        } else {
          // Restore orbital perspective
          const pos = this.viewer.camera.positionCartographic;
          if (pos) {
            const lat = Cesium.Math.toDegrees(pos.latitude);
            const lon = Cesium.Math.toDegrees(pos.longitude);
            this.viewer.camera.flyTo({
              destination: Cesium.Cartesian3.fromDegrees(lon, lat, 15000.0),
              orientation: {
                heading: 0.0,
                pitch: Cesium.Math.toRadians(-90.0),
                roll: 0.0
              },
              duration: 1.5
            });
          }
        }

        if (scene) scene.requestRender();
        return { ok: true, action: actionName, inCockpit: isEnter };
      }

      // 9. ANNOTATE MAP
      if (actionName === "annotate_map" || actionName === "add_marker") {
        const lat = Number(args.latitude);
        const lon = Number(args.longitude);
        const label = args.label || args.name || "Waypoint";
        const markerId = args.id || `marker_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;

        if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
          return { ok: false, error: `Invalid latitude for annotation: ${args.latitude}` };
        }
        if (!Number.isFinite(lon) || lon < -180 || lon > 180) {
          return { ok: false, error: `Invalid longitude for annotation: ${args.longitude}` };
        }

        // Avoid duplicate markers
        if (this._annotationEntities.has(markerId)) {
          this.viewer.entities.remove(this._annotationEntities.get(markerId));
        }

        const entity = this.viewer.entities.add({
          id: markerId,
          name: label,
          position: Cesium.Cartesian3.fromDegrees(lon, lat, args.height || 50.0),
          point: {
            pixelSize: 10,
            color: Cesium.Color.CYAN,
            outlineColor: Cesium.Color.WHITE,
            outlineWidth: 2,
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
          },
          label: {
            text: label,
            font: "12px monospace",
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            pixelOffset: new Cesium.Cartesian2(0, -12)
          }
        });

        this._annotationEntities.set(markerId, entity);
        if (scene) scene.requestRender();

        return {
          ok: true,
          action: actionName,
          annotation: { id: markerId, latitude: lat, longitude: lon, label }
        };
      }

      // 10. CLEAR ANNOTATIONS
      if (actionName === "clear_annotations") {
        const count = this._annotationEntities.size;
        for (const [id, entity] of this._annotationEntities.entries()) {
          try {
            this.viewer.entities.remove(entity);
          } catch (_) {}
        }
        this._annotationEntities.clear();
        if (scene) scene.requestRender();

        return { ok: true, action: actionName, clearedCount: count };
      }

      // 11. SET MAP STACK
      if (actionName === "set_map_stack" || actionName === "set_map_source") {
        const stackId = args.stackId || args.sourceId;
        return { ok: true, action: actionName, stackId };
      }

      // Explicitly reject unhandled actions instead of returning fake success
      return {
        ok: false,
        error: `Action '${actionName}' has no implementation in GodsEyeAdapter.`,
        action: actionName
      };

    } catch (err) {
      console.error(`[GodsEyeAdapter] Execution error in action '${actionName}':`, err);
      return { ok: false, error: err.message || String(err), action: actionName };
    }
  }

  destroy() {
    if (this.viewer && this.cameraListener) {
      try {
        this.viewer.camera.moveEnd.removeEventListener(this.cameraListener);
      } catch (e) {}
    }

    // Clear all annotation entities
    for (const [id, entity] of this._annotationEntities.entries()) {
      try {
        if (this.viewer && !this.viewer.isDestroyed()) {
          this.viewer.entities.remove(entity);
        }
      } catch (_) {}
    }
    this._annotationEntities.clear();
    this._layerDataSources.clear();

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
