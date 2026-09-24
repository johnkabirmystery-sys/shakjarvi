/**
 * J.A.R.V.I.S. Normalized Spatial Entity (frontend/spatial/core/spatialEntity.js)
 * ==============================================================================
 * Standardized schema and validation for all spatial intelligence entities.
 * Preserves source provenance, observed timestamp, freshness, and explicit status.
 */

export class SpatialEntity {
  /**
   * Constructs and normalizes a SpatialEntity.
   * @param {Object} data
   */
  constructor(data = {}) {
    if (!data.id) {
      throw new Error("SpatialEntity requires an 'id' property.");
    }
    this.id = String(data.id);
    this.entityType = data.entityType || "point_of_interest";
    this.name = data.name || this.id;

    // Position
    this.position = data.position ? {
      latitude: Number(data.position.latitude),
      longitude: Number(data.position.longitude),
      altitudeMeters: Number.isFinite(data.position.altitudeMeters) ? Number(data.position.altitudeMeters) : 0.0
    } : null;

    // Geometry
    this.geometry = data.geometry || (this.position ? {
      type: "Point",
      coordinates: [this.position.longitude, this.position.latitude, this.position.altitudeMeters]
    } : null);

    // Source & Provenance
    this.source = {
      provider: data.source?.provider || "unknown",
      recordId: data.source?.recordId,
      observedAt: data.source?.observedAt || new Date().toISOString(),
      receivedAt: data.source?.receivedAt || new Date().toISOString(),
      confidence: Number.isFinite(data.source?.confidence) ? Number(data.source.confidence) : 1.0
    };

    // Status: active, stale, expired, unknown
    this.status = ["active", "stale", "expired", "unknown"].includes(data.status) ? data.status : "unknown";

    // Permissions
    this.permissions = {
      visibility: data.permissions?.visibility || "public"
    };

    // Arbitrary domain properties
    this.properties = data.properties ? { ...data.properties } : {};
  }

  isFresh(freshnessThresholdSeconds = 300) {
    if (!this.source.observedAt) return false;
    const observedMs = new Date(this.source.observedAt).getTime();
    if (isNaN(observedMs)) return false;
    return (Date.now() - observedMs) / 1000.0 <= freshnessThresholdSeconds;
  }

  toJSON() {
    return {
      id: this.id,
      entityType: this.entityType,
      name: this.name,
      position: this.position,
      geometry: this.geometry,
      source: this.source,
      status: this.status,
      permissions: this.permissions,
      properties: this.properties
    };
  }
}
