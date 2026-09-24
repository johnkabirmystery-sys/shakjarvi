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
            try {
                this.state.status = 'loading';
                this.lastRequestTime = Date.now();
                await this._fetchAndRender(req.latitude, req.longitude, req.radiusKm, req.options);
                req.resolve();
            } catch (err) {
                this.state.status = 'error';
                if (this.eventBus) this.eventBus.emit('spatial.buildings.osm.error', { error: err.message });
                console.error("OSMBuildingProvider error:", err);
                req.reject(err);
            }
        }
        
        this.isProcessingQueue = false;
    }

    async _fetchAndRender(lat, lon, radiusKm, options) {
        if (!this.viewer) throw new Error("Viewer not attached");
        
        const radiusMeters = radiusKm * 1000;
        const query = `[out:json][timeout:25];way["building"](around:${radiusMeters},${lat},${lon});out body;>;out skel qt;`;
        
        const response = await fetch('https://overpass-api.de/api/interpreter', {
            method: 'POST',
            body: query
        });

        if (!response.ok) {
            throw new Error(`Overpass API error: ${response.status}`);
        }

        const data = await response.json();
        
        // Parse OSM nodes
        const nodes = new Map();
        for (const el of data.elements) {
            if (el.type === 'node') {
                nodes.set(el.id, { lon: el.lon, lat: el.lat });
            }
        }

        let newBuildingCount = 0;

        for (const el of data.elements) {
            if (el.type === 'way' && el.tags && el.tags.building) {
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
                        height = Math.max(3, parseInt(el.tags['building:levels']) * 3);
                    } else if (el.tags.height) {
                        height = parseFloat(el.tags.height) || 10;
                    }
                    
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
    }

    getState() {
        return { ...this.state };
    }

    clear() {
        if (!this.viewer) return;
        for (const entity of this.entities) {
            this.viewer.entities.remove(entity);
        }
        this.entities = [];
        this.state.isLoaded = false;
        this.state.buildingCount = 0;
        this.state.coverageArea = null;
        this.state.status = 'idle';
    }

    destroy() {
        this.clear();
        this.requestQueue = [];
        this.viewer = null;
        this.eventBus = null;
    }
}

export const osmBuildingProvider = new OSMBuildingProvider(null, null);
