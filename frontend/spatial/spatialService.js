/**
 * J.A.R.V.I.S. Spatial Intelligence Service (frontend/spatial/spatialService.js)
 * ==============================================================================
 * Master frontend controller for God's Eye View 3D Earth Workspace.
 * Handles lazy startup, Cesium integration, WebSocket command dispatch,
 * Stark HUD telemetry HUD overlays, and graceful teardown.
 */

import { spatialEventBus } from "./spatialEventBus.js";
import { spatialState } from "./spatialState.js";
import { spatialCommandBus } from "./spatialCommandBus.js";
import { godsEyeAdapter } from "./godsEyeAdapter.js";
import { spatialPerformanceGovernor } from "./spatialPerformanceGovernor.js";
import { spatialDiagnostics } from "./spatialDiagnostics.js";

class SpatialService {
  constructor() {
    this.isLoaded = false;
    this.isActive = false;
    this.viewer = null;
    this.container = null;
    this._initWebSocketSync();
  }

  _initWebSocketSync() {
    // Listen for WebSocket spatial events dispatched from Python core
    window.addEventListener("jarvis:spatial-event", (e) => {
      const payload = e.detail;
      if (payload && payload.action) {
        spatialCommandBus.dispatch(payload);
      }
    });

    // Listen for telemetry state changes to update HUD readouts
    spatialEventBus.on("spatial.camera.changed", (cam) => {
      this._updateCoordinateHud(cam);
    });

    spatialEventBus.on("spatial.entity.selected", (entity) => {
      this._updateEntityInspector(entity);
    });

    spatialEventBus.on("spatial.command.completed", (res) => {
      this._flashCommandStatus(`ACTION COMPLETE: ${res.type}`);
    });
  }

  async activate() {
    this.isActive = true;
    if (!this.isLoaded) {
      await this.init();
    }
  }

  deactivate() {
    this.isActive = false;
    // Tell performance governor tab or workspace is inactive
    spatialEventBus.emit("spatial.deactivated");
  }

  async init() {
    if (this.isLoaded) return;
    this.container = document.getElementById("spatialGlobeContainer");
    if (!this.container) return;

    console.log("[SpatialService] Initializing 3D Photorealistic Earth Subsystem...");
    this._showLoadingIndicator("INITIALIZING SPATIAL INTELLIGENCE CORE...");

    try {
      // 1. Check if Cesium global is available, or load bundle
      if (!window.Cesium) {
        await this._loadCesiumDependencies();
      }

      // 2. Initialize Cesium Viewer
      if (window.Cesium && this.container) {
        this._showLoadingIndicator("GENERATING 3D PHOTOREALISTIC GLOBE...");
        
        // Ensure Ion credentials or fallback to Esri keyless
        if (window.Cesium.Ion) {
          window.Cesium.Ion.defaultAccessToken = "";
        }

        const viewer = new window.Cesium.Viewer(this.container, {
          imageryProvider: new window.Cesium.ArcGisMapServerImageryProvider({
            url: "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer"
          }),
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
          requestRenderMode: true, // Idle render governor baseline!
          maximumRenderTimeChange: Infinity
        });

        // Optimize Cesium scene settings for Ryzen 7 7840HS
        viewer.scene.globe.enableLighting = false;
        viewer.scene.fog.enabled = true;
        viewer.scene.globe.depthTestAgainstTerrain = false;

        this.viewer = viewer;
        godsEyeAdapter.attachViewer(viewer);
      }

      this.isLoaded = true;
      this._hideLoadingIndicator();
      spatialEventBus.emit("spatial.initialized");
      console.log("[SpatialService] Spatial Intelligence Engine Online.");

    } catch (err) {
      console.error("[SpatialService] Initialization error:", err);
      this._showLoadingIndicator(`INITIALIZATION NOTICE: Running in Adaptive 3D Mode (${err.message})`, true);
    }
  }

  async _loadCesiumDependencies() {
    // Check if Cesium stylesheet is present
    if (!document.getElementById("cesiumCss")) {
      const link = document.createElement("link");
      link.id = "cesiumCss";
      link.rel = "stylesheet";
      link.href = "/spatial/cesium/Widgets/widgets.css";
      document.head.appendChild(link);
    }

    // Load Cesium.js from vendor build
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "/spatial/cesium/Cesium.js";
      script.onload = () => resolve();
      script.onerror = () => {
        // Fallback to unpkg CDN if local asset path is building
        console.warn("[SpatialService] Local Cesium.js unavailable, falling back to CDN...");
        const cdnScript = document.createElement("script");
        cdnScript.src = "https://cesium.com/downloads/cesiumjs/releases/1.124/Build/Cesium/Cesium.js";
        const cdnCss = document.createElement("link");
        cdnCss.rel = "stylesheet";
        cdnCss.href = "https://cesium.com/downloads/cesiumjs/releases/1.124/Build/Cesium/Widgets/widgets.css";
        document.head.appendChild(cdnCss);
        cdnScript.onload = () => resolve();
        cdnScript.onerror = () => reject(new Error("Cesium script load failed"));
        document.head.appendChild(cdnScript);
      };
      document.head.appendChild(script);
    });
  }

  _updateCoordinateHud(cam) {
    const latEl = document.getElementById("hudSpatialLat");
    const lonEl = document.getElementById("hudSpatialLon");
    const altEl = document.getElementById("hudSpatialAlt");
    const nameEl = document.getElementById("hudSpatialTargetName");

    if (latEl) latEl.innerText = `${cam.latitude > 0 ? "+" : ""}${cam.latitude.toFixed(4)}°`;
    if (lonEl) lonEl.innerText = `${cam.longitude > 0 ? "+" : ""}${cam.longitude.toFixed(4)}°`;
    if (altEl) altEl.innerText = `${(cam.height / 1000).toFixed(1)} KM`;
    if (nameEl && cam.locationName) nameEl.innerText = cam.locationName.toUpperCase();
  }

  _updateEntityInspector(entity) {
    const inspector = document.getElementById("spatialEntityInspector");
    const title = document.getElementById("spatialEntityTitle");
    const meta = document.getElementById("spatialEntityMeta");

    if (inspector) inspector.classList.add("active");
    if (title) title.innerText = entity.id || entity.callsign || "SELECTED ENTITY";
    if (meta) {
      meta.innerHTML = `
        <div class="entity-stat-row"><span>LAYER:</span> <strong>${(entity.entityType || "AIRCRAFT").toUpperCase()}</strong></div>
        <div class="entity-stat-row"><span>SOURCE:</span> <strong>${(entity.provider || "OPENSKY").toUpperCase()}</strong></div>
        <div class="entity-stat-row"><span>STATUS:</span> <strong style="color: #00ffcc;">LIVE TELEMETRY</strong></div>
      `;
    }
  }

  _showLoadingIndicator(msg, isWarning = false) {
    const loader = document.getElementById("spatialLoadingOverlay");
    const label = document.getElementById("spatialLoadingLabel");
    if (loader && label) {
      loader.style.display = "flex";
      label.innerText = msg;
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

  _flashCommandStatus(text) {
    const badge = document.getElementById("spatialCommandStatusBadge");
    if (badge) {
      badge.innerText = text;
      badge.style.opacity = "1";
      setTimeout(() => { badge.style.opacity = "0.7"; }, 2500);
    }
  }
}

export const spatialService = new SpatialService();
if (typeof window !== "undefined") {
  window.spatialService = spatialService;
  window.spatialCommandBus = spatialCommandBus;
  window.spatialEventBus = spatialEventBus;
  window.spatialState = spatialState;
  window.spatialDiagnostics = spatialDiagnostics;
}
