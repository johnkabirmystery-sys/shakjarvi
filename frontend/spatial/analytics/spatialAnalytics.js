/**
 * J.A.R.V.I.S. Spatial Analytics Engine (frontend/spatial/analytics/spatialAnalytics.js)
 * =======================================================================================
 * Deterministic client-side geospatial calculations:
 * - Great-circle geodesic distance (Haversine & Vincenty approximation)
 * - Initial forward azimuth / bearing (degrees)
 * - Spatial bounding-box and radius queries
 * - Point-in-polygon ray-casting and circular geofencing
 * - Distance-aware entity clustering for rendering optimization
 */

const EARTH_RADIUS_METERS = 6371008.8;

export class SpatialAnalytics {
  /**
   * Calculates the geodesic distance between two coordinate pairs in meters.
   */
  static calculateDistanceMeters(lat1, lon1, lat2, lon2) {
    const phi1 = (lat1 * Math.PI) / 180.0;
    const phi2 = (lat2 * Math.PI) / 180.0;
    const deltaPhi = ((lat2 - lat1) * Math.PI) / 180.0;
    const deltaLambda = ((lon2 - lon1) * Math.PI) / 180.0;

    const a =
      Math.sin(deltaPhi / 2.0) * Math.sin(deltaPhi / 2.0) +
      Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2.0) * Math.sin(deltaLambda / 2.0);
    const c = 2.0 * Math.atan2(Math.sqrt(a), Math.sqrt(Math.max(0.0, 1.0 - a)));

    return EARTH_RADIUS_METERS * c;
  }

  /**
   * Calculates the initial forward bearing/azimuth from point 1 to point 2 in degrees [0, 360).
   */
  static calculateBearingDegrees(lat1, lon1, lat2, lon2) {
    const phi1 = (lat1 * Math.PI) / 180.0;
    const phi2 = (lat2 * Math.PI) / 180.0;
    const deltaLambda = ((lon2 - lon1) * Math.PI) / 180.0;

    const y = Math.sin(deltaLambda) * Math.cos(phi2);
    const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(deltaLambda);
    const theta = Math.atan2(y, x);

    return ((theta * 180.0) / Math.PI + 360.0) % 360.0;
  }

  /**
   * Filters entities residing within a circular radius of a center coordinate.
   */
  static queryWithinRadius(entities, centerLat, centerLon, radiusMeters) {
    const results = [];
    for (const entity of entities) {
      const pos = entity.position || (entity.geometry?.type === "Point" ? {
        latitude: entity.geometry.coordinates[1],
        longitude: entity.geometry.coordinates[0]
      } : null);

      if (pos && Number.isFinite(pos.latitude) && Number.isFinite(pos.longitude)) {
        const dist = this.calculateDistanceMeters(centerLat, centerLon, pos.latitude, pos.longitude);
        if (dist <= radiusMeters) {
          results.push({
            entity,
            distanceMeters: Math.round(dist)
          });
        }
      }
    }

    results.sort((a, b) => a.distanceMeters - b.distanceMeters);

    return {
      ok: true,
      results,
      count: results.length,
      queryId: `radius_${Date.now()}`,
      generatedAt: new Date().toISOString(),
      dataStatus: "complete"
    };
  }

  /**
   * Filters entities residing inside a rectangular bounding box.
   */
  static queryWithinBoundingBox(entities, minLat, minLon, maxLat, maxLon) {
    const results = [];
    for (const entity of entities) {
      const pos = entity.position || (entity.geometry?.type === "Point" ? {
        latitude: entity.geometry.coordinates[1],
        longitude: entity.geometry.coordinates[0]
      } : null);

      if (pos && Number.isFinite(pos.latitude) && Number.isFinite(pos.longitude)) {
        if (pos.latitude >= minLat && pos.latitude <= maxLat && pos.longitude >= minLon && pos.longitude <= maxLon) {
          results.push(entity);
        }
      }
    }

    return {
      ok: true,
      results,
      count: results.length,
      queryId: `bbox_${Date.now()}`,
      generatedAt: new Date().toISOString(),
      dataStatus: "complete"
    };
  }

  /**
   * Checks if a point is inside a polygon using ray-casting algorithm.
   */
  static isPointInPolygon(lat, lon, polygonCoords) {
    let inside = false;
    for (let i = 0, j = polygonCoords.length - 1; i < polygonCoords.length; j = i++) {
      const xi = polygonCoords[i][0], yi = polygonCoords[i][1];
      const xj = polygonCoords[j][0], yj = polygonCoords[j][1];

      const intersect = ((yi > lat) !== (yj > lat)) &&
        (lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  }

  /**
   * Clusters a dense collection of entities for rendering efficiency.
   */
  static clusterEntities(entities, clusterDistanceMeters = 20000) {
    const clusters = [];
    const visited = new Set();

    for (let i = 0; i < entities.length; i++) {
      if (visited.has(i)) continue;

      const base = entities[i];
      const posA = base.position || { latitude: base.latitude, longitude: base.longitude };
      if (!posA || !Number.isFinite(posA.latitude)) continue;

      const currentCluster = [base];
      visited.add(i);

      for (let j = i + 1; j < entities.length; j++) {
        if (visited.has(j)) continue;

        const candidate = entities[j];
        const posB = candidate.position || { latitude: candidate.latitude, longitude: candidate.longitude };
        if (!posB || !Number.isFinite(posB.latitude)) continue;

        const dist = this.calculateDistanceMeters(posA.latitude, posA.longitude, posB.latitude, posB.longitude);
        if (dist <= clusterDistanceMeters) {
          currentCluster.push(candidate);
          visited.add(j);
        }
      }

      clusters.push({
        center: posA,
        count: currentCluster.length,
        entities: currentCluster
      });
    }

    return clusters;
  }
}
