/**
 * J.A.R.V.I.S. Render Health Monitor (frontend/spatial/runtime/renderHealthMonitor.js)
 * ====================================================================================
 * Real-time monitoring of WebGL rendering health, shader errors, context loss,
 * canvas resolution, and measured frame statistics. Never reports simulated metrics.
 */

export class RenderHealthMonitor {
  constructor(viewer) {
    this.viewer = viewer;
    this.contextLost = false;
    this.lastRenderTime = 0;
    this.renderErrorCount = 0;
    this.lastRenderError = null;
    this._fps = null;
    this._frameTimes = [];
    this._maxSampleCount = 60;
  }

  attachViewer(viewer) {
    this.viewer = viewer;
    if (viewer?.canvas) {
      viewer.canvas.addEventListener("webglcontextlost", () => {
        this.contextLost = true;
      });
      viewer.canvas.addEventListener("webglcontextrestored", () => {
        this.contextLost = false;
      });
    }
  }

  recordFrame(deltaMs) {
    if (!Number.isFinite(deltaMs)) return;
    this._frameTimes.push(deltaMs);
    if (this._frameTimes.length > this._maxSampleCount) {
      this._frameTimes.shift();
    }
    const avgDelta = this._frameTimes.reduce((a, b) => a + b, 0) / this._frameTimes.length;
    this._fps = avgDelta > 0 ? Math.round(1000.0 / avgDelta) : null;
  }

  recordError(err) {
    this.renderErrorCount++;
    this.lastRenderError = err ? (err.message || String(err)) : "Render error";
  }

  getHealth() {
    const isReady = Boolean(this.viewer && !this.viewer.isDestroyed());
    const canvas = this.viewer?.canvas;

    return {
      status: this.contextLost ? "CONTEXT_LOST" : (this.renderErrorCount > 5 ? "DEGRADED" : (isReady ? "OPTIMAL" : "STANDBY")),
      isReady,
      contextLost: this.contextLost,
      fps: this._fps,
      canvasResolution: canvas ? { width: canvas.width, height: canvas.height } : null,
      devicePixelRatio: typeof window !== "undefined" ? window.devicePixelRatio : 1.0,
      renderErrorCount: this.renderErrorCount,
      lastError: this.lastRenderError
    };
  }
}
