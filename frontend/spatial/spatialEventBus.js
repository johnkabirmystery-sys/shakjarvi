/**
 * J.A.R.V.I.S. Spatial Event Bus (frontend/spatial/spatialEventBus.js)
 * ===================================================================
 * Pub/Sub event communication for spatial events, camera motions,
 * entity tracking, layer states, and performance transitions.
 */

class SpatialEventBus {
  constructor() {
    this.handlers = new Map();
  }

  on(event, handler) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event).add(handler);
    return () => this.off(event, handler);
  }

  off(event, handler) {
    if (this.handlers.has(event)) {
      this.handlers.get(event).delete(handler);
    }
  }

  emit(event, data = {}) {
    const record = {
      event,
      data,
      timestamp: Date.now()
    };
    if (this.handlers.has(event)) {
      for (const fn of this.handlers.get(event)) {
        try {
          fn(record.data, record);
        } catch (err) {
          console.error(`[SpatialEventBus] Error in handler for '${event}':`, err);
        }
      }
    }
    // Also trigger wildcard listeners
    if (this.handlers.has("*")) {
      for (const fn of this.handlers.get("*")) {
        try {
          fn(event, record.data, record);
        } catch (err) {}
      }
    }
  }
}

export const spatialEventBus = new SpatialEventBus();
if (typeof window !== "undefined") {
  window.__jarvisSpatialEventBus = spatialEventBus;
}
