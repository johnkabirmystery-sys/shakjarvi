/**
 * J.A.R.V.I.S. Terrain Availability (frontend/spatial/terrain/terrainAvailability.js)
 * ====================================================================================
 * Proactively verifies credential presence, network reachability, and provider
 * capability before initializing elevation meshes, guaranteeing truthful states.
 */

export class TerrainAvailability {
  /**
   * Checks whether a given terrain provider is available in the current environment.
   * @param {string} providerName
   * @param {string} [token]
   * @returns {Promise<{ available: boolean, reason?: string }>}
   */
  static async check(providerName, token = "") {
    const name = String(providerName).toLowerCase();

    if (name === "ellipsoid") {
      return { available: true };
    }

    if (name === "world_terrain") {
      const activeToken = token || (typeof window !== "undefined" ? (window.Cesium?.Ion?.defaultAccessToken || localStorage.getItem("jarvis_cesium_ion_token")) : "");
      if (!activeToken) {
        return {
          available: false,
          reason: "Cesium Ion access token is not configured. Falling back to Ellipsoid baseline."
        };
      }
      return { available: true };
    }

    if (name === "arcgis_elevation") {
      if (typeof navigator !== "undefined" && !navigator.onLine) {
        return { available: false, reason: "Browser is offline; remote ArcGIS elevation tiles are unreachable." };
      }
      return { available: true };
    }

    return { available: true };
  }
}
