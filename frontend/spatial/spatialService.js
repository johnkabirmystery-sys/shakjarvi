/**
 * J.A.R.V.I.S. Spatial Intelligence Service (frontend/spatial/spatialService.js)
 * ==============================================================================
 * Master frontend controller for God's Eye View 3D Earth Workspace.
 * Handles lazy startup, Cesium 1.138 integration, WebSocket command dispatch,
 * Stark HUD telemetry HUD overlays, explicit lifecycle states, and graceful teardown.
 */

import { spatialEventBus } from "./spatialEventBus.js";
import { spatialState } from "./spatialState.js";
import { spatialCommandBus } from "./spatialCommandBus.js";
import { godsEyeAdapter } from "./godsEyeAdapter.js";
import { spatialPerformanceGovernor } from "./spatialPerformanceGovernor.js";
import { spatialDiagnostics } from "./spatialDiagnostics.js";
import { privacyManager } from "./privacyManager.js";
import { selfLocationEngine } from "./selfLocationEngine.js";
import { locationFusionEngine } from "./locationFusionEngine.js";
import { buildingResolutionService } from "./buildingResolutionService.js";
import { locationHistoryManager } from "./locationHistoryManager.js";

export const LIFECYCLE_STATES = {
  IDLE: "idle",
  LOADING: "loading",
  READY: "ready",
  FAILED: "failed",
  DESTROYED: "destroyed"
};

class SpatialService {
  constructor() {
    this.lifecycleState = LIFECYCLE_STATES.IDLE;
    this.isLoaded = false;
    this.isActive = false;
    this.viewer = null;
    this.container = null;
    this.lastError = null;
    this._wsListener = null;
    this._busUnsubscribers = [];

    this._initWebSocketSync();
  }

  _initWebSocketSync() {
    // Listen for WebSocket spatial events dispatched from Python core
    this._wsListener = (e) => {
      const payload = e.detail;
      if (payload && (payload.action || payload.type)) {
        spatialCommandBus.dispatch(payload);
      }
    };
    window.addEventListener("jarvis:spatial-event", this._wsListener);

    // Telemetry and status subscriptions
    const unsub1 = spatialEventBus.on("spatial.camera.changed", (cam) => {
      this._updateCoordinateHud(cam);
    });

    const unsub2 = spatialEventBus.on("spatial.entity.selected", (entity) => {
      this._updateEntityInspector(entity);
    });

    const unsub3 = spatialEventBus.on("spatial.command.completed", (res) => {
      this._flashCommandStatus(`ACTION COMPLETE: ${res.type}`);
    });

    const unsub4 = spatialEventBus.on("spatial.command.failed", (res) => {
      this._flashCommandStatus(`ERROR: ${res.error || res.type}`, true);
    });

    this._busUnsubscribers.push(unsub1, unsub2, unsub3, unsub4);
  }

  async activate() {
    this.isActive = true;
    if (this.lifecycleState === LIFECYCLE_STATES.IDLE || this.lifecycleState === LIFECYCLE_STATES.DESTROYED) {
      await this.init();
    } else if (this.lifecycleState === LIFECYCLE_STATES.READY && this.viewer) {
      // Re-trigger render and resume performance governor
      spatialPerformanceGovernor.resume();
      if (this.viewer.scene) {
        this.viewer.scene.requestRender();
      }
      spatialEventBus.emit("spatial.activated");
    }
  }

  deactivate() {
    this.isActive = false;
    spatialPerformanceGovernor.pause();
    spatialEventBus.emit("spatial.deactivated");
  }

