/**
 * J.A.R.V.I.S. Spatial Diagnostics (frontend/spatial/spatialDiagnostics.js)
 * =========================================================================
 * Telemetry and diagnostics tracker for rendering, viewer, memory, and feeds.
 */

import { spatialEventBus } from "./spatialEventBus.js";
import { spatialState } from "./spatialState.js";
import { spatialPerformanceGovernor } from "./spatialPerformanceGovernor.js";
import { networkBudgetManager } from "./networkBudgetManager.js";

class SpatialDiagnostics {
  constructor() {
    this.startupTime = Date.now();
    this.readyTime = null;
    this.firstRenderTime = null;
    this.totalCommandsExecuted = 0;
    this.lastCommandLatencyMs = 0;

    spatialEventBus.on("spatial.ready", () => {
      this.readyTime = Date.now();
    });

    spatialEventBus.on("spatial.command.completed", (payload) => {
      this.totalCommandsExecuted++;
      this.lastCommandLatencyMs = payload.diagnostics?.elapsedMs || 0;
    });
  }

  getReport() {
    const memory = performance?.memory ? {
      usedJsHeapMb: Math.round(performance.memory.usedJSHeapSize / 1048576),
      totalJsHeapMb: Math.round(performance.memory.totalJSHeapSize / 1048576)
    } : { usedJsHeapMb: "N/A", totalJsHeapMb: "N/A" };

    return {
      uptimeSeconds: Math.round((Date.now() - this.startupTime) / 1000),
      fps: spatialPerformanceGovernor.fps,
      profile: spatialPerformanceGovernor.currentProfile,
      effectiveDPR: spatialPerformanceGovernor.effectiveDPR,
      networkProfile: networkBudgetManager.networkProfile,
      memory,
      totalCommands: this.totalCommandsExecuted,
      lastLatencyMs: this.lastCommandLatencyMs,
      hardware: spatialPerformanceGovernor.hardwareProfile,
      activeLayers: Object.keys(spatialState.getState().layers).filter(k => spatialState.getState().layers[k])
    };
  }
}

export const spatialDiagnostics = new SpatialDiagnostics();
if (typeof window !== "undefined") {
  window.__jarvisSpatialDiagnostics = spatialDiagnostics;
}
