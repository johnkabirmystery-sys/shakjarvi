"""
J.A.R.V.I.S. Central Conversation Controller
===========================================
Authoritative governor of dialogue turns, state machine transitions, 
preemption, cancellation, and audio synchronization for Sir Shakil.
"""

import time
import asyncio
import re
from typing import Optional, Dict, Any, Callable
from enum import Enum

class ConversationState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"
    EXECUTING_TASK = "executing_task"
    ERROR = "error"

# Comprehensive cancellation and stop lexicon with phonetic tolerance
STOP_PATTERNS = [
    r"^(?:jarvis\s+|please\s+)?(?:stop|cancel|abort|wait|hold on|be quiet|quiet|shut up|never mind|nevermind|pause|hush|silence)(?:\s+(?:talking|speaking|it|that|please|(?:right\s+)?now))*$",
    r"^(?:stop|cancel|wait)\s+processing$",
    r"^(?:please\s+)?(?:stop|be quiet|shut up|cancel)(?:\s+.*)?$"
]

def is_stop_command(text: str) -> bool:
    """Robustly checks whether an utterance represents an interruption or cancellation directive."""
    if not text:
        return False
    clean = re.sub(r"[^\w\s]", "", text.lower()).strip()
    clean = re.sub(r"\s+", " ", clean)
    # Direct short keywords
    if clean in ["stop", "cancel", "abort", "wait", "hold on", "be quiet", "shut up", "nevermind", "never mind", "pause", "silence", "hush"]:
        return True
    for pat in STOP_PATTERNS:
        if re.match(pat, clean):
            return True
    return False

