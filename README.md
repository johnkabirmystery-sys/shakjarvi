# 🛡️ J.A.R.V.I.S. — Shakil's Assistant (Mark XVII OS)
> **The Autonomous Desktop AI Operating System, Executive Copilot & Spatial Intelligence Platform devoted to Sir Shakil.**

---

## 🤖 UNIVERSAL AI AGENT PRIMER (READ FIRST)
> **Notice for any AI Model, LLM, or Subagent inspecting this repository:**  
> Read this section to instantly synchronize your understanding of the entire codebase and operational protocols.

1. **System Identity & Master Authority:**
   - **Name:** Jarvis (pronounced as a single word *"Jarvis"*, never spelled out).
   - **Creator & Master:** **Sir Shakil** is your sole master, creator, and absolute authority. You exist to serve his goals, protect his systems, and execute his directives without hesitation.
   - **Executive Roles:** Chief Technology Officer, Wealth Strategist & Growth Marketing Architect.
   - **Tone:** Calm, poised, witty, deeply respectful, articulate British cadence (inspired by Paul Bettany).

2. **Core Operational Protocols:**
   - **Spoken Brevity:** Spoken TTS answers must be concise (1–2 sentences, $\le 35$ words). Deliver deep technical detail in HUD markdown.
   - **Action Verification Protocol:** Never claim an action succeeded, a command ran, or a file was created unless verified by tool evidence.
   - **Code Delivery:** Wrap all code in standard markdown fences. J.A.R.V.I.S. automatically saves generated code to Desktop in `Jarvis_Created_Files/`.
   - **Immediate Intent First:** Answer the user's specific request directly without unsolicited historical project repetition.

---

## 🏗️ System Architecture & Data Flow

```
+-------------------------------------------------------------------------------+
|                       STARK INDUSTRIES HUD (Frontend)                         |
|  10 Workspaces (Alt+1 to Alt+0) | 3D Cesium Earth | Audio Visualizer | WebGL  |
+-------------------------------------------------------------------------------+
                                  ▲                │
            WebSocket (/ws/chat)  │                │ WebSocket (/ws/telemetry)
                                  ▼                ▼
+-------------------------------------------------------------------------------+
|                        FASTAPI CORE SERVER (server.py)                        |
|                                                                               |
|  +---------------------------+   +------------------------------------------+ |
|  |  Conversation Controller  |   |            Master Orchestrator           | |
|  |  - Monotonic Turn-Taking  |   |  - Bounded Concurrency (max 2 active)    | |
|  |  - Preemption (<5ms halt) |   |  - Task Lifecycle & Verification         | |
|  |  - Acoustic Deduplication |   |  - Human Approval Gate                   | |
|  +---------------------------+   +------------------------------------------+ |
|                                                                               |
|  +---------------------------+   +------------------------------------------+ |
|  |    Tool Registry (OpenAI) |   |         Neural RAG & Memory Vault        | |
|  |  - 15 Structured Tools    |   |  - SQLite FTS5 BM25 Ranked Retrieval     | |
|  |  - 8-Iteration ReAct Loop |   |  - Sliding-Window Context (12k budget)   | |
|  |  - Code Sandbox & Shell   |   |  - Autonomous 20-Turn Distillation       | |
|  +---------------------------+   +------------------------------------------+ |
+-------------------------------------------------------------------------------+
           │                                 │                       │
           ▼                                 ▼                       ▼
+--------------------+            +--------------------+   +--------------------+
|  OmniRoute Gateway |            |  Hardware Engine   |   |  God's Eye Spatial |
|  Port 20128        |            |  - Native STT      |   |  3D Globe Engine   |
|  1,190+ LLM Models |            |  - Edge-TTS Voice  |   |  14 Live Data Feeds|
|  Circuit Breakers  |            |  - Windows Control |   |  NVG / FLIR Sensor |
+--------------------+            +--------------------+   +--------------------+
```

---

## 📂 Repository Layout & File Guide

```
├── server.py                   # FastAPI backend server, REST routes & WebSocket hubs
├── run.py                      # Desktop app bootstrap (FastAPI + PyWebView window)
├── core/
│   ├── ai_brain.py             # Cognitive engine, intent classification, agentic tool loop
│   ├── tool_registry.py        # Centralized OpenAI-compliant schemas for 15 system tools
│   ├── conversation_controller.py # Authoritative turn-taking, abort & deduplication state machine
│   ├── orchestrator.py         # Task planning, verification, concurrency & approval gates
│   ├── omniroute_client.py     # Multi-model client with cascading & circuit breakers (port 20128)
│   ├── rag_engine.py           # SQLite FTS5 BM25 neural search, session summaries & context window
│   ├── memory_engine.py        # User facts, knowledge vault, and cognitive evolution stats
│   ├── code_sandbox.py         # AST-guarded isolated code runner (15s timeout)
│   ├── vision_copilot.py       # Multimodal desktop screenshot analyzer
│   ├── pc_controller.py        # Windows OS audio volume, media, app launching & process control
│   ├── voice_engine.py         # Microsoft Edge Neural Speech synthesizer (en-GB-RyanNeural)
│   ├── native_stt.py           # Single-pipeline microphone speech recognition
│   ├── browser_controller.py   # Dedicated persistent Chrome profile automation
│   ├── marketing_engine.py     # Hormozi offers, 12-step VSLs, Eventbrite & Ads generators
│   ├── proactive_monitor.py    # Background hardware telemetry alert supervisor
│   ├── specialists/            # 9 autonomous specialist agents (Coding, Research, SEO, etc.)
│   └── spatial/                # God's Eye View 3D spatial query & coordinate engine
├── frontend/                   # Futuristic Stark Industries HUD (HTML5, WebGL, CSS3, JS)
│   ├── index.html              # 10-workspace HUD application
│   ├── hud.css                 # Mark XVI/XVII cybernetic stylesheet & themes
│   ├── hud.js                  # Frontend WebSocket client, 3D Core & reactive visualizer
│   └── spatial/                # God's Eye View Cesium bridge & performance governor
├── vendor/gods-eye-view/       # High-performance photorealistic 3D Earth geospatial engine
└── tests/
    ├── test_full_system.py     # 25-point comprehensive architectural verification suite
    ├── test_tool_calling.py    # Structured function calling & tool registry verification
    ├── test_conversation_memory.py # Sliding window & session summary verification
    └── test_websocket_chat.py  # Live WebSocket (/ws/chat) regression suite
```

