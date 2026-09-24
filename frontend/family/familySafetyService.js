/**
 * J.A.R.V.I.S. Mark XVII — Family Safety & Mobile Companion Service
 * =================================================================
 * Frontend state manager for Authorized Device Registry, Consent Scopes,
 * Safety Alerts, Voluntary Check-ins, and Remote Task Orchestration.
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

  async fetchDevices() {
    try {
      const resp = await fetch("/api/family/devices");
      const data = await resp.json();
      if (data.success) {
        this.devices = data.devices || [];
      }
      return this.devices;
    } catch (e) {
      console.warn("[FamilySafety] Error fetching devices:", e);
      return [];
    }
  }

  async fetchAlerts() {
    try {
      const resp = await fetch("/api/family/alerts");
      const data = await resp.json();
      if (data.success) {
        this.alerts = data.alerts || [];
      }
      return this.alerts;
    } catch (e) {
      console.warn("[FamilySafety] Error fetching alerts:", e);
      return [];
    }
  }

  async fetchConsents() {
    try {
      const resp = await fetch("/api/family/consent");
      const data = await resp.json();
      if (data.success) {
        this.consents = data.consents || [];
      }
      return this.consents;
    } catch (e) {
      console.warn("[FamilySafety] Error fetching consents:", e);
      return [];
    }
  }

  async fetchReliability() {
    try {
      const resp = await fetch("/api/remote/reliability");
      const data = await resp.json();
      if (data.success) {
        this.reliability = data;
      }
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
        body: JSON.stringify({ actorId: "shakil" })
      });
      return await resp.json();
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
          ownerProfileId: "shakil",
          displayName,
          deviceType,
          platform,
          ttlSeconds: 600
        })
      });
      return await resp.json();
    } catch (e) {
      return { success: false, error: String(e) };
    }
  }

  async dismissAlert(alertId) {
    try {
      const resp = await fetch(`/api/family/alerts/${alertId}/dismiss`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actorId: "shakil" })
      });
      return await resp.json();
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
      return await resp.json();
    } catch (e) {
      return { success: false, error: String(e) };
    }
  }

  async scanLocalNetwork() {
    try {
      const resp = await fetch("/api/family/discovery/scan", { method: "POST" });
      return await resp.json();
    } catch (e) {
      return { success: false, error: String(e) };
    }
  }
}

export const familySafetyService = new FamilySafetyService();
