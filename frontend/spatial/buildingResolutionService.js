/**
 * J.A.R.V.I.S. Building & Address Resolution Service (frontend/spatial/buildingResolutionService.js)
 * =================================================================================================
 * Resolves high-confidence building candidates, street addresses, and entrance points
 * from geospatial coordinates using free and lawful OpenStreetMap / Nominatim / Photon services.
 * - Enforces rate limits, caching, and attribution.
 * - Detects ambiguity and requests user confirmation when precision is insufficient.
 * - Never fabricates building numbers or assumes single-building certainty without evidence.
 */

import { spatialEventBus } from "./spatialEventBus.js";
import { networkBudgetManager } from "./networkBudgetManager.js";

export class BuildingResolutionService {
  constructor() {
    this.cache = new Map(); // key: "lat_lon_rounded" -> result
    this.maxCacheSize = 200;
  }

  _getCacheKey(lat, lon) {
    // Round to ~11 meters precision (4 decimal places)
    return `${lat.toFixed(4)}_${lon.toFixed(4)}`;
  }

  async resolveBuildingAndAddress(latitude, longitude, accuracyRadiusMeters = 15.0, userConfirmedName = null) {
    const lat = Number(latitude);
    const lon = Number(longitude);
    const acc = Number(accuracyRadiusMeters);

    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      return {
        status: "INVALID_COORDINATES",
        buildingCandidate: null,
        candidates: [],
        address: null,
        confidence: 0.0,
        limitations: "Coordinates provided are invalid or non-numeric."
      };
    }

    // If user explicitly confirmed a building, return immediate user-confirmed record
    if (userConfirmedName) {
      const confirmedResult = {
        status: "USER_CONFIRMED",
        buildingCandidate: {
          name: userConfirmedName,
          type: "user_confirmed",
          confidence: 1.0
        },
        candidates: [{ name: userConfirmedName, confidence: 1.0 }],
        address: { displayName: userConfirmedName },
        entranceCandidates: [],
        confidence: 1.0,
        source: "user_input",
        limitations: "Confirmed by operator Sir Shakil.",
        requiresUserConfirmation: false
      };
      spatialEventBus.emit("spatial.building.resolved", confirmedResult);
      return confirmedResult;
    }

    // Check if accuracy is too broad to pinpoint a building
    if (acc > 150.0) {
      return {
        status: "LOCATION_PRECISION_INSUFFICIENT",
        buildingCandidate: null,
        candidates: [],
        address: null,
        entranceCandidates: [],
        confidence: 0.2,
        source: "coarse_positioning",
        limitations: `Current horizontal accuracy (±${Math.round(acc)}m) exceeds building-level resolution threshold (150m). Move outdoors or acquire GPS lock.`,
        requiresUserConfirmation: true
      };
    }

    // Check cache
    const cacheKey = this._getCacheKey(lat, lon);
    if (this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey);
      spatialEventBus.emit("spatial.building.resolved", cached);
      return cached;
    }

    // Fetch from free Nominatim / Photon reverse geocoder with singleflight protection
    try {
      const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1`;
      
      let geoData = null;
      try {
        const resp = await networkBudgetManager.fetchSingleFlight(url, {
          headers: { "Accept-Language": "en" },
          timeoutMs: 8000
        }, "nominatim");
        geoData = await resp.json();
      } catch (nomErr) {
        // Fallback to Photon
        const photonUrl = `https://photon.komoot.io/reverse?lat=${lat}&lon=${lon}`;
        const pResp = await networkBudgetManager.fetchSingleFlight(photonUrl, { timeoutMs: 8000 }, "photon");
        const pJson = await pResp.json();
        if (pJson && pJson.features && pJson.features.length > 0) {
          const props = pJson.features[0].properties;
          geoData = {
            display_name: [props.name, props.street, props.city, props.country].filter(Boolean).join(", "),
            address: {
              building: props.name || null,
              road: props.street || null,
              city: props.city || props.town || null,
              postcode: props.postcode || null,
              country: props.country || null
            }
          };
        }
      }

      if (!geoData) {
        return {
          status: "NO_DATA",
          buildingCandidate: null,
          candidates: [],
          address: null,
          confidence: 0.0,
          limitations: "No reverse geocoding data available for this locus."
        };
      }

      const addr = geoData.address || {};
      const buildingName = addr.building || addr.amenity || addr.shop || addr.office || addr.house_name || null;
      const road = addr.road || addr.pedestrian || addr.suburb || "Unnamed Road";
      const houseNumber = addr.house_number ? `${addr.house_number} ` : "";
      const formattedAddress = geoData.display_name || `${houseNumber}${road}`;

      const isAmbiguous = acc > 40.0;
      const candidates = [];
      if (buildingName) {
        candidates.push({ name: buildingName, type: "named_building", confidence: isAmbiguous ? 0.6 : 0.9 });
      }
      candidates.push({ name: `${houseNumber}${road}`.trim(), type: "street_address", confidence: 0.75 });

      const resolved = {
        status: buildingName ? "BUILDING_CANDIDATE" : "STREET_ADDRESS",
        buildingCandidate: buildingName ? { name: buildingName, address: formattedAddress } : null,
        candidates,
        address: {
          displayName: formattedAddress,
          street: road,
          houseNumber: addr.house_number || null,
          city: addr.city || addr.town || addr.municipality || null,
          postcode: addr.postcode || null,
          country: addr.country || null
        },
        entranceCandidates: [],
        confidence: isAmbiguous ? 0.65 : 0.88,
        source: "osm_nominatim",
        attribution: "Data © OpenStreetMap contributors, ODbL",
        limitations: isAmbiguous ? `Accuracy is ±${Math.round(acc)}m. Multiple candidate buildings may exist within radius.` : "Estimated from OpenStreetMap cadastral data.",
        requiresUserConfirmation: isAmbiguous
      };

      // Store in LRU cache
      if (this.cache.size >= this.maxCacheSize) {
        const firstKey = this.cache.keys().next().value;
        this.cache.delete(firstKey);
      }
      this.cache.set(cacheKey, resolved);

      spatialEventBus.emit("spatial.building.resolved", resolved);
      return resolved;

    } catch (err) {
      console.warn("[BuildingResolutionService] Reverse geocode error:", err);
      return {
        status: "LOOKUP_FAILED",
        buildingCandidate: null,
        candidates: [],
        address: null,
        confidence: 0.0,
        limitations: `Reverse geocoding failed: ${err.message || err}`,
        requiresUserConfirmation: true
      };
    }
  }
}

export const buildingResolutionService = new BuildingResolutionService();
if (typeof window !== "undefined") {
  window.__jarvisBuildingResolutionService = buildingResolutionService;
}
