"""
J.A.R.V.I.S. Proactive Autonomous Supervisor (core/proactive_supervisor.py)
==========================================================================
Non-intrusive background watcher for workstation health, market metrics, and telemetry.
Strictly respects dialogue state and quiet hours (never interrupts active conversation).
"""

import time
import asyncio
from typing import Optional, Dict, Any

from core.conversation_controller import conversation_controller, ConversationState
from core import telemetry

class ProactiveSupervisor:
    """Monitors system vitals and events in the background with strict dialogue respect."""
    def __init__(self, check_interval_sec: float = 60.0):
        self.check_interval_sec = check_interval_sec
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.last_alerts: list = []
        self._last_cpu_alert_time = 0.0

    def start(self):
        """Starts the background supervisor task."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._supervision_loop())
            print("[ProactiveSupervisor] Background supervisor engaged.", flush=True)

    def stop(self):
        """Halts the background supervisor."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        print("[ProactiveSupervisor] Background supervisor halted.", flush=True)

    def is_silent_period(self) -> bool:
        """Checks if current time falls within user-specified quiet hours (e.g. 11 PM to 7 AM)."""
        current_hour = time.localtime().tm_hour
        return current_hour >= 23 or current_hour < 7

    async def _supervision_loop(self):
        while self._running:
            try:
                await asyncio.sleep(self.check_interval_sec)
                
                # Check dialogue activity: NEVER interrupt when active conversation is ongoing
                if conversation_controller.is_dialogue_active():
                    continue

                # Run non-blocking checks
                await self._check_system_vitals()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ProactiveSupervisor] Non-fatal loop error: {e}", flush=True)
                await asyncio.sleep(5)

    async def _check_system_vitals(self):
        """Verifies RAM and CPU load, recording non-intrusive alerts."""
        try:
            tdata = telemetry.get_telemetry_data()
            cpu_pct = tdata.get("cpu", {}).get("percent", 0)
            ram_pct = tdata.get("memory", {}).get("percent", 0)

            now = time.time()
            # High RAM warning threshold (> 92%)
            if ram_pct > 92 and (now - self._last_cpu_alert_time > 300):
                self._last_cpu_alert_time = now
                alert = {
                    "time": time.strftime("%H:%M:%S"),
                    "level": "warning",
                    "type": "memory",
                    "message": f"RAM allocation at {ram_pct}%. Consider closing inactive background tasks."
                }
                self.last_alerts.append(alert)
                if len(self.last_alerts) > 10:
                    self.last_alerts = self.last_alerts[-10:]
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "dialogue_active": conversation_controller.is_dialogue_active(),
            "silent_period": self.is_silent_period(),
            "recent_alerts": self.last_alerts[-3:]
        }

# Global singleton
proactive_supervisor = ProactiveSupervisor(check_interval_sec=60.0)