  async init() {
    // Prevent concurrent or duplicate initialization
    if (this.lifecycleState === LIFECYCLE_STATES.LOADING || this.lifecycleState === LIFECYCLE_STATES.READY) {
      return;
    }

    this.container = document.getElementById("spatialGlobeContainer");
    if (!this.container) {
      this.lifecycleState = LIFECYCLE_STATES.FAILED;
      this.lastError = "Container element '#spatialGlobeContainer' not found in DOM";
      console.error("[SpatialService]", this.lastError);
      this._showLoadingIndicator(`INITIALIZATION ERROR: ${this.lastError}`, true);
      spatialEventBus.emit("spatial.init.failed", { error: this.lastError });
      return;
    }

    this.lifecycleState = LIFECYCLE_STATES.LOADING;
    this.lastError = null;
    console.log("[SpatialService] Initializing 3D Photorealistic Earth Subsystem (Cesium 1.138)...");
    this._showLoadingIndicator("INITIALIZING SPATIAL INTELLIGENCE CORE...");

    try {
      // 1. Ensure Cesium Base URL is globally configured before any script execution
      window.CESIUM_BASE_URL = "/spatial/cesium/";

      // 2. Load Cesium 1.138.0 local bundle if not already present on window
      if (!window.Cesium) {
        await this._loadCesiumDependencies();
      }

      if (!window.Cesium) {
        throw new Error("Cesium global object unavailable after asset load.");
      }

      // 3. Configure Cesium global settings
      if (window.Cesium.Ion) {
        window.Cesium.Ion.defaultAccessToken = "";
      }

      this._showLoadingIndicator("GENERATING 3D PHOTOREALISTIC GLOBE...");

      // 4. Initialize Imagery Provider (ArcGIS World Imagery with async fallback)
      let baseLayer = undefined;
      try {
        if (window.Cesium.ArcGisMapServerImageryProvider && typeof window.Cesium.ArcGisMapServerImageryProvider.fromUrl === "function") {
          const provider = await window.Cesium.ArcGisMapServerImageryProvider.fromUrl(
            "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer"
          );
          baseLayer = new window.Cesium.ImageryLayer(provider);
        } else if (window.Cesium.createWorldImageryAsync) {
          baseLayer = await window.Cesium.createWorldImageryAsync();
        }
      } catch (imageryErr) {
        console.warn("[SpatialService] Primary imagery provider error, using procedural base:", imageryErr);
      }

      // 5. Instantiate Cesium Viewer with performance-governed settings
      const viewer = new window.Cesium.Viewer(this.container, {
        baseLayer: baseLayer || false,
        baseLayerPicker: false,
        geocoder: false,
        homeButton: false,
        infoBox: false,
        sceneModePicker: false,
        selectionIndicator: false,
        timeline: false,
        navigationHelpButton: false,
        animation: false,
        shouldAnimate: true,
        requestRenderMode: true, // Render governor baseline
        maximumRenderTimeChange: Infinity
      });

      // Optimize scene rendering settings
      viewer.scene.globe.enableLighting = false;
      viewer.scene.fog.enabled = true;
      viewer.scene.globe.depthTestAgainstTerrain = false;

      // Attach viewer to adapter and performance governor
      this.viewer = viewer;
      godsEyeAdapter.attachViewer(viewer);
      spatialPerformanceGovernor.attachViewer(viewer);

      // Verify viewer readiness
      this.isLoaded = true;
      this.lifecycleState = LIFECYCLE_STATES.READY;
      this._hideLoadingIndicator();

      spatialEventBus.emit("spatial.initialized", {
        version: window.Cesium.VERSION || "1.138.0",
        containerId: "spatialGlobeContainer"
      });
      console.log(`[SpatialService] Spatial Intelligence Engine Online (Cesium ${window.Cesium.VERSION || "1.138.0"}).`);

      // Initial frame render
      viewer.scene.requestRender();

    } catch (err) {
      this.lifecycleState = LIFECYCLE_STATES.FAILED;
      this.lastError = err.message || String(err);
      console.error("[SpatialService] Initialization failed:", err);
      this._showLoadingIndicator(`INITIALIZATION ERROR: ${this.lastError}`, true);
      spatialEventBus.emit("spatial.init.failed", { error: this.lastError });
    }
  }

  async _loadCesiumDependencies() {
    window.CESIUM_BASE_URL = "/spatial/cesium/";

    // 1. Ensure CSS stylesheet is present
    if (!document.getElementById("cesiumCss")) {
      const link = document.createElement("link");
      link.id = "cesiumCss";
      link.rel = "stylesheet";
      link.href = "/spatial/cesium/Widgets/widgets.css";
      document.head.appendChild(link);
    }

    // 2. Load Cesium.js script strictly from local vendor bundle
    return new Promise((resolve, reject) => {
      const existingScript = document.getElementById("cesiumScript");
      if (existingScript && window.Cesium) {
        return resolve();
      }

      const script = document.createElement("script");
      script.id = "cesiumScript";
      script.src = "/spatial/cesium/Cesium.js";
      script.onload = () => {
        console.log("[SpatialService] Local Cesium 1.138 bundle loaded successfully.");
        resolve();
      };
      script.onerror = (err) => {
        console.error("[SpatialService] Failed to load local Cesium.js asset from /spatial/cesium/Cesium.js", err);
        reject(new Error("Local Cesium.js asset failed to load. Ensure server static mounts are active."));
      };
      document.head.appendChild(script);
    });
  }

  _updateCoordinateHud(cam) {
    const latEl = document.getElementById("hudSpatialLat");
    const lonEl = document.getElementById("hudSpatialLon");
    const altEl = document.getElementById("hudSpatialAlt");
    const nameEl = document.getElementById("hudSpatialTargetName");

    if (latEl && Number.isFinite(cam.latitude)) {
      latEl.textContent = `${cam.latitude >= 0 ? "+" : ""}${cam.latitude.toFixed(4)}°`;
    }
    if (lonEl && Number.isFinite(cam.longitude)) {
      lonEl.textContent = `${cam.longitude >= 0 ? "+" : ""}${cam.longitude.toFixed(4)}°`;
    }
    if (altEl && Number.isFinite(cam.height)) {
      if (cam.height >= 1000) {
        altEl.textContent = `${(cam.height / 1000).toLocaleString(undefined, { maximumFractionDigits: 1 })} KM`;
      } else {
        altEl.textContent = `${Math.round(cam.height)} M`;
      }
    }
    if (nameEl && cam.locationName) {
      nameEl.textContent = String(cam.locationName).toUpperCase();
    }
  }

