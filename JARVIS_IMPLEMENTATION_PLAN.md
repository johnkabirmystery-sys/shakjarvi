# J.A.R.V.I.S. — ARCHITECTURAL UPGRADE & IMPLEMENTATION PLAN

**Target System**: J.A.R.V.I.S. (Shakil's Assistant) — Mark XVI  
**Target User**: Sir Shakil (Shakil Ahmed Chowdhury)  
**Host Environment**: Windows 11 Pro 64-bit Workstation  
**Author**: Principal AI Architect & Autonomous Agent Optimization Specialist  
**Status**: APPROVED FOR EXECUTION  
**Date**: September 23, 2026  

---

## 1. Overview of Proposed Changes

The implementation follows a strict modular approach to preserve all existing working capabilities (PC automation, volume control, marketing tools, RAG vault) while curing the synchronization, latency, audio echo, and context failures discovered during the audit.

```
+─────────────────────────────────────────────────────────────────────────────────────────────+
|                                    MODIFIED COMPONENTS MAP                                  |
+─────────────────────────────────────────────────────────────────────────────────────────────+
| 1. [NEW] core/conversation_controller.py    --> Central State Machine & Turn Management     |
| 2. [MODIFY] core/voice_engine.py            --> Epoch-based Playback & Instant OS Purge     |
| 3. [MODIFY] core/native_stt.py              --> Single Mic Authority & Robust VAD/Stop      |
| 4. [MODIFY] core/omniroute_client.py        --> Non-blocking SSE Streaming & 429 Resilience |
| 5. [MODIFY] core/ai_brain.py                --> Relevancy Filter (Dental fix) & Persona     |
| 6. [MODIFY] server.py                       --> Central Controller Routing & Audio Exclusiv.|
| 7. [MODIFY] frontend/hud.js                 --> Abort Handling & Anti-Echo Coordination     |
| 8. [MODIFY] core/proactive_monitor.py       --> Dialogue Busy Suppression                   |
+─────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 2. Component Specifications

### 2.1 Component 1: `core/conversation_controller.py` [NEW]
* **Purpose**: Single authoritative governor of conversation lifecycle and turn synchronization.
* **Key State Machine States**:
  - `IDLE`: Listening for user; no active generation or playback.
  - `LISTENING`: User is actively speaking.
  - `TRANSCRIBING`: Speech recognition processing audio.
  - `THINKING`: LLM generation in progress.
  - `SPEAKING`: Voice audio currently playing.
  - `INTERRUPTED`: Current turn aborted by user stop directive.
  - `CANCELLED`: Outdated turn superseded by a newer turn.
* **Key Mechanisms**:
  - `current_turn_id`: Monotonic integer incremented on every prompt.
  - `active_task`: Handle to the running asyncio generation task.
  - `abort_current_turn(reason)`: Cancels active task, purges audio queue, increments epoch counter, broadcasts abort event to WebSocket clients.
  - `is_dialogue_active()`: Returns `True` if user spoke within 15 seconds or Jarvis is processing/speaking. Used by ProactiveMonitor to suppress alerts.

### 2.2 Component 2: `core/voice_engine.py` [MODIFY]
* **Purpose**: Ensure zero-delay speech cancellation and eliminate queued playback spillover.
* **Key Modifications**:
  - Add `_playback_epoch`: Integer incremented every time `stop_local_audio()` is called.
  - Inside `play_audio_file_on_speakers(filepath, epoch)`: Worker thread checks if its `epoch == _playback_epoch` before playing and after acquiring `_speaker_lock`. If epoch changed, worker discards the audio immediately without playing.
  - In `stop_local_audio()`: Increment `_playback_epoch`, execute `winsound.PlaySound(None, winsound.SND_PURGE)`, and terminate any spawned `ffplay` audio processes.
  - Refine `get_spoken_summary(text)`: Constrain standard spoken responses to a maximum of 2 punchy sentences (<= 35 words).

### 2.3 Component 3: `core/native_stt.py` [MODIFY]
* **Purpose**: Robust speech detection, proper microphone device selection, and instant wake-word/stop detection.
* **Key Modifications**:
  - Microphone selection: Use system default `Microphone Array (AMD Audio Device)` instead of defaulting to low-bandwidth Bluetooth Hands-Free profiles unless high-quality mode is verified.
  - Implement lifecycle functions: `start_listening()`, `stop_listening()`, `pause_listening()`, `resume_listening()`.
  - Add fast-path regex check in `_process_audio`: If recognized text matches stop phrases (*"stop"*, *"wait"*, *"be quiet"*, *"cancel"*, *"never mind"*, *"shut up"*), trigger immediate interruption callback **before** sending to full processing.

### 2.4 Component 4: `core/omniroute_client.py` [MODIFY]
* **Purpose**: Fast token streaming and resilience against HTTP 429 rate limits.
* **Key Modifications**:
  - Replace blocking `content_chunks, reasoning_chunks = await asyncio.to_thread(_stream_request)` with genuine non-blocking HTTP streaming that yields each SSE token as it arrives.
  - Prioritize working, fast models: If `agy/gemini-3.7-flash-low` returns 429, quickly fallback to `auto/best-fast` or `auto/chat` without lingering timeouts.
  - Ensure socket handles close immediately upon `asyncio.CancelledError`.

### 2.5 Component 5: `core/ai_brain.py` [MODIFY]
* **Purpose**: Topic-shift context filtering, removing the stale "Dental" anchor, eliminating canned announcements, and enforcing verified action claims.
* **Key Modifications**:
  - Topic-Shift Detection: If the user's prompt is a new standalone question (e.g. *"what is your architecture?"*), suppress stale historical project tasks (such as the Canadian dental TRD) from dominating the response.
  - Clean Persona Directives: Eliminate long repetitive monologues (wealth pillars, marketing curriculums) unless specifically requested by Sir Shakil.
  - Action Verification: Never claim an app launched or file was saved without verifying return status.

### 2.6 Component 6: `server.py` [MODIFY]
* **Purpose**: Integrate ConversationController and enforce audio channel exclusivity.
* **Key Modifications**:
  - Route both native speech (`on_native_speech`) and WebSocket messages (`process_chat_message`) through `conversation_controller.handle_user_prompt()`.
  - Enforce Audio Exclusivity in `dispatch_tts`:
    - If `play_speaker == True`: Play on Windows kernel, broadcast metadata to HUD with `audio_base64: null`.
    - If `play_speaker == False`: Do NOT play on Windows kernel, broadcast playable `audio_base64` to HUD.
    - Zero double playback.

### 2.7 Component 7: `frontend/hud.js` [MODIFY]
* **Purpose**: Anti-echo coordination, `abort` message handling, and Web Speech synchronization.
* **Key Modifications**:
  - Handle `type: "abort"`: Immediately pause current HTML5 audio, set `currentTime = 0`, clear `audioQueue`, and reset visualizer.
  - Coordinate STT: When Native STT is active on the workstation, disable browser Web Speech transmission to prevent duplicate messages.

### 2.8 Component 8: `core/proactive_monitor.py` [MODIFY]
* **Purpose**: Prevent background alerts from interrupting active dialogue.
* **Key Modifications**:
  - Check `conversation_controller.is_dialogue_active()` before issuing proactive alerts. If conversation is active, defer alert by 30 seconds.

---

## 3. Implementation Order & Testing Gates

```
Step 1: Create `core/conversation_controller.py`
Step 2: Update `core/voice_engine.py` (epoch playback & purge)
Step 3: Update `core/native_stt.py` (lifecycle & mic fix)
Step 4: Update `core/omniroute_client.py` (true streaming & fallback)
Step 5: Update `core/ai_brain.py` (context filter & persona)
Step 6: Update `core/proactive_monitor.py` (dialogue silence)
Step 7: Update `server.py` (central routing & exclusive audio)
Step 8: Update `frontend/hud.js` (abort handling & STT coordination)
Step 9: Run Automated Verification Test Suite (`test_voice_sync.py`)
```
