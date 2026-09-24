/**
 * J.A.R.V.I.S. Self-Location Engine (frontend/spatial/selfLocationEngine.js)
 * =========================================================================
 * Live self-location acquisition engine with explicit privacy controls.
 * - Manages browser Geolocation API watcher.
 * - Hardware and browser capability detection.
 * - Fallback to network approximation or manual confirmation.
 * - Dispatches validated observations to the LocationFusionEngine.
 */

import { spatialEventBus } from "./spatialEventBus.js";
import { privacyManager, PERMISSION_SCOPES } from "./privacyManager.js";
import { locationFusionEngine } from "./locationFusionEngine.js";

export const TRACKING_MODES = {
  HIGH_ACCURACY: { enableHighAccuracy: true, timeout: 15000, maximumAge: 3000, minDistanceM: 3 },
  NORMAL: { enableHighAccuracy: false, timeout: 10000, maximumAge: 10000, minDistanceM: 10 },
  LOW_POWER: { enableHighAccuracy: false, timeout: 30000, maximumAge: 60000, minDistanceM: 50 }
};

class SelfLocationEngine {
  constructor() {
    this.watchId = null;
    this.isTracking = false;
    this.currentMode = "NORMAL";
    this.lastPosition = null;
    this.lastError = null;
    this.capabilities = this._detectCapabilities();
  }

  _detectCapabilities() {
    const hasGeo = typeof navigator !== "undefined" && "geolocation" in navigator;
    const isSecure = typeof window !== "undefined" ? window.isSecureContext : false;

    return {
      browserGeolocation: hasGeo ? "available" : "unsupported",
      highAccuracyMode: hasGeo ? "available" : "unsupported",
      backgroundLocation: "unsupported", // Standard browser limitation
      osLocationIntegration: typeof window !== "undefined" && window.pywebview ? "available" : "not_configured",
      gpsHardware: "unknown",
      networkApproximation: "available",
      heading: hasGeo ? "available" : "unsupported",
      speed: hasGeo ? "available" : "unsupported",
      altitude: hasGeo ? "available" : "unsupported",
      floorLevel: "not_configured",
      buildingIdentification: "available",
      offlineSupport: "available",
      isSecureContext: isSecure
    };
  }

  getCapabilities() {
    return {
      ...this.capabilities,
      trackingActive: this.isTracking,
      trackingMode: this.currentMode,
      permissionState: privacyManager.getPermissionState(PERMISSION_SCOPES.WHILE_USING)
    };
  }

  async startTracking(modeKey = "NORMAL") {
    if (this.isTracking) {
      return { ok: true, message: "Tracking already active." };
    }

    // Check privacy permission
    if (!privacyManager.hasPermission(PERMISSION_SCOPES.WHILE_USING)) {
      const req = privacyManager.requestPermission(
        PERMISSION_SCOPES.WHILE_USING,
        "Live location tracking for personal God's Eye View map positioning"
      );
      if (!req.granted) {
        return { ok: false, error: "Location tracking permission was not granted by user." };
      }
    }

    if (typeof navigator === "undefined" || !("geolocation" in navigator)) {
      return { ok: false, error: "Browser Geolocation API is unsupported in this environment." };
    }

    this.currentMode = TRACKING_MODES[modeKey] ? modeKey : "NORMAL";
    const geoOptions = TRACKING_MODES[this.currentMode];

    return new Promise((resolve) => {
      this.watchId = navigator.geolocation.watchPosition(
        (pos) => {
          this._handlePositionSuccess(pos);
          if (!this.isTracking) {
            this.isTracking = true;
            privacyManager.setTrackingState(true, "geolocation_active");
            spatialEventBus.emit("spatial.self_location.started", { mode: this.currentMode });
            resolve({ ok: true, mode: this.currentMode });
          }
        },
        (err) => {
          this._handlePositionError(err);
          if (!this.isTracking) {
            resolve({ ok: false, error: this.lastError });
          }
        },
        geoOptions
      );
    });
  }

  stopTracking() {
    if (this.watchId !== null && typeof navigator !== "undefined" && navigator.geolocation) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
    }
    this.isTracking = false;
    privacyManager.setTrackingState(false, "user_stop");
    spatialEventBus.emit("spatial.self_location.stopped");
    return { ok: true };
  }

  async getCurrentLocation(options = { highAccuracy: true }) {
    if (!privacyManager.hasPermission(PERMISSION_SCOPES.ONE_TIME) && !privacyManager.hasPermission(PERMISSION_SCOPES.WHILE_USING)) {
      const req = privacyManager.requestPermission(PERMISSION_SCOPES.ONE_TIME, "Single location query");
      if (!req.granted) {
        return { ok: false, error: "One-time location permission denied." };
      }
    }

    if (typeof navigator === "undefined" || !("geolocation" in navigator)) {
      return { ok: false, error: "Browser Geolocation API unavailable." };
    }

    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const res = this._handlePositionSuccess(pos);
          resolve(res);
        },
        (err) => {
          this._handlePositionError(err);
          resolve({ ok: false, error: this.lastError });
        },
        { enableHighAccuracy: options.highAccuracy, timeout: 10000, maximumAge: 5000 }
      );
    });
  }

  setManualLocation(latitude, longitude, name = "User Confirmed Location", altitudeM = 15.0) {
    const raw = {
      latitude: Number(latitude),
      longitude: Number(longitude),
      horizontalAccuracyMeters: 5.0, // High certainty for user-confirmed coordinate
      altitude: Number(altitudeM),
      source: "user_confirmed_manual",
      userConfirmed: true,
      observedAt: Date.now(),
      rawMetadata: { name }
    };

    const res = locationFusionEngine.processObservation(raw);
    if (res.ok) {
      this.lastPosition = res.observation;
      spatialEventBus.emit("spatial.self_location.updated", res.observation);
    }
    return res;
  }

  _handlePositionSuccess(pos) {
    const raw = {
      latitude: pos.coords.latitude,
      longitude: pos.coords.longitude,
      horizontalAccuracyMeters: pos.coords.accuracy,
      altitude: pos.coords.altitude,
      altitudeAccuracy: pos.coords.altitudeAccuracy,
      heading: pos.coords.heading,
      speed: pos.coords.speed,
      source: this.currentMode === "HIGH_ACCURACY" ? "browser_geolocation_high_accuracy" : "browser_geolocation",
      userConfirmed: false,
      observedAt: pos.timestamp || Date.now()
    };

    const res = locationFusionEngine.processObservation(raw);
    if (res.ok) {
      this.lastPosition = res.observation;
      this.lastError = null;
      spatialEventBus.emit("spatial.self_location.updated", res.observation);
    }
    return res;
  }

  _handlePositionError(err) {
    let msg = "Unknown geolocation error";
    if (err.code === 1) msg = "Location permission denied by browser.";
    else if (err.code === 2) msg = "Location unavailable (position fix timeout or hardware offline).";
    else if (err.code === 3) msg = "Location request timed out.";

    this.lastError = msg;
    console.warn(`[SelfLocationEngine] ${msg} (${err.message || ""})`);
    spatialEventBus.emit("spatial.self_location.error", { error: msg, code: err.code });
  }
}

export const selfLocationEngine = new SelfLocationEngine();
if (typeof window !== "undefined") {
  window.__jarvisSelfLocationEngine = selfLocationEngine;
}
