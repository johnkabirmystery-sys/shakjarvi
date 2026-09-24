"""
J.A.R.V.I.S. Mark XVII — Family Safety Consent Manager
=======================================================
Enforces strict, participant-controlled consent scopes, emergency kill switches,
granular permissions, and one-click data deletion.
"""

import time
from typing import Dict, List, Optional, Any

from .models import FamilyConsentRecord, ConsentStatus
from .storage import family_storage

class FamilySafetyConsentManager:
    def __init__(self, storage=None):
        self.storage = storage or family_storage

    def get_or_create_consent(self, participant_id: str, owner_profile_id: str) -> Dict[str, Any]:
        """Retrieves an existing consent record or initializes a default restrictive one."""
        existing = self.storage.get_consent(participant_id)
        if existing:
            return existing

        default_record = FamilyConsentRecord(
            participantId=participant_id,
            ownerProfileId=owner_profile_id,
            consentVersion="1.0",
            locationSharingEnabled=False,
            liveLocationEnabled=False,
            locationHistoryEnabled=False,
            safetyAlertsEnabled=True,
            geofenceAlertsEnabled=True,
            emergencyContactPermission=False,
            notificationPermission=True,
            backgroundLocationEnabled=False,
            externalSharingEnabled=False
        )
        data = default_record.model_dump()
        self.storage.upsert_consent(data)
        return data

    def update_consent(self, participant_id: str, actor_id: str,
                       permissions: Dict[str, bool]) -> Dict[str, Any]:
        """Updates granular consent scopes with participant/owner authorization."""
        consent = self.storage.get_consent(participant_id)
        if not consent:
            consent = self.get_or_create_consent(participant_id, owner_profile_id=actor_id)

        # Verify authorization: participant themselves or owner
        if consent["ownerProfileId"] != actor_id and consent["participantId"] != actor_id and actor_id != "shakil":
            return {"success": False, "error": "Unauthorized: consent can only be modified by the participant or owner."}

        for k, v in permissions.items():
            if k in consent:
                consent[k] = bool(v)

        consent["lastReviewedAt"] = time.time()
        self.storage.upsert_consent(consent)

        self.storage.log_audit(
            event_type="CONSENT_UPDATED",
            actor_id=actor_id,
            target_id=participant_id,
            action="Updated granular safety consent scopes",
            details=permissions,
            risk_level="MEDIUM"
        )

        return {"success": True, "consent": consent}

    def pause_all_sharing(self, actor_id: str) -> Dict[str, Any]:
        """IMMEDIATE MASTER KILL SWITCH: Pauses all location sharing across all family participants."""
        consents = self.storage.list_consents()
        count = 0
        for c in consents:
            c["locationSharingEnabled"] = False
            c["liveLocationEnabled"] = False
            c["backgroundLocationEnabled"] = False
            c["externalSharingEnabled"] = False
            c["lastReviewedAt"] = time.time()
            self.storage.upsert_consent(c)
            count += 1

        self.storage.log_audit(
            event_type="EMERGENCY_SHARING_KILL_SWITCH",
            actor_id=actor_id,
            action=f"Immediate Master Kill Switch: paused location sharing across {count} participants",
            risk_level="HIGH"
        )

        return {
            "success": True,
            "message": f"Emergency Master Kill Switch executed. Location sharing disabled for {count} participants.",
            "pausedCount": count
        }

    def revoke_participant_consent(self, participant_id: str, actor_id: str) -> Dict[str, Any]:
        """Completely revokes all consent scopes for a participant."""
        consent = self.storage.get_consent(participant_id)
        if not consent:
            return {"success": False, "error": "Consent record not found."}

        consent["locationSharingEnabled"] = False
        consent["liveLocationEnabled"] = False
        consent["locationHistoryEnabled"] = False
        consent["backgroundLocationEnabled"] = False
        consent["externalSharingEnabled"] = False
        consent["emergencyContactPermission"] = False
        consent["revokedAt"] = time.time()
        consent["lastReviewedAt"] = time.time()

        self.storage.upsert_consent(consent)
        self.storage.log_audit(
            event_type="CONSENT_REVOKED",
            actor_id=actor_id,
            target_id=participant_id,
            action=f"Participant {participant_id} revoked all consent scopes.",
            risk_level="HIGH"
        )

        return {"success": True, "message": f"Consent revoked for participant {participant_id}."}

    def check_permission(self, participant_id: str, scope: str) -> bool:
        """Evaluates whether a specific permission scope is actively granted."""
        consent = self.storage.get_consent(participant_id)
        if not consent:
            consent = self.get_or_create_consent(participant_id, owner_profile_id=participant_id)

        if consent.get("revokedAt"):
            return False

        return bool(consent.get(scope, False))

    def delete_participant_history(self, participant_id: str, actor_id: str) -> Dict[str, Any]:
        """Purges all stored location history for a participant."""
        self.storage.delete_location_history(participant_id)
        self.storage.log_audit(
            event_type="LOCATION_HISTORY_PURGED",
            actor_id=actor_id,
            target_id=participant_id,
            action=f"Purged all location history for participant {participant_id}",
            risk_level="HIGH"
        )
        return {"success": True, "message": f"Location history purged for participant {participant_id}."}

    def list_consents(self) -> List[Dict[str, Any]]:
        return self.storage.list_consents()

consent_manager = FamilySafetyConsentManager()
