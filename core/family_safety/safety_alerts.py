"""
J.A.R.V.I.S. Mark XVII — Safety Alert Engine
=============================================
Manages tiered safety alerts, deduplication, alert storm protection,
and escalation procedures with evidence preservation.
"""

import time
from typing import Dict, List, Optional, Any

from .models import SafetyAlert, AlertSeverity, SignalType
from .storage import family_storage
from .consent_manager import consent_manager
from .safety_signals import safety_signal_engine

class SafetyAlertEngine:
    def __init__(self, storage=None, consent=None):
        self.storage = storage or family_storage
        self.consent = consent or consent_manager
        self.recent_alerts: Dict[str, float] = {}  # Deduplication cache: key -> timestamp
        self.dedup_cooldown_seconds = 300.0  # 5 minutes cooldown per alert type/participant

        # Wire signal listener
        safety_signal_engine.register_signal_handler(self.evaluate_signal)

    def evaluate_signal(self, sig: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transforms an incoming signal into a structured, evidence-backed safety alert."""
        participant_id = sig["participantId"]
        sig_type = sig["signalType"]
        raw = sig.get("rawData") or {}

        # Build deduplication key
        dedup_key = f"{participant_id}:{sig_type}"
        now = time.time()
        if dedup_key in self.recent_alerts and (now - self.recent_alerts[dedup_key]) < self.dedup_cooldown_seconds:
            # Drop duplicate within cooldown window to prevent alert storms
            return None

        alert_type = sig_type
        severity = AlertSeverity.LOW
        evidence = f"Signal '{sig_type}' received from {sig.get('source', 'sensor')} at {time.strftime('%H:%M:%S')}."
        action = "Review participant status."
        fp_risk = "low"

        if sig_type == SignalType.VOLUNTARY_SOS.value:
            severity = AlertSeverity.CRITICAL
            evidence = f"User explicitly triggered voluntary SOS button on their enrolled device. Message: {raw.get('message', 'Emergency assistance requested')}."
            action = "Establish immediate contact with participant. Review emergency escalation policy."
            fp_risk = "very_low"
        elif sig_type == SignalType.MISSED_CHECKIN.value:
            severity = AlertSeverity.MEDIUM
            evidence = f"Participant missed scheduled check-in window (Grace period: {raw.get('gracePeriod', 15)}m expired). Note: No response received does NOT confirm danger."
            action = "Send follow-up check-in reminder or call participant."
            fp_risk = "medium"
        elif sig_type == SignalType.GEOFENCE_EXIT.value:
            severity = AlertSeverity.INFO
            fence_name = raw.get("fenceName", "Designated Safe Zone")
            evidence = f"Participant exited geofence boundary '{fence_name}'."
            action = "Informational update."
            fp_risk = "low"
        elif sig_type == SignalType.GEOFENCE_ENTER.value:
            severity = AlertSeverity.INFO
            fence_name = raw.get("fenceName", "Designated Safe Zone")
            evidence = f"Participant entered geofence boundary '{fence_name}'."
            action = "Informational update."
            fp_risk = "low"
        elif sig_type == SignalType.LOW_BATTERY.value:
            severity = AlertSeverity.LOW
            evidence = f"Enrolled device battery dropped to {raw.get('batteryLevel', 10)}%."
            action = "Remind participant to charge device."
            fp_risk = "very_low"
        elif sig_type == SignalType.PUBLIC_WEATHER_ALERT.value or sig_type == SignalType.PUBLIC_EARTHQUAKE_ALERT.value:
            severity = AlertSeverity.HIGH
            event_name = raw.get("event", "Severe public event")
            evidence = f"Public emergency broadcast detected: {event_name} near participant's shared region."
            action = "Verify participant awareness and safety."
            fp_risk = "low"

        alert = SafetyAlert(
            participantId=participant_id,
            alertType=alert_type,
            severity=severity,
            triggeredAt=now,
            evidence=evidence,
            source=sig.get("source", "SafetySignalEngine"),
            confidence=sig.get("confidence", 1.0),
            locationPrecision="city" if not sig.get("location") else "precise",
            expiration=now + 14400,  # 4 hours TTL
            recommendedAction=action,
            notificationState="queued",
            escalationState="none",
            falsePositiveRisk=fp_risk
        )

        alert_dict = alert.model_dump()
        self.storage.save_alert(alert_dict)
        self.recent_alerts[dedup_key] = now

        self.storage.log_audit(
            event_type="SAFETY_ALERT_TRIGGERED",
            actor_id="system",
            target_id=participant_id,
            action=f"Generated {severity.value} alert: {alert_type}",
            details=alert_dict,
            risk_level=severity.value
        )

        return alert_dict

    def trigger_manual_alert(self, participant_id: str, alert_type: str, severity: str,
                             evidence: str, recommended_action: str) -> Dict[str, Any]:
        """Manually creates an alert from user command or external webhook."""
        now = time.time()
        try:
            sev_enum = AlertSeverity(severity.upper())
        except ValueError:
            sev_enum = AlertSeverity.LOW

        alert = SafetyAlert(
            participantId=participant_id,
            alertType=alert_type,
            severity=sev_enum,
            triggeredAt=now,
            evidence=evidence,
            source="manual_dispatch",
            recommendedAction=recommended_action,
            notificationState="queued"
        )
        data = alert.model_dump()
        self.storage.save_alert(data)
        return {"success": True, "alert": data}

    def list_active_alerts(self, participant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.storage.list_active_alerts(participant_id)

    def dismiss_alert(self, alert_id: str, actor_id: str) -> Dict[str, Any]:
        self.storage.dismiss_alert(alert_id)
        self.storage.log_audit(
            event_type="SAFETY_ALERT_DISMISSED",
            actor_id=actor_id,
            target_id=alert_id,
            action=f"Alert {alert_id} dismissed by {actor_id}",
            risk_level="LOW"
        )
        return {"success": True, "message": f"Alert {alert_id} dismissed."}

safety_alert_engine = SafetyAlertEngine()
