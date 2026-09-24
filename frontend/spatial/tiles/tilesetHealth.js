/**
 * J.A.R.V.I.S. Tileset Health Tracker (frontend/spatial/tiles/tilesetHealth.js)
 * ==============================================================================
 * Telemetry and health tracker for 3D Tilesets, tile loading errors, and memory load.
 */

export class TilesetHealth {
  constructor(tilesetManager) {
    this.tilesetManager = tilesetManager;
    this.failedTilesCount = 0;
    this.lastError = null;
  }

  attachTileset(id, tileset) {
    if (!tileset) return;
    tileset.tileFailed?.addEventListener((event) => {
      this.failedTilesCount++;
      this.lastError = event.message || "Tile failed to load";
      console.warn(`[TilesetHealth] Tile failed in tileset '${id}':`, event);
    });
  }

  getHealth() {
    return {
      activeTilesets: this.tilesetManager.list(),
      failedTilesCount: this.failedTilesCount,
      lastError: this.lastError
    };
  }
}
