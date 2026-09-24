"""
J.A.R.V.I.S. Mark XVII — Safety Signal Engine
==============================================
Processes authorized safety signals and telemetry from enrolled devices
and verified public emergency feeds. Free from demographic bias or speculative heuristics.
"""

import time
from typing import Dict, List, Optional, Any

from .models import SafetySignal, SignalType
from .storage import family_storage
from .consent_manager import consent_manager

class SafetySignalEngine:
    def __init__(self, storage=None, consent=None):
        self.storage = storage or family_storage
        self.consent = consent or consent_manager
        self.signal_handlers = []

    def register_signal_handler(self, handler):
        self.signal_handlers.append(handler)

    def ingest_signal(self, participant_id: str, signal_type: str,
                      raw_data: Optional[Dict[str, Any]] = None,
                      source: str = "device_telemetry",
                      confidence: float = 1.0,
                      location: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Ingests a verified safety signal after validating participant consent."""
        # 1. Safety Alerts Consent Check
        if not self.consent.check_permission(participant_id, "safetyAlertsEnabled"):
            return {
                "success": False,
                "error": f"Safety signals/alerts are disabled in participant {participant_id}'s consent policy."
            }

        # 2. Location Consent Check if location is attached
        valid_location = None
        if location and self.consent.check_permission(participant_id, "locationSharingEnabled"):
            valid_location = location

        try:
            sig_enum = SignalType(signal_type)
        except ValueError:
            return {"success": False, "error": f"Invalid signal type: {signal_type}"}

        sig = SafetySignal(
            participantId=participant_id,
            signalType=sig_enum,
            timestamp=time.time(),
            rawData=raw_data or {},
            source=source,
            confidence=max(0.1, min(1.0, float(confidence))),
            location=valid_location
        )

        sig_dict = sig.model_dump()
        self.storage.save_signal(sig_dict)

        # Notify downstream alert engine handlers
        for handler in self.signal_handlers:
            try:
                handler(sig_dict)
            except Exception as e:
                pass

        return {
            "success": True,
            "signalId": sig.signalId,
            "signalType": sig.signalType.value,
            "timestamp": sig.timestamp
        }

safety_signal_engine = SafetySignalEngine()
