# J.A.R.V.I.S. — VOICE PIPELINE & ACOUSTIC SYNCHRONIZATION REPORT

**Document Version**: 2.0  
**Target User**: Sir Shakil (Shakil Ahmed Chowdhury)  
**Host System**: Windows 11 Pro 64-bit Workstation  
**Author**: Principal AI Architect & Senior Voice Systems Engineer  
**Date**: September 23, 2026  
**Status**: EMPIRICALLY BENCHMARKED  

---

## 1. Measured Latency Breakdown (Pre-Optimization Baseline)

All benchmarks recorded on Sir Shakil's live hardware and OmniRoute network:

| Pipeline Stage | Component | Measured Baseline | Target Optimization | Primary Bottleneck Identified |
| :--- | :--- | :--- | :--- | :--- |
| **1. Speech Detection** | `core/native_stt.py` | ~250ms (Energy VAD) | 150ms | Dynamic calibration threshold clipping |
| **2. STT Finalization** | Google Speech API | 1,200ms – 1,800ms | 800ms – 1,200ms | Network roundtrip; silence timeout was 0.85s |
| **3. Intent Processing** | `core/ai_brain.py` | 15ms (Regex / Local) | < 10ms | Stale context injection in RAG |
| **4. LLM First-Token (TTFT)** | `core/omniroute_client.py` | **9,560ms – 12,821ms** | **< 600ms** | `_stream_request` buffered all tokens until `[DONE]`; `agy/` returning 429 |
| **5. Model Completion** | OmniRoute Gateway | 9,800ms – 14,000ms | 1,500ms – 3,000ms | Candidate cascade timeout stalls |
| **6. TTS First-Audio (TTFA)** | `core/voice_engine.py` | **1,096ms** (fresh)<br>**0.063ms** (cached) | **< 400ms** (first sentence) | Edge-TTS whole-message chunking vs sentence 1 priority |
| **7. Audio Playback** | OS Kernel / WebView2 | 50ms – 250ms (echo) | < 20ms (exclusive) | Unconditional dual playback on both speaker and browser |

---

## 2. Audio Pipeline Lifecycle Management

To prevent duplicate listeners and ensure clean resource allocation and tear-down, the voice subsystem requires an authoritative lifecycle:

```python
class VoiceLifecycleManager:
    """Authoritative audio capture controller for Sir Shakil's workstation."""
    def start_listening() -> None:
        """Initializes single hardware mic capture (Microphone Array AMD Audio Device)."""
        ...
    def stop_listening() -> None:
        """Safely stops hardware stream and releases WASAPI handles."""
        ...
    def pause_listening() -> None:
        """Temporarily pauses audio capture while Jarvis is speaking to prevent self-trigger."""
        ...
    def resume_listening() -> None:
        """Re-arms speech capture immediately upon audio playback completion."""
        ...
```

### Hardware Capture Resolution
* **System Hardware Scan Findings**:
  - `[1] Microphone Array (AMD Audio Device)`: System Default Input (44.1kHz / 48kHz Stereo).
  - `[2] Headset (3- QCY SP7)`: Bluetooth Hands-Free mono input (drops audio to 8/16kHz and degrades speaker output).
  - `[4] Headphones (3- QCY SP7)`: High-Fidelity Stereo Output.
* **Resolution**: Default capture binds to `Microphone Array (AMD Audio Device)` unless a dedicated high-fidelity headset mic is explicitly verified active. Avoid switching Bluetooth into low-bitrate Hands-Free Profile (HFP).

---

## 3. Acoustic Echo Prevention (Channel Exclusivity)

To eliminate the double-voice echo chamber permanently:

1. **Strict Audio Mode Enforcement**:
   - `audioMode == "speaker"`: Output plays **only** via Windows PC audio (`voice_engine.play_audio_file_on_speakers`). The WebSocket packet to `hud.js` omits playable audio (`audio_base64: null`) and sends frequency/duration metadata strictly for Arc Reactor visualizer animation.
   - `audioMode == "browser"`: Output plays **only** via browser HTML5 Audio in WebView2 (`hud.js`). The server **skips** `voice_engine.play_audio_file_on_speakers()`.
   - **Under no circumstances shall both channels play the same audio simultaneously.**
2. **Audio Ducking & Mic Lockout**:
   - During `SPEAKING` state, STT capture is muted or filtered so that TTS sound escaping the speakers cannot be recognized as a user command.
   - A 150ms settling buffer is observed after playback ends before re-arming the microphone.

---

## 4. Multi-Layer Interruption & Cancellation Architecture

When Sir Shakil says any phrase matching the cancellation lexicon:
- *"Jarvis, stop"*
- *"Stop"*
- *"Cancel"*
- *"Hold on"*
- *"Wait"*
- *"Never mind"*
- *"Shut up"*

The cancellation chain triggers instantaneously across 5 layers:

```
[ User Utterance: "Jarvis, stop" ]
               │
               ▼
[ 1. Pattern Matcher: Fuzzy Regex Strips Wake-Word ]
   Recognized as STOP_DIRECTIVE within < 5ms.
               │
               ▼
[ 2. Conversation Controller: Abort Active Turn ]
   `turn_id` incremented; state transitions to INTERRUPTED.
               │
               ├─────────────────────────────────────────┐
               ▼                                         ▼
[ 3. Audio Kernel Purge ]              [ 4. HUD WebSocket Broadcast ]
- `winsound.PlaySound(None, SND_PURGE)`  - Sends: `{"type": "abort", "turn_id": N}`
- Kill any active ffplay child PID       - `hud.js` executes:
- Increment `_playback_epoch`              * `audio.pause(); audio.currentTime = 0;`
  (invalidates all queued sentences)       * `audioQueue.length = 0;`
                                           * Reset status light to IDLE / LISTENING
               │                                         │
               └────────────────────┬────────────────────┘
                                    ▼
[ 5. Model & Network Task Cancellation ]
- Cancel in-flight asyncio LLM generation task.
- Close HTTP connection socket immediately.
- Discard pending TTS synthesis futures.
- Total Elapsed Time to Total Silence: < 180ms.
```
