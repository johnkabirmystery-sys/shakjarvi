/**
 * J.A.R.V.I.S. Spatial Intelligence Service (frontend/spatial/spatialService.js)
 * ==============================================================================
 * Master frontend controller for God's Eye View 3D Earth Workspace.
 * Orchestrates:
 * - Cesium 1.138+ runtime lifecycle and ViewerFactory instantiation
 * - Pluggable TerrainManager with real elevation & honest degraded mode
 * - 3D TilesetManager and BuildingLayer for architectural 3D geometry
 * - ImageryLayerManager with provider registry & fail-safe offline handling
 * - Dedicated CameraController and SceneModeController (3D, 2D, Columbus View)
 * - RenderLoopController & RenderHealthMonitor for GPU performance budgeting
 * - SpatialLayerRegistry, Normalized SpatialEntity, and SpatialAnalytics engine
 * - Stark HUD telemetry, coordinate overlays, entity inspector & clean teardown
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

// Modular Spatial Runtime Subsystems
import { cesiumRuntime, RUNTIME_STATUS } from "./runtime/cesiumRuntime.js";
import { ViewerFactory } from "./runtime/viewerFactory.js";
import { RenderLoopController } from "./runtime/renderLoopController.js";
import { CameraController } from "./runtime/cameraController.js";
import { SceneModeController } from "./runtime/sceneModeController.js";
import { RenderHealthMonitor } from "./runtime/renderHealthMonitor.js";

// Terrain Subsystem
import { TerrainManager, TERRAIN_STATUS } from "./terrain/terrainManager.js";
import { terrainProviderRegistry } from "./terrain/terrainProviderRegistry.js";

// 3D Tiles Subsystem
import { TilesetManager } from "./tiles/tilesetManager.js";
import { BuildingLayer } from "./tiles/buildingLayer.js";
import { TilesetHealth } from "./tiles/tilesetHealth.js";

// Imagery Subsystem
import { ImageryLayerManager } from "./imagery/imageryLayerManager.js";
import { imageryProviderRegistry } from "./imagery/imageryProviderRegistry.js";

// Core and Analytics Subsystems
import { SpatialEntity } from "./core/spatialEntity.js";
import { spatialLayerRegistry } from "./core/spatialLayerRegistry.js";
import { SpatialAnalytics } from "./analytics/spatialAnalytics.js";

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

    // Subsystem Controllers
    this.renderLoop = new RenderLoopController(null);
    this.cameraController = new CameraController(null);
    this.sceneModeController = new SceneModeController(null);
    this.renderHealth = new RenderHealthMonitor(null);
    this.terrainManager = new TerrainManager(null, spatialEventBus);
    this.tilesetManager = new TilesetManager(null, spatialEventBus);
    this.buildingLayer = new BuildingLayer(this.tilesetManager, spatialEventBus);
    this.tilesetHealth = new TilesetHealth(this.tilesetManager);
    this.imageryManager = new ImageryLayerManager(null, spatialEventBus);

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

    const unsub5 = spatialEventBus.on("spatial.terrain.degraded", (info) => {
      console.warn("[SpatialService] Terrain degraded to ellipsoid:", info.reason);
      this._updateTerrainHud("ELLIPSOID (DEGRADED)", "#ffab00");
    });

    const unsub6 = spatialEventBus.on("spatial.terrain.changed", (info) => {
      const label = info.isRealTerrain ? info.provider.toUpperCase() : "ELLIPSOID";
      const color = info.isRealTerrain ? "#00ffcc" : "#888888";
      this._updateTerrainHud(label, color);
    });

    this._busUnsubscribers.push(unsub1, unsub2, unsub3, unsub4, unsub5, unsub6);
  }

  async activate() {
    this.isActive = true;
    if (this.lifecycleState === LIFECYCLE_STATES.IDLE || this.lifecycleState === LIFECYCLE_STATES.DESTROYED) {
      await this.init();
    } else if (this.lifecycleState === LIFECYCLE_STATES.READY && this.viewer) {
      this.renderLoop.resume();
      spatialPerformanceGovernor.resume();
      if (this.viewer.scene) {
        this.viewer.scene.requestRender();
      }
      spatialEventBus.emit("spatial.activated");
    }
  }

  deactivate() {
    this.isActive = false;
    this.renderLoop.pause();
    spatialPerformanceGovernor.pause();
    spatialEventBus.emit("spatial.deactivated");
  }

  async init() {
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
    console.log("[SpatialService] Initializing 3D Photorealistic Earth Subsystem...");
    this._showLoadingIndicator("INITIALIZING SPATIAL INTELLIGENCE CORE...");

    try {
      // 1. Load Cesium runtime asset bundle
      const Cesium = await cesiumRuntime.load();

      this._showLoadingIndicator("CONFIGURING IMAGERY & 3D TERRAIN...");

      // 2. Resolve primary imagery provider via registry
      let baseLayer = undefined;
      try {
        const primaryImagery = await imageryProviderRegistry.create("arcgis_imagery");
        baseLayer = new Cesium.ImageryLayer(primaryImagery);
      } catch (imageryErr) {
        console.warn("[SpatialService] Primary imagery error, attempting OpenStreetMap:", imageryErr);
        try {
          const fallbackOsm = await imageryProviderRegistry.create("osm");
          baseLayer = new Cesium.ImageryLayer(fallbackOsm);
        } catch (_) {
          console.warn("[SpatialService] Running in procedural globe mode.");
        }
      }

      // 3. Create Cesium Viewer via ViewerFactory
      this.container.innerHTML = "";
      const viewer = ViewerFactory.create(this.container, {
        baseLayer: baseLayer || false,
        depthTestAgainstTerrain: false,
        enableLighting: false,
        fog: true,
        requestRenderMode: true
      });

      this.viewer = viewer;

      // 4. Attach subsystems to active viewer
      this.renderLoop.attachViewer(viewer);
      this.cameraController.attachViewer(viewer);
      this.sceneModeController.attachViewer(viewer);
      this.renderHealth.attachViewer(viewer);
      this.terrainManager.attachViewer(viewer);
      this.tilesetManager.attachViewer(viewer);
      this.imageryManager.attachViewer(viewer);

      // Attach legacy/bridge adapter and performance governor
      godsEyeAdapter.attachViewer(viewer);
      spatialPerformanceGovernor.attachViewer(viewer);

      // 5. Initialize Terrain (Ellipsoid baseline with automatic promotion if configured)
      await this.terrainManager.setTerrain("ellipsoid");

      this.isLoaded = true;
      this.lifecycleState = LIFECYCLE_STATES.READY;
      this._hideLoadingIndicator();

      spatialEventBus.emit("spatial.initialized", {
        version: Cesium.VERSION || "1.138.0",
        containerId: "spatialGlobeContainer",
        terrain: this.terrainManager.getState(),
        sceneMode: this.sceneModeController.getSceneMode()
      });

      console.log(`[SpatialService] Spatial Intelligence Engine Online (Cesium ${Cesium.VERSION || "1.138.0"}).`);

      // Initial frame render
      this.renderLoop.requestRender();

    } catch (err) {
      this.lifecycleState = LIFECYCLE_STATES.FAILED;
      this.lastError = err.message || String(err);
      console.error("[SpatialService] Initialization failed:", err);
      this._showLoadingIndicator(`INITIALIZATION ERROR: ${this.lastError}`, true);
      spatialEventBus.emit("spatial.init.failed", { error: this.lastError });
    }
  }

  // -------------------------------------------------------------
  // HUD TELEMETRY HELPERS
  // -------------------------------------------------------------
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

  _updateTerrainHud(label, color = "#00ffcc") {
    const el = document.getElementById("hudSpatialTerrainStatus");
    if (el) {
      el.textContent = label;
      el.style.color = color;
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
      meta.appendChild(makeRow("SOURCE:", (entity.provider || entity.source?.provider || "OPENSKY").toUpperCase()));
      meta.appendChild(makeRow("STATUS:", entity.status || "TRACKED", "#00ffcc"));

      if (Number.isFinite(entity.altitude_m)) {
        meta.appendChild(makeRow("ALTITUDE:", `${Math.round(entity.altitude_m).toLocaleString()} M`));
      }
      if (Number.isFinite(entity.speed_kts)) {
        meta.appendChild(makeRow("SPEED:", `${Math.round(entity.speed_kts)} KTS`));
      }
      if (entity.source?.observedAt) {
        meta.appendChild(makeRow("OBSERVED:", new Date(entity.source.observedAt).toLocaleTimeString()));
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

    this._busUnsubscribers.forEach((unsub) => {
      try { unsub(); } catch (_) {}
    });
    this._busUnsubscribers = [];

    this.renderLoop.destroy();
    this.cameraController.destroy();
    this.tilesetManager.destroy();
    this.imageryManager.destroy();

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

    if (this.container) {
      try { this.container.innerHTML = ""; } catch (_) {}
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

// Export modules to window for browser diagnostics and CLI access
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
  window.SpatialEntity = SpatialEntity;
  window.spatialLayerRegistry = spatialLayerRegistry;
  window.SpatialAnalytics = SpatialAnalytics;
  window.terrainProviderRegistry = terrainProviderRegistry;
  window.imageryProviderRegistry = imageryProviderRegistry;
}
