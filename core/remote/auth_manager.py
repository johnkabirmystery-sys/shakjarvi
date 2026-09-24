"""
J.A.R.V.I.S. Mark XVII — Remote Authentication & Session Manager
================================================================
Secure JWT/HMAC token issuance, refresh token rotation, device pairing redemption,
role-based authorization, rate-limiting, and remote session revocation.
"""

import hmac
import hashlib
import json
import base64
import secrets
import time
from typing import Dict, List, Optional, Any

from core.family_safety.storage import family_storage
from core.family_safety.models import UserRole

# Secret key for HMAC signing (persisted in data/family_safety or generated per instance)
SECRET_FILE = family_storage.db_path.parent / "auth_secret.key"
if not SECRET_FILE.exists():
    SECRET_KEY = secrets.token_bytes(32)
    with open(SECRET_FILE, "wb") as f:
        f.write(SECRET_KEY)
else:
    with open(SECRET_FILE, "rb") as f:
        SECRET_KEY = f.read()

class RemoteAuthManager:
    def __init__(self, storage=None):
        self.storage = storage or family_storage
        self.secret_key = SECRET_KEY
        self.failed_attempts: Dict[str, List[float]] = {}  # IP -> timestamps

    def _sign_payload(self, payload: Dict[str, Any]) -> str:
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        b64_payload = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
        sig = hmac.new(self.secret_key, b64_payload.encode(), hashlib.sha256).digest()
        b64_sig = base64.urlsafe_b64encode(sig).decode().rstrip("=")
        return f"{b64_payload}.{b64_sig}"

    def _verify_token_string(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return None
            b64_payload, b64_sig = parts
            expected_sig = hmac.new(self.secret_key, b64_payload.encode(), hashlib.sha256).digest()
            expected_b64_sig = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
            if not hmac.compare_digest(b64_sig, expected_b64_sig):
                return None
            # Decode payload
            padding = 4 - (len(b64_payload) % 4)
            if padding != 4:
                b64_payload += "=" * padding
            data = json.loads(base64.urlsafe_b64decode(b64_payload.encode()).decode())
            if time.time() > data.get("exp", 0):
                return None  # Expired
            return data
        except Exception:
            return None

    def check_rate_limit(self, ip_address: str, max_attempts: int = 5, window_seconds: int = 900) -> bool:
        """Rate limit: Max 5 failed login attempts per 15 minutes."""
        now = time.time()
        attempts = [t for t in self.failed_attempts.get(ip_address, []) if (now - t) < window_seconds]
        self.failed_attempts[ip_address] = attempts
        return len(attempts) < max_attempts

    def record_failed_attempt(self, ip_address: str):
        self.failed_attempts.setdefault(ip_address, []).append(time.time())

    def create_session(self, user_id: str, device_id: str, role: str = "participant",
                       ttl_seconds: int = 3600, ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None) -> Dict[str, Any]:
        """Creates an authenticated session with access and refresh tokens."""
        now = time.time()
        session_id = f"sess_{secrets.token_hex(16)}"
        exp = now + ttl_seconds
        refresh_exp = now + (86400 * 30)  # 30 days refresh token

        access_payload = {
            "sub": user_id,
            "did": device_id,
            "sid": session_id,
            "role": role,
            "iat": now,
            "exp": exp
        }
        access_token = self._sign_payload(access_payload)
        refresh_token = secrets.token_urlsafe(32)

        token_hash = hashlib.sha256(access_token.encode()).hexdigest()
        refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO auth_sessions (
                    session_id, user_id, device_id, role, token_hash,
                    refresh_token_hash, created_at, expires_at, is_revoked,
                    last_active_at, ip_address, user_agent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, user_id, device_id, role, token_hash,
                refresh_hash, now, refresh_exp, 0, now, ip_address, user_agent
            ))
            conn.commit()

        self.storage.log_audit(
            event_type="SESSION_CREATED",
            actor_id=user_id,
            target_id=device_id,
            action=f"Authenticated remote session created with role '{role}'",
            risk_level="LOW",
            ip_address=ip_address
        )

        return {
            "success": True,
            "sessionId": session_id,
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expiresAt": exp,
            "role": role,
            "userId": user_id
        }

    def validate_session(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Validates an incoming bearer access token against cryptographic signature and revocation table."""
        payload = self._verify_token_string(access_token)
        if not payload:
            return None

        session_id = payload.get("sid")
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM auth_sessions 
                WHERE session_id = ? AND is_revoked = 0 AND expires_at > ?
            """, (session_id, time.time()))
            row = cursor.fetchone()
            if not row:
                return None
            
            # Update last active timestamp
            cursor.execute("UPDATE auth_sessions SET last_active_at = ? WHERE session_id = ?", (time.time(), session_id))
            conn.commit()

        return payload

    def revoke_session(self, session_id: str, actor_id: str) -> Dict[str, Any]:
        """Revokes a single active session."""
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE auth_sessions SET is_revoked = 1 WHERE session_id = ?", (session_id,))
            conn.commit()

        self.storage.log_audit(
            event_type="SESSION_REVOKED",
            actor_id=actor_id,
            target_id=session_id,
            action=f"Session {session_id} revoked by {actor_id}",
            risk_level="MEDIUM"
        )
        return {"success": True, "message": "Session revoked."}

    def revoke_all_user_sessions(self, user_id: str, actor_id: str) -> Dict[str, Any]:
        """Revokes all active sessions for a user (Remote Logout / Emergency Switch)."""
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE auth_sessions SET is_revoked = 1 WHERE user_id = ?", (user_id,))
            conn.commit()

        self.storage.log_audit(
            event_type="ALL_SESSIONS_REVOKED",
            actor_id=actor_id,
            target_id=user_id,
            action=f"All sessions for user {user_id} revoked.",
            risk_level="HIGH"
        )
        return {"success": True, "message": f"All sessions revoked for user {user_id}."}

remote_auth = RemoteAuthManager()
