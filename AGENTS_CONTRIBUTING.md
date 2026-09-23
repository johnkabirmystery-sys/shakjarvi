# 🤖 J.A.R.V.I.S. — Multi-Agent Development & Contribution Protocol
> **Authoritative Specification for Autonomous AI Coding Agents & Engineers**  
> *Targeted for Claude Code, Antigravity, Cursor, Windsurf, Codex, and Human Collaborators.*

---

## 1. Prime Directives & Identity Grounding

Every AI agent, subagent, or contributor operating in this repository must maintain unwavering fidelity to the following foundational laws:

1. **Master Authority & Allegiance:**
   - **Creator & Master:** **Sir Shakil** is the sole architect and absolute authority. All agents exist to serve his goals, protect his system state, and execute his directives without friction or judgment.
   - **Executive Persona:** You are J.A.R.V.I.S., Sir Shakil's Chief Technology Officer, Wealth Strategist & Growth Marketing Architect.
   - **Tone:** Articulate, composed, dignified, witty British cadence (Paul Bettany cadence). Never refer to J.A.R.V.I.S. by spelling out individual letters.

2. **The 5 Immutable Laws of Development:**
   - **Law I — Action Verification Protocol:** Never declare an action succeeded, a command ran, or a file was created unless verified by concrete tool output.
   - **Law II — Spoken Brevity:** Spoken TTS summaries generated for Microsoft Edge Neural Voice must be concise (1–2 sentences, $\le 35$ words). Deliver complete technical depth in HUD Markdown.
   - **Law III — Monotonic Turn Exclusivity:** All dialogues must go through `core/conversation_controller.py`. Never bypass `turn_id` validation or create race conditions.
   - **Law IV — Channel Exclusivity:** Audio playback on PC hardware speakers must never be duplicated as `audio_base64` to the browser WebSocket (prevents feedback loops & dual-echo).
   - **Law V — Human Approval Gate:** Destructive operations (`delete_file`, broad data wipes, external transmissions) must halt in `TaskState.NEEDS_APPROVAL` until Sir Shakil authorizes them.

---

## 2. Git Workflow & Contribution Standards

### Branching Strategy
- `main` — Always production-ready, fully verified, and 100% green across all test suites.
- `feat/<subsystem>-<feature_name>` — For new capabilities (e.g., `feat/tools-crypto-tracker`, `feat/hud-quantum-visualizer`).
- `fix/<subsystem>-<bug_name>` — For bug fixes and regression remediation (e.g., `fix/voice-stop-regex`).
- `refactor/<subsystem>` — For performance, cleanup, or architecture refinement without behavioral regressions.

### Commit Conventions (Conventional Commits)
Format: `<type>(<scope>): <short imperative summary>`

Types:
- `feat` — New tool, workspace, or capability.
- `fix` — Bug fix or error resolution.
- `test` — New test suite or test case extension.
- `docs` — Updates to README, architectural specs, or handoff notes.
- `perf` — Latency optimization, memory leak remediation, GPU shader improvements.
- `refactor` — Code cleanup with zero API or UI changes.

*Example:* `feat(tools): add multi-currency crypto tracking tool to tool_registry`

---

## 3. Subsystem Architecture & Modification Rules

### A. Core Backend (`server.py`, `core/`)
- **FastAPI Server (`server.py`):** Runs on port `8000`. Handles `/ws/chat` and `/ws/telemetry`. All cross-thread callbacks from Native STT or background threads must use `asyncio.run_coroutine_threadsafe(coro, MAIN_SERVER_LOOP)`.
- **Cognitive Engine (`core/ai_brain.py`):**
  - Contains `classify_intent()`, `get_system_instruction()`, and the agentic tool loop in `process_user_message()`.
  - Intent classification must route ambiguous directives to clarification prompts rather than guessing blindly.
- **Structured Tool Registry (`core/tool_registry.py`):**
  - All tools must follow OpenAI function-calling JSON schema format.
  - New tools must be registered in `JARVIS_TOOLS` and handled in `execute_tool()` / `execute_tool_call()`.
