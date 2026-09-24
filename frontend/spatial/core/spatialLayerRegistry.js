/**
 * J.A.R.V.I.S. Spatial Layer Registry (frontend/spatial/core/spatialLayerRegistry.js)
 * ====================================================================================
 * Modular registry coordinating geospatial layer lifecycles, states, and authorizations.
 * Categories: aviation, maritime, natural_events, infrastructure, routes_geofences.
 */

export const LAYER_CATEGORIES = {
  AVIATION: "aviation",
  MARITIME: "maritime",
  NATURAL_EVENTS: "natural_events",
  INFRASTRUCTURE: "infrastructure",
  ROUTES_GEOFENCES: "routes_geofences"
};

export const LAYER_STATUS = {
  UNLOADED: "unloaded",
  LOADING: "loading",
  ACTIVE: "active",
  DEGRADED: "degraded",
  FAILED: "failed",
  DISABLED: "disabled"
};

export class SpatialLayerRegistry {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.layers = new Map();
  }

  /**
   * Registers a layer definition.
   */
  register(layerDef) {
    if (!layerDef || !layerDef.id) {
      throw new Error("Invalid layer definition: 'id' property is required.");
    }
    const id = String(layerDef.id).toLowerCase();
    this.layers.set(id, {
      id,
      name: layerDef.name || id,
      category: layerDef.category || LAYER_CATEGORIES.INFRASTRUCTURE,
      enabled: Boolean(layerDef.enabled),
      status: layerDef.enabled ? LAYER_STATUS.ACTIVE : LAYER_STATUS.UNLOADED,
      attribution: layerDef.attribution || "Public feed",
      isSensitive: Boolean(layerDef.isSensitive),
      create: typeof layerDef.create === "function" ? layerDef.create : null,
      destroy: typeof layerDef.destroy === "function" ? layerDef.destroy : null,
      ...layerDef
    });
  }

  get(id) {
    return this.layers.get(String(id).toLowerCase());
  }

  has(id) {
    return this.layers.has(String(id).toLowerCase());
  }

  enable(id) {
    const layer = this.get(id);
    if (!layer) {
      return { ok: false, error: `Layer '${id}' is not registered.` };
    }
    if (layer.isSensitive && !layer.isAuthorized) {
      return { ok: false, error: `Layer '${id}' requires explicit user authorization.` };
    }

    layer.enabled = true;
    layer.status = LAYER_STATUS.ACTIVE;

    if (this.eventBus) {
      this.eventBus.emit("spatial.layer.enabled", { id, layer });
    }
    return { ok: true, id, status: layer.status };
  }

  disable(id) {
    const layer = this.get(id);
    if (!layer) {
      return { ok: false, error: `Layer '${id}' is not registered.` };
    }

    layer.enabled = false;
    layer.status = LAYER_STATUS.DISABLED;

    if (this.eventBus) {
      this.eventBus.emit("spatial.layer.disabled", { id, layer });
    }
    return { ok: true, id, status: layer.status };
  }

  toggle(id) {
    const layer = this.get(id);
    if (!layer) return { ok: false, error: `Layer '${id}' is not registered.` };
    return layer.enabled ? this.disable(id) : this.enable(id);
  }

  list() {
    return Array.from(this.layers.values()).map(l => ({
      id: l.id,
      name: l.name,
      category: l.category,
      enabled: l.enabled,
      status: l.status,
      attribution: l.attribution,
      isSensitive: l.isSensitive
    }));
  }
}

export const spatialLayerRegistry = new SpatialLayerRegistry();

// Pre-register standard public layers
spatialLayerRegistry.register({
  id: "flights",
  name: "Commercial & Civil Aviation",
  category: LAYER_CATEGORIES.AVIATION,
  enabled: true,
  attribution: "OpenSky Network (Public ADS-B)"
});

spatialLayerRegistry.register({
  id: "vessels",
  name: "Maritime AIS Navigation",
  category: LAYER_CATEGORIES.MARITIME,
  enabled: false,
  attribution: "Public Marine AIS Feeds"
});

spatialLayerRegistry.register({
  id: "satellites",
  name: "Orbital Satellites & TLEs",
  category: LAYER_CATEGORIES.AVIATION,
  enabled: false,
  attribution: "CelesTrak Orbital Elements"
});

spatialLayerRegistry.register({
  id: "weather",
  name: "Global Weather & Wind Dynamics",
  category: LAYER_CATEGORIES.NATURAL_EVENTS,
  enabled: true,
  attribution: "NOAA GFS / RainViewer"
});

spatialLayerRegistry.register({
  id: "firms",
  name: "Thermal Anomalies & Wildfires",
  category: LAYER_CATEGORIES.NATURAL_EVENTS,
  enabled: false,
  attribution: "NASA FIRMS Active Fires"
});

spatialLayerRegistry.register({
  id: "earthquakes",
  name: "Seismic Events & Earthquakes",
  category: LAYER_CATEGORIES.NATURAL_EVENTS,
  enabled: false,
  attribution: "USGS Earthquake Hazards Program"
});

spatialLayerRegistry.register({
  id: "self_geofence",
  name: "Personal Safety Geofences",
  category: LAYER_CATEGORIES.ROUTES_GEOFENCES,
  enabled: true,
  isSensitive: true,
  isAuthorized: true,
  attribution: "Owner-Controlled Security Perimeter"
});
