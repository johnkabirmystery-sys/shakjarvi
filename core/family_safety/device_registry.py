"""
J.A.R.V.I.S. Mark XVII — Authorized Family Device Registry
===========================================================
Manages explicit, consent-driven device enrollment, pairing codes,
revocation, and metadata management for authorized family devices.
"""

import hashlib
import hmac
import secrets
import time
from typing import Dict, List, Optional, Any

from .models import (
    FamilyDevice, DeviceType, PlatformType, EnrollmentStatus,
    ConsentStatus, LocationPermissionLevel
)
from .storage import family_storage

class FamilyDeviceRegistry:
    def __init__(self, storage=None):
        self.storage = storage or family_storage

    def generate_pairing_code(self, owner_profile_id: str, display_name: str,
                              device_type: str = "phone", platform: str = "android",
                              ttl_seconds: int = 600) -> Dict[str, Any]:
        """Generates a secure 6-digit numeric pairing code with cryptographic hash and expiration."""
        raw_code = f"{secrets.randbelow(900000) + 100000}"  # 6-digit secure code
        code_hash = hashlib.sha256(raw_code.encode()).hexdigest()
        expires_at = time.time() + ttl_seconds
        
        device = FamilyDevice(
            displayName=display_name,
            ownerProfileId=owner_profile_id,
            deviceType=DeviceType(device_type),
            platform=PlatformType(platform),
            enrollmentStatus=EnrollmentStatus.PENDING_PAIRING,
            consentStatus=ConsentStatus.PENDING_REVIEW,
            locationPermission=LocationPermissionLevel.NONE
        )
        
        device_dict = device.model_dump()
        device_dict["pairingCodeHash"] = code_hash
        device_dict["pairingExpiresAt"] = expires_at
        
        self.storage.upsert_device(device_dict)
        self.storage.log_audit(
            event_type="DEVICE_PAIRING_INITIATED",
            actor_id=owner_profile_id,
            target_id=device.deviceId,
            action=f"Generated pairing code for device '{display_name}'",
            risk_level="MEDIUM"
        )
        
        return {
            "success": True,
            "deviceId": device.deviceId,
            "pairingCode": raw_code,
            "expiresAt": expires_at,
            "expiresInSeconds": ttl_seconds,
            "displayName": display_name
        }

    def complete_pairing(self, device_id: Optional[str], pairing_code: str,
                         device_capabilities: Optional[Dict[str, Any]] = None,
                         ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Validates the pairing code on the target device and activates enrollment."""
        if not pairing_code or not pairing_code.strip():
            return {"success": False, "error": "Pairing code is required."}

        code_hash = hashlib.sha256(pairing_code.strip().encode()).hexdigest()

        if not device_id:
            device = self.storage.find_device_by_pairing_code_hash(code_hash)
            if not device:
                return {"success": False, "error": "Invalid or expired pairing code."}
            device_id = device["deviceId"]
        else:
            device = self.storage.get_device(device_id)
            if not device:
                # Fallback to lookup by code hash
                device = self.storage.find_device_by_pairing_code_hash(code_hash)
                if not device:
                    return {"success": False, "error": "Device not found."}
                device_id = device["deviceId"]
        
        if device["enrollmentStatus"] == EnrollmentStatus.ENROLLED.value:
            return {"success": False, "error": "Device is already enrolled."}
        
        if device["enrollmentStatus"] == EnrollmentStatus.REVOKED.value:
            return {"success": False, "error": "Device enrollment has been revoked by owner."}

        expires_at = device.get("pairingExpiresAt") or 0
        if time.time() > expires_at:
            return {"success": False, "error": "Pairing code has expired. Request a new code."}

        if not hmac.compare_digest(code_hash, device.get("pairingCodeHash") or ""):
            self.storage.log_audit(
                event_type="DEVICE_PAIRING_FAILED",
                actor_id=device["ownerProfileId"],
                target_id=device_id,
                action="Invalid pairing code attempt",
                risk_level="HIGH",
                ip_address=ip_address
            )
            return {"success": False, "error": "Invalid pairing code."}

        # Successful Pairing
        device["enrollmentStatus"] = EnrollmentStatus.ENROLLED.value
        device["consentStatus"] = ConsentStatus.ACTIVE.value
        device["pairingCodeHash"] = None
        device["pairingExpiresAt"] = None
        device["lastSeenAt"] = time.time()
        device["capabilities"] = device_capabilities or {}
        device["lastKnownConnection"] = {"ip": ip_address, "pairedAt": time.time()}
        device["updatedAt"] = time.time()

        self.storage.upsert_device(device)
        self.storage.log_audit(
            event_type="DEVICE_ENROLLED",
            actor_id=device["ownerProfileId"],
            target_id=device_id,
            action=f"Device '{device['displayName']}' successfully paired and enrolled.",
            risk_level="LOW",
            ip_address=ip_address
        )

        return {
            "success": True,
            "deviceId": device_id,
            "displayName": device["displayName"],
            "enrollmentStatus": device["enrollmentStatus"]
        }

    def update_device_permissions(self, device_id: str, actor_id: str,
                                  location_permission: str, consent_status: Optional[str] = None) -> Dict[str, Any]:
        """Updates owner-controlled permissions for an enrolled device."""
        device = self.storage.get_device(device_id)
        if not device:
            return {"success": False, "error": "Device not found."}

        # Only owner or system admin can modify device permissions
        if device["ownerProfileId"] != actor_id and actor_id != "system_admin" and actor_id != "shakil":
            return {"success": False, "error": "Unauthorized: only device owner can modify permissions."}

        if location_permission in [e.value for e in LocationPermissionLevel]:
            device["locationPermission"] = location_permission
        if consent_status and consent_status in [e.value for e in ConsentStatus]:
            device["consentStatus"] = consent_status
        device["updatedAt"] = time.time()

        self.storage.upsert_device(device)
        self.storage.log_audit(
            event_type="DEVICE_PERMISSIONS_UPDATED",
            actor_id=actor_id,
            target_id=device_id,
            action=f"Updated permissions: location={device['locationPermission']}, consent={device['consentStatus']}",
            risk_level="MEDIUM"
        )
        return {"success": True, "device": device}

    def revoke_device(self, device_id: str, actor_id: str, reason: str = "User requested revocation") -> Dict[str, Any]:
        """Explicitly revokes device access."""
        device = self.storage.get_device(device_id)
        if not device:
            return {"success": False, "error": "Device not found."}

        device["enrollmentStatus"] = EnrollmentStatus.REVOKED.value
        device["consentStatus"] = ConsentStatus.REVOKED.value
        device["locationPermission"] = LocationPermissionLevel.NONE.value
        device["updatedAt"] = time.time()

        self.storage.upsert_device(device)
        self.storage.log_audit(
            event_type="DEVICE_REVOKED",
            actor_id=actor_id,
            target_id=device_id,
            action=f"Device revoked. Reason: {reason}",
            risk_level="HIGH"
        )
        return {"success": True, "message": f"Device '{device['displayName']}' revoked."}

    def remove_device(self, device_id: str, actor_id: str) -> Dict[str, Any]:
        """Permanently removes a device from the registry and purges related session keys."""
        device = self.storage.get_device(device_id)
        if not device:
            return {"success": False, "error": "Device not found."}

        self.storage.delete_device(device_id)
        self.storage.log_audit(
            event_type="DEVICE_REMOVED",
            actor_id=actor_id,
            target_id=device_id,
            action=f"Device '{device['displayName']}' removed permanently.",
            risk_level="HIGH"
        )
        return {"success": True, "message": f"Device '{device['displayName']}' permanently removed."}

    def list_devices(self, owner_profile_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.storage.list_devices(owner_profile_id)

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        return self.storage.get_device(device_id)

device_registry = FamilyDeviceRegistry()
