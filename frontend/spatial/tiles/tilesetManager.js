/**
 * J.A.R.V.I.S. 3D Tileset Manager (frontend/spatial/tiles/tilesetManager.js)
 * ==============================================================================
 * Manages 3D Tilesets with explicit lifecycle states, error tracking, maximum
 * screen-space error configuration, memory budgeting, and graceful fallback.
 */

export class TilesetManager {
  constructor(viewer, eventBus) {
    this.viewer = viewer;
    this.eventBus = eventBus;
    this.tilesets = new Map(); // id -> { tileset, status, options }
  }

  attachViewer(viewer) {
    this.viewer = viewer;
  }

  /**
   * Loads a 3D Tileset into the active Cesium scene.
   * @param {string} id - Unique tileset identifier.
   * @param {Function} factory - Async factory function returning a Cesium3DTileset.
   * @param {Object} [options] - Options such as maximumScreenSpaceError.
   */
  async load(id, factory, options = {}) {
    if (!this.viewer || !window.Cesium) {
      return { ok: false, id, error: "Cesium Viewer not available." };
    }

    if (this.tilesets.has(id)) {
      return {
        ok: true,
        id,
        status: "already_loaded"
      };
    }

    try {
      const tileset = await factory(options);
      if (!tileset) {
        throw new Error("Tileset factory returned null or undefined.");
      }

      // Configure screen-space error if requested
      if (Number.isFinite(options.maximumScreenSpaceError)) {
        tileset.maximumScreenSpaceError = options.maximumScreenSpaceError;
      }

      this.viewer.scene.primitives.add(tileset);
      this.tilesets.set(id, {
        tileset,
        status: "loaded",
        options
      });

      if (this.eventBus) {
        this.eventBus.emit("tileset.loaded", { id, status: "loaded" });
      }

      if (this.viewer.scene) this.viewer.scene.requestRender();

      return {
        ok: true,
        id,
        status: "loaded"
      };
    } catch (error) {
      const msg = error.message || String(error);
      console.warn(`[TilesetManager] Failed to load 3D Tileset '${id}':`, msg);

      if (this.eventBus) {
        this.eventBus.emit("tileset.failed", { id, error: msg });
      }

      return {
        ok: false,
        id,
        status: "failed",
        error: msg
      };
    }
  }

  /**
   * Toggles visibility of a loaded tileset.
   */
  setVisible(id, visible) {
    const entry = this.tilesets.get(id);
    if (!entry) {
      return { ok: false, error: `Tileset '${id}' not loaded.` };
    }
    entry.tileset.show = Boolean(visible);
    if (this.viewer?.scene) this.viewer.scene.requestRender();
    return { ok: true, id, visible: Boolean(visible) };
  }

  /**
   * Removes and unloads a 3D Tileset from the active Cesium scene.
   */
  remove(id) {
    const entry = this.tilesets.get(id);
    if (!entry) {
      return {
        ok: false,
        error: `Tileset not loaded: ${id}`
      };
    }

    try {
      this.viewer.scene.primitives.remove(entry.tileset);
      this.tilesets.delete(id);

      if (this.eventBus) {
        this.eventBus.emit("tileset.removed", { id, status: "removed" });
      }

      if (this.viewer.scene) this.viewer.scene.requestRender();

      return {
        ok: true,
        id,
        status: "removed"
      };
    } catch (e) {
      return { ok: false, id, error: e.message || String(e) };
    }
  }

  has(id) {
    return this.tilesets.has(id);
  }

  list() {
    return Array.from(this.tilesets.entries()).map(([id, entry]) => ({
      id,
      status: entry.status,
      visible: entry.tileset?.show !== false
    }));
  }

  destroy() {
    for (const [id] of this.tilesets.entries()) {
      this.remove(id);
    }
    this.tilesets.clear();
    this.viewer = null;
  }
}
