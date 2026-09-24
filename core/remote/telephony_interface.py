"""
J.A.R.V.I.S. Mark XVII — Telephony & Voice Call Gateway
========================================================
Optional telephony interface with strict caller verification, IVR voice
command recognition, and caller identity verification before disclosing sensitive information.
"""

import time
import secrets
from typing import Dict, List, Optional, Any

from .auth_manager import remote_auth
from .command_gateway import remote_command_gateway
from core.family_safety.storage import family_storage

class TelephonyGateway:
    def __init__(self, auth=None, storage=None, command_gateway=None):
        self.auth = auth or remote_auth
        self.storage = storage or family_storage
        self.command_gateway = command_gateway or remote_command_gateway
        self.authorized_phone_numbers: Dict[str, str] = {
            # E.164 phone -> user_id
            "+10000000000": "shakil"
        }
        self.call_pin_cache: Dict[str, Dict[str, Any]] = {}

    def register_authorized_number(self, phone_number: str, user_id: str):
        self.authorized_phone_numbers[phone_number.strip()] = user_id

    def handle_incoming_call(self, caller_number: str, caller_pin: Optional[str] = None) -> Dict[str, Any]:
        """
        Verifies incoming caller against authorized registry and 4-digit voice PIN.
        Never discloses private information solely based on spoofable Caller ID.
        """
        user_id = self.authorized_phone_numbers.get(caller_number.strip())
        if not user_id:
            return {
                "authorized": False,
                "speechPrompt": "This number is not recognized by J.A.R.V.I.S. Access denied.",
                "hangup": True
            }

        # Verify Voice PIN
        if not caller_pin or len(caller_pin) < 4:
            return {
                "authorized": False,
                "needsPin": True,
                "speechPrompt": "Welcome Sir Shakil. Please speak or enter your 4-digit security PIN."
            }

        # For demo/testing, PIN 1701 or 1234
        if caller_pin not in ["1701", "1234"]:
            self.storage.log_audit(
                event_type="TELEPHONY_AUTH_FAILED",
                actor_id=user_id,
                action=f"Invalid telephony PIN attempt from {caller_number}",
                risk_level="HIGH"
            )
            return {
                "authorized": False,
                "speechPrompt": "Security PIN incorrect. Session terminated.",
                "hangup": True
            }

        session_token = secrets.token_hex(8)
        self.call_pin_cache[session_token] = {"userId": user_id, "expiresAt": time.time() + 300}

        return {
            "authorized": True,
            "sessionToken": session_token,
            "speechPrompt": "Authentication verified. J.A.R.V.I.S. is listening for your command."
        }

    def process_voice_call_command(self, session_token: str, transcript: str) -> Dict[str, Any]:
        """Processes voice command from verified telephony session."""
        session = self.call_pin_cache.get(session_token)
        if not session or time.time() > session["expiresAt"]:
            return {"success": False, "speechResponse": "Telephony session expired. Please re-authenticate."}

        res = self.command_gateway.execute_remote_command(
            user_id=session["userId"],
            command_text=transcript,
            role="family_admin" if session["userId"] == "shakil" else "participant",
            source_channel="telephony_voice_call"
        )

        speech = res.get("result", {}).get("speech", "Command processed.")
        return {"success": True, "speechResponse": speech, "result": res}

telephony_gateway = TelephonyGateway()
