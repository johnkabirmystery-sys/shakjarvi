/**
 * @fileoverview OSM Building Provider
 * Fetches building footprints from OpenStreetMap Overpass API and visualizes them on Cesium globe.
 */

export class OSMBuildingProvider {
    /**
     * @param {object} viewer - Cesium Viewer
     * @param {object} eventBus - Global event bus
     */
    constructor(viewer = null, eventBus = null) {
        this.viewer = viewer;
        this.eventBus = eventBus;
        this.entities = [];
        this.lastRequestTime = 0;
        this.requestQueue = [];
        this.isProcessingQueue = false;
        
        this.state = {
            isLoaded: false,
            buildingCount: 0,
            provider: 'osm_overpass',
            coverageArea: null,
            lastLoadedAt: null,
            attribution: '© OpenStreetMap contributors',
            status: 'idle' // available, loading, loaded, error, rate_limited, idle
        };
    }

    attachViewer(viewer) {
        this.viewer = viewer;
    }

    /**
     * @param {number} latitude 
     * @param {number} longitude 
     * @param {number} radiusKm 
     * @param {object} options 
     */
    async loadBuildingsAround(latitude, longitude, radiusKm = 1, options = {}) {
        return new Promise((resolve, reject) => {
            this.requestQueue.push({ latitude, longitude, radiusKm, options, resolve, reject });
            this._processQueue();
        });
    }

    async _processQueue() {
        if (this.isProcessingQueue || this.requestQueue.length === 0) return;
        this.isProcessingQueue = true;

        while (this.requestQueue.length > 0) {
            const timeSinceLastRequest = Date.now() - this.lastRequestTime;
            if (timeSinceLastRequest < 10000) {
                this.state.status = 'rate_limited';
                await new Promise(resolve => setTimeout(resolve, 10000 - timeSinceLastRequest));
            }

            const req = this.requestQueue.shift();
            if (!req) continue;

            try {
                this.state.status = 'loading';
                this.lastRequestTime = Date.now();
                const count = await this._fetchAndRender(req.latitude, req.longitude, req.radiusKm, req.options);
                req.resolve({ ok: true, buildingCount: count, ...this.state });
            } catch (err) {
                this.state.status = 'error';
                if (this.eventBus) this.eventBus.emit('spatial.buildings.osm.error', { error: err.message });
                console.error("OSMBuildingProvider error:", err);
                req.reject(err);
            }
        }
        
        this.isProcessingQueue = false;
    }

    async _fetchAndRender(lat, lon, radiusKm, options = {}) {
        if (!this.viewer || (typeof this.viewer.isDestroyed === 'function' && this.viewer.isDestroyed())) {
            throw new Error("Viewer not attached or destroyed");
        }
        
        const radiusMeters = Math.min(Math.max(radiusKm * 1000, 100), 5000); // 100m to 5km bound
        const timeoutMs = options.timeoutMs || 15000;
        const query = `[out:json][timeout:15];way["building"](around:${radiusMeters},${lat},${lon});out body;>;out skel qt;`;
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        let response;
        try {
            response = await fetch('https://overpass-api.de/api/interpreter', {
                method: 'POST',
                body: query,
                signal: controller.signal
            });
        } catch (fetchErr) {
            if (fetchErr.name === 'AbortError') {
                throw new Error(`OSM Overpass request timed out (${timeoutMs / 1000}s limit).`);
            }
            throw new Error(`OSM Overpass network error: ${fetchErr.message}`);
        } finally {
            clearTimeout(timeoutId);
        }

        if (!response.ok) {
            throw new Error(`Overpass API error: HTTP ${response.status}`);
        }

        const data = await response.json();
        if (!data || !Array.isArray(data.elements)) {
            data.elements = [];
        }
        
        // Parse OSM nodes
        const nodes = new Map();
        for (const el of data.elements) {
            if (el.type === 'node' && el.id !== undefined && el.lon !== undefined && el.lat !== undefined) {
                nodes.set(el.id, { lon: el.lon, lat: el.lat });
            }
        }

        let newBuildingCount = 0;

        if (this.viewer && !this.viewer.isDestroyed()) {
            for (const el of data.elements) {
                if (this.viewer.isDestroyed()) break;

                if (el.type === 'way' && el.tags && el.tags.building && Array.isArray(el.nodes)) {
                    const coordinates = [];
                    for (const nodeId of el.nodes) {
                        const node = nodes.get(nodeId);
                        if (node) {
                            coordinates.push(node.lon, node.lat);
                        }
                    }
                    
                    if (coordinates.length >= 6) { // At least 3 points
                        let height = 10;
                        if (el.tags['building:levels']) {
                            const lvls = parseInt(el.tags['building:levels'], 10);
                            height = Number.isFinite(lvls) ? Math.max(3, lvls * 3) : 10;
                        } else if (el.tags.height) {
                            const parsedH = parseFloat(el.tags.height);
                            height = Number.isFinite(parsedH) ? Math.max(3, parsedH) : 10;
                        }
                        
                        try {
                            const entity = this.viewer.entities.add({
                                polygon: {
                                    hierarchy: window.Cesium.Cartesian3.fromDegreesArray(coordinates),
                                    extrudedHeight: height,
                                    material: window.Cesium.Color.fromCssColorString('#00e5ff').withAlpha(0.2),
                                    outline: true,
                                    outlineColor: window.Cesium.Color.CYAN,
                                    height: 0
                                },
                                description: 'OSM Building'
                            });
                            this.entities.push(entity);
                            newBuildingCount++;
                        } catch (addErr) {
                            // Non-fatal if a single polygon has invalid topology
                        }
                    }
                }
            }
        }

        this.state.isLoaded = true;
        this.state.buildingCount += newBuildingCount;
        this.state.coverageArea = { lat, lon, radiusKm };
        this.state.lastLoadedAt = new Date().toISOString();
        this.state.status = 'loaded';

        if (this.eventBus) {
            this.eventBus.emit('spatial.buildings.osm.loaded', this.state);
        }

        return newBuildingCount;
    }

    getState() {
        return { ...this.state };
    }

    clear() {
        if (this.viewer && !this.viewer.isDestroyed()) {
            for (const entity of this.entities) {
                try {
                    this.viewer.entities.remove(entity);
                } catch (_) {}
            }
        }
        this.entities = [];
        this.state.isLoaded = false;
        this.state.buildingCount = 0;
        this.state.coverageArea = null;
        this.state.status = 'idle';
    }

    destroy() {
        // Cancel all pending queue requests
        for (const req of this.requestQueue) {
            try {
                req.reject(new Error("OSMBuildingProvider destroyed"));
            } catch (_) {}
        }
        this.requestQueue = [];
        this.clear();
        this.viewer = null;
        this.eventBus = null;
    }
}

export const osmBuildingProvider = new OSMBuildingProvider(null, null);
