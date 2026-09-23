---
name: jarvis-controller
description: "Control, interact with, and monitor Shakil's Assistant (J.A.R.V.I.S.) desktop system. Use to speak out loud via PC speakers, inspect live hardware telemetry, execute Windows PC actions, and query or update the permanent long-term memory vault."
---

# Shakil's Assistant (J.A.R.V.I.S.) Controller Skill

This skill allows Antigravity agents to interface directly with Sir Shakil's J.A.R.V.I.S. desktop assistant, holographic HUD, hardware telemetry, neural voice engine, and persistent memory vault.

## 1. System Endpoints & Architecture

Jarvis runs locally at `http://127.0.0.1:8000`:
- **Real-Time Telemetry**: `GET http://127.0.0.1:8000/ws/telemetry` (or via Python `from core import telemetry; telemetry.get_telemetry_data()`)
- **Neural Voice & Speaker Broadcast**: `POST http://127.0.0.1:8000/api/broadcast`
- **PC Automation & Actions**: `POST http://127.0.0.1:8000/api/action` (or via `from core import pc_controller`)
- **Long-term Memory Vault**: `GET / POST http://127.0.0.1:8000/api/memory` (or via `from core import memory_engine`)
- **Autonomous Research Engine**: `POST http://127.0.0.1:8000/api/research/trigger` (or via `from core import research_engine`)
- **Google Antigravity SDK Status**: `GET http://127.0.0.1:8000/api/antigravity/status`

---

## 2. Common Agent Operations

### A. Speak Out Loud to Sir Shakil
Broadcast a voice message through Sir Shakil's PC speakers and update the holographic HUD:

```python
import requests

requests.post("http://127.0.0.1:8000/api/broadcast", json={
    "text": "Sir Shakil, I have completed the assigned code optimization.",
    "level": "info",
    "play_speaker": True
})
```

### B. Query Live Hardware Telemetry
Retrieve live diagnostics (CPU per-core load, RAM, GPU, storage, foreground window):

```python
from core import telemetry

data = telemetry.get_telemetry_data()
print("Active Window:", data["active_window"])
print("CPU Percent:", data["cpu"]["percent"])
print("RAM Percent:", data["memory"]["percent"])
```

### C. Store Knowledge or User Facts in Permanent Memory
Save an architectural decision, user preference, or financial blueprint into Jarvis's permanent database:

```python
from core import memory_engine

memory_engine.save_fact(
    category="preference",
    key="tech_stack_preference",
    value="Sir Shakil prefers FastAPI backends with modern vanilla HUD interfaces."
)
```

### D. Execute PC Automation Actions
Control system volume, media, or launch applications:

```python
from core import pc_controller

# Adjust volume
pc_controller.set_volume(70)

# Capture screen
pc_controller.take_screenshot()

# Launch tool
pc_controller.launch_app("code")
```
