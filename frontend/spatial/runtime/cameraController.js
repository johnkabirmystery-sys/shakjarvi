/**
 * J.A.R.V.I.S. Camera Controller (frontend/spatial/runtime/cameraController.js)
 * ==============================================================================
 * Comprehensive programmatic camera control with strict validation, zero-value
 * preservation, smooth interpolation, target tracking, and orbit dynamics.
 */

export function validateCoordinates(latitude, longitude) {
  return (
    Number.isFinite(latitude) &&
    Number.isFinite(longitude) &&
    latitude >= -90.0 &&
    latitude <= 90.0 &&
    longitude >= -180.0 &&
    longitude <= 180.0
  );
}

export function validateHeight(height, minHeight = 0, maxHeight = 50000000.0) {
  return Number.isFinite(height) && height >= minHeight && height <= maxHeight;
}

export class CameraController {
  constructor(viewer) {
    this.viewer = viewer;
    this._orbitTimer = null;
    this._trackedEntity = null;
    this._moveEndListener = null;
  }

  attachViewer(viewer) {
    this.viewer = viewer;
  }

  /**
   * Fly camera to explicit geographic coordinates.
   */
  async flyToCoordinates(params = {}) {
    if (!this.viewer || !window.Cesium) {
      return { ok: false, error: "Cesium Viewer not initialized." };
    }

    const Cesium = window.Cesium;
    const lat = Number(params.latitude);
    const lon = Number(params.longitude);
    const height = Number.isFinite(params.height)
      ? Number(params.height)
      : (Number.isFinite(params.altitude) ? Number(params.altitude) : (Number.isFinite(params.rangeM) ? Number(params.rangeM) : 15000.0));
    const duration = Number.isFinite(params.duration) ? Math.max(0.1, Math.min(10.0, Number(params.duration))) : 2.0;

    if (!validateCoordinates(lat, lon)) {
      return {
        ok: false,
        error: `Invalid coordinates: latitude=${params.latitude}, longitude=${params.longitude}. Latitude must be [-90, 90], Longitude [-180, 180].`
      };
    }

    if (!validateHeight(height)) {
      return {
        ok: false,
        error: `Invalid altitude/height: ${height}. Must be a finite non-negative number <= 50,000,000m.`
      };
    }

    // Stop active orbiting or entity tracking
    this.stopOrbit();
    this.stopFollowing();

    const destination = Cesium.Cartesian3.fromDegrees(lon, lat, height);

    const heading = Number.isFinite(params.heading) ? Cesium.Math.toRadians(Number(params.heading)) : undefined;
    const pitch = Number.isFinite(params.pitch) ? Cesium.Math.toRadians(Number(params.pitch)) : undefined;
    const roll = Number.isFinite(params.roll) ? Cesium.Math.toRadians(Number(params.roll)) : undefined;

    const orientation = (heading !== undefined || pitch !== undefined || roll !== undefined) ? {
      heading: heading !== undefined ? heading : this.viewer.camera.heading,
      pitch: pitch !== undefined ? pitch : this.viewer.camera.pitch,
      roll: roll !== undefined ? roll : this.viewer.camera.roll
    } : undefined;

    return new Promise((resolve) => {
      this.viewer.camera.flyTo({
        destination,
        orientation,
        duration,
        complete: () => {
          if (this.viewer?.scene) this.viewer.scene.requestRender();
          resolve({
            ok: true,
            status: "completed",
            destination: { latitude: lat, longitude: lon, height },
            duration
          });
        },
        cancel: () => {
          resolve({
            ok: false,
            status: "cancelled",
            error: "Camera flight was interrupted by user or another command."
          });
        }
      });
      if (this.viewer.scene) this.viewer.scene.requestRender();
    });
  }

