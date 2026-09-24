/**
 * J.A.R.V.I.S. Mark XVII — Family Safety & Mobile Companion Service
 * =================================================================
 * Centralized frontend state manager for Authorized Device Registry,
 * Consent Scopes, Safety Alerts, Voluntary Check-ins, and Remote Tasks.
 *
 * ARCHITECTURE NOTE: This service is the CANONICAL API client for all
 * family-safety operations. The HUD (hud.js) should progressively
 * migrate to using this service instead of making direct fetch() calls.
 * Both currently work because the backend exposes aliases for route paths.
 *
 * SECURITY NOTE: The server enforces actor identity server-side.
 * Client-provided actorId is logged but NOT used for authorization.
 */

export class FamilySafetyService {
  constructor() {
    this.devices = [];
    this.alerts = [];
    this.consents = [];
    this.tasks = [];
    this.reliability = null;
    this.activeCheckins = [];
  }

  /**
   * Validates a backend API response and returns the parsed data.
   * Throws if the response indicates failure.
   */
  async _validateResponse(resp, context = "API call") {
    const data = await resp.json();
    if (!resp.ok || data.ok === false || data.executed === false) {
      const errorMsg = data.message || data.error || `${context} failed`;
      console.error(`[FamilySafety] ${context} failed:`, errorMsg);
      throw new Error(errorMsg);
    }
    return data;
  }

  async fetchDevices() {
    try {
      const resp = await fetch("/api/family/devices");
      const data = await this._validateResponse(resp, "Fetch devices");
      this.devices = data.devices || (data.data && data.data.devices) || [];
      return this.devices;
    } catch (e) {
      console.warn("[FamilySafety] Error fetching devices:", e);
      return [];
    }
  }

  async fetchAlerts() {
    try {
      const resp = await fetch("/api/family/alerts");
      const data = await this._validateResponse(resp, "Fetch alerts");
      this.alerts = data.alerts || (data.data && data.data.alerts) || [];
      return this.alerts;
    } catch (e) {
      console.warn("[FamilySafety] Error fetching alerts:", e);
      return [];
    }
  }

  async fetchConsents() {
    try {
      const resp = await fetch("/api/family/consent");
      const data = await this._validateResponse(resp, "Fetch consents");
      this.consents = data.consents || (data.data && data.data.consents) || [];
      return this.consents;
    } catch (e) {
      console.warn("[FamilySafety] Error fetching consents:", e);
      return [];
    }
  }

  async fetchReliability() {
    try {
      const resp = await fetch("/api/remote/reliability");
      const data = await this._validateResponse(resp, "Fetch reliability");
      this.reliability = data;
      return this.reliability;
    } catch (e) {
      console.warn("[FamilySafety] Error fetching reliability:", e);
      return null;
    }
  }

  async pauseAllSharing() {
    try {
      const resp = await fetch("/api/family/consent/pause_all", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "Kill switch triggered via FamilySafetyService" })
      });
      return await this._validateResponse(resp, "Pause all sharing");
    } catch (e) {
      return { success: false, error: String(e) };
    }
  }

  async initiatePairing(displayName, deviceType = "phone", platform = "android") {
    try {
      const resp = await fetch("/api/family/devices/pair/init", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          displayName,
          deviceType,
          platform,
          ttlSeconds: 600
        })
      });
      return await this._validateResponse(resp, "Initiate pairing");
    } catch (e) {
      return { success: false, error: String(e) };
    }
  }

  async dismissAlert(alertId) {
    try {
      const resp = await fetch(`/api/family/alerts/${alertId}/dismiss`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });
      return await this._validateResponse(resp, "Dismiss alert");
    } catch (e) {
      return { success: false, error: String(e) };
    }
  }

  async respondCheckIn(checkInId, responseType = "safe", notes = "") {
    try {
      const resp = await fetch("/api/family/checkin/respond", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          checkInId,
          responseType,
          notes
        })
      });
      return await this._validateResponse(resp, "Respond to check-in");
    } catch (e) {
      return { success: false, error: String(e) };
    }
  }

  async scanLocalNetwork() {
    try {
      const resp = await fetch("/api/family/discovery/scan", { method: "POST" });
      return await this._validateResponse(resp, "Network scan");
    } catch (e) {
      return { success: false, error: String(e) };
    }
  }
}

export const familySafetyService = new FamilySafetyService();
