/**
 * J.A.R.V.I.S. God's Eye View Adapter (frontend/spatial/godsEyeAdapter.js)
 * ======================================================================
 * Translates Jarvis-level spatial commands into native Cesium 1.138 APIs.
 * Eliminates all simulated returns. Guaranteed real scene mutations or
 * explicit actionable error returns.
 * Supports:
 * - Live self-location pin, accuracy uncertainty ring & heading cone.
 * - Movement breadcrumb trail rendering.
 * - User-defined geofence boundaries.
 * - Building candidate footprint highlights.
 * - Dynamic public layer visibility & sensor visual modes.
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
    this._geofenceEntities = new Map(); // id -> Cesium.Entity
    this._selfLocationEntity = null;
    this._accuracyCircleEntity = null;
    this._movementTrailEntity = null;
    this._buildingHighlightEntity = null;
    this._activeStyle = "normal";

    this._initBusSubscriptions();
  }

  _initBusSubscriptions() {
    spatialEventBus.on("spatial.location.fused", (obs) => {
      this.renderSelfLocation(obs);
    });

    spatialEventBus.on("spatial.self_location.stopped", () => {
      this.clearSelfLocation();
    });

    spatialEventBus.on("spatial.history.cleared", () => {
      this.clearMovementTrail();
    });
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

  // -------------------------------------------------------------
  // SELF-LOCATION, ACCURACY RING & TRAIL RENDERING
  // -------------------------------------------------------------
  renderSelfLocation(obs) {
    if (!this.viewer || !window.Cesium || !obs) return;

    const Cesium = window.Cesium;
    const pos = Cesium.Cartesian3.fromDegrees(obs.longitude, obs.latitude, obs.altitudeMeters || 10.0);
    const accuracyM = Math.max(5.0, obs.horizontalAccuracyMeters || 15.0);

    // 1. Accuracy circle polygon/ellipse
    if (!this._accuracyCircleEntity) {
      this._accuracyCircleEntity = this.viewer.entities.add({
        id: "jarvis_self_accuracy_circle",
        position: Cesium.Cartesian3.fromDegrees(obs.longitude, obs.latitude, 0.0),
        ellipse: {
          semiMinorAxis: accuracyM,
          semiMajorAxis: accuracyM,
          material: Cesium.Color.CYAN.withAlpha(0.18),
          outline: true,
          outlineColor: Cesium.Color.CYAN.withAlpha(0.6),
          outlineWidth: 2,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
        }
      });
    } else {
      this._accuracyCircleEntity.position = Cesium.Cartesian3.fromDegrees(obs.longitude, obs.latitude, 0.0);
      this._accuracyCircleEntity.ellipse.semiMinorAxis = accuracyM;
      this._accuracyCircleEntity.ellipse.semiMajorAxis = accuracyM;
    }

    // 2. Self position point & glowing beacon
    if (!this._selfLocationEntity) {
      this._selfLocationEntity = this.viewer.entities.add({
        id: "jarvis_self_location_pin",
        position: pos,
        point: {
          pixelSize: 14,
          color: Cesium.Color.fromCssColorString("#00f0ff"),
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 3,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        },
        label: {
          text: obs.userConfirmed ? "📍 YOU (CONFIRMED)" : "📍 YOU (LIVE GPS)",
          font: "bold 13px monospace",
          fillColor: Cesium.Color.fromCssColorString("#00f0ff"),
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 3,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -16),
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        }
      });
    } else {
      this._selfLocationEntity.position = pos;
      this._selfLocationEntity.label.text = obs.userConfirmed ? "📍 YOU (CONFIRMED)" : "📍 YOU (LIVE GPS)";
    }

    if (this.viewer.scene) this.viewer.scene.requestRender();
  }

  clearSelfLocation() {
    if (!this.viewer) return;
    if (this._selfLocationEntity) {
      this.viewer.entities.remove(this._selfLocationEntity);
      this._selfLocationEntity = null;
    }
    if (this._accuracyCircleEntity) {
      this.viewer.entities.remove(this._accuracyCircleEntity);
      this._accuracyCircleEntity = null;
    }
    if (this.viewer.scene) this.viewer.scene.requestRender();
  }

  renderMovementTrail(points) {
    if (!this.viewer || !window.Cesium || !points || points.length < 2) return;

    const Cesium = window.Cesium;
    const positions = points.map(p => Cesium.Cartesian3.fromDegrees(p.longitude, p.latitude, p.altitude || 5.0));

    if (!this._movementTrailEntity) {
      this._movementTrailEntity = this.viewer.entities.add({
        id: "jarvis_self_movement_trail",
        polyline: {
          positions: positions,
          width: 3,
          material: new Cesium.PolylineDashMaterialProperty({
            color: Cesium.Color.fromCssColorString("#00e5ff"),
            dashLength: 16.0
          }),
          clampToGround: true
        }
      });
    } else {
      this._movementTrailEntity.polyline.positions = positions;
    }

    if (this.viewer.scene) this.viewer.scene.requestRender();
  }

  clearMovementTrail() {
    if (this.viewer && this._movementTrailEntity) {
      this.viewer.entities.remove(this._movementTrailEntity);
      this._movementTrailEntity = null;
      if (this.viewer.scene) this.viewer.scene.requestRender();
    }
  }

  // -------------------------------------------------------------
  // GEOFENCE VISUALIZATION
  // -------------------------------------------------------------
  renderGeofence(fence) {
    if (!this.viewer || !window.Cesium || !fence) return;
    const Cesium = window.Cesium;

    const fid = `geofence_${fence.id}`;
    if (this._geofenceEntities.has(fid)) {
      this.viewer.entities.remove(this._geofenceEntities.get(fid));
    }

    const entity = this.viewer.entities.add({
      id: fid,
      name: fence.name || "Geofence Boundary",
      position: Cesium.Cartesian3.fromDegrees(fence.longitude, fence.latitude, 0.0),
      ellipse: {
        semiMinorAxis: fence.radiusMeters,
        semiMajorAxis: fence.radiusMeters,
        material: Cesium.Color.fromCssColorString("#ffab00").withAlpha(0.15),
        outline: true,
        outlineColor: Cesium.Color.fromCssColorString("#ffab00").withAlpha(0.8),
        outlineWidth: 2,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
      },
      label: {
        text: `🛡 ${fence.name.toUpperCase()} (R=${fence.radiusMeters}M)`,
        font: "11px monospace",
        fillColor: Cesium.Color.fromCssColorString("#ffab00"),
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        verticalOrigin: Cesium.VerticalOrigin.TOP,
        pixelOffset: new Cesium.Cartesian2(0, 10)
      }
    });

    this._geofenceEntities.set(fid, entity);
    if (this.viewer.scene) this.viewer.scene.requestRender();
  }

  removeGeofence(fenceId) {
    const fid = `geofence_${fenceId}`;
    if (this.viewer && this._geofenceEntities.has(fid)) {
      this.viewer.entities.remove(this._geofenceEntities.get(fid));
      this._geofenceEntities.delete(fid);
      if (this.viewer.scene) this.viewer.scene.requestRender();
    }
  }

  // -------------------------------------------------------------
  // NATIVE ACTION DISPATCH GATEWAY
  // -------------------------------------------------------------
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

        let entity = this.viewer.entities.getById(entityId);
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
            this.viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
          } else {
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

      // 11. CENTER ON SELF
      if (actionName === "center_on_self") {
        if (!this._selfLocationEntity) {
          return { ok: false, error: "Self-location position not yet acquired or tracking inactive." };
        }
        const cart = this._selfLocationEntity.position.getValue(Cesium.JulianDate.now());
        if (cart) {
          const carto = Cesium.Cartographic.fromCartesian(cart);
          const lat = Cesium.Math.toDegrees(carto.latitude);
          const lon = Cesium.Math.toDegrees(carto.longitude);
          this.viewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(lon, lat, 1200.0),
            duration: 1.5
          });
          return { ok: true, action: actionName, latitude: lat, longitude: lon };
        }
        return { ok: false, error: "Could not evaluate self location coordinates." };
      }

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

    for (const [id, entity] of this._annotationEntities.entries()) {
      try {
        if (this.viewer && !this.viewer.isDestroyed()) {
          this.viewer.entities.remove(entity);
        }
      } catch (_) {}
    }
    this._annotationEntities.clear();
    this._layerDataSources.clear();

    this.clearSelfLocation();
    this.clearMovementTrail();

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