  /**
   * Adjust camera zoom in or out.
   */
  zoom(direction = "in", amount = null) {
    if (!this.viewer?.camera) {
      return { ok: false, error: "Viewer camera not available." };
    }

    const currentHeight = this.viewer.camera.positionCartographic?.height || 1000000.0;
    const delta = Number.isFinite(amount) && amount > 0
      ? Number(amount)
      : (direction === "out" ? currentHeight * 0.5 : currentHeight * 0.35);

    if (direction === "out") {
      this.viewer.camera.zoomOut(delta);
    } else {
      this.viewer.camera.zoomIn(delta);
    }

    if (this.viewer.scene) this.viewer.scene.requestRender();

    const newHeight = this.viewer.camera.positionCartographic?.height;
    return { ok: true, direction, delta, currentHeight: newHeight };
  }

  /**
   * Reset camera to planetary overview.
   */
  async resetCamera(duration = 2.5) {
    return this.flyToCoordinates({
      latitude: 20.0,
      longitude: 0.0,
      height: 20000000.0,
      duration
    });
  }

  /**
   * Sets camera orientation (heading, pitch, roll in degrees).
   */
  setOrientation({ heading = 0, pitch = -90, roll = 0 } = {}) {
    if (!this.viewer?.camera || !window.Cesium) {
      return { ok: false, error: "Viewer camera not available." };
    }
    const Cesium = window.Cesium;
    this.viewer.camera.setView({
      orientation: {
        heading: Cesium.Math.toRadians(heading),
        pitch: Cesium.Math.toRadians(pitch),
        roll: Cesium.Math.toRadians(roll)
      }
    });
    if (this.viewer.scene) this.viewer.scene.requestRender();
    return { ok: true, orientation: { heading, pitch, roll } };
  }

  /**
   * Orbit target location or entity.
   */
  startOrbit(targetCartesian = null, speedDegPerSec = 10.0) {
    if (!this.viewer || !window.Cesium) return { ok: false, error: "Viewer unavailable." };
    const Cesium = window.Cesium;
    this.stopOrbit();

    const center = targetCartesian || this.viewer.scene.camera.position;
    const rate = Cesium.Math.toRadians(speedDegPerSec) / 60.0;

    this._orbitTimer = setInterval(() => {
      if (this.viewer?.camera) {
        this.viewer.camera.rotate(Cesium.Cartesian3.UNIT_Z, rate);
        if (this.viewer.scene) this.viewer.scene.requestRender();
      }
    }, 16);

    return { ok: true, status: "orbiting", speedDegPerSec };
  }

  stopOrbit() {
    if (this._orbitTimer) {
      clearInterval(this._orbitTimer);
      this._orbitTimer = null;
    }
    return { ok: true, status: "orbit_stopped" };
  }

  /**
   * Follow a tracked entity.
   */
  followEntity(entity) {
    if (!this.viewer) return { ok: false, error: "Viewer unavailable." };
    this._trackedEntity = entity;
    this.viewer.trackedEntity = entity;
    if (this.viewer.scene) this.viewer.scene.requestRender();
    return { ok: true, status: "following", entityId: entity?.id };
  }

  stopFollowing() {
    if (!this.viewer) return { ok: false, error: "Viewer unavailable." };
    this._trackedEntity = null;
    this.viewer.trackedEntity = undefined;
    if (this.viewer.scene) this.viewer.scene.requestRender();
    return { ok: true, status: "stopped_following" };
  }

  /**
   * Reads the current ground-truth camera state.
   */
  getCameraState() {
    if (!this.viewer?.camera || !window.Cesium) {
      return { latitude: null, longitude: null, height: null, heading: null, pitch: null, roll: null };
    }
    const Cesium = window.Cesium;
    const camera = this.viewer.camera;
    const carto = camera.positionCartographic;

    if (!carto) {
      return { latitude: null, longitude: null, height: null, heading: null, pitch: null, roll: null };
    }

    return {
      latitude: parseFloat(Cesium.Math.toDegrees(carto.latitude).toFixed(4)),
      longitude: parseFloat(Cesium.Math.toDegrees(carto.longitude).toFixed(4)),
      height: Math.round(carto.height),
      heading: Math.round(Cesium.Math.toDegrees(camera.heading)),
      pitch: Math.round(Cesium.Math.toDegrees(camera.pitch)),
      roll: Math.round(Cesium.Math.toDegrees(camera.roll))
    };
  }

  destroy() {
    this.stopOrbit();
    this.stopFollowing();
    this.viewer = null;
  }
}