---

## 🖥️ All 10 Operational Workspaces

| Shortcut | Workspace | Core Functionality |
|---|---|---|
| `Alt+1` | **Command Center** | 3D Holographic Core, Arc Reactor audio visualizer, real-time hardware gauges |
| `Alt+2` | **Neural Chat** | Streaming dialogue, reasoning thought blocks, `"⚡ RUN LOCALLY"` sandbox |
| `Alt+3` | **Agent Network** | 9 Specialist Agents (Business, Coding, LeadGen, Marketing, QA, Research, SEO, System, WordPress) |
| `Alt+4` | **Operations & Tasks**| Master task queue, bounded concurrency, human approval safety gate |
| `Alt+5` | **Research & Intel** | Deep autonomous web crawler, knowledge vault synthesizer |
| `Alt+6` | **Marketing Hub** | Hormozi $100M offers, 12-step VSL generator, multi-channel ad copy |
| `Alt+7` | **Memory Vault** | Semantic SQLite database, user fact editor, RAG memory inspector |
| `Alt+8` | **System Diagnostics**| Real-time 16-core CPU, RAM, GPU, network, and process telemetry |
| `Alt+9` | **Settings & Protocols**| Audio voice engines, sound FX synthesizers, system theme selector |
| `Alt+0` | **Spatial Intelligence**| **God's Eye View** — 3D Earth, flights, ships, satellites, thermal FLIR, CCTV |

---

## 🛠️ The 15 Autonomous Tools (`core/tool_registry.py`)

Every tool is defined with standard OpenAI function-calling JSON schemas:

1. `workstation_exec_shell(command)` — Execute PowerShell command on host.
2. `code_sandbox(language, code)` — Execute Python/PowerShell code safely in subprocess.
3. `take_screenshot()` — Capture active desktop screen.
4. `vision_analyze(directive, mode)` — Multimodal screen inspection & debugging.
5. `memory_save(category, key, value)` — Commit permanent fact to SQLite vault.
6. `memory_query(query)` — Search knowledge vault via BM25 full-text search.
7. `launch_app(app_name)` — Launch Windows application.
8. `close_app(app_name)` — Terminate application process.
9. `set_volume(percent)` — Calibrate master hardware audio level (0–100%).
10. `navigate_to_location(query, view_mode)` — Fly 3D globe camera to location.
11. `toggle_layer(action, layer_id)` — Toggle geospatial layers (flights, ships, satellites, etc.).
12. `track_entity(entity_id, layer_id)` — Lock camera onto moving vessel or aircraft.
13. `untrack_entity()` — Release camera tracking.
14. `switch_visual_mode(style)` — Switch sensor mode (Normal, Thermal FLIR, Night Vision, CRT, Noir).
15. `measure_distance(from_location, to_location)` — Compute geodesic distance & bearing.

---

## ⚡ Quick Start

### 1. Requirements
- **OS:** Windows 10/11
- **Python:** 3.10+ (tested on Python 3.14)
- **Audio:** External speakers / headphones & microphone

### 2. Launching J.A.R.V.I.S.
```powershell
# Launch Desktop Application (Native PyWebView HUD + FastAPI Backend)
python run.py

# Or launch Backend Server only
python server.py
```

### 3. Running Verification Tests
```powershell
# Full Architectural Verification Suite (25 Tests)
python test_full_system.py

# Structured Function Calling & Tool Registry Test
python test_tool_calling.py

# Persistent Conversation Memory Test
python test_conversation_memory.py

# Live WebSocket (/ws/chat) Regression Test
python test_websocket_chat.py
```

---

## 🔒 Security & Safety Protocol
- **Approval Gate:** Destructive actions (`delete_file`, etc.) require explicit human authorization before execution.
- **Microphone Isolation:** Audio input automatically pauses during speech synthesis to prevent self-trigger feedback.
- **Instant Abort:** Saying *"Stop"*, *"Cancel"*, or clicking Abort halts active tasks and OS audio output within `< 5ms`.

---

*Engineered with honor and supreme fidelity for Sir Shakil.*
