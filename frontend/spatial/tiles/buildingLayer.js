/**
 * J.A.R.V.I.S. 3D Building Layer (frontend/spatial/tiles/buildingLayer.js)
 * ==============================================================================
 * High-level building geometry layer providing photorealistic and 3D architectural
 * buildings. Verifies provider requirements and reports truthful status.
 */

import { osmBuildingProvider } from '../data/osmBuildingProvider.js';

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
      return { ok: true, status: "enabled", provider: this.providerName };
    }

    if (!window.Cesium) {
      return { ok: false, error: "Cesium not loaded." };
    }

    const Cesium = window.Cesium;
    const token = options.token || Cesium.Ion?.defaultAccessToken || (typeof localStorage !== "undefined" ? localStorage.getItem("jarvis_cesium_ion_token") : "");

    // Strategy 1: Try Cesium Ion 3D Buildings (requires token)
    if (token) {
      const factory = async () => {
        if (typeof Cesium.createOsmBuildingsAsync === "function") {
          return await Cesium.createOsmBuildingsAsync(options);
        } else if (typeof Cesium.Cesium3DTileset?.fromIonAssetId === "function") {
          return await Cesium.Cesium3DTileset.fromIonAssetId(96188, options);
        }
        throw new Error("Cesium Ion 3D building factory not available.");
      };

      const res = await this.tilesetManager.load(this.layerId, factory, options);
      if (res.ok) {
        this.isEnabled = true;
        this.providerName = "cesium_ion_buildings";
        if (this.eventBus) {
          this.eventBus.emit("spatial.buildings.enabled", { id: this.layerId, provider: this.providerName });
        }
        return { ...res, provider: this.providerName };
      }
    }

    // Strategy 2: Free OSM Building Extrusion (no token needed)
    // This uses Overpass API to fetch building footprints and extrudes them locally
    console.log("[BuildingLayer] Ion token unavailable or failed. Attempting free OSM building provider...");
    try {
      if (window.spatialService?.cameraController) {
        const cam = window.spatialService.cameraController.getCameraState();
        if (cam && Number.isFinite(cam.latitude) && Number.isFinite(cam.longitude)) {
          const result = await osmBuildingProvider.loadBuildingsAround(
            cam.latitude, cam.longitude, options.radiusKm || 2, options
          );
          if (result.ok) {
            this.isEnabled = true;
            this.providerName = "osm_free_extrusion";
            if (this.eventBus) {
              this.eventBus.emit("spatial.buildings.enabled", {
                id: this.layerId, provider: this.providerName, source: "osm_overpass"
              });
            }
            return { ok: true, status: "enabled", provider: this.providerName, ...result };
          }
        }
      }
    } catch (osmErr) {
      console.warn("[BuildingLayer] Free OSM building fallback failed:", osmErr.message);
    }

    return {
      ok: false,
      error: "3D Buildings requires a Cesium Ion token or a reachable OSM Overpass service. Neither is currently available.",
      provider: "none"
    };
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

  getState() {
    return {
      isEnabled: this.isEnabled,
      layerId: this.layerId,
      provider: this.providerName,
      hasTileset: this.tilesetManager ? this.tilesetManager.has(this.layerId) : false
    };
  }
}
