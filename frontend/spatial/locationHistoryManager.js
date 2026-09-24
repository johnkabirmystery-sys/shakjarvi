/**
 * J.A.R.V.I.S. Location History Manager (frontend/spatial/locationHistoryManager.js)
 * =================================================================================
 * Optional, privacy-preserving, local-first personal location history store.
 * - STRICT DEFAULT: Disabled until explicitly permitted by Sir Shakil.
 * - Enforces automatic retention expiration and purge policies.
 * - Provides one-click deletion and export to JSON or CSV.
 * - Zero cloud transmission or external telemetry leakage.
 */

import { spatialEventBus } from "./spatialEventBus.js";
import { privacyManager, PERMISSION_SCOPES } from "./privacyManager.js";

export const RETENTION_POLICIES = {
  SESSION_ONLY: { key: "session_only", maxAgeMs: 0, label: "Session Only (Purge on Tab Close)" },
  ONE_HOUR: { key: "1_hour", maxAgeMs: 3600000, label: "1 Hour" },
  TWENTY_FOUR_HOURS: { key: "24_hours", maxAgeMs: 86400000, label: "24 Hours" },
  SEVEN_DAYS: { key: "7_days", maxAgeMs: 604800000, label: "7 Days" },
  MANUAL: { key: "manual", maxAgeMs: Infinity, label: "Manual Deletion Only" }
};

class LocationHistoryManager {
  constructor() {
    this.storageKey = "jarvis_personal_location_history";
    this.currentPolicy = RETENTION_POLICIES.SESSION_ONLY;
    this.history = [];
    this.sessionId = `session_${Date.now()}`;
    this.isEnabled = false;

    this._initAutoListener();
    this._loadHistory();
    this.purgeExpired();
  }

  _initAutoListener() {
    spatialEventBus.on("spatial.location.fused", (obs) => {
      if (this.isEnabled && privacyManager.hasPermission(PERMISSION_SCOPES.LOCATION_HISTORY)) {
        this.recordObservation(obs);
      }
    });

    spatialEventBus.on("spatial.privacy.permission_changed", (e) => {
      if (e.scope === PERMISSION_SCOPES.LOCATION_HISTORY && e.state !== "granted") {
        this.isEnabled = false;
      }
    });
  }

  _loadHistory() {
    try {
      const raw = localStorage.getItem(this.storageKey);
      if (raw) {
        this.history = JSON.parse(raw);
      }
    } catch (_) {
      this.history = [];
    }
  }

  _saveHistory() {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.history));
    } catch (_) {}
  }

  enableHistory(retentionKey = "session_only") {
    const perm = privacyManager.requestPermission(
      PERMISSION_SCOPES.LOCATION_HISTORY,
      "Local recording of personal location breadcrumbs on God's Eye View map"
    );

    if (perm.granted) {
      this.isEnabled = true;
      this.setRetentionPolicy(retentionKey);
      spatialEventBus.emit("spatial.history.enabled", { policy: this.currentPolicy.key });
      return { ok: true, policy: this.currentPolicy.key };
    }
    return { ok: false, error: "Permission to store location history was denied." };
  }

  disableHistory() {
    this.isEnabled = false;
    privacyManager.revokePermission(PERMISSION_SCOPES.LOCATION_HISTORY);
    spatialEventBus.emit("spatial.history.disabled");
    return { ok: true };
  }

  setRetentionPolicy(policyKey) {
    if (RETENTION_POLICIES[policyKey.toUpperCase()]) {
      this.currentPolicy = RETENTION_POLICIES[policyKey.toUpperCase()];
    } else {
      this.currentPolicy = RETENTION_POLICIES.SESSION_ONLY;
    }
    this.purgeExpired();
    return this.currentPolicy;
  }

  recordObservation(fusedObs) {
    if (!this.isEnabled || !fusedObs) return;

    const expiresAt = Number.isFinite(this.currentPolicy.maxAgeMs) && this.currentPolicy.maxAgeMs > 0
      ? Date.now() + this.currentPolicy.maxAgeMs
      : null;

    const entry = {
      observationId: fusedObs.id || `hist_${Date.now()}`,
      sessionId: this.sessionId,
      observedAt: fusedObs.observedAt || Date.now(),
      latitude: fusedObs.latitude,
      longitude: fusedObs.longitude,
      accuracyMeters: fusedObs.horizontalAccuracyMeters,
      altitudeMeters: fusedObs.altitudeMeters,
      headingDegrees: fusedObs.headingDegrees,
      speedMps: fusedObs.speedMps,
      source: fusedObs.source,
      confidence: fusedObs.confidenceScore,
      userConfirmed: Boolean(fusedObs.userConfirmed),
      retentionExpiresAt: expiresAt
    };

    this.history.push(entry);
    // Cap total local history to 5000 points to prevent storage bloat
    if (this.history.length > 5000) {
      this.history.shift();
    }

    this._saveHistory();
    spatialEventBus.emit("spatial.history.recorded", entry);
  }

  purgeExpired() {
    const now = Date.now();
    const initialCount = this.history.length;
    this.history = this.history.filter(item => {
      if (!item.retentionExpiresAt) return true;
      return item.retentionExpiresAt > now;
    });

    if (this.history.length !== initialCount) {
      this._saveHistory();
    }
    return { purgedCount: initialCount - this.history.length, remainingCount: this.history.length };
  }

  clearAllHistory() {
    const count = this.history.length;
    this.history = [];
    this._saveHistory();
    privacyManager.logPrivacyEvent("LOCATION_HISTORY_DELETED", "location_history", { count });
    spatialEventBus.emit("spatial.history.cleared", { count });
    return { ok: true, deletedCount: count };
  }

  clearCurrentSessionHistory() {
    const count = this.history.filter(h => h.sessionId === this.sessionId).length;
    this.history = this.history.filter(h => h.sessionId !== this.sessionId);
    this._saveHistory();
    spatialEventBus.emit("spatial.history.session_cleared", { count, sessionId: this.sessionId });
    return { ok: true, deletedCount: count };
  }

  getTrailCoordinates() {
    return this.history.map(h => ({
      latitude: h.latitude,
      longitude: h.longitude,
      altitude: h.altitudeMeters || 10,
      timestamp: h.observedAt
    }));
  }

  exportAsJson() {
    return JSON.stringify({
      exportedAt: new Date().toISOString(),
      sessionId: this.sessionId,
      totalPoints: this.history.length,
      history: this.history
    }, null, 2);
  }

  exportAsCsv() {
    const headers = ["observationId", "sessionId", "observedAt", "latitude", "longitude", "accuracyMeters", "altitudeMeters", "speedMps", "headingDegrees", "source", "confidence"];
    const rows = this.history.map(h => [
      h.observationId,
      h.sessionId,
      new Date(h.observedAt).toISOString(),
      h.latitude,
      h.longitude,
      h.accuracyMeters || "",
      h.altitudeMeters || "",
      h.speedMps || "",
      h.headingDegrees || "",
      h.source || "",
      h.confidence || ""
    ].join(","));

    return [headers.join(","), ...rows].join("\n");
  }
}

export const locationHistoryManager = new LocationHistoryManager();
if (typeof window !== "undefined") {
  window.__jarvisLocationHistoryManager = locationHistoryManager;
}
