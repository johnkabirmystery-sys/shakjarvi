/**
 * @fileoverview Spatial Data Manager
 * Central manager for imported spatial data and building providers.
 */

import { geoJsonDataLayer } from './geoJsonDataLayer.js';
import { osmBuildingProvider } from './osmBuildingProvider.js';

export class SpatialDataManager {
    /**
     * @param {object} viewer 
     * @param {object} eventBus 
     */
    constructor(viewer = null, eventBus = null) {
        this.viewer = viewer;
        this.eventBus = eventBus;
    }

    attachViewer(viewer) {
        this.viewer = viewer;
        geoJsonDataLayer.attachViewer(viewer);
        osmBuildingProvider.attachViewer(viewer);
    }

    /**
     * @param {object} geojson 
     * @param {object} options 
     */
    async importGeoJSON(geojson, options = {}) {
        return await geoJsonDataLayer.loadFromObject(geojson, options);
    }

    /**
     * @param {string} url 
     * @param {object} options 
     */
    async importGeoJSONFromUrl(url, options = {}) {
        return await geoJsonDataLayer.loadFromUrl(url, options);
    }

    /**
     * @param {number} lat 
     * @param {number} lon 
     * @param {number} radiusKm 
     * @param {object} options 
     */
    async loadBuildingsNearby(lat, lon, radiusKm = 1, options = {}) {
        return await osmBuildingProvider.loadBuildingsAround(lat, lon, radiusKm, options);
    }

    getImportedDatasets() {
        return geoJsonDataLayer.getLoadedSources();
    }

    getBuildingState() {
        return osmBuildingProvider.getState();
    }

    clearAll() {
        geoJsonDataLayer.clear();
        osmBuildingProvider.clear();
    }

    destroy() {
        this.clearAll();
        osmBuildingProvider.destroy();
        this.viewer = null;
        this.eventBus = null;
    }
}

export const spatialDataManager = new SpatialDataManager(null, null);
