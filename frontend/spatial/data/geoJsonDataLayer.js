/**
 * @fileoverview GeoJSON Data Layer for Cesium
 * Handles importing and visualizing GeoJSON data.
 */

import { SpatialEntity } from '../core/spatialEntity.js';
import { SpatialAnalytics } from '../analytics/spatialAnalytics.js';

export class GeoJsonDataLayer {
    /**
     * @param {object} viewer - Cesium Viewer instance
     * @param {object} eventBus - Global event bus
     */
    constructor(viewer = null, eventBus = null) {
        this.viewer = viewer;
        this.eventBus = eventBus;
        this.dataSources = new Map();
    }

    /**
     * Attaches the Cesium viewer instance
     * @param {object} viewer 
     */
    attachViewer(viewer) {
        this.viewer = viewer;
    }

    /**
     * Loads GeoJSON from an object
     * @param {object} geojsonObject 
     * @param {object} options 
     * @returns {Promise<string>} dataSourceId
     */
    async loadFromObject(geojsonObject, options = {}) {
        try {
            if (!this.viewer) throw new Error("Viewer not attached");
            this._validateGeoJSON(geojsonObject);
            
            // Generate ID
            const id = `geojson_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            const dataSource = await window.Cesium.GeoJsonDataSource.load(geojsonObject, {
                stroke: options.stroke || window.Cesium.Color.WHITE,
                fill: options.fill || window.Cesium.Color.WHITE.withAlpha(0.5),
                strokeWidth: options.strokeWidth || 2,
                markerSize: options.markerSize || 48,
                markerColor: options.markerColor || window.Cesium.Color.ROYALBLUE,
                clampToGround: options.clampToGround || false
            });

            dataSource.name = options.name || id;
            this.viewer.dataSources.add(dataSource);
            
            const metadata = {
                id,
                name: dataSource.name,
                featureCount: dataSource.entities.values.length,
                loadedAt: new Date().toISOString()
            };
            
            this.dataSources.set(id, { dataSource, metadata });
            
            if (this.eventBus) {
                this.eventBus.emit('spatial.geojson.loaded', metadata);
            }
            
            return id;
        } catch (error) {
            if (this.eventBus) {
                this.eventBus.emit('spatial.geojson.error', { error: error.message });
            }
            console.error("GeoJsonDataLayer load error:", error);
            return null;
        }
    }

    /**
     * Load from URL
     * @param {string} url 
     * @param {object} options 
     */
    async loadFromUrl(url, options = {}) {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            return await this.loadFromObject(data, options);
        } catch (error) {
            if (this.eventBus) {
                this.eventBus.emit('spatial.geojson.error', { error: error.message });
            }
            console.error("GeoJsonDataLayer URL load error:", error);
            return null;
        }
    }

    /**
     * Load from File
     * @param {File} file 
     * @param {object} options 
     */
    async loadFromFile(file, options = {}) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    const data = JSON.parse(e.target.result);
                    const id = await this.loadFromObject(data, options);
                    resolve(id);
                } catch (err) {
                    if (this.eventBus) this.eventBus.emit('spatial.geojson.error', { error: err.message });
                    console.error("GeoJsonDataLayer File parse error:", err);
                    resolve(null);
                }
            };
            reader.onerror = (e) => {
                if (this.eventBus) this.eventBus.emit('spatial.geojson.error', { error: "File read error" });
                resolve(null);
            };
            reader.readAsText(file);
        });
    }

    _validateGeoJSON(geojson) {
        if (!geojson || (geojson.type !== 'FeatureCollection' && geojson.type !== 'Feature')) {
            throw new Error("Invalid GeoJSON type. Must be FeatureCollection or Feature.");
        }
        
        const features = geojson.type === 'FeatureCollection' ? geojson.features : [geojson];
        if (!Array.isArray(features)) {
            throw new Error("FeatureCollection must have a features array.");
        }
        
        for (const feature of features) {
            if (!feature.geometry || !feature.geometry.type || !feature.geometry.coordinates) {
                throw new Error("Invalid Feature: missing geometry or coordinates.");
            }
            this._validateCoordinates(feature.geometry.coordinates);
        }
    }

    _validateCoordinates(coords) {
        if (typeof coords[0] === 'number') {
            const [lon, lat] = coords;
            if (lat < -90 || lat > 90) throw new Error(`Invalid latitude: ${lat}`);
            if (lon < -180 || lon > 180) throw new Error(`Invalid longitude: ${lon}`);
        } else if (Array.isArray(coords)) {
            for (const c of coords) {
                this._validateCoordinates(c);
            }
        }
    }

    /**
     * Remove data source by id
     * @param {string} dataSourceId 
     */
    remove(dataSourceId) {
        const item = this.dataSources.get(dataSourceId);
        if (item && this.viewer) {
            this.viewer.dataSources.remove(item.dataSource);
            this.dataSources.delete(dataSourceId);
            if (this.eventBus) {
                this.eventBus.emit('spatial.geojson.removed', { id: dataSourceId });
            }
        }
    }

    /**
     * Clear all data sources
     */
    clear() {
        if (!this.viewer) return;
        for (const [id, item] of this.dataSources.entries()) {
            this.viewer.dataSources.remove(item.dataSource);
            if (this.eventBus) {
                this.eventBus.emit('spatial.geojson.removed', { id });
            }
        }
        this.dataSources.clear();
    }

    /**
     * Get loaded sources metadata
     * @returns {Array<object>}
     */
    getLoadedSources() {
        return Array.from(this.dataSources.values()).map(item => item.metadata);
    }

    /**
     * Convert entities to SpatialEntity format
     * @param {string} dataSourceId 
     * @returns {Array<SpatialEntity>}
     */
    getEntities(dataSourceId) {
        const item = this.dataSources.get(dataSourceId);
        if (!item) return [];
        
        return item.dataSource.entities.values.map(entity => {
            return new SpatialEntity({
                id: entity.id,
                name: entity.name,
                description: entity.description ? entity.description.getValue() : '',
                entity: entity
            });
        });
    }
}

export const geoJsonDataLayer = new GeoJsonDataLayer(null, null);
