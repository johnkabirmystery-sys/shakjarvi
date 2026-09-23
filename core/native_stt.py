import sounddevice as sd
import numpy as np
import speech_recognition as sr
import threading
import queue
import time
import re
from collections import deque
from typing import Optional, Callable, Dict, Any, Tuple, List

def normalize_spoken_text(text: str) -> str:
    """Phonetic auto-corrector & regional speech normalizer."""
    if not text:
        return ""
    clean = text.strip()

    # 1. Wake-word phonetic mishearings from Google Speech engine
    clean = re.sub(
        r'\b(travis|service|harvest|charles|starbucks|java|jawis|job is|chavez|drvis|jarbis|javish|jarv|jervis|davis|garvis|tarvis)\b',
        "Jarvis",
        clean,
        flags=re.IGNORECASE
    )

    # 2. Antigravity and OmniRoute platform mishearings
    clean = re.sub(r'\b(anti\s*gravity|anti-gravity|anti\s*grabby|integrative|integra)\b', "antigravity", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(omni\s*route|omni\s*road|army\s*route|omni\s*root)\b', "omniroute", clean, flags=re.IGNORECASE)

    # 3. AI Models and Providers
    clean = re.sub(r'\b(cloud|claud|clod)\s*(sonnet|opus|3\.5|3\.7|4\.6)?\b', r"Claude \2", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(jiminy|jimmy|gemini)\s*(flash|pro|3\.7|3\.8)?\b', r"Gemini \2", clean, flags=re.IGNORECASE)

    # 4. Common application and tool mishearings
    clean = re.sub(r'\b(note\s*pad|not\s*pad|no\s*pad)\b', "notepad", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(cal\s*culator|calculater|calc|cockulator)\b', "calculator", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(event\s*bright|even\s*bright|event\s*bride|event\s*bite|even\s*bite)\b', "eventbrite", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(google\s*chrome|chrome\s*browser)\b', "chrome", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(vs\s*code|visual\s*studio\s*code|visual\s*code|v\s*s\s*code)\b', "vscode", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(you\s*tube|u\s*tube)\b', "youtube", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(screen\s*shot|clean\s*shot|screen\s*short|capture\s*screen|take\s*a\s*screenshot)\b', "screenshot", clean, flags=re.IGNORECASE)

    # 5. Regional / Banglish directives translated to English intents
    clean = re.sub(r'\b(kholo|khulo|open koro|chalu koro|start koro)\b', "open", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(bondho koro|bondho|close koro|off koro)\b', "close", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(dekhao|dekhiye dao|show koro)\b', "show", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(email dekhao|email check koro|inbox dekhao|mail dekhao)\b', "check emails", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(internet e search koro|internet e research koro|online e research koro|online search koro|web research)\b', "research online", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(ki obostha|kemon acho|status ki|diagnostics dekhao)\b', "status report", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(sound barhao|volume barhao|sound increase|sound up)\b', "turn up volume", clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(sound komao|volume komao|sound decrease|sound down)\b', "turn down volume", clean, flags=re.IGNORECASE)

    return clean.strip()

from core import audio_device_manager as adm

def get_preferred_input_device() -> Tuple[Optional[int], str]:
    return adm.resolve_best_input_device()

def list_input_devices() -> List[Dict[str, Any]]:
    return adm.list_input_devices()


class NativeSTT:
    def __init__(self, callback: Callable[[str], Any], status_callback: Optional[Callable[[str, str], Any]] = None):
        self.callback = callback
        self.status_callback = status_callback
        self.recognizer = sr.Recognizer()
        self.is_listening = False
        self._stop_event = threading.Event()
        self.thread = None
        self.q = queue.Queue()
        self.samplerate = 16000
        self.is_muted = False
        self.energy_threshold = 24.0
        self.silence_timeout_sec = 0.65
        self.device_id, self.device_name = adm.resolve_best_input_device()

    def set_status(self, status: str, label: str):
        if self.status_callback:
            try:
                self.status_callback(status, label)
            except Exception as e:
                pass

    def _audio_callback(self, indata, frames, time_info, status):
        self.q.put(indata.copy())

    def mute(self):
        self.is_muted = True
        self.set_status("idle", "MIC PAUSED")
        print("[NativeSTT] Audio input muted.", flush=True)

    def unmute(self):
        self.is_muted = False
        self.set_status("listening", "LISTENING")
        print("[NativeSTT] Audio input unmuted. Listening active.", flush=True)

    def set_device(self, device_id: Union[int, str]):
        """Switches the input device dynamically."""
        adm.set_preferred_input(device_id)
        self.device_id, self.device_name = adm.resolve_best_input_device()
        print(f"[NativeSTT] Switched microphone to [{self.device_id}] '{self.device_name}'", flush=True)
        # If currently listening, stop and restart stream
        if self.is_listening:
            self._restart_stream()

    def _restart_stream(self):
        """Signals stream restart to bind to new hardware."""
        self._stop_event.set()
        time.sleep(0.1)
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def _listen_loop(self):
        try:
            self.device_id, self.device_name = adm.resolve_best_input_device()

            with sd.InputStream(device=self.device_id, samplerate=self.samplerate, channels=1, dtype='int16', blocksize=1024, callback=self._audio_callback):
                print(f"[NativeSTT] Online. Listening via [{self.device_id}] '{self.device_name}' at {self.samplerate}Hz (Threshold={self.energy_threshold:.1f})...", flush=True)
                self.set_status("listening", "LISTENING")

                # Rolling pre-speech ring buffer (~0.4s: 6 blocks of 1024 samples)
                pre_buffer = deque(maxlen=6)
                audio_buffer = []
                silence_blocks = 0
                is_speaking = False
                blocks_per_sec = self.samplerate / 1024.0
                required_silence_blocks = int(self.silence_timeout_sec * blocks_per_sec)
                min_speech_blocks = 2  # ~0.12s min duration

                while not self._stop_event.is_set():
                    if self.is_muted:
                        while not self.q.empty():
                            self.q.get_nowait()
                        time.sleep(0.08)
                        continue

                    try:
                        data = self.q.get(timeout=0.3)
                    except queue.Empty:
                        continue

                    energy = float(np.abs(data).mean())

                    if energy > self.energy_threshold:
                        if not is_speaking:
                            is_speaking = True
                            print(f"[NativeSTT] >>> Voice detected (energy: {energy:.1f} > {self.energy_threshold:.1f}), capturing...", flush=True)
                            self.set_status("speech_detected", "HEARING SIR SHAKIL...")
                            audio_buffer = list(pre_buffer)
                        audio_buffer.append(data)
                        silence_blocks = 0
                    else:
                        if is_speaking:
                            silence_blocks += 1
                            audio_buffer.append(data)

                            if silence_blocks >= required_silence_blocks:
                                is_speaking = False
                                print(f"[NativeSTT] Speech finished ({len(audio_buffer)} chunks). Transcribing...", flush=True)
                                self.set_status("transcribing", "TRANSCRIBING...")

                                if len(audio_buffer) >= min_speech_blocks:
                                    audio_data = np.concatenate(audio_buffer)
                                    raw_bytes = audio_data.tobytes()
                                    audio = sr.AudioData(raw_bytes, self.samplerate, 2)

                                    threading.Thread(target=self._process_audio, args=(audio,), daemon=True).start()

                                audio_buffer = []
                                silence_blocks = 0
                        else:
                            pre_buffer.append(data)
        except Exception as e:
            print(f"[NativeSTT] Stream error: {e}", flush=True)
            self.set_status("idle", "MIC ERROR")

    def _process_audio(self, audio):
        recognized_text = None
        for lang in ["en-IN", "en-US", "en-GB", "bn-BD"]:
            try:
                text = self.recognizer.recognize_google(audio, language=lang)
                if text and text.strip():
                    recognized_text = normalize_spoken_text(text.strip())
                    print(f"\n==========================================")
                    print(f">>> [JARVIS HEARD] \"{recognized_text}\" (lang: {lang})")
                    print(f"==========================================\n", flush=True)
                    break
            except sr.UnknownValueError:
                continue
            except Exception as e:
                print(f"[NativeSTT] Google API ({lang}): {e}", flush=True)
                break

        if recognized_text:
            try:
                self.callback(recognized_text)
            except Exception as cb_err:
                import traceback
                print(f"[!] Callback execution error: {cb_err}", flush=True)
                traceback.print_exc()
        else:
            print("[NativeSTT] Speech detected but unparsed (murmur/noise).", flush=True)
            self.set_status("listening", "LISTENING")

    def start(self):
        if not self.is_listening:
            self._stop_event.clear()
            self.is_listening = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()

    def stop(self):
        if self.is_listening:
            self._stop_event.set()
            self.is_listening = False

_global_stt: Optional[NativeSTT] = None

def start_stt(callback: Callable[[str], Any], status_callback: Optional[Callable[[str, str], Any]] = None):
    global _global_stt
    if not _global_stt:
        _global_stt = NativeSTT(callback, status_callback=status_callback)
        _global_stt.start()
    else:
        if status_callback:
            _global_stt.status_callback = status_callback
        _global_stt.unmute()

def stop_stt():
    global _global_stt
    if _global_stt:
        _global_stt.stop()
        _global_stt = None

def mute_stt():
    if _global_stt:
        _global_stt.mute()

def unmute_stt():
    if _global_stt:
        _global_stt.unmute()

def is_stt_muted() -> bool:
    if _global_stt:
        return _global_stt.is_muted
    return True

def get_stt_device_info() -> Dict[str, Any]:
    if _global_stt:
        return {
            "device_id": _global_stt.device_id,
            "device_name": _global_stt.device_name,
            "is_listening": _global_stt.is_listening,
            "is_muted": _global_stt.is_muted,
            "energy_threshold": _global_stt.energy_threshold
        }
    dev_id, dev_name = get_preferred_input_device()
    return {
        "device_id": dev_id,
        "device_name": dev_name,
        "is_listening": False,
        "is_muted": True,
        "energy_threshold": 22.0
    }

def set_stt_device(device_id: int):
    if _global_stt:
        _global_stt.set_device(device_id)

# Standardized Lifecycle Aliases
def start_listening(callback, status_callback=None):
    start_stt(callback, status_callback=status_callback)

def stop_listening():
    stop_stt()

def pause_listening():
    mute_stt()

def resume_listening():
    unmute_stt()
