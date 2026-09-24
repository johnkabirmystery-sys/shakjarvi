/**
 * J.A.R.V.I.S. Spatial Performance Governor (frontend/spatial/spatialPerformanceGovernor.js)
 * =========================================================================================
 * Continuous adaptive governor for desktop GPU rendering.
 * - Dynamic DPR & distance-aware LOD management.
 * - Real FPS and frame-time calculation from actual render ticks.
 * - Hysteresis mode switching (prevents rapid oscillation).
 * - Background tab & inactive workspace throttling.
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
    this.viewer = null;
    this.hardwareProfile = this._detectHardware();
    this.currentProfile = "BALANCED";
    this.effectiveDPR = 1.0;
    this.fps = null; // null until measured
    this.frameTimeMs = null;
    this.lowFpsDurationSec = 0;
    this.highFpsDurationSec = 0;
    this.isTabVisible = true;
    this.isPaused = false;
    this.rafId = null;
    this._frameCount = 0;
    this._lastSecond = performance.now();
    this._lastFrameTime = performance.now();

    this._initVisibilityListener();
    this._startGovernorLoop();
  }

  attachViewer(viewer) {
    this.viewer = viewer;
    if (this.viewer && this.viewer.resolutionScale !== undefined) {
      this.viewer.resolutionScale = this.effectiveDPR;
    }
  }

  _detectHardware() {
    const cores = typeof navigator !== "undefined" ? (navigator.hardwareConcurrency || 8) : 8;
    const memoryGb = typeof navigator !== "undefined" ? (navigator.deviceMemory || 16) : 16;
    let gpuRenderer = "Unknown";
    let isHardwareGpu = true;

    if (typeof document !== "undefined") {
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
      } catch (_) {}
    }

    return {
      cores,
      memoryGb,
      gpuRenderer,
      isHardwareGpu,
      devicePixelRatio: typeof window !== "undefined" ? (window.devicePixelRatio || 1.0) : 1.0
    };
  }

  _initVisibilityListener() {
    if (typeof document === "undefined") return;

    document.addEventListener("visibilitychange", () => {
      this.isTabVisible = !document.hidden;
      if (!this.isTabVisible) {
        this.pause();
        spatialEventBus.emit("spatial.performance.throttled", { reason: "tab_hidden" });
      } else {
        this.resume();
        spatialEventBus.emit("spatial.performance.restored", { profile: this.currentProfile });
      }
    });
  }

  _startGovernorLoop() {
    if (typeof requestAnimationFrame === "undefined") return;

    const tick = (now) => {
      if (!this.isPaused && this.isTabVisible) {
        this._frameCount++;
        const frameDelta = now - this._lastFrameTime;
        this._lastFrameTime = now;
        this.frameTimeMs = Math.round(frameDelta * 10) / 10;

        const secondDelta = now - this._lastSecond;
        if (secondDelta >= 1000) {
          this.fps = Math.round((this._frameCount * 1000) / secondDelta);
          this._frameCount = 0;
          this._lastSecond = now;
          this._evaluateHysteresis(this.fps);
        }
      }

      this.rafId = requestAnimationFrame(tick);
    };

    this.rafId = requestAnimationFrame(tick);
  }

  _evaluateHysteresis(currentFps) {
    if (!this.isTabVisible || this.isPaused || currentFps === null) return;

    if (currentFps < 28) {
      this.lowFpsDurationSec += 1;
      this.highFpsDurationSec = 0;
      if (this.lowFpsDurationSec >= 3 && this.currentProfile !== "PERFORMANCE") {
        this.setProfile("PERFORMANCE");
      }
    } else if (currentFps > 52) {
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
      frameTimeMs: this.frameTimeMs,
      performanceMode: this.currentProfile,
      effectiveDPR: this.effectiveDPR
    });

    const govPill = document.getElementById("hudSpatialGovernor");
    if (govPill) {
      govPill.textContent = `${this.currentProfile} · ${this.fps !== null ? this.fps + " FPS" : "CALIBRATING"}`;
    }
  }

  setProfile(profileKey) {
    if (!PROFILES[profileKey]) return;
    this.currentProfile = profileKey;
    const cfg = PROFILES[profileKey];
    this.effectiveDPR = Math.min(window.devicePixelRatio || 1.0, cfg.dprMax);

    if (this.viewer && this.viewer.resolutionScale !== undefined) {
      this.viewer.resolutionScale = this.effectiveDPR;
      if (this.viewer.scene) this.viewer.scene.requestRender();
    }

    spatialEventBus.emit("spatial.profile.changed", {
      profile: profileKey,
      config: cfg,
      effectiveDPR: this.effectiveDPR
    });
    console.log(`[SpatialGovernor] Active profile: ${profileKey} (DPR: ${this.effectiveDPR})`);
  }

  pause() {
    this.isPaused = true;
  }

  resume() {
    this.isPaused = false;
    this._lastSecond = performance.now();
    this._lastFrameTime = performance.now();
    this._frameCount = 0;
  }

  getBudget() {
    return PROFILES[this.currentProfile];
  }
}

export const spatialPerformanceGovernor = new SpatialPerformanceGovernor();
if (typeof window !== "undefined") {
  window.__jarvisSpatialPerformanceGovernor = spatialPerformanceGovernor;
}