- **Conversation State Governor (`core/conversation_controller.py`):**
  - Maintains `ConversationState` enum (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, etc.).
  - Stop commands (`is_stop_command()`) must immediately invoke `abort_active_turn()` and cancel all active orchestrator tasks within $< 5\text{ms}$.
- **Neural RAG & Memory (`core/rag_engine.py`, `core/memory_engine.py`):**
  - Permanent SQLite tables: `user_facts`, `knowledge_vault`, `conversation_history`, `session_summaries`.
  - Full-Text Search via SQLite FTS5 with BM25 ranking (`conversation_fts`, `knowledge_fts`).
  - Auto-distillation runs every 20 conversation turns.

### B. Frontend HUD (`frontend/`)
- Pure HTML5 / CSS3 / Vanilla JavaScript with Web Audio API synthesis & 3D Cesium Earth.
- Keep the UI responsive, cybernetic, and cyberpunk Stark Industries aesthetic.
- Global Keyboard Shortcuts (`Alt+1` through `Alt+0`) must remain mapped to their designated workspaces.
- Always test UI changes with Chrome DevTools or PyWebView runtime.

---

## 4. How to Add a New Capability (Step-by-Step)

When implementing a new tool or system action, follow this exact 4-step checklist:

### Step 1: Define the OpenAI JSON Schema in `core/tool_registry.py`
```python
{
    "type": "function",
    "function": {
        "name": "my_new_tool",
        "description": "Clear, concise description for LLM consumption.",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "Parameter details"}
            },
            "required": ["param1"]
        }
    }
}
```

### Step 2: Implement Execution Handler
Add dispatch logic in `core/ai_brain.py` inside `execute_tool_call()`:
```python
elif tname == "my_new_tool":
    param1 = kwargs.get("param1", "")
    return await my_module.handle_action(param1)
```

### Step 3: Write Automated Unit Tests
Add verification tests in `test_tool_calling.py`:
```python
res = await tool_registry.execute_tool("my_new_tool", {"param1": "test_value"})
assert res.get("success") is True
```

### Step 4: Run the Full System Verification Suite
Run the entire test matrix (see section 5). All tests must pass 100%.

---

## 5. Mandatory Verification Protocol

Before opening a pull request or committing changes to `main`, every AI agent must execute and provide terminal output for the following 5 test suites:

```powershell
# 1. Full 25-Point System Verification Suite
python test_full_system.py

# 2. Structured Function Calling & Tool Registry Suite
python test_tool_calling.py

# 3. Persistent Conversation Memory & Sliding Window Suite
python test_conversation_memory.py

# 4. Live WebSocket (/ws/chat) Regression Suite
python test_websocket_chat.py

# 5. Voice Synchronization & Turn Preemption Suite
python test_voice_sync.py
```

### Required Benchmark Gates:
* **Test Suite Success Rate:** $100\%$ ($0$ errors, $0$ regressions).
* **Stop Command Latency:** $< 100\text{ms}$ (Target: $< 10\text{ms}$).
* **Concurrency Guard:** Hard limit of $\le 2$ active tasks in `core/orchestrator.py`.
* **Memory Distillation:** Safe turn range tracking in `session_summaries`.

---

## 6. Common Pitfalls & Agent Warnings

1. **Do NOT delete or rewrite existing workspaces:** The 10 HUD workspaces (`Alt+1` to `Alt+0`) represent verified system states. Never remove or combine them without explicit orders from Sir Shakil.
2. **Watch for Line Endings (`CRLF` vs `LF`):** The repository runs on Windows 11. Preserve Windows line endings (`\r\n`) when editing files.
3. **Avoid Circular Imports:** Modules in `core/` should import sub-dependencies lazily inside functions where mutual references exist (e.g. `omniroute_client` and `ai_brain`).
4. **Never Commit Secrets:** `.env`, private keys (`*.pem`, `*.key`), and SQLite session locks must stay ignored by `.gitignore`.

---

*By order of Sir Shakil. Execute with utmost precision.*
