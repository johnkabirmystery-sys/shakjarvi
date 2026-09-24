/**
 * J.A.R.V.I.S. Terrain Provider Registry (frontend/spatial/terrain/terrainProviderRegistry.js)
 * ==============================================================================================
 * Extensible registry for pluggable digital elevation models and 3D terrain providers.
 * Supports Cesium World Terrain, Quantized-Mesh tiles, ArcGIS elevation, and Ellipsoid baseline.
 */

export const terrainProviderRegistry = {
  providers: new Map(),

  register(name, factory, metadata = {}) {
    if (!name || typeof factory !== "function") {
      throw new Error("Invalid terrain provider registration: name and factory function required.");
    }
    this.providers.set(name.toLowerCase(), {
      factory,
      metadata: {
        requiresToken: false,
        attribution: "Unknown",
        ...metadata
      }
    });
  },

  has(name) {
    return this.providers.has(String(name).toLowerCase());
  },

  async create(name, options = {}) {
    const key = String(name).toLowerCase();
    const entry = this.providers.get(key);
    if (!entry) {
      throw new Error(`Terrain provider '${name}' is not registered. Available: ${this.list().map(p => p.name).join(", ")}`);
    }
    return entry.factory(options);
  },

  getMetadata(name) {
    const entry = this.providers.get(String(name).toLowerCase());
    return entry ? entry.metadata : null;
  },

  list() {
    return Array.from(this.providers.entries()).map(([name, entry]) => ({
      name,
      ...entry.metadata
    }));
  }
};

// Register default providers
terrainProviderRegistry.register("ellipsoid", (options = {}) => {
  if (!window.Cesium) throw new Error("Cesium is not loaded.");
  return new window.Cesium.EllipsoidTerrainProvider(options);
}, {
  title: "WGS84 Ellipsoid (Smooth Flat Globe)",
  requiresToken: false,
  isDefault: true,
  attribution: "WGS84 Standard Ellipsoid"
});

terrainProviderRegistry.register("world_terrain", async (options = {}) => {
  if (!window.Cesium) throw new Error("Cesium is not loaded.");
  const Cesium = window.Cesium;
  if (typeof Cesium.createWorldTerrainAsync === "function") {
    return await Cesium.createWorldTerrainAsync({
      requestVertexNormals: options.requestVertexNormals !== undefined ? options.requestVertexNormals : true,
      requestWaterMask: options.requestWaterMask !== undefined ? options.requestWaterMask : true
    });
  } else if (typeof Cesium.CesiumTerrainProvider?.fromIonAssetId === "function") {
    return await Cesium.CesiumTerrainProvider.fromIonAssetId(1, options);
  }
  throw new Error("Cesium World Terrain factory function is not available in current Cesium build.");
}, {
  title: "Cesium World Terrain (High Resolution 3D Mesh)",
  requiresToken: true,
  attribution: "Cesium Ion & OpenStreetMap Contributors"
});

terrainProviderRegistry.register("arcgis_elevation", async (options = {}) => {
  if (!window.Cesium) throw new Error("Cesium is not loaded.");
  const Cesium = window.Cesium;
  if (typeof Cesium.ArcGISTiledElevationTerrainProvider?.fromUrl === "function") {
    const url = options.url || "https://elevation3d.arcgis.com/arcgis/rest/services/WorldElevation3D/Terrain3D/ImageServer";
    return await Cesium.ArcGISTiledElevationTerrainProvider.fromUrl(url, options);
  }
  throw new Error("ArcGIS Tiled Elevation Terrain Provider is not supported in this Cesium build.");
}, {
  title: "ArcGIS World Elevation 3D",
  requiresToken: false,
  attribution: "Esri, USGS, NOAA"
});
