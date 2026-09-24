/**
 * J.A.R.V.I.S. Location Fusion Engine (frontend/spatial/locationFusionEngine.js)
 * ==============================================================================
 * Validates, normalizes, and fuses raw geospatial observations into high-confidence
 * location telemetry. Evaluates multi-level accuracy (Level 0 through Level 7) and
 * calculates evidence-based confidence without fabricating indoor or room-level precision.
 */

import { spatialEventBus } from "./spatialEventBus.js";

export const ACCURACY_LEVELS = {
  LEVEL_0_UNKNOWN: { level: 0, code: "UNKNOWN", label: "No reliable location available" },
  LEVEL_1_COUNTRY: { level: 1, code: "COUNTRY", label: "Broad Country or Region" },
  LEVEL_2_CITY: { level: 2, code: "CITY", label: "City or Metro Area (~5-25 km)" },
  LEVEL_3_STREET: { level: 3, code: "STREET", label: "Street or Neighborhood (~100-500 m)" },
  LEVEL_4_PROPERTY_CANDIDATE: { level: 4, code: "PROPERTY_CANDIDATE", label: "Property or Building Candidate (~20-100 m)" },
  LEVEL_5_BUILDING_CONFIRMED: { level: 5, code: "BUILDING_CONFIRMED", label: "Building Confirmed (< 15 m / Verified Match)" },
  LEVEL_6_ENTRANCE: { level: 6, code: "ENTRANCE", label: "Entrance / Access Point (< 5 m)" },
  LEVEL_7_FLOOR_ROOM: { level: 7, code: "FLOOR_ROOM", label: "Floor / Room (Verified Indoor Sensor or User Confirmed)" }
};

export class LocationFusionEngine {
  constructor() {
    this.lastObservation = null;
    this.observationHistory = [];
    this.anomalyThresholdSpeedMps = 150.0; // ~540 km/h (land anomaly threshold)
  }

  validateRawObservation(raw) {
    if (!raw || typeof raw !== "object") {
      return { valid: false, error: "Empty or invalid observation object" };
    }

    const lat = Number(raw.latitude);
    const lon = Number(raw.longitude);

    if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
      return { valid: false, error: `Invalid latitude: ${raw.latitude}. Must be between -90 and 90.` };
    }
    if (!Number.isFinite(lon) || lon < -180 || lon > 180) {
      return { valid: false, error: `Invalid longitude: ${raw.longitude}. Must be between -180 and 180.` };
    }

    const accuracy = Number(raw.accuracy || raw.horizontalAccuracyMeters || 0);
    if (!Number.isFinite(accuracy) || accuracy < 0) {
      return { valid: false, error: `Invalid horizontal accuracy: ${accuracy}. Must be non-negative.` };
    }

    const observedAt = raw.timestamp || raw.observedAt || Date.now();
    const ageMs = Date.now() - (typeof observedAt === "number" ? observedAt : new Date(observedAt).getTime());
    if (ageMs > 3600000) {
      // Older than 1 hour is considered expired for live streaming
      return { valid: false, error: "Observation is stale (> 1 hour old)." };
    }

