/**
 * J.A.R.V.I.S. Terrain Manager (frontend/spatial/terrain/terrainManager.js)
 * ==============================================================================
 * Manages the active terrain provider for the 3D globe. Guarantees graceful fallback
 * to Ellipsoid without pretending real terrain is loaded when it fails.
 */

import { terrainProviderRegistry } from "./terrainProviderRegistry.js";
import { TerrainAvailability } from "./terrainAvailability.js";

export const TERRAIN_STATUS = {
  UNLOADED: "unloaded",
  LOADING: "loading",
  ACTIVE: "active",
  DEGRADED: "degraded",
  FAILED: "failed"
};

export class TerrainManager {
  constructor(viewer, eventBus) {
    this.viewer = viewer;
    this.eventBus = eventBus;
    this.currentProviderName = "ellipsoid";
    this.status = TERRAIN_STATUS.UNLOADED;
    this.lastError = null;
    this.isTerrainActive = false;
  }

  attachViewer(viewer) {
    this.viewer = viewer;
  }

  async setTerrain(providerName, options = {}) {
    const name = String(providerName).toLowerCase();
    if (!this.viewer || !window.Cesium) {
      return { ok: false, error: "Cesium Viewer not initialized." };
    }

    this.status = TERRAIN_STATUS.LOADING;
    this.lastError = null;

    if (this.eventBus) {
      this.eventBus.emit("spatial.terrain.loading", { provider: name });
    }

    try {
      // 1. Check availability
      const avail = await TerrainAvailability.check(name, options.token);
      if (!avail.available) {
        console.warn(`[TerrainManager] Terrain provider '${name}' unavailable: ${avail.reason}`);
        // Fallback to ellipsoid
        await this._fallbackToEllipsoid(avail.reason);
        return {
          ok: false,
          status: TERRAIN_STATUS.DEGRADED,
          fallback: "ellipsoid",
          reason: avail.reason
        };
      }

      // 2. Create provider
      const provider = await terrainProviderRegistry.create(name, options);
      this.viewer.terrainProvider = provider;
      this.viewer.scene.globe.depthTestAgainstTerrain = name !== "ellipsoid";

      this.currentProviderName = name;
      this.isTerrainActive = name !== "ellipsoid";
      this.status = TERRAIN_STATUS.ACTIVE;

      if (this.viewer.scene) this.viewer.scene.requestRender();

      if (this.eventBus) {
        this.eventBus.emit("spatial.terrain.changed", {
          provider: name,
          isRealTerrain: this.isTerrainActive,
          status: this.status
        });
      }

      return {
        ok: true,
        provider: name,
        status: this.status,
        isRealTerrain: this.isTerrainActive
      };

    } catch (err) {
      this.lastError = err.message || String(err);
      console.error(`[TerrainManager] Failed to apply terrain '${name}':`, err);
      await this._fallbackToEllipsoid(`Error applying ${name}: ${this.lastError}`);

      return {
        ok: false,
        status: TERRAIN_STATUS.DEGRADED,
        fallback: "ellipsoid",
        error: this.lastError
      };
    }
  }

  async _fallbackToEllipsoid(reason) {
    if (!this.viewer || !window.Cesium) return;
    try {
      const ellipsoid = await terrainProviderRegistry.create("ellipsoid");
      this.viewer.terrainProvider = ellipsoid;
      this.viewer.scene.globe.depthTestAgainstTerrain = false;
      this.currentProviderName = "ellipsoid";
      this.isTerrainActive = false;
      this.status = TERRAIN_STATUS.DEGRADED;

      if (this.viewer.scene) this.viewer.scene.requestRender();

      if (this.eventBus) {
        this.eventBus.emit("spatial.terrain.degraded", {
          fallback: "ellipsoid",
          reason
        });
      }
    } catch (fallbackErr) {
      this.status = TERRAIN_STATUS.FAILED;
      console.error("[TerrainManager] Ellipsoid fallback failed:", fallbackErr);
    }
  }

  getState() {
    return {
      provider: this.currentProviderName,
      status: this.status,
      isRealTerrain: this.isTerrainActive,
      lastError: this.lastError
    };
  }
}
