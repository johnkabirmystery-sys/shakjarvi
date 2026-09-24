/**
 * J.A.R.V.I.S. Imagery Layer Manager (frontend/spatial/imagery/imageryLayerManager.js)
 * ====================================================================================
 * Coordinates imagery layers on the Cesium globe, handles basemap switching, layer
 * opacity, and fallback when network tiles are unreachable.
 */

import { imageryProviderRegistry } from "./imageryProviderRegistry.js";

export class ImageryLayerManager {
  constructor(viewer, eventBus) {
    this.viewer = viewer;
    this.eventBus = eventBus;
    this.currentBasemap = "arcgis_imagery";
    this.overlayLayers = new Map(); // id -> Cesium.ImageryLayer
  }

  attachViewer(viewer) {
    this.viewer = viewer;
  }

  /**
   * Sets or switches the base imagery layer.
   * @param {string} providerName - Name registered in imageryProviderRegistry.
   * @param {Object} [options]
   */
  async setBasemap(providerName, options = {}) {
    if (!this.viewer || !window.Cesium) {
      return { ok: false, error: "Cesium Viewer not initialized." };
    }

    const name = String(providerName).toLowerCase();
    try {
      const provider = await imageryProviderRegistry.create(name, options);
      const layers = this.viewer.imageryLayers;

      // Remove current basemap (index 0) or add
      if (layers.length > 0) {
        layers.remove(layers.get(0));
      }

      const newBaseLayer = layers.addImageryProvider(provider, 0);
      this.currentBasemap = name;

      if (this.viewer.scene) this.viewer.scene.requestRender();

      if (this.eventBus) {
        this.eventBus.emit("spatial.imagery.basemap_changed", {
          basemap: name,
          attribution: imageryProviderRegistry.getMetadata(name)?.attribution
        });
      }

      return { ok: true, basemap: name, layer: newBaseLayer };
    } catch (err) {
      console.error(`[ImageryLayerManager] Failed to set basemap '${name}':`, err);
      return { ok: false, error: err.message || String(err) };
    }
  }

  /**
   * Adds an overlay imagery layer (e.g. weather radar, labels).
   */
  async addOverlayLayer(id, providerName, options = {}) {
    if (!this.viewer) return { ok: false, error: "Viewer unavailable." };
    if (this.overlayLayers.has(id)) {
      return { ok: true, id, status: "already_added" };
    }

    try {
      const provider = await imageryProviderRegistry.create(providerName, options);
      const layer = this.viewer.imageryLayers.addImageryProvider(provider);
      if (Number.isFinite(options.alpha)) {
        layer.alpha = options.alpha;
      }
      this.overlayLayers.set(id, layer);
      if (this.viewer.scene) this.viewer.scene.requestRender();
      return { ok: true, id, status: "added" };
    } catch (err) {
      return { ok: false, id, error: err.message || String(err) };
    }
  }

  removeOverlayLayer(id) {
    if (!this.viewer || !this.overlayLayers.has(id)) {
      return { ok: false, error: `Overlay layer '${id}' not found.` };
    }
    const layer = this.overlayLayers.get(id);
    this.viewer.imageryLayers.remove(layer);
    this.overlayLayers.delete(id);
    if (this.viewer.scene) this.viewer.scene.requestRender();
    return { ok: true, id, status: "removed" };
  }

  destroy() {
    this.overlayLayers.clear();
    this.viewer = null;
  }
}
