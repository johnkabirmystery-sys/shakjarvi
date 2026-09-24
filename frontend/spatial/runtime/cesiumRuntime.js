/**
 * J.A.R.V.I.S. Cesium Runtime Loader (frontend/spatial/runtime/cesiumRuntime.js)
 * ==============================================================================
 * Manages loading, lifecycle, and baseline configuration of the Cesium 1.138+ runtime.
 * Strictly uses local vendor bundles by default with optional remote Ion token config.
 */

export const RUNTIME_STATUS = {
  UNLOADED: "unloaded",
  LOADING: "loading",
  READY: "ready",
  FAILED: "failed"
};

class CesiumRuntime {
  constructor() {
    this.status = RUNTIME_STATUS.UNLOADED;
    this.version = null;
    this.lastError = null;
    this._loadPromise = null;
    this._baseUrl = "/spatial/cesium/";
    this._ionToken = null;
  }

  setBaseUrl(url) {
    this._baseUrl = url;
    if (typeof window !== "undefined") {
      window.CESIUM_BASE_URL = url;
    }
  }

  setIonToken(token) {
    this._ionToken = token;
    if (typeof window !== "undefined" && window.Cesium?.Ion) {
      window.Cesium.Ion.defaultAccessToken = token || "";
    }
  }

  getIonToken() {
    if (this._ionToken) return this._ionToken;
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("jarvis_cesium_ion_token");
      if (stored) return stored;
      return window.CESIUM_ION_TOKEN || "";
    }
    return "";
  }

  async load() {
    if (this.status === RUNTIME_STATUS.READY && window.Cesium) {
      return window.Cesium;
    }

    if (this._loadPromise) {
      return this._loadPromise;
    }

    this.status = RUNTIME_STATUS.LOADING;
    this.lastError = null;

    this._loadPromise = (async () => {
      try {
        if (typeof window === "undefined") {
          throw new Error("CesiumRuntime requires a browser window environment.");
        }

        window.CESIUM_BASE_URL = this._baseUrl;

        // 1. Inject Cesium Widgets CSS if not present
        if (!document.getElementById("cesiumWidgetsCss")) {
          const link = document.createElement("link");
          link.id = "cesiumWidgetsCss";
          link.rel = "stylesheet";
          link.href = `${this._baseUrl}Widgets/widgets.css`;
          document.head.appendChild(link);
        }

        // 2. Load Cesium script if Cesium is not already on window
        if (!window.Cesium) {
          await new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.id = "cesiumBundleScript";
            script.src = `${this._baseUrl}Cesium.js`;
            script.async = true;
            script.onload = () => resolve();
            script.onerror = (e) => reject(new Error(`Failed to load Cesium asset from ${script.src}`));
            document.head.appendChild(script);
          });
        }

        if (!window.Cesium) {
          throw new Error("window.Cesium is undefined after script execution.");
        }

        // Configure default Ion token if available
        const token = this.getIonToken();
        if (window.Cesium.Ion) {
          window.Cesium.Ion.defaultAccessToken = token;
        }

        this.version = window.Cesium.VERSION || "1.138.0";
        this.status = RUNTIME_STATUS.READY;
        console.log(`[CesiumRuntime] Cesium v${this.version} runtime initialized successfully.`);
        return window.Cesium;
      } catch (err) {
        this.status = RUNTIME_STATUS.FAILED;
        this.lastError = err.message || String(err);
        console.error("[CesiumRuntime] Failed to load Cesium runtime:", err);
        throw err;
      } finally {
        this._loadPromise = null;
      }
    })();

    return this._loadPromise;
  }

  isReady() {
    return this.status === RUNTIME_STATUS.READY && Boolean(window.Cesium);
  }
}

export const cesiumRuntime = new CesiumRuntime();