  _updateEntityInspector(entity) {
    const inspector = document.getElementById("spatialEntityInspector");
    const title = document.getElementById("spatialEntityTitle");
    const meta = document.getElementById("spatialEntityMeta");

    if (!inspector || !entity) return;

    inspector.classList.add("active");
    if (title) {
      title.textContent = entity.name || entity.id || entity.callsign || "SELECTED ENTITY";
    }

    if (meta) {
      // Clear and construct safe DOM elements without innerHTML
      meta.textContent = "";

      const makeRow = (label, val, color) => {
        const row = document.createElement("div");
        row.className = "entity-stat-row";
        const lblSpan = document.createElement("span");
        lblSpan.textContent = label;
        const valStrong = document.createElement("strong");
        valStrong.textContent = val;
        if (color) valStrong.style.color = color;
        row.appendChild(lblSpan);
        row.appendChild(valStrong);
        return row;
      };

      meta.appendChild(makeRow("LAYER:", (entity.entityType || entity.layerId || "AIRCRAFT").toUpperCase()));
      meta.appendChild(makeRow("SOURCE:", (entity.provider || "OPENSKY").toUpperCase()));
      meta.appendChild(makeRow("STATUS:", entity.status || "TRACKED", "#00ffcc"));

      if (Number.isFinite(entity.altitude_m)) {
        meta.appendChild(makeRow("ALTITUDE:", `${Math.round(entity.altitude_m).toLocaleString()} M`));
      }
      if (Number.isFinite(entity.speed_kts)) {
        meta.appendChild(makeRow("SPEED:", `${Math.round(entity.speed_kts)} KTS`));
      }
    }
  }

  _showLoadingIndicator(msg, isWarning = false) {
    const loader = document.getElementById("spatialLoadingOverlay");
    const label = document.getElementById("spatialLoadingLabel");
    if (loader && label) {
      loader.style.display = "flex";
      label.textContent = msg;
      label.style.color = isWarning ? "#ffab00" : "#00f0ff";
    }
  }

  _hideLoadingIndicator() {
    const loader = document.getElementById("spatialLoadingOverlay");
    if (loader) {
      loader.style.transition = "opacity 0.5s ease";
      loader.style.opacity = "0";
      setTimeout(() => {
        loader.style.display = "none";
        loader.style.opacity = "1";
      }, 500);
    }
  }

  _flashCommandStatus(text, isError = false) {
    const badge = document.getElementById("spatialCommandStatusBadge");
    if (badge) {
      badge.textContent = text;
      badge.style.color = isError ? "#ff5252" : "#00f0ff";
      badge.style.opacity = "1";
      setTimeout(() => {
        badge.style.opacity = "0.7";
        badge.style.color = "";
      }, 3000);
    }
  }

  destroy() {
    if (this._wsListener) {
      window.removeEventListener("jarvis:spatial-event", this._wsListener);
      this._wsListener = null;
    }

    this._busUnsubscribers.forEach(unsub => {
      try { unsub(); } catch (_) {}
    });
    this._busUnsubscribers = [];

    if (godsEyeAdapter) {
      godsEyeAdapter.destroy();
    }

    if (this.viewer && !this.viewer.isDestroyed()) {
      try {
        this.viewer.destroy();
      } catch (e) {
        console.warn("[SpatialService] Error destroying Cesium viewer:", e);
      }
    }

    this.viewer = null;
    this.container = null;
    this.isLoaded = false;
    this.isActive = false;
    this.lifecycleState = LIFECYCLE_STATES.DESTROYED;
    spatialEventBus.emit("spatial.destroyed");
    console.log("[SpatialService] Spatial Intelligence Engine torn down cleanly.");
  }
}

export const spatialService = new SpatialService();
if (typeof window !== "undefined") {
  window.spatialService = spatialService;
  window.spatialCommandBus = spatialCommandBus;
  window.spatialEventBus = spatialEventBus;
  window.spatialState = spatialState;
  window.spatialDiagnostics = spatialDiagnostics;
  window.privacyManager = privacyManager;
  window.selfLocationEngine = selfLocationEngine;
  window.locationFusionEngine = locationFusionEngine;
  window.buildingResolutionService = buildingResolutionService;
  window.locationHistoryManager = locationHistoryManager;
}