    return {
      valid: true,
      data: {
        latitude: lat,
        longitude: lon,
        horizontalAccuracyMeters: accuracy,
        verticalAccuracyMeters: Number.isFinite(raw.altitudeAccuracy) ? Number(raw.altitudeAccuracy) : null,
        altitudeMeters: Number.isFinite(raw.altitude) ? Number(raw.altitude) : null,
        headingDegrees: Number.isFinite(raw.heading) && raw.heading >= 0 && raw.heading <= 360 ? Number(raw.heading) : null,
        speedMps: Number.isFinite(raw.speed) && raw.speed >= 0 ? Number(raw.speed) : null,
        floorLevel: Number.isFinite(raw.floorLevel) ? Math.round(raw.floorLevel) : null,
        source: raw.source || "browser_geolocation",
        userConfirmed: Boolean(raw.userConfirmed),
        observedAt: typeof observedAt === "number" ? observedAt : Date.now(),
        rawMetadata: raw.rawMetadata || {}
      }
    };
  }

  determineAccuracyLevel(obs) {
    if (!obs) return ACCURACY_LEVELS.LEVEL_0_UNKNOWN;

    // Floor/Room level is strictly restricted to user confirmation or verified indoor systems
    if (obs.floorLevel !== null && (obs.userConfirmed || obs.source === "indoor_positioning")) {
      return ACCURACY_LEVELS.LEVEL_7_FLOOR_ROOM;
    }

    if (obs.userConfirmed) {
      return ACCURACY_LEVELS.LEVEL_5_BUILDING_CONFIRMED;
    }

    const acc = obs.horizontalAccuracyMeters;
    if (acc <= 5.0 && obs.source === "differential_gps") {
      return ACCURACY_LEVELS.LEVEL_6_ENTRANCE;
    }
    if (acc <= 15.0) {
      return ACCURACY_LEVELS.LEVEL_5_BUILDING_CONFIRMED;
    }
    if (acc <= 60.0) {
      return ACCURACY_LEVELS.LEVEL_4_PROPERTY_CANDIDATE;
    }
    if (acc <= 500.0) {
      return ACCURACY_LEVELS.LEVEL_3_STREET;
    }
    if (acc <= 25000.0) {
      return ACCURACY_LEVELS.LEVEL_2_CITY;
    }
    return ACCURACY_LEVELS.LEVEL_1_COUNTRY;
  }

  calculateConfidenceScore(obs, accuracyLevel) {
    if (!obs) return 0.0;

    let score = 0.5;

    // Accuracy bonus
    if (obs.horizontalAccuracyMeters <= 10.0) score += 0.3;
    else if (obs.horizontalAccuracyMeters <= 30.0) score += 0.2;
    else if (obs.horizontalAccuracyMeters <= 100.0) score += 0.1;
    else if (obs.horizontalAccuracyMeters > 5000.0) score -= 0.2;

    // Source weighting
    if (obs.userConfirmed) score += 0.25;
    if (obs.source === "browser_geolocation_high_accuracy") score += 0.1;
    if (obs.source === "ip_network_approximation") score -= 0.15;

    // Freshness penalty
    const ageSec = (Date.now() - obs.observedAt) / 1000.0;
    if (ageSec > 60.0) score -= 0.1;
    if (ageSec > 300.0) score -= 0.2;

    return Math.max(0.0, Math.min(1.0, Math.round(score * 100) / 100));
  }

  detectAnomaly(currentObs) {
    if (!this.lastObservation) return { isAnomaly: false };

    const timeDeltaSec = (currentObs.observedAt - this.lastObservation.observedAt) / 1000.0;
    if (timeDeltaSec <= 0.1) return { isAnomaly: false };

    // Calculate approximate surface distance (Haversine)
    const dLat = (currentObs.latitude - this.lastObservation.latitude) * Math.PI / 180.0;
    const dLon = (currentObs.longitude - this.lastObservation.longitude) * Math.PI / 180.0;
    const lat1 = this.lastObservation.latitude * Math.PI / 180.0;
    const lat2 = currentObs.latitude * Math.PI / 180.0;

    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.sin(dLon / 2) * Math.sin(dLon / 2) * Math.cos(lat1) * Math.cos(lat2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distM = 6371000.0 * c;

    const impliedSpeedMps = distM / timeDeltaSec;

    if (impliedSpeedMps > this.anomalyThresholdSpeedMps && !currentObs.userConfirmed) {
      return {
        isAnomaly: true,
        reason: `Implied speed jump (${Math.round(impliedSpeedMps * 3.6)} km/h) exceeds land threshold.`,
        impliedSpeedMps,
        distM
      };
    }

    return { isAnomaly: false, impliedSpeedMps, distM };
  }

  processObservation(rawInput) {
    const val = this.validateRawObservation(rawInput);
    if (!val.valid) {
      return { ok: false, error: val.error };
    }

    const obs = val.data;
    const anomaly = this.detectAnomaly(obs);
    const accuracyLevel = this.determineAccuracyLevel(obs);
    const confidenceScore = this.calculateConfidenceScore(obs, accuracyLevel);

    const fusedObservation = {
      id: `obs_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
      receivedAt: Date.now(),
      ...obs,
      accuracyLevel,
      confidenceScore,
      confidenceLabel: confidenceScore >= 0.85 ? "HIGH" : (confidenceScore >= 0.6 ? "MODERATE" : "LOW"),
      isAnomaly: anomaly.isAnomaly,
      anomalyReason: anomaly.reason || null,
      freshnessSeconds: Math.round((Date.now() - obs.observedAt) / 1000)
    };

    this.lastObservation = fusedObservation;
    this.observationHistory.push(fusedObservation);
    if (this.observationHistory.length > 50) this.observationHistory.shift();

    spatialEventBus.emit("spatial.location.fused", fusedObservation);
    return { ok: true, observation: fusedObservation };
  }
}

export const locationFusionEngine = new LocationFusionEngine();
if (typeof window !== "undefined") {
  window.__jarvisLocationFusionEngine = locationFusionEngine;
}
