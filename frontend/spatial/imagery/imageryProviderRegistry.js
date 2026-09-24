/**
 * J.A.R.V.I.S. Imagery Provider Registry (frontend/spatial/imagery/imageryProviderRegistry.js)
 * ==============================================================================================
 * Extensible registry of global satellite imagery, aerial photography, and street basemaps.
 * Provides ArcGIS World Imagery, OpenStreetMap, CartoDB Dark Matter, NASA GIBS, and offline tiles.
 */

export const imageryProviderRegistry = {
  providers: new Map(),

  register(name, factory, metadata = {}) {
    if (!name || typeof factory !== "function") {
      throw new Error("Invalid imagery provider registration: name and factory function required.");
    }
    this.providers.set(name.toLowerCase(), {
      factory,
      metadata: {
        attribution: "Unknown",
        requiresToken: false,
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
      throw new Error(`Imagery provider '${name}' is not registered. Available: ${this.list().map(p => p.name).join(", ")}`);
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

// 1. ArcGIS World Imagery (Primary Satellite)
imageryProviderRegistry.register("arcgis_imagery", async (options = {}) => {
  if (!window.Cesium) throw new Error("Cesium not loaded.");
  const Cesium = window.Cesium;
  if (typeof Cesium.ArcGisMapServerImageryProvider?.fromUrl === "function") {
    return await Cesium.ArcGisMapServerImageryProvider.fromUrl(
      options.url || "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer",
      options
    );
  }
  return new Cesium.ArcGisMapServerImageryProvider({
    url: options.url || "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer"
  });
}, {
  title: "ArcGIS World Imagery (High-Res Satellite)",
  attribution: "Esri, Maxar, Earthstar Geographics",
  isDefault: true
});

// 2. OpenStreetMap (Global Street Map)
imageryProviderRegistry.register("osm", (options = {}) => {
  if (!window.Cesium) throw new Error("Cesium not loaded.");
  const Cesium = window.Cesium;
  if (typeof Cesium.OpenStreetMapImageryProvider === "function") {
    return new Cesium.OpenStreetMapImageryProvider({
      url: "https://tile.openstreetmap.org/",
      ...options
    });
  }
  return new Cesium.UrlTemplateImageryProvider({
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    subdomains: ["a", "b", "c"],
    ...options
  });
}, {
  title: "OpenStreetMap (Global Cartography)",
  attribution: "© OpenStreetMap contributors"
});

// 3. CartoDB Dark Matter (Tactical Night Mode)
imageryProviderRegistry.register("cartodb_dark", (options = {}) => {
  if (!window.Cesium) throw new Error("Cesium not loaded.");
  const Cesium = window.Cesium;
  return new Cesium.UrlTemplateImageryProvider({
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
    subdomains: ["a", "b", "c", "d"],
    ...options
  });
}, {
  title: "CartoDB Dark Matter (Tactical Cyber Basemap)",
  attribution: "© CARTO, © OpenStreetMap contributors"
});

// 4. NASA GIBS (Blue Marble / VIIRS)
imageryProviderRegistry.register("nasa_gibs", (options = {}) => {
  if (!window.Cesium) throw new Error("Cesium not loaded.");
  const Cesium = window.Cesium;
  return new Cesium.WebMapTileServiceImageryProvider({
    url: "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/wmts.cgi",
    layer: "VIIRS_SNPP_CorrectedReflectance_TrueColor",
    style: "default",
    format: "image/jpeg",
    tileMatrixSetID: "250m",
    maximumLevel: 8,
    ...options
  });
}, {
  title: "NASA GIBS Satellite Composite",
  attribution: "NASA Global Imagery Browse Services (GIBS)"
});
