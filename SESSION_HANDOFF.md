# J.A.R.V.I.S. MARK XVI — EXECUTIVE SESSION HANDOFF & SYSTEM STATE
**Generated:** September 24, 2026 | **Target:** New Low-Context Chat Session Initialization

---

## 1. System Overview & Core Architecture
- **Product:** J.A.R.V.I.S. (Shakil's Assistant) Mark XVI AI Operating System.
- **Hardware Environment:** Windows 11 Mini PC, AMD Ryzen 7 7840HS (8C/16T), 16 GB DDR5 RAM, external USB/3.5mm audio peripherals.
- **Backend:** Python 3.14 + FastAPI (`server.py`) on port `8000`.
- **LLM Gateway:** OmniRoute multi-model gateway on port `20128` (1,156 models available, primary: `agy/gemini-3.7-flash-low`, `auto/chat`).
- **Desktop Runtime:** Native `pywebview` window via `run.py`.
- **WebSockets:** `/ws/chat` (bidirectional dialogue & tool stream), `/ws/telemetry` (real-time hardware & pipeline stats).

---

## 2. All 10 Operational Workspaces (Keyboard Shortcuts: Alt+1 to Alt+0)
1. **Command Center (`Alt+1`)**: Reference Stark Mark XVI HUD with interactive 3D Holographic Core (Helmet, Arc Reactor, Planetary Grid), audio frequency vertex deformation, and status telemetry.
2. **Neural Chat (`Alt+2`)**: Dedicated streaming dialogue with thought reasoning blocks and interactive `"⚡ RUN LOCALLY"` sandbox execution buttons.
3. **Agent Network (`Alt+3`)**: 9 autonomous specialists (Business, Coding, LeadGen, Marketing, QA, Research, SEO, System, WordPress).
4. **Operations & Tasks (`Alt+4`)**: Master task pipeline, bounded concurrency (max 2 parallel), human-in-the-loop approval gate.
5. **Research & Intel (`Alt+5`)**: Deep research engine with autonomous web scraping and multi-source synthesis.
6. **Marketing Hub (`Alt+6`)**: Hormozi $100M offers, 12-step VSL script generator, omnichannel retargeting cascades.
7. **Memory Vault (`Alt+7`)**: Semantic SQLite knowledge database with RAG retrieval and user preference persistence.
8. **System Diagnostics (`Alt+8`)**: Real-time CPU, RAM, GPU, network, and process telemetry.
9. **Settings & Protocols (`Alt+9`)**: Audio voice engine configuration, sound FX toggles, and OS protocols.
10. **Spatial Intelligence (`Alt+0`)**: **God's Eye View** integration with 3D Cesium Earth, live telemetry HUD, layer chips (flights, ships, satellites, weather, fires, quakes, CCTV, radio), and sensor modes (NVG, FLIR thermal, CRT retro, noir).

---

## 3. Latest Completed Upgrades

### Track 1: God's Eye View Deep Architectural Integration
- **Upstream Verified:** `vendor/gods-eye-view` fully audited; 4,879/4,879 upstream unit tests and GC benchmarks pass (100%).
- **Python Spatial Backend (`core/spatial/`):**
  - `spatial_session.py`: Coordinates, layers, entity tracking, mission tracking, and agent handoffs.
  - `spatial_query_engine.py`: Haversine distance, initial bearing, spherical polygon area, point-in-polygon ray-casting, and LLM-safe bounded entity summarization.
  - `provider_manager.py`: Health tracking & circuit breakers for 14 geospatial providers.
  - `spatial_tools.py`: 8 declarative spatial tools (`navigate_to_location`, `zoom_to_globe`, `track_entity`, `untrack_entity`, `toggle_layer`, `switch_visual_mode`, `measure_distance`, `query_nearby_entities`).
  - `spatial_service.py`: Central coordination and WebSocket event broadcasting.
- **Frontend Modules (`frontend/spatial/`):**
  - `spatialEventBus.js`, `spatialState.js`, `spatialPerformanceGovernor.js` (Ryzen 7 7840HS budget, dynamic DPR, requestRenderMode idle governor, background tab throttling), `networkBudgetManager.js`, `godsEyeAdapter.js`, `spatialCommandBus.js`, `spatialDiagnostics.js`, `spatialService.js`.
- **FastAPI Endpoints:** `/api/spatial/command`, `/api/spatial/state`, `/api/spatial/health`, `/api/spatial/session`, `/api/spatial/providers`, `/api/spatial/query`, and `/spatial` static mount for Cesium bundle.

### Track 2: Power & Visual Upgrades
- **Code Execution Sandbox (`core/code_sandbox.py`):** Isolated subprocess runner for Python/PowerShell with AST syntax checking and a 15-second timeout guard.
- **Screen Vision Copilot (`core/vision_copilot.py`):** Multimodal screen analysis for UI inspection and code debugging.
- **Interactive 3D Holographic Core:** Physics inertia, drag-to-rotate, mouse-wheel zoom, double-click shockwaves, and Web Audio API frequency-reactive vertex deformation.
- **4 Tactical HUD Themes:** Mark XVI Tactical (Cyan), War Machine (Red/Gold), Stealth (Emerald), Neural Matrix (Magenta/Purple).
- **Stark Audio FX Engine:** Web Audio synthesizer with tactical soundscapes.
- **Cybernetic Terminal Drawer (`~`):** Slide-out live console for running PowerShell commands.
- **Spotlight Command Palette (`Ctrl+K`):** Global fuzzy-search launcher with 30+ directives including spatial shortcuts.
- **Audio Routing & Hardware Matrix:** Hotplug mic/speaker detection, anti-echo duplex lock, and spoken brevity constraint (<= 35 words).

---

## 4. Test Verification Status (100% Green)
- `test_spatial_integration.py`: **6/6 phases PASS (100%)**
- `test_spatial_core.py`: **6/6 tests PASS (100%)**
- `test_spatial_endpoints.py`: **6/6 tests PASS (100%)**
- `test_power_upgrades.py`: **5/5 tests PASS (100%)**
- `test_server_endpoints.py`: **3/3 tests PASS (100%)**
- `test_full_system.py`: **25/25 architectural tests PASS (100%)**
- Upstream God's Eye View: **4,879/4,879 tests PASS (100%)**

---

## 5. How to Run
```powershell
# Launch Full Desktop Application (FastAPI + PyWebView Native Window)
python run.py

# Launch Backend Server Only
python server.py

# Run Integration Verification Suite
python test_spatial_integration.py
python test_full_system.py
```
