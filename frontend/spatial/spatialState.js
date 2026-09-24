/**
 * J.A.R.V.I.S. Spatial State Store (frontend/spatial/spatialState.js)
 * =================================================================
 * Normalized, serializable state store for the 3D world interface.
 * Stores strictly plain data — never raw Cesium or WebGL objects.
 */

import { spatialEventBus } from "./spatialEventBus.js";

class SpatialStateStore {
  constructor() {
    this._state = {
      isReady: false,
      camera: {
        latitude: 20.0,
        longitude: 0.0,
        height: 20000000.0, // meters
        heading: 0.0,
        pitch: -90.0,
        roll: 0.0,
        mode: "globe", // globe, overview, street, cockpit
        locationName: "World Overview"
      },
      selection: {
        entityId: null,
        entityType: null,
        provider: null,
        metadata: {}
      },
      tracking: {
        entityId: null,
        entityType: null,
        active: false,
        name: "",
        altitude_m: 0,
        speed_kts: 0,
        heading_deg: 0
      },
      layers: {
        flights: true,
        military: false,
        vessels: false,
        satellites: false,
        earthquakes: false,
        firms: false,
        weather: true,
        traffic: false,
        cctv: false,
        radio: false,
        bikeshare: false,
        "submarine-cables": false,
        datacenters: false
      },
      mapSource: {
        active: "esri-imagery",
        available: ["esri-imagery", "osm", "photoreal", "bing-aerial"]
      },
      visualStyle: {
        active: "normal", // normal, surveillance, thermal, retro, noir
        available: ["normal", "surveillance", "thermal", "retro", "noir"]
      },
      annotations: [],
      inCockpit: false,
      diagnostics: {
        fps: null,
        frameTimeMs: null,
        memoryPressure: "NORMAL",
        activeEntities: 0,
        networkProfile: "FAST",
        performanceMode: "BALANCED"
      }
    };
  }

  getState() {
    return JSON.parse(JSON.stringify(this._state));
  }

  setCamera(cameraData) {
    if (!cameraData || typeof cameraData !== "object") return;
    Object.assign(this._state.camera, cameraData);
    spatialEventBus.emit("spatial.camera.changed", this._state.camera);
  }

  setSelection(entityId, entityType, provider, metadata = {}) {
    this._state.selection = {
      entityId,
      entityType,
      provider,
      metadata: metadata || {}
    };
    spatialEventBus.emit("spatial.entity.selected", this._state.selection);
  }

  clearSelection() {
    this._state.selection = {
      entityId: null,
      entityType: null,
      provider: null,
      metadata: {}
    };
    spatialEventBus.emit("spatial.entity.unselected");
  }

  setTracking(entityId, entityType, name = "", telemetry = {}) {
    this._state.tracking = {
      entityId,
      entityType,
      active: Boolean(entityId),
      name: name || entityId || "",
      altitude_m: telemetry.altitude_m || 0,
      speed_kts: telemetry.speed_kts || 0,
      heading_deg: telemetry.heading_deg || 0
    };
    if (entityId) {
      spatialEventBus.emit("spatial.entity.tracked", this._state.tracking);
    } else {
      spatialEventBus.emit("spatial.entity.untracked");
    }
  }

  setLayerVisibility(layerId, isVisible) {
    if (layerId in this._state.layers) {
      this._state.layers[layerId] = Boolean(isVisible);
      spatialEventBus.emit("spatial.layer.changed", { layerId, isVisible: Boolean(isVisible) });
    }
  }

  setVisualStyle(style) {
    if (this._state.visualStyle.available.includes(style)) {
      this._state.visualStyle.active = style;
      spatialEventBus.emit("spatial.style.changed", { style });
    }
  }

  setMapSource(sourceId) {
    this._state.mapSource.active = sourceId;
    spatialEventBus.emit("spatial.mapsource.changed", { sourceId });
  }

  setCockpit(inCockpit) {
    this._state.inCockpit = Boolean(inCockpit);
    spatialEventBus.emit("spatial.cockpit.changed", { inCockpit: this._state.inCockpit });
  }

  addAnnotation(annotation) {
    if (!annotation) return;
    this._state.annotations.push(annotation);
    spatialEventBus.emit("spatial.annotations.updated", this._state.annotations);
  }

  clearAnnotations() {
    this._state.annotations = [];
    spatialEventBus.emit("spatial.annotations.cleared");
  }

  updateDiagnostics(diagUpdate) {
    if (!diagUpdate || typeof diagUpdate !== "object") return;
    Object.assign(this._state.diagnostics, diagUpdate);
    spatialEventBus.emit("spatial.diagnostics.updated", this._state.diagnostics);
  }
}

export const spatialState = new SpatialStateStore();
if (typeof window !== "undefined") {
  window.__jarvisSpatialState = spatialState;
}
