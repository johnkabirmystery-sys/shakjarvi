/**
 * J.A.R.V.I.S. Spatial Provider Adapter Contract (frontend/spatial/core/spatialProviderAdapter.js)
 * =================================================================================================
 * Provider-neutral interface standardizing snapshot fetching, normalization,
 * rate limit handling, and truthful availability telemetry.
 */

export const PROVIDER_STATES = {
  CONFIGURED: "configured",
  CONNECTING: "connecting",
  AVAILABLE: "available",
  DEGRADED: "degraded",
  RATE_LIMITED: "rate_limited",
  UNAUTHORIZED: "unauthorized",
  STALE: "stale",
  FAILED: "failed",
  DISABLED: "disabled"
};

export class SpatialProviderAdapter {
  constructor(config = {}) {
    this.config = config;
    this.state = PROVIDER_STATES.CONFIGURED;
    this.lastSuccessfulFetch = null;
    this.lastError = null;
    this.cachedEntities = [];
  }

  async healthCheck() {
    return {
      ok: this.state === PROVIDER_STATES.AVAILABLE || this.state === PROVIDER_STATES.CONFIGURED,
      state: this.state,
      provider: this.getMetadata().provider
    };
  }

  async fetchSnapshot() {
    throw new Error("fetchSnapshot must be implemented by subclass adapter.");
  }

  normalize(record) {
    throw new Error("normalize must be implemented by subclass adapter.");
  }

  getMetadata() {
    return {
      provider: this.config.providerName || "generic_spatial_provider",
      capabilities: [],
      terms: "Public Open Data / Attribution Required",
      rateLimitRpm: this.config.rateLimitRpm || 60
    };
  }
}
