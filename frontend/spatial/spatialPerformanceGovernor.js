/**
 * J.A.R.V.I.S. Spatial Performance Governor (frontend/spatial/spatialPerformanceGovernor.js)
 * =========================================================================================
 * Continuous adaptive governor for AMD Ryzen 7 7840HS (16 GB DDR5).
 * - Dynamic DPR & distance-aware LOD management.
 * - Hysteresis mode switching (prevents rapid oscillation).
 * - Background tab throttling (pauses render loops when hidden).
 */

import { spatialEventBus } from "./spatialEventBus.js";
import { spatialState } from "./spatialState.js";

export const PROFILES = {
  ULTRA: { dprMax: 1.5, maxEntities: 15000, postProcessing: true, modelDetail: "high", pollIntervalMs: 5000 },
  HIGH: { dprMax: 1.25, maxEntities: 8000, postProcessing: true, modelDetail: "high", pollIntervalMs: 8000 },
  BALANCED: { dprMax: 1.0, maxEntities: 4000, postProcessing: true, modelDetail: "medium", pollIntervalMs: 10000 },
  PERFORMANCE: { dprMax: 0.85, maxEntities: 1500, postProcessing: false, modelDetail: "low", pollIntervalMs: 15000 },
  SAFE_MODE: { dprMax: 0.75, maxEntities: 500, postProcessing: false, modelDetail: "lowest", pollIntervalMs: 30000 }
};

class SpatialPerformanceGovernor {
  constructor() {
    this.hardwareProfile = this._detectHardware();
    this.currentProfile = "BALANCED";
    this.effectiveDPR = 1.0;
    this.fpsHistory = [];
    this.lowFpsDurationSec = 0;
    this.highFpsDurationSec = 0;
    this.isTabVisible = true;
    this.isThrottled = false;
    this.rafId = null;
    this.lastFrameTime = performance.now();
    this.fps = 60;

    this._initVisibilityListener();
    this._startGovernorLoop();
  }

  _detectHardware() {
    const cores = navigator.hardwareConcurrency || 8;
    const memoryGb = navigator.deviceMemory || 16;
    let gpuRenderer = "Unknown";
    let isHardwareGpu = true;

    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
      if (gl) {
        const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
        if (debugInfo) {
          gpuRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
          if (/swiftshader|software|llvmpipe/i.test(gpuRenderer)) {
            isHardwareGpu = false;
          }
        }
      }
    } catch (e) {}

    return {
      cores,
      memoryGb,
      gpuRenderer,
      isHardwareGpu,
      devicePixelRatio: window.devicePixelRatio || 1.0
    };
  }

  _initVisibilityListener() {
    document.addEventListener("visibilitychange", () => {
      this.isTabVisible = !document.hidden;
      if (!this.isTabVisible) {
        this.isThrottled = true;
        spatialEventBus.emit("spatial.performance.throttled", { reason: "tab_hidden" });
      } else {
        this.isThrottled = false;
        spatialEventBus.emit("spatial.performance.restored", { profile: this.currentProfile });
      }
    });
  }

  _startGovernorLoop() {
    let frameCount = 0;
    let lastSecond = performance.now();

    const tick = (now) => {
      frameCount++;
      const delta = now - lastSecond;

      if (delta >= 1000) {
        this.fps = Math.round((frameCount * 1000) / delta);
        frameCount = 0;
        lastSecond = now;
        this._evaluateHysteresis(this.fps);
      }

      this.rafId = requestAnimationFrame(tick);
    };

    this.rafId = requestAnimationFrame(tick);
  }

  _evaluateHysteresis(currentFps) {
    if (!this.isTabVisible) return;

    // Hysteresis rules
    if (currentFps < 28) {
      this.lowFpsDurationSec += 1;
      this.highFpsDurationSec = 0;
      if (this.lowFpsDurationSec >= 3 && this.currentProfile !== "PERFORMANCE") {
        this.setProfile("PERFORMANCE");
      }
    } else if (currentFps > 45) {
      this.highFpsDurationSec += 1;
      this.lowFpsDurationSec = 0;
      if (this.highFpsDurationSec >= 8 && this.currentProfile === "PERFORMANCE") {
        this.setProfile("BALANCED");
      }
    } else {
      this.lowFpsDurationSec = 0;
      this.highFpsDurationSec = 0;
    }

    spatialState.updateDiagnostics({
      fps: this.fps,
      performanceMode: this.currentProfile,
      effectiveDPR: this.effectiveDPR
    });
  }

  setProfile(profileKey) {
    if (!PROFILES[profileKey]) return;
    this.currentProfile = profileKey;
    const cfg = PROFILES[profileKey];
    this.effectiveDPR = Math.min(window.devicePixelRatio || 1.0, cfg.dprMax);

    spatialEventBus.emit("spatial.profile.changed", {
      profile: profileKey,
      config: cfg,
      effectiveDPR: this.effectiveDPR
    });
    console.log(`[SpatialGovernor] Active profile transitioned to: ${profileKey} (DPR: ${this.effectiveDPR})`);
  }

  getBudget() {
    return PROFILES[this.currentProfile];
  }
}

export const spatialPerformanceGovernor = new SpatialPerformanceGovernor();
if (typeof window !== "undefined") {
  window.__jarvisSpatialGovernor = spatialPerformanceGovernor;
}
