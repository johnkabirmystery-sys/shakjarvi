import asyncio
import time
from core import telemetry
from core.voice_engine import synthesize_speech_async

class ProactiveMonitor:
    def __init__(self, broadcast_callback=None):
        self.broadcast_callback = broadcast_callback
        self.is_running = False
        self.last_ram_alert = 0
        self.last_cpu_alert = 0
        self.last_battery_alert = 0
        self.last_research_run = time.time() - 14340  # trigger first auto-research 60s after boot
        self.has_greeted = False

    async def start(self):
        self.is_running = True
        
        # Initial boot greeting after 3 seconds
        await asyncio.sleep(3)
        if not self.has_greeted:
            self.has_greeted = True
            await self._trigger_alert(
                "Good day, Sir Shakil. J.A.R.V.I.S. online, all auxiliary systems functional, and memory vault synchronized.",
                level="info"
            )

        # Launch background research loop
        asyncio.create_task(self._autonomous_research_loop())

        while self.is_running:
            try:
                from core.conversation_controller import conversation_controller
                # Suppress non-critical proactive announcements during active user dialogue
                if conversation_controller.is_dialogue_active():
                    await asyncio.sleep(5)
                    continue

                data = telemetry.get_telemetry_data()
                now = time.time()
                
                # RAM check (> 88%)
                ram_percent = data["memory"]["percent"]
                if ram_percent > 88 and (now - self.last_ram_alert > 900):
                    self.last_ram_alert = now
                    await self._trigger_alert(
                        f"Notice, Sir Shakil. Physical memory allocation has reached {ram_percent}%.",
                        level="warning"
                    )

                # CPU check (> 92%)
                cpu_percent = data["cpu"]["percent"]
                if cpu_percent > 92 and (now - self.last_cpu_alert > 900):
                    self.last_cpu_alert = now
                    await self._trigger_alert(
                        f"Core alert, Sir Shakil. Processor load is currently peaking at {cpu_percent}%.",
                        level="warning"
                    )

                # Battery check (< 20% and not plugged)
                battery = data.get("battery")
                if battery and not battery.get("power_plugged") and battery.get("percent", 100) < 20:
                    if now - self.last_battery_alert > 1200:
                        self.last_battery_alert = now
                        b_pct = battery.get("percent")
                        await self._trigger_alert(
                            f"Power grid notification, Sir Shakil. Battery reserves are down to {b_pct}%. Please connect main power.",
                            level="warning"
                        )

            except Exception:
                pass
                
            await asyncio.sleep(5)

    async def _autonomous_research_loop(self):
        """Periodically carries out self-directed research to make J.A.R.V.I.S. smarter every day."""
        # Wait 45s after boot before starting first research
        await asyncio.sleep(45)
        
        while self.is_running:
            try:
                from core import research_engine
                res = await research_engine.conduct_deep_research()
                if res.get("success"):
                    text = f"Sir Shakil, I have completed an autonomous research cycle on {res['topic']} and assimilated a new knowledge node. My evolution rating is now Level {res['stats']['level']}."
                    await self._trigger_alert(text, level="info")
            except Exception:
                pass
            
            # Run research every 4 hours (14400 seconds)
            await asyncio.sleep(14400)

    async def _trigger_alert(self, text: str, level: str = "info"):
        tts_res = await synthesize_speech_async(text)
        payload = {
            "type": "proactive_update",
            "level": level,
            "text": text,
            "audio_base64": tts_res.get("base64"),
            "timestamp": time.time()
        }
        if self.broadcast_callback:
            await self.broadcast_callback(payload)

    def stop(self):
        self.is_running = False
