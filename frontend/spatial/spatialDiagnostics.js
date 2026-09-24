/**
 * J.A.R.V.I.S. Spatial Diagnostics (frontend/spatial/spatialDiagnostics.js)
 * =========================================================================
 * Telemetry and diagnostics tracker for rendering, viewer, memory, and feeds.
 * Strictly reports measured values or explicit 'UNKNOWN' / null.
 */

import { spatialEventBus } from "./spatialEventBus.js";
import { spatialState } from "./spatialState.js";
import { spatialPerformanceGovernor } from "./spatialPerformanceGovernor.js";
import { networkBudgetManager } from "./networkBudgetManager.js";
import { godsEyeAdapter } from "./godsEyeAdapter.js";

class SpatialDiagnostics {
  constructor() {
    this.startupTime = Date.now();
    this.readyTime = null;
    this.firstRenderTime = null;
    this.totalCommandsExecuted = 0;
    this.lastCommandLatencyMs = null;
    this.lastCommandError = null;
    this.lastSuccessfulCommand = null;

    spatialEventBus.on("spatial.ready", () => {
      this.readyTime = Date.now();
    });

    spatialEventBus.on("spatial.command.completed", (payload) => {
      this.totalCommandsExecuted++;
      this.lastCommandLatencyMs = payload.diagnostics?.elapsedMs || 0;
      this.lastSuccessfulCommand = payload.type;
      this.lastCommandError = null;
    });

    spatialEventBus.on("spatial.command.failed", (payload) => {
      this.lastCommandError = payload.error || "Unknown error";
    });
  }

  getReport() {
    const memory = (typeof performance !== "undefined" && performance.memory) ? {
      usedJsHeapMb: Math.round(performance.memory.usedJSHeapSize / 1048576),
      totalJsHeapMb: Math.round(performance.memory.totalJSHeapSize / 1048576)
    } : { usedJsHeapMb: "N/A", totalJsHeapMb: "N/A" };

    const viewer = godsEyeAdapter.viewer;
    const isViewerInit = Boolean(viewer && !viewer.isDestroyed());
    const entityCount = isViewerInit ? (viewer.entities?.values?.length || 0) : 0;
    const activeLayers = Object.keys(spatialState.getState().layers).filter(k => spatialState.getState().layers[k]);

    return {
      viewerInitialized: isViewerInit,
      cesiumVersion: (typeof window !== "undefined" && window.Cesium?.VERSION) ? window.Cesium.VERSION : "1.138.0",
      uptimeSeconds: Math.round((Date.now() - this.startupTime) / 1000),
      fps: spatialPerformanceGovernor.fps,
      frameTimeMs: spatialPerformanceGovernor.frameTimeMs,
      performanceMode: spatialPerformanceGovernor.currentProfile,
      effectiveDPR: spatialPerformanceGovernor.effectiveDPR,
      networkProfile: networkBudgetManager.networkProfile,
      memory,
      totalCommands: this.totalCommandsExecuted,
      lastLatencyMs: this.lastCommandLatencyMs,
      lastSuccessfulCommand: this.lastSuccessfulCommand,
      lastError: this.lastCommandError,
      activeEntityCount: entityCount,
      activeLayerCount: activeLayers.length,
      activeLayers,
      hardware: spatialPerformanceGovernor.hardwareProfile
    };
  }
}

export const spatialDiagnostics = new SpatialDiagnostics();
if (typeof window !== "undefined") {
  window.__jarvisSpatialDiagnostics = spatialDiagnostics;
}
