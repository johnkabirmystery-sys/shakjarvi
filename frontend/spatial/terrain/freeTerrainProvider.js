/**
 * @fileoverview Free Terrain Provider Manager
 * Manages free terrain providers for Cesium globe.
 */

export class FreeTerrainProvider {
    /**
     * @param {object} viewer 
     * @param {object} eventBus 
     */
    constructor(viewer = null, eventBus = null) {
        this.viewer = viewer;
        this.eventBus = eventBus;
        this.currentProvider = null;
        this.state = {
            ok: false,
            provider: 'ellipsoid',
            status: 'available', // available, active, degraded, unavailable, error, not_configured
            isRealTerrain: false,
            source: 'WGS84 Ellipsoid',
            attribution: '',
            error: null
        };
    }

    attachViewer(viewer) {
        this.viewer = viewer;
    }

    getAvailableProviders() {
        return [
            {
                name: 'ellipsoid',
                description: 'WGS84 mathematical ellipsoid (always available, no network)',
                isRealTerrain: false
            },
            {
                name: 'arcgis_elevation',
                description: 'Esri ArcGIS World Elevation 3D (free public REST service)',
                isRealTerrain: true
            },
            {
                name: 'cesium_world',
                description: 'Cesium World Terrain (requires Ion token)',
                isRealTerrain: true
            }
        ];
    }

    /**
     * @param {string} providerName 
     */
    async checkAvailability(providerName) {
        if (providerName === 'ellipsoid') return true;
        
        if (providerName === 'arcgis_elevation') {
            if (!navigator.onLine) return false;
            try {
                // Test fetch to Esri elevation service
                const res = await fetch('https://elevation3d.arcgis.com/arcgis/rest/services/WorldElevation3D/Terrain3D/ImageServer?f=json', { method: 'HEAD' });
                return res.ok;
            } catch (e) {
                return false;
            }
        }
        
        if (providerName === 'cesium_world') {
            return !!window.Cesium.Ion.defaultAccessToken;
        }

        return false;
    }

    /**
     * @param {string} providerName 
     * @param {object} options 
     */
    async setProvider(providerName, options = {}) {
        if (!this.viewer) {
            return { ...this.state, ok: false, error: "Viewer not attached", status: 'error' };
        }

        const isAvailable = await this.checkAvailability(providerName);
        
        if (!isAvailable && providerName !== 'ellipsoid') {
            const status = providerName === 'cesium_world' && !window.Cesium.Ion.defaultAccessToken ? 'not_configured' : 'unavailable';
            this.state = {
                ok: false,
                provider: providerName,
                status: status,
                isRealTerrain: false,
                source: providerName,
                attribution: '',
                error: `Provider ${providerName} is not available.`
            };
            return this.state;
        }

        try {
            if (providerName === 'ellipsoid') {
                this.viewer.terrainProvider = new window.Cesium.EllipsoidTerrainProvider();
                this.state = {
                    ok: true,
                    provider: 'ellipsoid',
                    status: 'active',
                    isRealTerrain: false,
                    source: 'WGS84 Ellipsoid',
                    attribution: '',
                    error: null
                };
            } else if (providerName === 'arcgis_elevation') {
                this.viewer.terrainProvider = await window.Cesium.ArcGISTiledElevationTerrainProvider.fromUrl(
                    'https://elevation3d.arcgis.com/arcgis/rest/services/WorldElevation3D/Terrain3D/ImageServer'
                );
                this.state = {
                    ok: true,
                    provider: 'arcgis_elevation',
                    status: 'active',
                    isRealTerrain: true,
                    source: 'Esri ArcGIS World Elevation 3D',
                    attribution: 'Esri, USGS',
                    error: null
                };
            } else if (providerName === 'cesium_world') {
                this.viewer.terrainProvider = await window.Cesium.createWorldTerrainAsync();
                this.state = {
                    ok: true,
                    provider: 'cesium_world',
                    status: 'active',
                    isRealTerrain: true,
                    source: 'Cesium World Terrain',
                    attribution: 'Cesium Ion',
                    error: null
                };
            } else {
                throw new Error("Unknown terrain provider: " + providerName);
            }
        } catch (error) {
            this.state = {
                ok: false,
                provider: providerName,
                status: 'error',
                isRealTerrain: false,
                source: providerName,
                attribution: '',
                error: error.message
            };
        }

        return this.state;
    }

    getState() {
        return { ...this.state };
    }
}

export const freeTerrainProvider = new FreeTerrainProvider(null, null);
