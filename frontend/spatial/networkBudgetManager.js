/**
 * J.A.R.V.I.S. Network Budget Manager (frontend/spatial/networkBudgetManager.js)
 * =============================================================================
 * Manages provider rate-limits, request concurrency, singleflight deduplication,
 * exponential backoff, and network quality profiles.
 */

import { spatialEventBus } from "./spatialEventBus.js";

class NetworkBudgetManager {
  constructor() {
    this.inFlight = new Map(); // url -> Promise
    this.providerFailures = new Map(); // providerId -> count
    this.providerBackoffUntil = new Map(); // providerId -> timestamp
    this.networkProfile = "FAST"; // FAST, MEDIUM, SLOW, VERY_SLOW, OFFLINE
    this.latencyHistory = [];
  }

  isProviderBlocked(providerId) {
    const unblockTime = this.providerBackoffUntil.get(providerId);
    if (!unblockTime) return false;
    if (Date.now() < unblockTime) return true;
    this.providerBackoffUntil.delete(providerId);
    return false;
  }

  recordFailure(providerId, statusCode = 500) {
    const count = (this.providerFailures.get(providerId) || 0) + 1;
    this.providerFailures.set(providerId, count);

    // Exponential backoff: 2s, 4s, 8s, 16s, up to 60s
    const backoffSec = Math.min(60, Math.pow(2, count));
    this.providerBackoffUntil.set(providerId, Date.now() + (backoffSec * 1000));

    spatialEventBus.emit("spatial.provider.rate_limited", {
      providerId,
      statusCode,
      backoffSec
    });
  }

  recordSuccess(providerId, latencyMs) {
    this.providerFailures.delete(providerId);
    this.providerBackoffUntil.delete(providerId);

    this.latencyHistory.push(latencyMs);
    if (this.latencyHistory.length > 20) this.latencyHistory.shift();
    this._updateNetworkProfile();
  }

  _updateNetworkProfile() {
    if (this.latencyHistory.length === 0) return;
    const avg = this.latencyHistory.reduce((a, b) => a + b, 0) / this.latencyHistory.length;

    let profile = "FAST";
    if (avg > 1500) profile = "SLOW";
    else if (avg > 600) profile = "MEDIUM";

    if (profile !== this.networkProfile) {
      this.networkProfile = profile;
      spatialEventBus.emit("spatial.network.quality_changed", { profile, avgLatencyMs: Math.round(avg) });
    }
  }

  async fetchSingleFlight(url, options = {}, providerId = "default") {
    if (this.isProviderBlocked(providerId)) {
      throw new Error(`Provider '${providerId}' is in failure cooldown.`);
    }

    if (this.inFlight.has(url)) {
      return this.inFlight.get(url);
    }

    const start = performance.now();
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeoutMs || 10000);

    const promise = fetch(url, { ...options, signal: controller.signal })
      .then(async (res) => {
        clearTimeout(timeoutId);
        const elapsed = performance.now() - start;
        if (!res.ok) {
          this.recordFailure(providerId, res.status);
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        this.recordSuccess(providerId, elapsed);
        return res;
      })
      .catch((err) => {
        clearTimeout(timeoutId);
        this.recordFailure(providerId, 0);
        throw err;
      })
      .finally(() => {
        this.inFlight.delete(url);
      });

    this.inFlight.set(url, promise);
    return promise;
  }
}

export const networkBudgetManager = new NetworkBudgetManager();
if (typeof window !== "undefined") {
  window.__jarvisNetworkManager = networkBudgetManager;
}
