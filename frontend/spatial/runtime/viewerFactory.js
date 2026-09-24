/**
 * J.A.R.V.I.S. Cesium Viewer Factory (frontend/spatial/runtime/viewerFactory.js)
 * ==============================================================================
 * Instantiates and configures Cesium.Viewer instances with explicit performance
 * settings, custom render options, and truthful fallback handling.
 */

export class ViewerFactory {
  /**
   * Builds and configures a new Cesium.Viewer instance.
   * @param {HTMLElement|string} container - DOM element or element ID.
   * @param {Object} options - Configuration overrides.
   * @returns {Cesium.Viewer} Configured Cesium Viewer instance.
   */
  static create(container, options = {}) {
    if (!window.Cesium) {
      throw new Error("ViewerFactory requires Cesium to be loaded in window.Cesium");
    }

    const Cesium = window.Cesium;
    const targetElement = typeof container === "string" ? document.getElementById(container) : container;

    if (!targetElement) {
      throw new Error(`Target container '${container}' was not found in the DOM.`);
    }

    const defaultViewerOptions = {
      baseLayer: options.baseLayer !== undefined ? options.baseLayer : false,
      terrainProvider: options.terrainProvider,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      infoBox: false,
      sceneModePicker: false, // We use our own customized Stark HUD scene mode selector
      selectionIndicator: false,
      timeline: false,
      navigationHelpButton: false,
      animation: false,
      shouldAnimate: options.shouldAnimate !== undefined ? options.shouldAnimate : true,
      requestRenderMode: options.requestRenderMode !== undefined ? options.requestRenderMode : true,
      maximumRenderTimeChange: Infinity,
      scene3DOnly: false // Allow 2D and Columbus View transitions
    };

    const viewerOptions = { ...defaultViewerOptions, ...options.cesiumOptions };

    const viewer = new Cesium.Viewer(targetElement, viewerOptions);

    // Optimize scene rendering settings
    const scene = viewer.scene;
    scene.globe.enableLighting = options.enableLighting || false;
    scene.fog.enabled = options.fog !== undefined ? options.fog : true;
    scene.fog.density = 0.00015;
    scene.globe.depthTestAgainstTerrain = options.depthTestAgainstTerrain || false;

    // Atmospheric bloom / visual post-processing if supported and requested
    if (scene.postProcessStages && options.bloom) {
      scene.postProcessStages.bloom.enabled = true;
      scene.postProcessStages.bloom.uniforms.contrast = 115;
      scene.postProcessStages.bloom.uniforms.brightness = -0.05;
    }

    // Attach WebGL context loss listener
    const canvas = viewer.canvas;
    if (canvas) {
      canvas.addEventListener("webglcontextlost", (e) => {
        console.error("[ViewerFactory] WebGL Context Lost! Preventing default to allow recovery:", e);
        e.preventDefault();
      }, false);

      canvas.addEventListener("webglcontextrestored", () => {
        console.warn("[ViewerFactory] WebGL Context Restored. Re-requesting render...");
        viewer.scene.requestRender();
      }, false);
    }

    return viewer;
  }
}
