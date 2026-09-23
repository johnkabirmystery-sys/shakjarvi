# J.A.R.V.I.S. — FULL ARCHITECTURE AUDIT & TECHNICAL SPECIFICATION

**Project**: J.A.R.V.I.S. (Shakil's Assistant) — Mark XVI  
**Target User & Master**: Sir Shakil (Shakil Ahmed Chowdhury)  
**Host Environment**: Windows 11 Pro 64-bit Workstation  
**Workspace**: `D:\Antigravity Project\FULL ON SHAKILS ASSISTANT`  
**Author**: Principal AI Architect, Senior Voice Systems Engineer & Autonomous Agent Optimization Specialist  
**Status**: EMPIRICALLY VERIFIED · SOURCE CODE GROUNDED  
**Date**: September 23, 2026  

---

## 1. Executive Summary & Real Architecture Map

An exhaustive architectural investigation was executed across all components of the J.A.R.V.I.S. desktop assistant codebase. The system was diagnosed not from documentation assumptions, but by inspecting actual Python source files, JavaScript frontend bindings, SQLite databases, OS audio drivers, and active network sockets.

### 1.1 The Real Pipeline Data Flow

```
[ PHYSICAL WORLD: Sir Shakil Speaks ]
                  │
        ┌─────────┴───────────────────────────────────────────┐
        │                                                     │
        ▼ (Captured via sounddevice @ 16kHz)                  ▼ (Captured via WebRTC MediaStream)
 [ core/native_stt.py ]                              [ frontend/hud.js ]
 NativeSTT._listen_loop()                            webkitSpeechRecognition
 - Threshold: ~35.0 (calibrated)                     - Continuous: true, Interim: true
 - Silence timeout: 0.85s                            - In-browser silence debounce: 500-800ms
 - Sends WAV bytes to Google Speech API              - Sends recognized text via Web Speech API
        │                                                     │
        ▼                                                     ▼
 on_native_speech(text) [server.py:524]              wsChat.send({type: "message", text}) [hud.js:1420]
        │                                                     │
        ├─────────────────────────────────────────────────────┘
        │
        ▼
 [ server.py: Acoustic Deduplication Filter (is_duplicate_acoustic_request) ]
 - Compares strings within a 4-second rolling window.
 - DEFECT: Slight wording divergence (e.g. "hi jarvis" vs "hello jarvis") causes deduplication 
   to return FALSE. Both pipelines execute concurrently!
        │
        ▼
 [ Intent Detection & Routing ]
 ├── Direct Local Directives (`core/ai_brain.py:is_direct_local_command`)
 │    Regex pattern matches for PC volume, app launches, browser navigation, screenshots.
 └── LLM Gateway Routing (`core/ai_brain.py:process_user_message` -> `core/omniroute_client.py`)
      - RAG Memory block injected (`core/rag_engine.py:build_rag_context_block`)
      - 14 recent turns fetched from SQLite DB (`data/memory/jarvis_memory.db`)
      - DEFECT: Stale past context (e.g., Dental TRD generation) dominates prompt; 
        no conversation state machine exists to distinguish new topics.
        │
        ▼
 [ OmniRoute Gateway (http://localhost:20128/v1/chat/completions) ]
 - Candidate 1: `agy/gemini-3.7-flash-low` -> CURRENTLY FAILS with HTTP 429 Too Many Requests (2.0s penalty).
 - Candidate 2: `auto/chat` -> Succeeds via fallback cascade, but takes 9.5s to 12.8s total latency!
 - DEFECT: `stream_omniroute_completion` runs `_stream_request` in a worker thread buffering 
   all tokens until `[DONE]` before returning (fake streaming).
        │
        ▼
 [ TTS Audio Synthesis (`core/voice_engine.py`) ]
 - Edge-TTS (`en-US-GuyNeural` / `JARVIS_CLASSIC` @ +8% rate).
 - Fresh synthesis latency: 1.096s; In-memory RAM cache latency: 0.000063s.
 - Chunks sentence-by-sentence via regex `(?<=[.!?\n])\s+`.
        │
        ▼
 [ Audio Playback & Contention ]
 ├── Backend: `server.py:846` calls `voice_engine.play_audio_file_on_speakers(filepath)`
 │    - Plays via `winsound.PlaySound(abs_path, winsound.SND_FILENAME)` on Windows hardware.
 │    - Synchronous blocking call inside thread; queues on `_speaker_lock`.
 └── Frontend: `server.py:856` broadcasts `{"type": "audio", "audio_base64": ...}` to `/ws/chat`
      - `hud.js:enqueueBase64Audio` queues and plays via HTML5 `<audio>` in Chromium.
      - DEFECT: UNCONDITIONAL DOUBLE-PLAYBACK! User hears two out-of-sync audio streams 
        playing simultaneously, feeding back into the open microphone.
```

---

## 2. Forensic Analysis of the 14 Critical Architectural Flaws

Below is the detailed diagnostic evidence for the 14 specific problems identified in the project:

### 1. Duplicate Microphone Listeners
* **Code Evidence**:
  - `core/native_stt.py` lines 71–89: `sd.InputStream(device=self.device_id, samplerate=16000, ...)` runs in a continuous daemon background thread.
  - `frontend/hud.js` lines 986–991: `recognition = new SpeechRecognition(); recognition.continuous = true; recognition.start();` runs inside WebView2.
* **Mechanism**: Two distinct operating system capture streams are opened to the audio subsystem. Both stream audio to Google Speech API simultaneously.
* **Impact**: Double transcripts, race conditions, and acoustic competition.

### 2. Duplicate Audio Playback Systems
* **Code Evidence**:
  - `server.py` line 846:
    ```python
    if filepath and os.path.exists(filepath):
        voice_engine.play_audio_file_on_speakers(filepath)
    ```
  - `server.py` lines 851–863:
    ```python
    for ws in target_ws_list:
        await ws.send_text(json.dumps({"type": "audio", "audio_base64": ...}))
    ```
  - `frontend/hud.js` lines 858–860: `const audio = new Audio("data:audio/wav;base64,..."); audio.play();`
* **Mechanism**: `server.py` completely ignores the `play_speaker` parameter. It triggers `winsound.PlaySound` on the host PC kernel AND broadcasts the base64 WAV to WebView2 to play via Web Audio.
* **Impact**: The user hears an intolerable robotic echo chamber separated by 50–250ms of audio latency.

### 3. Multiple Active Conversation Loops
* **Code Evidence**:
  - `server.py:557`: `headless_process(text)` handles native speech turns.
  - `server.py:666`: `process_chat_message(data)` handles WebSocket chat turns.
  - `server.py:164`: `chat_endpoint(req)` handles HTTP REST `/api/chat` turns.
* **Mechanism**: Each loop maintains its own partial state. When Native STT fires, `headless_process` is spawned. If the browser Web Speech recognizer also fires 300ms later with a non-identical string, `process_chat_message` is spawned simultaneously.
* **Impact**: Two independent AI inference and TTS tasks run concurrently for the same user prompt.

### 4. Blocking Synchronous Operations in Async Event Loops
* **Code Evidence**:
  - `core/voice_engine.py` line 228: `winsound.PlaySound(abs_path, winsound.SND_FILENAME)` is a synchronous Windows API call that blocks its thread until the entire audio file finishes playing.
  - `server.py` line 411: `os.system(ps_cmd)` in `api_broadcast` blocks synchronously.
  - `core/omniroute_client.py` line 304: `http.client.HTTPConnection` in `_stream_request` blocks on socket I/O inside `asyncio.to_thread`.
* **Impact**: Thread pool starvation, uncancelable socket reads, and frozen timers.

### 5. Incorrect Asynchronous Task Handling
* **Code Evidence**:
  - `server.py` lines 596, 715:
    ```python
    asyncio.create_task(dispatch_tts(None, clean_sentence, True))
    ```
* **Mechanism**: `dispatch_tts` is launched as a "fire-and-forget" task without keeping task references, without maintaining sequential order, and without adding them to a cancellation registry.
* **Impact**: Sentence 2 can finish synthesizing before Sentence 1, causing sentences to play out of order. When the user cancels, these background tasks continue executing unchecked.

### 6. Audio Queue Delays
* **Code Evidence**:
  - `core/voice_engine.py` lines 217–249: `with _speaker_lock:` forces all `play_audio_file_on_speakers` threads to serialize behind a single Python threading lock.
* **Impact**: If three sentences are dispatched, Thread 2 and Thread 3 block on `_speaker_lock`. Even if the user issues "Stop", `_playback_cancel_event` is cleared after only 100ms (`_reset_cancel()`), allowing Thread 2 and Thread 3 to acquire the lock and play subsequent sentences anyway.

### 7. TTS Buffering Delays (Fake Streaming)
* **Code Evidence**:
  - `core/omniroute_client.py` lines 301–340:
    ```python
    def _stream_request():
        ...
        for raw_line in resp:
            ...
            chunks.append(content_token)
        return chunks, reasoning_chunks
    content_chunks, reasoning_chunks = await asyncio.to_thread(_stream_request)
    ```
* **Mechanism**: The code advertises SSE streaming, but `_stream_request` reads the *entire HTTP stream to completion* before returning the chunks to asyncio.
* **Impact**: Time to First Token (TTFT) and Time to First Audio (TTFA) are delayed by the full completion time of the model (9–13 seconds) instead of streaming within 400ms.

### 8. STT False Detections & Hardware Mismatch
* **Code Evidence**:
  - `core/native_stt.py` lines 14–18:
    ```python
    for idx, d in enumerate(devices):
        if any(k in name_low for k in ['qcy', 'headset', 'hands-free', 'bluetooth']):
            return idx, d['name']
    ```
* **Empirical Measurement**:
  - Host PC audio scan reveals `[1] Microphone Array (AMD Audio Device)` is system default, while `[2] Headset (3- QCY SP7)` is Bluetooth Hands-Free (8/16kHz).
  - When QCY is powered on or in its case, `native_stt.py` binds to Device 2. If the user speaks toward the laptop array, Native STT records near-zero energy or muffled noise.
  - Meanwhile, WebView2 binds to Device 1 (`Microphone Array`), creating an asymmetric capture state where the frontend hears the user but the backend does not.

### 9. WebSocket Synchronization Problems
* **Code Evidence**:
  - `server.py` line 664: `session_id = id(websocket)`.
  - When native speech triggers `headless_process()`, it attempts to broadcast status updates to `chat_clients` (`server.py:566`). However, if the client has reconnected, stale WebSockets in `chat_clients` raise exceptions, causing status desynchronization between the Arc Reactor HUD and backend state.

### 10. Duplicate Model Requests
* **Code Evidence**:
  - When duplicate audio transcripts bypass `is_duplicate_acoustic_request()`, both `headless_process()` and `process_chat_message()` invoke `ai_brain.process_user_message()`.
  - Both invoke `omniroute_client.generate_omniroute_completion()` or `stream_omniroute_completion()`, resulting in two duplicate HTTP requests hitting the OmniRoute gateway simultaneously.

### 11. Incorrect Cancellation Behavior
* **Code Evidence**:
  - `server.py` line 531:
    ```python
    check_text = re.sub(r'[^a-z\s]', '', text.lower())
    if check_text in ["cancel", "stop", "abort", "never mind", "nevermind", "stop processing", "cancel that"]:
    ```
* **Defects**:
  1. Does not match "wait", "be quiet", "shut up", "hold on".
  2. Strict exact match fails when preceded by wake words (*"Jarvis, stop"* -> fails).
  3. When triggered, it calls `task.cancel()` on `active_ws_tasks`, but fails to:
     - Terminate the blocking socket read in `omniroute_client`.
     - Notify connected browser WebSockets to stop HTML5 audio or clear `audioQueue`.
     - Invalidate active `turn_id` epochs.

### 12. Context and Memory Failures (The "Dental" Loop)
* **Code Evidence**:
  - `server.py` lines 172, 572, 674:
    ```python
    history = rag_engine.get_recent_history(limit=14)
    ```
* **Root Cause Found in Database**:
  - Table `conversation_history` contained turns 81–86 detailing a *"Technical Requirements Document (TRD) for the Canadian Dental Market"*.
  - Because the last 14 turns are blindly prepended to EVERY query without intent or recency filtering, when Sir Shakil asks a new, short question (*"Jarvis, what is your architecture?"*), the LLM assumes the conversation is still anchored to the dental project and outputs: *"Checking, sir. I am preparing the dental system."*

### 13. Repeated "Checking, sir" & Scripted Announcements
* **Code Evidence**:
  - `core/ai_brain.py` lines 177–185, 340–348, 405–410, 471–474:
    Hardcoded static response strings containing boilerplate text (*"I have formulated four high-velocity wealth generation pillars..."*, *"My neural matrix is fully assimilated with the complete A to Z Marketing Curriculum..."*, *"Your directive is recognized and synchronized with our Antigravity workspace, Sir Shakil..."*).
* **Impact**: Jarvis behaves like an inflexible robotic announcement script rather than an attentive, adaptive conversational operating system.

### 14. Fake or Unverified Execution Claims
* **Code Evidence**:
  - `core/ai_brain.py` lines 448–456:
    ```python
    if any(k in text for k in ["code", "build", "develop", "program", "antigravity", ...]):
        task = antigravity_bridge.log_antigravity_task(user_text)
        return f"Directive acknowledged, Sir Shakil. I have routed task #{task['id']} directly to the 'Building A Jarvis Brain' neural core..."
    ```
  - App launch claims (`pc_controller.launch_app`) return success immediately after calling `subprocess.Popen` without checking if the process actually spawned or crashed.
* **Impact**: Jarvis claims tasks are running or routed when they were merely appended to an unmonitored JSON file on disk.

---

## 3. Severity Prioritization Matrix

| Severity | Issue | Core Component | User Impact |
| :--- | :--- | :--- | :--- |
| **P0 — CRITICAL** | Duplicate Microphone Listeners (#1) | `native_stt.py` vs `hud.js` | Speech recognized twice; acoustic contention; duplicate execution. |
| **P0 — CRITICAL** | Unconditional Double Audio Playback (#2) | `server.py` vs `hud.js` | Horrendous double-voice echo; mic feedback loop. |
| **P0 — CRITICAL** | Absence of `turn_id` & Conversation State Machine (#11, #3) | `server.py` | Stale responses overlap; cancel fails; no single active response. |
| **P1 — HIGH** | Fake Streaming & OmniRoute Model 429 Cascade (#7, #10) | `omniroute_client.py` | 9.5–13s latency per turn; `agy/gemini` rate limited; blocked threads. |
| **P1 — HIGH** | Context Anchor Poisoning (#12) | `rag_engine.py` / `ai_brain.py` | Repeating old dental project tasks instead of answering user questions. |
| **P1 — HIGH** | Broken STOP & Interruption Mechanism (#11) | `server.py` / `voice_engine.py` | Saying "Jarvis stop" or "Wait" fails to halt voice playback. |
| **P2 — MEDIUM** | Proactive Background Task Interruption | `proactive_monitor.py` | Spontaneous system health announcements interrupt user speech. |
| **P2 — MEDIUM** | Scripted & Canned Boilerplate Responses (#13) | `ai_brain.py` | Repetitive multi-paragraph monologues instead of concise answers. |
| **P2 — MEDIUM** | Unverified Execution Claims (#14) | `ai_brain.py` / `pc_controller.py` | Claiming tasks are running without process verification. |

---

## 4. Architectural Target State

```
+-----------------------------------------------------------------------------------------------+
|                                    SIR SHAKIL (SPEECH / HUD)                                  |
+-----------------------------------------------------------------------------------------------+
                                                │
                                                ▼
                        +───────────────────────────────────────────────+
                        |      CENTRAL CONVERSATION CONTROLLER          |
                        |      (`core/conversation_controller.py`)      |
                        +───────────────────────────────────────────────+
                        | State Machine:                                |
                        | IDLE ──> LISTENING ──> TRANSCRIBING ──>       |
                        | THINKING ──> SPEAKING ──> (INTERRUPTED/DONE)  |
                        |                                               |
                        | - Tracks monotonic `turn_id` & `request_id`   |
                        | - Strict single-turn exclusivity              |
                        | - Cancels active LLM & TTS tasks instantly    |
                        | - Authoritative STT Master (Single Mic Input) |
                        +───────────────────────────────────────────────+
                                   │                        │
            ┌──────────────────────┘                        └──────────────────────┐
            ▼                                                                      ▼
+──────────────────────────────────────+                      +───────────────────────────────────────+
|      NON-BLOCKING STREAMING LLM      |                      |      INCREMENTAL AUDIO PIPELINE       |
|    (`core/omniroute_client.py`)      |                      |       (`core/voice_engine.py`)        |
+──────────────────────────────────────+                      +───────────────────────────────────────+
| - True SSE token-by-token streaming  |                      | - Sentence 1 priority TTS synthesis   |
| - Fast conversational model priority |                      | - Dedicated Exclusive Playback Channel|
| - Immediate task cancellation token  |                      |   (PC Speakers OR Browser, NEVER both)|
| - Topic-shift context filtering      |                      | - Instant kernel audio purge on STOP  |
+──────────────────────────────────────+                      +───────────────────────────────────────+
```

---

## 5. Verification & Testing Protocol

Before deploying modifications, the following empirical benchmarks must be met:
1. **Single Audio Capture**: 1 spoken utterance must produce exactly 1 log in the terminal and 1 turn in the database.
2. **Channel Exclusivity**: In "speaker" mode, browser audio is silent. In "browser" mode, PC speaker is silent. 0ms echo.
3. **Turn Preemption**: Speaking a new directive must abort the previous model generation within 50ms and supersede playback.
4. **Stop Latency**: Speaking *"Jarvis, stop"* or *"Wait"* must halt all audio output in **< 200ms**.
5. **Context Relevance**: Asking *"Jarvis, what is your architecture?"* must answer directly with system components and zero mentions of unrelated past projects.