class ConversationController:
    def __init__(self, broadcast_fn: Optional[Callable] = None):
        self.broadcast_fn = broadcast_fn
        self.state = ConversationState.IDLE
        self.current_turn_id = 0
        self.active_turn_id = 0
        self.active_task: Optional[asyncio.Task] = None
        self.last_interaction_time = 0.0
        self.last_user_speech = ""
        self.last_assistant_speech = ""
        self.recent_request_hashes = {}  # for acoustic deduplication

    def set_broadcast_fn(self, fn: Callable):
        self.broadcast_fn = fn

    is_stop_command = staticmethod(is_stop_command)

    def register_new_turn(self, source: str = "native") -> int:
        """Explicitly advances and returns the new monotonic turn ID."""
        self.current_turn_id += 1
        self.active_turn_id = self.current_turn_id
        return self.current_turn_id

    def is_turn_current(self, turn_id: int) -> bool:
        """Validates if a given turn_id is the currently active turn."""
        return turn_id == self.current_turn_id

    def get_state(self) -> str:
        return self.state.value

    def is_dialogue_active(self, window_seconds: float = 15.0) -> bool:
        """Returns True if user or assistant spoke recently or is currently active."""
        if self.state in [ConversationState.LISTENING, ConversationState.THINKING, ConversationState.SPEAKING]:
            return True
        return (time.time() - self.last_interaction_time) < window_seconds

    async def set_state(self, new_state: ConversationState, subtext: str = ""):
        self.state = new_state
        self.last_interaction_time = time.time()
        if self.broadcast_fn:
            try:
                await self.broadcast_fn({
                    "type": "status",
                    "status": new_state.value,
                    "subtext": subtext,
                    "turn_id": self.current_turn_id,
                    "timestamp": time.time()
                })
            except Exception as e:
                print(f"[ConversationController] Broadcast error: {e}", flush=True)

    def is_duplicate_acoustic_request(self, text: str) -> bool:
        """Thread-safe deduplication preventing dual-device or dual-engine duplicate executions."""
        now = time.time()
        clean = text.lower().strip()
        # Prune old hashes (> 5.0 seconds)
        for k in list(self.recent_request_hashes.keys()):
            if now - self.recent_request_hashes[k]["time"] > 5.0:
                self.recent_request_hashes.pop(k, None)

        for req_id, data in self.recent_request_hashes.items():
            prev = data["text"]
            if (clean == prev or (len(clean) > 6 and clean in prev) or (len(prev) > 6 and prev in clean)) and (now - data["time"] < 3.5):
                return True

        self.recent_request_hashes[f"turn_{now}_{clean[:10]}"] = {"text": clean, "time": now}
        return False

    async def abort_active_turn(self, reason: str = "user_stop"):
        """Immediately halts active model inference, TTS generation, and audio playback."""
        print(f"[ConversationController] >>> ABORT TRIGGERED: reason='{reason}' on Turn #{self.active_turn_id}", flush=True)
        
        # 1. Cancel the active Python asyncio task
        if self.active_task and not self.active_task.done():
            self.active_task.cancel()
            self.active_task = None

        # 2. Halt local OS audio kernel playback immediately
        from core import voice_engine
        voice_engine.stop_local_audio()

        # 3. Halt active orchestrator tasks
        try:
            from core.orchestrator import orchestrator
            await orchestrator.cancel_all_active(reason=reason)
        except Exception as e:
            print(f"[ConversationController] Orchestrator cancel error: {e}", flush=True)

        # 4. Broadcast instant abort event to all connected WebSocket HUD clients
        if self.broadcast_fn:
            try:
                await self.broadcast_fn({
                    "type": "abort",
                    "turn_id": self.active_turn_id,
                    "reason": reason,
                    "timestamp": time.time()
                })
            except Exception as e:
                print(f"[ConversationController] Broadcast abort error: {e}", flush=True)

        await self.set_state(ConversationState.IDLE, "READY FOR SIR SHAKIL")

    async def handle_user_prompt(
        self,
        prompt: str,
        source: str = "native",
        voice_enabled: bool = True,
        play_speaker: bool = False,
        model: Optional[str] = None,
        history: Optional[list] = None,
        workspace: str = "personal",
        process_callback: Optional[Callable] = None
    ) -> Optional[Dict[str, Any]]:
        """Coordinates a user prompt turn, enforcing preemption and single-response exclusivity."""
        prompt = (prompt or "").strip()
        if not prompt:
            return None

        self.last_interaction_time = time.time()
        print(f"\n[ConversationController] Prompt received via [{source}]: '{prompt}'", flush=True)

        # 1. Immediate Stop & Interruption Directive Detection
        if is_stop_command(prompt):
            print(f"[ConversationController] Stop command identified from '{prompt}'. Halting active operations.", flush=True)
            await self.abort_active_turn(reason="user_stop")
            return {
                "turn_id": self.current_turn_id,
                "status": "aborted",
                "message": "Operations paused, Sir Shakil."
            }

        # 2. Acoustic Deduplication (prevents dual-microphone or phone+PC duplicate capture)
        if self.is_duplicate_acoustic_request(prompt):
            print(f"[ConversationController] Dropped duplicate acoustic request: '{prompt}'", flush=True)
            return {"turn_id": self.current_turn_id, "duplicate": True}

        # 3. Turn Preemption: If a previous turn is in progress, abort it immediately!
        if self.active_task and not self.active_task.done():
            print(f"[ConversationController] Preempting previous Turn #{self.active_turn_id} with new prompt!", flush=True)
            await self.abort_active_turn(reason="superseded_by_new_input")

        # 4. Advance Monotonic Turn ID
        self.current_turn_id += 1
        turn_id = self.current_turn_id
        self.active_turn_id = turn_id
        self.last_user_speech = prompt

        await self.set_state(ConversationState.THINKING, "PROCESSING DIRECTIVE")

        # 5. Launch processing coroutine if callback provided
        if process_callback:
            coro = process_callback(
                turn_id=turn_id,
                prompt=prompt,
                source=source,
                voice_enabled=voice_enabled,
                play_speaker=play_speaker,
                model=model,
                history=history,
                workspace=workspace
            )
            self.active_task = asyncio.create_task(coro)
            return {"turn_id": turn_id, "status": "started"}

        return {"turn_id": turn_id, "status": "acknowledged"}

# Global singleton
conversation_controller = ConversationController()
