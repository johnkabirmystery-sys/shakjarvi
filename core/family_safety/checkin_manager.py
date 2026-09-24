"""
J.A.R.V.I.S. Mark XVII — Family Check-In & Wellness Workflow
============================================================
Manages voluntary family check-in schedules, 'I'm Safe' / 'Need Help'
responses, grace period expiration, and truthful status classification.
"""

import time
from typing import Dict, List, Optional, Any

from .models import CheckInRecord, SignalType
from .storage import family_storage
from .safety_signals import safety_signal_engine

class CheckInManager:
    def __init__(self, storage=None, signal_engine=None):
        self.storage = storage or family_storage
        self.signal_engine = signal_engine or safety_signal_engine

    def schedule_checkin(self, participant_id: str, scheduled_at: float,
                         grace_period_minutes: int = 15, notes: Optional[str] = None) -> Dict[str, Any]:
        """Schedules a voluntary check-in for a family participant."""
        chk = CheckInRecord(
            participantId=participant_id,
            scheduledAt=scheduled_at,
            status="pending",
            gracePeriodMinutes=grace_period_minutes,
            notes=notes
        )
        data = chk.model_dump()
        self.storage.save_checkin(data)
        
        self.storage.log_audit(
            event_type="CHECKIN_SCHEDULED",
            actor_id=participant_id,
            target_id=chk.checkInId,
            action=f"Scheduled voluntary check-in for {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(scheduled_at))}",
            risk_level="LOW"
        )
        return {"success": True, "checkin": data}

    def respond_checkin(self, checkin_id: str, response_type: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """Processes a participant's response: 'safe' or 'need_help'."""
        chk = self.storage.get_checkin(checkin_id)
        if not chk:
            return {"success": False, "error": "Check-in record not found."}

        now = time.time()
        resp_clean = response_type.lower().strip()
        participant_id = chk.get("participantId") or chk.get("participant_id")
        
        if resp_clean == "safe" or resp_clean == "i_am_safe":
            chk["status"] = "confirmed"
            chk["responseType"] = "safe"
            chk["respondedAt"] = now
            chk["notes"] = notes or "Participant confirmed safe."
            self.storage.save_checkin(chk)

            # Ingest manual check-in signal
            self.signal_engine.ingest_signal(
                participant_id=participant_id,
                signal_type=SignalType.MANUAL_CHECKIN.value,
                raw_data={"checkInId": checkin_id, "status": "safe", "notes": notes},
                source="user_response"
            )

            return {"success": True, "status": "confirmed", "message": "Safety confirmed. Thank you!"}

        elif resp_clean == "need_help" or resp_clean == "sos":
            chk["status"] = "alerted"
            chk["responseType"] = "need_help"
            chk["respondedAt"] = now
            chk["notes"] = notes or "Participant requested assistance."
            self.storage.save_checkin(chk)

            # Trigger voluntary SOS signal
            self.signal_engine.ingest_signal(
                participant_id=participant_id,
                signal_type=SignalType.VOLUNTARY_SOS.value,
                raw_data={"checkInId": checkin_id, "message": notes or "Participant clicked Need Help"},
                source="user_response"
            )

            return {"success": True, "status": "alerted", "message": "Assistance request logged and escalated."}

        else:
            return {"success": False, "error": "Invalid response_type. Must be 'safe' or 'need_help'."}

    def evaluate_pending_checkins(self) -> List[Dict[str, Any]]:
        """Evaluates pending check-ins; triggers missed check-in signal if grace period expired."""
        now = time.time()
        missed = []
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM family_checkins WHERE status = 'pending'")
            rows = cursor.fetchall()
            for r in rows:
                chk = dict(r)
                scheduled = chk["scheduled_at"]
                grace_seconds = chk["grace_period_minutes"] * 60
                if now > (scheduled + grace_seconds):
                    # Grace period expired
                    chk["status"] = "missed"
                    self.storage.save_checkin(chk)
                    
                    self.signal_engine.ingest_signal(
                        participant_id=chk["participant_id"],
                        signal_type=SignalType.MISSED_CHECKIN.value,
                        raw_data={"checkInId": chk["checkin_id"], "gracePeriod": chk["grace_period_minutes"]},
                        source="scheduler_check"
                    )
                    missed.append(chk)
    def record_direct_checkin(self, participant_id: str, response_type: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """Records an immediate voluntary check-in directly without needing a pending scheduled record."""
        now = time.time()
        resp_clean = response_type.lower().strip()
        chk = CheckInRecord(
            participantId=participant_id,
            scheduledAt=now,
            status="confirmed" if (resp_clean in ["safe", "i_am_safe"]) else "alerted",
            responseType="safe" if (resp_clean in ["safe", "i_am_safe"]) else "need_help",
            respondedAt=now,
            notes=notes or ("Direct check-in via HUD" if resp_clean in ["safe", "i_am_safe"] else "SOS emergency triggered via HUD")
        )
        data = chk.model_dump()
        self.storage.save_checkin(data)

        if resp_clean in ["safe", "i_am_safe"]:
            self.signal_engine.ingest_signal(
                participant_id=participant_id,
                signal_type=SignalType.MANUAL_CHECKIN.value,
                raw_data={"checkInId": chk.checkInId, "status": "safe", "notes": notes},
                source="hud_direct_checkin"
            )
            return {"success": True, "status": "confirmed", "message": "Direct safety check-in recorded.", "checkin": data}
        else:
            self.signal_engine.ingest_signal(
                participant_id=participant_id,
                signal_type=SignalType.VOLUNTARY_SOS.value,
                raw_data={"checkInId": chk.checkInId, "message": notes or "Emergency SOS direct check-in"},
                source="hud_direct_sos"
            )
            return {"success": True, "status": "alerted", "message": "Emergency SOS alert dispatched to safety matrix.", "checkin": data}

    def get_status(self, participant_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves the latest check-in and next pending scheduled check-in."""
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Latest responded checkin
            if participant_id:
                cursor.execute("""
                    SELECT * FROM family_checkins 
                    WHERE participant_id = ? AND responded_at IS NOT NULL
                    ORDER BY responded_at DESC LIMIT 1
                """, (participant_id,))
            else:
                cursor.execute("""
                    SELECT * FROM family_checkins 
                    WHERE responded_at IS NOT NULL
                    ORDER BY responded_at DESC LIMIT 1
                """)
            latest_row = cursor.fetchone()
            latest = dict(latest_row) if latest_row else None

            # 2. Next pending scheduled checkin
            now = time.time()
            if participant_id:
                cursor.execute("""
                    SELECT * FROM family_checkins 
                    WHERE participant_id = ? AND status = 'pending' AND scheduled_at > ?
                    ORDER BY scheduled_at ASC LIMIT 1
                """, (participant_id, now))
            else:
                cursor.execute("""
                    SELECT * FROM family_checkins 
                    WHERE status = 'pending' AND scheduled_at > ?
                    ORDER BY scheduled_at ASC LIMIT 1
                """, (now,))
            next_row = cursor.fetchone()
            next_pending = dict(next_row) if next_row else None

            status_label = "ALL CLEAR"
            if latest and latest.get("response_type") == "need_help":
                status_label = "ASSISTANCE REQUESTED"

            return {
                "success": True,
                "status": status_label,
                "lastCheckIn": latest,
                "nextScheduled": next_pending["scheduled_at"] if next_pending else None,
                "nextScheduledIso": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(next_pending["scheduled_at"])) if next_pending else None
            }

checkin_manager = CheckInManager()
