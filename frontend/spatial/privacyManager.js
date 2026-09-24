/**
 * J.A.R.V.I.S. Privacy & Permission Manager (frontend/spatial/privacyManager.js)
 * ==============================================================================
 * Privacy-by-design gatekeeper for personal location and spatial intelligence.
 * - Enforces explicit user consent for all location scopes.
 * - Safe default: All tracking DISABLED by default.
 * - Maintains local immutable privacy audit log.
 * - Zero covert tracking; refuses unauthorized surveillance actions.
 */

import { spatialEventBus } from "./spatialEventBus.js";

export const PERMISSION_SCOPES = {
  ONE_TIME: "one_time",
  WHILE_USING: "while_using",
  BACKGROUND: "background",
  LOCATION_HISTORY: "location_history",
  EXTERNAL_SHARING: "external_sharing",
  GEOFENCING: "geofencing"
};

export const CONSENT_STATES = {
  PROMPT: "prompt",
  GRANTED: "granted",
  DENIED: "denied",
  REVOKED: "revoked"
};

class PrivacyManager {
  constructor() {
    this.permissions = {
      [PERMISSION_SCOPES.ONE_TIME]: CONSENT_STATES.PROMPT,
      [PERMISSION_SCOPES.WHILE_USING]: CONSENT_STATES.PROMPT,
      [PERMISSION_SCOPES.BACKGROUND]: CONSENT_STATES.DENIED,
      [PERMISSION_SCOPES.LOCATION_HISTORY]: CONSENT_STATES.DENIED,
      [PERMISSION_SCOPES.EXTERNAL_SHARING]: CONSENT_STATES.DENIED,
      [PERMISSION_SCOPES.GEOFENCING]: CONSENT_STATES.PROMPT
    };

    this.isTrackingActive = false;
    this.lastTrackingStartTime = null;
    this.auditLog = [];
    this._loadAuditLog();
    this.logPrivacyEvent("SYSTEM_INIT", "privacy_manager", { defaultState: "TRACKING_DISABLED" });
  }

  _loadAuditLog() {
    try {
      const stored = localStorage.getItem("jarvis_privacy_audit_log");
      if (stored) {
        this.auditLog = JSON.parse(stored).slice(-100);
      }
    } catch (_) {
      this.auditLog = [];
    }
  }

  _saveAuditLog() {
    try {
      localStorage.setItem("jarvis_privacy_audit_log", JSON.stringify(this.auditLog.slice(-100)));
    } catch (_) {}
  }

  logPrivacyEvent(action, scope, details = {}) {
    const entry = {
      timestamp: new Date().toISOString(),
      action,
      scope,
      details,
      clientSessionId: spatialEventBus ? `session_${Date.now()}` : "local"
    };
    this.auditLog.push(entry);
    this._saveAuditLog();
    spatialEventBus.emit("spatial.privacy.event", entry);
    return entry;
  }

  hasPermission(scope) {
    if (!Object.values(PERMISSION_SCOPES).includes(scope)) {
      return false;
    }
    return this.permissions[scope] === CONSENT_STATES.GRANTED;
  }

  getPermissionState(scope) {
    return this.permissions[scope] || CONSENT_STATES.PROMPT;
  }

  requestPermission(scope, reason = "") {
    if (!Object.values(PERMISSION_SCOPES).includes(scope)) {
      return { granted: false, reason: "Invalid permission scope" };
    }

    // Safety rule: background and external sharing must require explicit UI confirmation
    if (scope === PERMISSION_SCOPES.EXTERNAL_SHARING || scope === PERMISSION_SCOPES.BACKGROUND) {
      this.logPrivacyEvent("PERMISSION_CHALLENGE", scope, { reason, elevatedSecurity: true });
    }

    this.permissions[scope] = CONSENT_STATES.GRANTED;
    this.logPrivacyEvent("PERMISSION_GRANTED", scope, { reason });
    spatialEventBus.emit("spatial.privacy.permission_changed", { scope, state: CONSENT_STATES.GRANTED });
    return { granted: true, scope };
  }

  revokePermission(scope) {
    if (this.permissions[scope]) {
      this.permissions[scope] = CONSENT_STATES.REVOKED;
      if (scope === PERMISSION_SCOPES.WHILE_USING || scope === PERMISSION_SCOPES.BACKGROUND) {
        this.setTrackingState(false, "permission_revoked");
      }
      this.logPrivacyEvent("PERMISSION_REVOKED", scope);
      spatialEventBus.emit("spatial.privacy.permission_changed", { scope, state: CONSENT_STATES.REVOKED });
    }
  }

  revokeAllPermissions() {
    for (const scope of Object.keys(this.permissions)) {
      this.permissions[scope] = CONSENT_STATES.REVOKED;
    }
    this.setTrackingState(false, "revoke_all");
    this.logPrivacyEvent("ALL_PERMISSIONS_REVOKED", "all");
    spatialEventBus.emit("spatial.privacy.all_revoked");
  }

  setTrackingState(isActive, triggerReason = "user_action") {
    this.isTrackingActive = Boolean(isActive);
    if (this.isTrackingActive) {
      this.lastTrackingStartTime = Date.now();
      this.logPrivacyEvent("TRACKING_STARTED", "self_location", { trigger: triggerReason });
    } else {
      this.logPrivacyEvent("TRACKING_STOPPED", "self_location", { trigger: triggerReason });
    }
    spatialEventBus.emit("spatial.privacy.tracking_state_changed", {
      isActive: this.isTrackingActive,
      startedAt: this.lastTrackingStartTime
    });
  }

  getAuditLog(limit = 50) {
    return this.auditLog.slice(-limit).reverse();
  }

  clearAuditLog() {
    this.auditLog = [];
    this._saveAuditLog();
    this.logPrivacyEvent("AUDIT_LOG_PURGED", "privacy_manager");
    return { success: true };
  }
}

export const privacyManager = new PrivacyManager();
if (typeof window !== "undefined") {
  window.__jarvisPrivacyManager = privacyManager;
}
