import os
import hashlib
import asyncio
import base64
from pathlib import Path
import edge_tts

DEFAULT_VOICE = "JARVIS_IRONMAN"
CACHE_DIR = Path("data/tts_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

POPULAR_VOICES = [
    {
        "id": "JARVIS_IRONMAN",
        "name": "JARVIS_IRONMAN (Stark MK-85 Robotic Paul Bettany)",
        "gender": "Male",
        "base": "en-GB-RyanNeural",
        "rate": "+9%",
        "pitch": "-6Hz",
        "dsp_filter": "equalizer=f=3400:t=q:w=1.2:g=4.5,flanger=delay=2.5:depth=2.0:regen=28:width=80:speed=0.5,aecho=0.8:0.7:20:0.25,volume=1.15"
    },
    {
        "id": "JARVIS_CLASSIC",
        "name": "JARVIS_CLASSIC (Futuristic Robotic British)",
        "gender": "Male",
        "base": "en-GB-RyanNeural",
        "rate": "+12%",
        "pitch": "-8Hz",
        "dsp_filter": "equalizer=f=3200:t=q:w=1.2:g=3.5,flanger=delay=2.0:depth=1.6:regen=22:width=75:speed=0.4,aecho=0.8:0.7:15:0.20,volume=1.1"
    },
    {
        "id": "JARVIS_DEEP",
        "name": "JARVIS_DEEP (Hulkbuster Deep Robotic)",
        "gender": "Male",
        "base": "en-GB-ThomasNeural",
        "rate": "+8%",
        "pitch": "-18Hz",
        "dsp_filter": "equalizer=f=2800:t=q:w=1.2:g=5,flanger=delay=3.0:depth=2.5:regen=32:width=85:speed=0.6,aecho=0.8:0.7:25:0.30,volume=1.2"
    },
    {
        "id": "JARVIS_FAST",
        "name": "JARVIS_FAST (High-Speed Neural Processor)",
        "gender": "Male",
        "base": "en-GB-RyanNeural",
        "rate": "+25%",
        "pitch": "-4Hz",
        "dsp_filter": "equalizer=f=3400:t=q:w=1.2:g=4,flanger=delay=2.0:depth=1.5:regen=20:width=70:speed=0.5,aecho=0.8:0.7:15:0.18,volume=1.1"
    },
    {
        "id": "JARVIS_CALM",
        "name": "JARVIS_CALM (F.R.I.D.A.Y. Robotic Female)",
        "gender": "Female",
        "base": "en-GB-SoniaNeural",
        "rate": "+5%",
        "pitch": "-3Hz",
        "dsp_filter": "equalizer=f=3500:t=q:w=1.2:g=3,flanger=delay=1.8:depth=1.2:regen=18:width=65:speed=0.4,aecho=0.8:0.7:15:0.18,volume=1.05"
    }
]

import re

def clean_text_for_speech(text: str) -> str:
    # Ensure JARVIS is pronounced as the single word "Jarvis", never spelled out "J-A-R-V-I-S"
    text = re.sub(r"\bJ\.?\s*A\.?\s*R\.?\s*V\.?\s*I\.?\s*S\.?", "Jarvis", text, flags=re.IGNORECASE)
    text = re.sub(r"\bJARVIS\b", "Jarvis", text)

    # 1. Replace multi-line code blocks ```...``` with a clean spoken notice
    if re.search(r"```[\w]*\n[\s\S]*?```", text):
        text = re.sub(
            r"```[\w]*\n[\s\S]*?```", 
            " I have saved the complete code to your Desktop in the Jarvis Generated Code folder for your review, Sir Shakil. ", 
            text
        )

    # 2. Suppress raw CSS, HTML tags, or programming syntax that slips through
    # (e.g. selector { prop: val; }, function calls, semicolons blocks)
    text = re.sub(r"\{[^{}]*(?:margin|padding|border|color|background|display|font|width|height|position)[^{}]*\}", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)

    # Strip markdown syntax for natural voice delivery
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`+([^`]+)`+", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

    # Clean up excess whitespace and repetitive notices
    text = re.sub(r"(?:I have saved the complete code to your Desktop in the Jarvis Generated Code folder for your review, Sir Shakil\.\s*){2,}", "I have saved the complete code to your Desktop in the Jarvis Generated Code folder for your review, Sir Shakil. ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def get_spoken_summary(text: str) -> str:
    """Extracts a concise, punchy spoken executive summary (1-2 sentences, max 35 words)."""
    clean = clean_text_for_speech(text)
    if not clean:
        return ""
    # Split into clean sentences
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
    if not sentences:
        return clean

    # Strict rule: 1 to 2 sentences, maximum ~35 words for crisp executive delivery
    summary_sentences = []
    word_count = 0
    for s in sentences:
        words_in_s = len(s.split())
        if summary_sentences and (word_count + words_in_s > 35 or len(summary_sentences) >= 2):
            break
        summary_sentences.append(s)
        word_count += words_in_s
        if len(summary_sentences) >= 2:
            break
            
    summary = " ".join(summary_sentences)
    return summary

def get_first_sentence(text: str) -> str:
    """Extracts just the first complete sentence for priority TTS synthesis."""
    clean = clean_text_for_speech(text)
    if not clean:
        return ""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean) if s.strip()]
    if sentences:
        return sentences[0]
    return clean[:120] if len(clean) > 120 else clean

_IN_MEMORY_AUDIO_CACHE = {}

async def synthesize_speech_async(text: str, voice: str = DEFAULT_VOICE, rate: str = None, pitch: str = None) -> dict:
    text = clean_text_for_speech(text)
    if not text:
        return {"success": False, "error": "Empty text"}
        
    # Resolve preset config
    resolved_voice = voice
    resolved_rate = rate or "+9%"
    resolved_pitch = pitch or "-6Hz"
    dsp_filter = None
    
    preset = next((p for p in POPULAR_VOICES if p["id"] == voice), None)
    if preset:
        resolved_voice = preset.get("base", voice)
        if not rate: resolved_rate = preset.get("rate", "+9%")
        if not pitch: resolved_pitch = preset.get("pitch", "-6Hz")
        dsp_filter = preset.get("dsp_filter")
        
    cache_key = hashlib.md5(f"{text}_{resolved_voice}_{resolved_rate}_{resolved_pitch}_{dsp_filter or ''}".encode('utf-8')).hexdigest()
    
    # 0ms RAM cache check (ensure non-empty audio)
    if cache_key in _IN_MEMORY_AUDIO_CACHE and _IN_MEMORY_AUDIO_CACHE[cache_key].get("size_bytes", 0) > 0:
        return _IN_MEMORY_AUDIO_CACHE[cache_key]

    output_file = CACHE_DIR / f"{cache_key}.mp3"
    wav_file = CACHE_DIR / f"{cache_key}.wav"
    
    if not output_file.exists() or output_file.stat().st_size == 0:
        communicate = edge_tts.Communicate(text, resolved_voice, rate=resolved_rate, pitch=resolved_pitch)
        await communicate.save(str(output_file))
        
    # Convert to uncompressed 16-bit PCM WAV with Stark Robotic DSP filter chain
    if not wav_file.exists() or wav_file.stat().st_size == 0:
        try:
            import subprocess
            cmd = ['ffmpeg', '-y', '-i', str(output_file)]
            if dsp_filter:
                cmd.extend(['-af', dsp_filter])
            cmd.extend(['-c:a', 'pcm_s16le', '-ar', '24000', str(wav_file), '-loglevel', 'quiet'])
            subprocess.run(cmd, check=False)
        except Exception:
            pass

    target_file = wav_file if wav_file.exists() and wav_file.stat().st_size > 0 else output_file
    mime_type = "audio/wav" if target_file.suffix == ".wav" else "audio/mp3"

    with open(target_file, "rb") as f:
        audio_bytes = f.read()
        b64_audio = base64.b64encode(audio_bytes).decode('utf-8')
        
    est_duration = max(1.5, min(35.0, (len(text) / 14.0) + 0.6))

    res = {
        "success": True,
        "filepath": str(target_file),
        "filename": target_file.name,
        "base64": b64_audio,
        "mime": mime_type,
        "duration": est_duration,
        "voice": voice,
        "size_bytes": len(audio_bytes)
    }
    _IN_MEMORY_AUDIO_CACHE[cache_key] = res
    return res

def get_audio_duration_estimate(text: str) -> float:
    """Estimates spoken duration in seconds."""
    return max(1.5, min(35.0, (len(text) / 14.0) + 0.6))

async def prewarm_voice_cache():
    """Pre-synthesizes common wake-up and direct command responses in RAM for instant 0ms playback."""
    common_phrases = [
        "Online and ready, Sir. All systems functioning at peak capacity.",
        "At your service, Sir Shakil. Neural matrix synchronized and awaiting your directive.",
        "Always listening, Sir. What is your will?",
        "Systems nominal, Sir Shakil. Ready for your directive.",
        "Right away, Sir Shakil.",
        "Core diagnostics nominal, Sir Shakil.",
        "Initiating Google Chrome immediately, Sir Shakil.",
        "Dedicated Jarvis Chrome browser profile launched on your display, Sir Shakil.",
        "Screen capture completed, Sir.",
        "Securing workstation protocols now, Sir Shakil.",
        "Audio muted as requested, Sir Shakil.",
        "Audio unmuted, Sir Shakil."
    ]
    for phrase in common_phrases:
        try:
            await synthesize_speech_async(phrase)
        except Exception:
            pass

def synthesize_speech(text: str, voice: str = DEFAULT_VOICE, rate: str = None, pitch: str = None) -> dict:
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(synthesize_speech_async(text, voice, rate, pitch), loop)
            return future.result()
        else:
            return asyncio.run(synthesize_speech_async(text, voice, rate, pitch))
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_voice_list():
    return POPULAR_VOICES

import ctypes
import threading

_speaker_lock = threading.Lock()
_is_speaker_playing = False
_playback_epoch = 0
_active_audio_process = None

def get_current_epoch() -> int:
    return _playback_epoch

def is_speaking() -> bool:
    """Returns True if local speaker playback is currently active."""
    return _is_speaker_playing

def play_audio_file_on_speakers(filepath: str, epoch: Optional[int] = None):
    """Plays an audio file directly through Windows PC speakers via winsound (WAV) or ffplay with epoch validation."""
    global _is_speaker_playing, _active_audio_process
    assigned_epoch = epoch if epoch is not None else _playback_epoch

    def _worker():
        global _is_speaker_playing, _active_audio_process
        if assigned_epoch != _playback_epoch:
            return

        with _speaker_lock:
            if assigned_epoch != _playback_epoch:
                return

            try:
                _is_speaker_playing = True
                abs_path = os.path.abspath(filepath)
                
                from core import audio_device_manager as adm
                target_dev, target_name = adm.resolve_best_output_device()
                
                # Direct hardware routing to selected speaker
                if target_dev is not None and abs_path.lower().endswith(".wav") and os.path.exists(abs_path):
                    try:
                        import wave
                        import sounddevice as sd
                        import numpy as np
                        with wave.open(abs_path, 'rb') as wf:
                            ch = wf.getnchannels()
                            sr = wf.getframerate()
                            frames = wf.readframes(wf.getnframes())
                            audio_arr = np.frombuffer(frames, dtype=np.int16)
                            if ch > 1:
                                audio_arr = audio_arr.reshape(-1, ch)
                            sd.play(audio_arr, samplerate=sr, device=target_dev)
                            sd.wait()
                    except Exception as sd_err:
                        import winsound
                        winsound.PlaySound(abs_path, winsound.SND_FILENAME)
                elif abs_path.lower().endswith(".wav") and os.path.exists(abs_path):
                    import winsound
                    winsound.PlaySound(abs_path, winsound.SND_FILENAME)
                else:
                    # ffplay native fallback
                    import subprocess
                    proc = subprocess.Popen(
                        ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', abs_path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    _active_audio_process = proc
                    proc.wait()
                    _active_audio_process = None
            except Exception as e:
                print(f"[!] Primary speaker playback error: {e}")
                try:
                    winmm = ctypes.windll.winmm
                    winmm.mciSendStringW('close jarvis_voice', None, 0, None)
                    ret_open = winmm.mciSendStringW(f'open "{abs_path}" type mpegvideo alias jarvis_voice', None, 0, None)
                    if ret_open == 0:
                        winmm.mciSendStringW('play jarvis_voice wait', None, 0, None)
                        winmm.mciSendStringW('close jarvis_voice', None, 0, None)
                except Exception as mci_err:
                    print(f"[!] WinMM fallback failed: {mci_err}")
            finally:
                _is_speaker_playing = False

    threading.Thread(target=_worker, daemon=True).start()

def stop_local_audio():
    """Immediately halts any active local speaker playback and discards all queued sentences."""
    global _is_speaker_playing, _playback_epoch, _active_audio_process
    _playback_epoch += 1  # Invalidate all queued playback threads immediately
    _is_speaker_playing = False

    try:
        import winsound
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass

    if _active_audio_process:
        try:
            _active_audio_process.terminate()
            _active_audio_process = None
        except Exception:
            pass

    try:
        winmm = ctypes.windll.winmm
        winmm.mciSendStringW('stop jarvis_voice', None, 0, None)
        winmm.mciSendStringW('close jarvis_voice', None, 0, None)
    except Exception:
        pass

