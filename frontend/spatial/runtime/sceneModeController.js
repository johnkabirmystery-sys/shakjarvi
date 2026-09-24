/**
 * J.A.R.V.I.S. Scene Mode Controller (frontend/spatial/runtime/sceneModeController.js)
 * ====================================================================================
 * Controls transitions between 3D Globe, 2D Map, and Columbus View with explicit
 * state queries from the actual Cesium Scene.
 */

export const SCENE_MODES = {
  SCENE3D: "3D",
  SCENE2D: "2D",
  COLUMBUS_VIEW: "COLUMBUS_VIEW"
};

export class SceneModeController {
  constructor(viewer) {
    this.viewer = viewer;
  }

  attachViewer(viewer) {
    this.viewer = viewer;
  }

  /**
   * Sets scene mode.
   * @param {"3D"|"2D"|"COLUMBUS_VIEW"} mode
   * @param {number} duration - Transition duration in seconds.
   */
  async setSceneMode(mode, duration = 1.5) {
    if (!this.viewer || !this.viewer.scene || !window.Cesium) {
      return { ok: false, error: "Cesium Viewer not initialized." };
    }

    const Cesium = window.Cesium;
    const scene = this.viewer.scene;
    const targetMode = String(mode).toUpperCase().trim();

    try {
      if (targetMode === "3D" || targetMode === "SCENE3D") {
        if (scene.mode === Cesium.SceneMode.SCENE3D) {
          return { ok: true, status: "already_in_mode", mode: "3D" };
        }
        scene.morphTo3D(duration);
      } else if (targetMode === "2D" || targetMode === "SCENE2D") {
        if (scene.mode === Cesium.SceneMode.SCENE2D) {
          return { ok: true, status: "already_in_mode", mode: "2D" };
        }
        scene.morphTo2D(duration);
      } else if (targetMode === "COLUMBUS_VIEW" || targetMode === "CV") {
        if (scene.mode === Cesium.SceneMode.COLUMBUS_VIEW) {
          return { ok: true, status: "already_in_mode", mode: "COLUMBUS_VIEW" };
        }
        scene.morphToColumbusView(duration);
      } else {
        return {
          ok: false,
          error: `Unsupported scene mode '${mode}'. Supported: 3D, 2D, COLUMBUS_VIEW.`
        };
      }

      if (scene) scene.requestRender();

      return {
        ok: true,
        status: "transitioning",
        targetMode,
        duration
      };
    } catch (err) {
      return { ok: false, error: err.message || String(err) };
    }
  }

  /**
   * Returns current ground-truth scene mode from Cesium scene.
   */
  getSceneMode() {
    if (!this.viewer?.scene || !window.Cesium) return "UNKNOWN";
    const Cesium = window.Cesium;
    const mode = this.viewer.scene.mode;
    if (mode === Cesium.SceneMode.SCENE3D) return "3D";
    if (mode === Cesium.SceneMode.SCENE2D) return "2D";
    if (mode === Cesium.SceneMode.COLUMBUS_VIEW) return "COLUMBUS_VIEW";
    if (mode === Cesium.SceneMode.MORPHING) return "TRANSITIONING";
    return "UNKNOWN";
  }
}
