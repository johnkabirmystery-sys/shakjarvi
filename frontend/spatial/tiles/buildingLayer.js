/**
 * J.A.R.V.I.S. 3D Building Layer (frontend/spatial/tiles/buildingLayer.js)
 * ==============================================================================
 * High-level building geometry layer providing photorealistic and 3D architectural
 * buildings. Verifies provider requirements and reports truthful status.
 */

export class BuildingLayer {
  constructor(tilesetManager, eventBus) {
    this.tilesetManager = tilesetManager;
    this.eventBus = eventBus;
    this.layerId = "buildings_3d";
    this.isEnabled = false;
    this.providerName = "osm_buildings";
  }

  /**
   * Enables 3D Buildings.
   */
  async enable(options = {}) {
    if (this.isEnabled && this.tilesetManager.has(this.layerId)) {
      this.tilesetManager.setVisible(this.layerId, true);
      return { ok: true, status: "enabled" };
    }

    if (!window.Cesium) {
      return { ok: false, error: "Cesium not loaded." };
    }

    const Cesium = window.Cesium;
    const token = options.token || Cesium.Ion?.defaultAccessToken || (typeof localStorage !== "undefined" ? localStorage.getItem("jarvis_cesium_ion_token") : "");

    const factory = async () => {
      if (typeof Cesium.createOsmBuildingsAsync === "function") {
        return await Cesium.createOsmBuildingsAsync(options);
      } else if (typeof Cesium.Cesium3DTileset?.fromIonAssetId === "function") {
        if (!token) {
          throw new Error("3D Buildings requires a configured Cesium Ion token or local 3D Tiles source.");
        }
        return await Cesium.Cesium3DTileset.fromIonAssetId(96188, options); // Cesium OSM Buildings Ion asset
      }
      throw new Error("Cesium 3D Tiles building factory not supported in this build.");
    };

    const res = await this.tilesetManager.load(this.layerId, factory, options);
    if (res.ok) {
      this.isEnabled = true;
      if (this.eventBus) {
        this.eventBus.emit("spatial.buildings.enabled", { id: this.layerId });
      }
    }
    return res;
  }

  disable() {
    if (!this.isEnabled) return { ok: true, status: "already_disabled" };
    this.tilesetManager.setVisible(this.layerId, false);
    this.isEnabled = false;
    if (this.eventBus) {
      this.eventBus.emit("spatial.buildings.disabled", { id: this.layerId });
    }
    return { ok: true, status: "disabled" };
  }

  toggle() {
    return this.isEnabled ? this.disable() : this.enable();
  }
}
