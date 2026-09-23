# J.A.R.V.I.S. — VOICE SYNCHRONIZATION AND TURN-TAKING AUDIT

**Target System**: J.A.R.V.I.S. (Shakil's Assistant) — Mark XVI  
**Audit Date**: September 23, 2026  
**Auditor**: Antigravity Core Engineering  
**Workspace**: `d:\Antigravity Project\FULL ON SHAKILS ASSISTANT`  
**Status**: DIAGNOSTIC PHASE COMPLETE — AWAITING USER APPROVAL PRIOR TO MODIFICATION  

---

## 1. Executive Summary

This forensic audit investigates the conversation synchronization, turn-taking, speech recognition, audio playback, and cancellation failures observed in J.A.R.V.I.S.

The investigation traced the complete voice lifecycle from microphone input to acoustic playback. The primary conclusion is that **the system suffers from architectural contention**:
1. Two independent speech recognition engines (Native Python sounddevice + Browser Web Speech API) run concurrently, causing duplicate triggers and race conditions.
2. Two independent audio playback pipelines (Windows OS kernel via `winsound`/`ffplay` + Chromium WebView2 HTML5 Audio) play simultaneously, creating double-voice echo.
3. No central conversation controller exists: there are no `turn_id` identifiers, no state machine enforcing single-turn exclusivity, and no preemption mechanism to invalidate stale model generations.
4. The cancellation ("Stop") mechanism fails because background threads block on synchronous network sockets and audio devices without cancellation tokens, while stop keywords ("wait", "be quiet", "jarvis stop") are missed by brittle string matching.
5. Proactive monitor alerts and autonomous background tasks trigger unconstrained audio broadcasts, interrupting active user dialogues.

---

## 2. End-to-End Voice Lifecycle Analysis

```
[Hardware Mic] 
      │
      ├──> (1) Native STT (`core/native_stt.py`)
      │         sounddevice @ 16kHz Mono ──> Google Speech API ──> on_native_speech() [server.py]
      │
      └──> (2) Web Speech API (`frontend/hud.js`)
                webkitSpeechRecognition ──> onresult ──> wsChat.send("message") [/ws/chat]
                        │
                        ▼
            [Race Condition in server.py]
      Two parallel requests with slight transcription differences bypass
      `is_duplicate_acoustic_request()`. Both trigger AI inference concurrently.
                        │
                        ▼
      [AI Model Inference (`core/ai_brain.py` / `core/omniroute_client.py`)]
      - In omniroute_client: `_stream_request` collects all tokens in a blocking worker thread
        before returning (buffered, not true real-time streaming).
      - No `turn_id` attached. If user speaks again, old generation is not cancelled.
                        │
                        ▼
      [TTS Generation (`core/voice_engine.py`)]
      - Sentences split and dispatched via unmanaged `asyncio.create_task(dispatch_tts())`.
      - Parallel synthesis requests execute out-of-order.
                        │
                        ▼
            [Dual Audio Playback Contention]
      ├──> (A) `server.py` unconditionally plays on Windows speakers via `winsound.PlaySound`
      └──> (B) `server.py` broadcasts `{"type": "audio", "audio_base64": ...}` to HUD WebSocket
                HUD plays via HTML5 `new Audio()` inside Chromium.
                RESULT: Double-voice acoustic reverberation and mic feedback loop.
                        │
                        ▼
      [Interruption / STOP Request]
      - "Stop" / "Wait" / "Be quiet" fails to match regex if preceded by "Jarvis".
      - Cancelling WebSocket task does NOT kill blocking audio thread or clear browser queue.
```

---

## 3. Discovered Root Causes & File-by-File Breakdown

### 3.1 Dual Speech Recognition Engines Operating in Contention
- **Files**: `core/native_stt.py` (`NativeSTT._listen_loop`), `server.py` (`on_native_speech`), `frontend/hud.js` (`recognition = new SpeechRecognition()`).
- **Mechanism**:
  - `native_stt.py` captures hardware microphone input directly using `sounddevice` at 16,000 Hz and sends audio buffers to Google's Speech API. Upon recognition, it triggers `on_native_speech()` in `server.py`.
  - Concurrently, `frontend/hud.js` initializes `webkitSpeechRecognition` inside WebView2, capturing the exact same microphone and sending a `{ type: "message", text: ... }` JSON payload across `/ws/chat`.
- **Failure Mode**:
  - The server attempts deduplication via `is_duplicate_acoustic_request()`, but because the two speech recognizers produce slightly different transcripts (e.g., *"Jarvis what's the weather"* vs *"what is the weather"*), the deduplication check evaluates to `False`.
  - Both requests trigger full parallel pipelines in `headless_process()` and `websocket_chat()`, causing dual replies, conflicting TTS outputs, and corrupting conversation history.

### 3.2 Unconditional Dual Audio Playback (Speaker + Browser Echo)
- **Files**: `server.py` (`dispatch_tts`), `core/voice_engine.py` (`play_audio_file_on_speakers`), `frontend/hud.js` (`enqueueBase64Audio`, `playBase64Audio`).
- **Mechanism**:
  - In `server.py` line 846, `dispatch_tts()` contains:
    ```python
    if filepath and os.path.exists(filepath):
        voice_engine.play_audio_file_on_speakers(filepath)
    ```
    This line plays audio directly through the Windows OS sound kernel (`winsound.PlaySound`), **completely ignoring** the `play_speaker` boolean argument passed into the function.
  - Simultaneously, lines 851–863 broadcast `{"type": "audio", "audio_base64": ...}` over WebSocket to `hud.js`.
  - In `hud.js`, because `state.audioMode` defaults to `"browser"`, the client creates `new Audio("data:audio/wav;base64,...")` and starts playback.
- **Failure Mode**:
  - The user hears the exact same utterance twice: once from the Python kernel and once from WebView2, separated by 50–200ms of buffer latency.
  - The live microphone hears the speaker output, triggering acoustic feedback loops and false speech detections.

### 3.3 Audio Queue Concurrency & Blocking Speaker Lock
- **Files**: `core/voice_engine.py` (`play_audio_file_on_speakers`, `stop_local_audio`), `server.py` (`headless_process`, `websocket_chat`).
- **Mechanism**:
  - Streaming sentence chunking invokes `asyncio.create_task(dispatch_tts(...))` concurrently for each completed sentence.
  - In `voice_engine.py`, `play_audio_file_on_speakers()` spawns a daemon thread that acquires `_speaker_lock` and executes `winsound.PlaySound(abs_path, winsound.SND_FILENAME)`.
- **Failure Mode**:
  - `winsound.PlaySound(..., SND_FILENAME)` is **synchronous and blocking**.
  - If multiple sentences are created, multiple threads queue on `_speaker_lock`.
  - When `stop_local_audio()` is called, it issues `winsound.PlaySound(None, winsound.SND_PURGE)` and sets `_playback_cancel_event`. However, `_playback_cancel_event` is cleared after only 100ms via `_reset_cancel()`. Any worker thread that was waiting behind the lock then acquires the lock and plays the remaining sentences anyway!
  - Furthermore, `stop_local_audio()` does not terminate `ffplay` subprocesses if fallback is used.

### 3.4 Absence of Turn Tracking (`turn_id`) and Conversation State Machine
- **Files**: `server.py`, `core/ai_brain.py`, `frontend/hud.js`.
- **Mechanism**:
  - No message or request possesses a unique `turn_id` or monotonic sequence counter.
  - When the user speaks while Jarvis is still responding or processing:
    - There is no mechanism to invalidate the previous turn.
    - Ongoing AI generation continues to stream tokens.
    - Ongoing TTS continues to synthesize audio.
    - Outdated responses arrive and intermingle in the UI and audio playback queue.
- **Failure Mode**:
  - Violates the fundamental requirement: *"One active response at a time. New user input taking priority over stale responses."*

### 3.5 Brittle "STOP" Command Detection & Incomplete Cancellation Chain
- **Files**: `server.py` (`on_native_speech`), `frontend/hud.js` (`recognition.onresult`), `core/omniroute_client.py` (`stream_omniroute_completion`).
- **Mechanism**:
  - In `server.py` line 531:
    ```python
    check_text = re.sub(r'[^a-z\s]', '', text.lower())
    if check_text in ["cancel", "stop", "abort", "never mind", "nevermind", "stop processing", "cancel that"]:
    ```
  - In `frontend/hud.js` line 1060:
    ```javascript
    if (/^(cancel|stop|abort|never mind|nevermind|stop processing|cancel that)$/.test(checkText))
    ```
- **Failure Modes**:
  1. **Missing Keywords**: Fails on "wait", "be quiet", "quiet", "hold on", "hush".
  2. **Failed Pattern Matching**: If the user says *"Jarvis, stop"*, *"Jarvis wait"*, or *"Please be quiet"*, the check fails because of strict equality matching against `check_text`.
  3. **Broken Cancellation Flow**: When matched, `server.py` only cancels tasks in `active_ws_tasks` and calls `voice_engine.stop_local_audio()`. It **never** sends a cancellation packet to `chat_clients` to halt browser audio playback or clear `audioQueue` in `hud.js`.
  4. **Uninterruptible Network Thread**: In `omniroute_client.py`, `_stream_request` runs in a worker thread blocking on `conn.getresponse()`. Python cannot interrupt a blocking socket read inside `asyncio.to_thread` via standard task cancellation.

### 3.6 Fake Streaming in OmniRoute Gateway
- **Files**: `core/omniroute_client.py` (`stream_omniroute_completion`).
- **Mechanism**:
  - Lines 301–340 execute `content_chunks, reasoning_chunks = await asyncio.to_thread(_stream_request)`.
  - `_stream_request()` reads the entire SSE stream from OmniRoute into memory (`chunks.append(content_token)`) until `[DONE]` or connection close.
  - Only *after* the entire response is received does `stream_omniroute_completion` begin yielding chunks.
- **Failure Mode**:
  - The UI and TTS engine receive nothing for 3–15 seconds, followed by a sudden burst of all tokens at once.
  - TTFT (Time to First Token) and latency to first spoken audio are severely degraded.

### 3.7 Proactive Background Alerts Interrupting Active User Conversation
- **Files**: `core/proactive_monitor.py` (`ProactiveMonitor.start`, `_trigger_alert`), `server.py` (`monitor`).
- **Mechanism**:
  - `ProactiveMonitor` runs an uncoordinated 5-second polling loop checking system telemetry (RAM, CPU, Battery) and launching periodic autonomous research tasks.
  - When a threshold is met (e.g. RAM > 88%), it immediately synthesizes speech and broadcasts a `proactive_update` event to all clients.
- **Failure Mode**:
  - The monitor does not check whether `is_speaking()` is `True`, whether the user's mic is active, or whether a conversation turn is in progress.
  - Spontaneous system announcements interrupt Sir Shakil mid-sentence.

### 3.8 Long-Winded Canned Announcements & Unverified Action Claims
- **Files**: `core/ai_brain.py` (`handle_offline_commands`), `core/voice_engine.py` (`get_spoken_summary`).
- **Mechanism**:
  - `handle_offline_commands` contains static strings with multi-paragraph speeches (e.g., 5-bullet marketing curriculums, 4 wealth pillars, speculative task routing notices).
  - The spoken summary extractor allows up to 4 sentences and 80 words, leading to overly verbose voice output.
  - Actions (such as task scheduling or file generation) are declared as completed before verifying return codes.

---

## 4. Current State Management Problems

| Component | Current State Implementation | Defect / Failure |
| :--- | :--- | :--- |
| **Active Turn Tracking** | None. No `turn_id` exists. | Stale background tasks continue running and emit audio even after a new query arrives. |
| **STT Authority** | Split: Native Python STT and Browser Web Speech run concurrently. | Double-transcription, duplicate execution, acoustic race conditions. |
| **Audio Playback Mode** | Split: Server plays via `winsound`; HUD plays via `Audio()`. | Double-voice echo; ignoring `play_speaker` parameter in `dispatch_tts`. |
| **Cancellation Propagation** | Local only. Server does not inform HUD; HUD does not inform server tasks. | Audio continues playing in browser when cancelled on server, and vice versa. |
| **System Busy / Idle State** | Loose string status (`"thinking"`, `"speaking"`, `"idle"`). | Proactive alerts bypass busy state; mic re-arms prematurely during audio reverberation. |

---

## 5. Architectural Recommendations

### Recommendation 1: Unified Central Conversation Controller (`core/conversation_controller.py`)
Create a single authoritative state machine on the backend that manages:
1. **Monotonic `turn_id`**: Incremented on every valid user prompt. Every chunk, TTS synthesis request, and audio packet carries this `turn_id`. Any worker or callback whose `turn_id < current_turn_id` is discarded immediately.
2. **Turn Preemption**: When a new prompt arrives:
   - Cancel the active AI generation task.
   - Cancel all pending TTS synthesis jobs.
   - Halt active audio playback immediately on both Windows speakers and connected HUD clients.
   - Invalidate any in-flight database conversation logs for the aborted turn.
3. **Single STT Authority Selection**:
   - Establish a single master speech input channel. If Native STT is active and functional on the workstation, disable or mute the browser's Web Speech API to prevent duplicate acoustic capturing, OR coordinate them through the Conversation Controller with strict lock-out.

### Recommendation 2: Robust STOP & Interruption Engine
1. **Expanded Lexicon & Fuzzy Match**:
   - Match any of: `"stop"`, `"cancel"`, `"be quiet"`, `"quiet"`, `"wait"`, `"never mind"`, `"nevermind"`, `"shut up"`, `"hold on"`, `"pause"`.
   - Strip leading wake-words (*"jarvis stop"* -> *"stop"*).
2. **Immediate Multi-Layer Cancellation**:
   - `voice_engine.stop_local_audio()`: Abort `winsound` with `SND_PURGE`, kill active `ffplay`/audio child processes, and invalidate queued playback threads using a generation epoch counter.
   - Broadcast `{"type": "abort", "turn_id": current_turn_id}` to all WebSocket clients to immediately pause HTML5 audio, clear `audioQueue`, and reset visualizer.
   - Set assistant status to `idle` and re-arm listening state without generating an apologetic AI reply.

### Recommendation 3: Audio Output Channel Exclusivity
- Fix `dispatch_tts()` in `server.py`:
  - Enforce strict channel separation: If audio is played locally via PC speakers (`play_speaker=True`), do **not** send playable audio base64 to the browser (or send it with `mute=True` strictly for visualizer frequency analysis).
  - If `audioMode == "browser"`, do **not** invoke `voice_engine.play_audio_file_on_speakers()`.
- Eliminate double playback permanently.

### Recommendation 4: Real-Time Non-Blocking OmniRoute Streaming
- Refactor `core/omniroute_client.py` to use non-blocking HTTP streaming (e.g. `aiohttp` or an asynchronous line-iterator) so tokens are yielded to the caller *as they arrive* over the wire.
- Ensure the underlying connection is closed immediately upon `asyncio.CancelledError`.

### Recommendation 5: Proactive Alert Suppression During Active Conversation
- Update `core/proactive_monitor.py` to consult `conversation_controller.is_busy()` before triggering any announcement.
- If a conversation is active or user speech was detected within the last 15 seconds, queue or suppress non-critical alerts.

### Recommendation 6: Concise Spoken Responses & Verified Action Protocol
- Update `core/voice_engine.py`: Limit standard spoken responses to 1–2 punchy sentences (maximum 35 words).
- Remove repetitive boilerplate speeches from `core/ai_brain.py`.
- Enforce the Action Verification rule: Never announce that an action succeeded unless the underlying Python function returned `{"success": True}`.

---

## 6. Comprehensive Test Plan with Measurable Success Criteria

| Test ID | Test Scenario | Execution Method | Measurable Pass Criteria |
| :--- | :--- | :--- | :--- |
| **TEST-01** | **Single Spoken Request Synchronization** | Speak: *"Jarvis, what time is it?"* via mic. | Exactly **one** user event logged; exactly **one** response generated; **zero** double-voice echo. |
| **TEST-02** | **Acoustic Preemption / New Request Priority** | Speak: *"Tell me a long story"* then immediately speak *"What is 2 plus 2?"* after 1 second. | First generation cancelled; `turn_id` updated; Jarvis immediately answers *"Four"* without completing the story. |
| **TEST-03** | **Immediate "Stop" Command** | Ask a question; while Jarvis is speaking, say *"Stop"*. | Audio playback halts within **< 250ms**; browser audio clears; no further sentences played; system returns to listening. |
| **TEST-04** | **Varied Stop Phrasing** | Test with: *"Jarvis, be quiet"*, *"Wait"*, *"Never mind"*, *"Cancel that"*. | All variants immediately halt audio, abort current turn, and restore idle/listening state. |
| **TEST-05** | **Channel Exclusivity (No Echo)** | Play response in `"browser"` mode, then switch to `"speaker"` mode. | In `"browser"` mode: only web audio plays. In `"speaker"` mode: only PC speaker plays. Never both. |
| **TEST-06** | **Proactive Monitor Silence During Dialogue** | Trigger heavy CPU load during a chat turn. | Proactive alert is suppressed or deferred until conversation has been idle for > 15 seconds. |
| **TEST-07** | **Concise Voice Delivery** | Ask a general knowledge question. | Spoken audio summary is **<= 2 sentences** and under 35 words; full text is rendered in HUD. |
| **TEST-08** | **Verified Action Integrity** | Ask Jarvis to launch an invalid/non-existent app. | Jarvis explicitly states the application could not be launched; does not claim false success. |

---

## 7. Next Steps

Awaiting Sir Shakil's review and approval of this audit. Upon approval, implementation will proceed systematically:
1. Implement `core/conversation_controller.py` with `turn_id` management and cancellation tokens.
2. Update `server.py` to route all inputs through the conversation controller and fix audio routing.
3. Update `core/voice_engine.py` for guaranteed audio preemption.
4. Update `frontend/hud.js` to coordinate STT and audio playback with `turn_id`.
5. Execute the test plan and record measurable verification results.
