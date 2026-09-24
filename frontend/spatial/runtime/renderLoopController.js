/**
 * J.A.R.V.I.S. Render Loop Controller (frontend/spatial/runtime/renderLoopController.js)
 * =====================================================================================
 * Controls requestRenderMode, manual render requests, tab-switching throttling,
 * and frame-rate budgeting to prevent desktop GPU over-utilization.
 */

export class RenderLoopController {
  constructor(viewer) {
    this.viewer = viewer;
    this.isPaused = false;
    this.renderRequested = false;
    this._rafId = null;
    this._lastRenderTime = 0;
    this._minFrameIntervalMs = 16.6; // Target 60 FPS max
  }

  attachViewer(viewer) {
    this.viewer = viewer;
  }

  requestRender() {
    if (this.isPaused || !this.viewer || !this.viewer.scene) return;
    this.viewer.scene.requestRender();
  }

  pause() {
    this.isPaused = true;
    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
  }

  resume() {
    this.isPaused = false;
    this.requestRender();
  }

  setTargetFps(fps) {
    if (fps <= 0) return;
    this._minFrameIntervalMs = 1000.0 / fps;
  }

  destroy() {
    this.pause();
    this.viewer = null;
  }
}
