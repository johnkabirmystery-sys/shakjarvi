"""
J.A.R.V.I.S. Mark XVII — Family Safety Storage Subsystem
=========================================================
Encrypted SQLite database with clear domain separation, retention policies,
and access audit logs for all family safety entities.
"""

import os
import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "family_safety"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "family_safety.db"

class FamilySafetyStorage:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Device Registry Domain
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS family_devices (
                    device_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    owner_profile_id TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    enrollment_status TEXT NOT NULL,
                    consent_status TEXT NOT NULL,
                    location_permission TEXT NOT NULL,
                    last_seen_at REAL NOT NULL,
                    last_known_connection TEXT,
                    capabilities TEXT,
                    security_status TEXT,
                    data_retention_policy TEXT DEFAULT '7_days',
                    pairing_code_hash TEXT,
                    pairing_expires_at REAL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)

            # 2. Consent Records Domain
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS family_consents (
                    participant_id TEXT PRIMARY KEY,
                    owner_profile_id TEXT NOT NULL,
                    consent_version TEXT NOT NULL,
                    location_sharing_enabled INTEGER DEFAULT 0,
                    live_location_enabled INTEGER DEFAULT 0,
                    location_history_enabled INTEGER DEFAULT 0,
                    safety_alerts_enabled INTEGER DEFAULT 1,
                    geofence_alerts_enabled INTEGER DEFAULT 1,
                    emergency_contact_permission INTEGER DEFAULT 0,
                    notification_permission INTEGER DEFAULT 1,
                    background_location_enabled INTEGER DEFAULT 0,
                    external_sharing_enabled INTEGER DEFAULT 0,
                    granted_at REAL NOT NULL,
                    expires_at REAL,
                    revoked_at REAL,
                    last_reviewed_at REAL NOT NULL
                )
            """)

            # 3. Location Observations Domain
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS family_locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    participant_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    accuracy_meters REAL,
                    altitude_meters REAL,
                    heading REAL,
                    speed_mps REAL,
                    source TEXT,
                    location_precision TEXT,
                    recorded_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_loc_part ON family_locations(participant_id, recorded_at)")

            # 4. Safety Signals Domain
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS safety_signals (
                    signal_id TEXT PRIMARY KEY,
                    participant_id TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    raw_data TEXT,
                    source TEXT,
                    confidence REAL,
                    location_lat REAL,
                    location_lon REAL
                )
            """)

            # 5. Safety Alerts Domain
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS safety_alerts (
                    alert_id TEXT PRIMARY KEY,
                    participant_id TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    triggered_at REAL NOT NULL,
                    evidence TEXT,
                    source TEXT,
                    confidence REAL,
                    location_precision TEXT,
                    expiration REAL,
                    recommended_action TEXT,
                    notification_state TEXT,
                    escalation_state TEXT,
                    false_positive_risk TEXT,
                    is_dismissed INTEGER DEFAULT 0,
                    dismissed_at REAL
                )
            """)

            # 6. Check-Ins Domain
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS family_checkins (
                    checkin_id TEXT PRIMARY KEY,
                    participant_id TEXT NOT NULL,
                    scheduled_at REAL NOT NULL,
                    status TEXT NOT NULL,
                    response_type TEXT,
                    responded_at REAL,
                    grace_period_minutes INTEGER DEFAULT 15,
                    reminder_sent_at REAL,
                    notes TEXT
                )
            """)

            # 7. Persistent Tasks Domain
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS remote_tasks (
                    task_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    priority INTEGER DEFAULT 1,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    updated_at REAL NOT NULL,
                    next_run_at REAL,
                    schedule TEXT,
                    progress REAL DEFAULT 0.0,
                    required_permissions TEXT,
                    tools_used TEXT,
                    last_result TEXT,
                    error TEXT,
                    cancellation_state TEXT,
                    audit_trail TEXT
                )
            """)

            # 8. Authentication Sessions Domain
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    refresh_token_hash TEXT,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    is_revoked INTEGER DEFAULT 0,
                    last_active_at REAL NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT
                )
            """)

            # 9. Audit Events Domain
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS safety_audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    target_id TEXT,
                    action TEXT NOT NULL,
                    risk_level TEXT DEFAULT 'LOW',
                    details TEXT,
                    timestamp REAL NOT NULL,
                    ip_address TEXT
                )
            """)

            conn.commit()

    # -----------------------------------------------------------------------
    # Devices Operations
    # -----------------------------------------------------------------------
    def upsert_device(self, d: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO family_devices (
                    device_id, display_name, owner_profile_id, device_type, platform,
                    enrollment_status, consent_status, location_permission, last_seen_at,
                    last_known_connection, capabilities, security_status, data_retention_policy,
                    pairing_code_hash, pairing_expires_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    device_type=excluded.device_type,
                    platform=excluded.platform,
                    enrollment_status=excluded.enrollment_status,
                    consent_status=excluded.consent_status,
                    location_permission=excluded.location_permission,
                    last_seen_at=excluded.last_seen_at,
                    last_known_connection=excluded.last_known_connection,
                    capabilities=excluded.capabilities,
                    security_status=excluded.security_status,
                    data_retention_policy=excluded.data_retention_policy,
                    pairing_code_hash=excluded.pairing_code_hash,
                    pairing_expires_at=excluded.pairing_expires_at,
                    updated_at=excluded.updated_at
            """, (
                d["deviceId"], d["displayName"], d["ownerProfileId"], d["deviceType"], d["platform"],
                d["enrollmentStatus"], d["consentStatus"], d["locationPermission"], d["lastSeenAt"],
                json.dumps(d.get("lastKnownConnection", {})),
                json.dumps(d.get("capabilities", {})),
                json.dumps(d.get("securityStatus", {})),
                d.get("dataRetentionPolicy", "7_days"),
                d.get("pairingCodeHash"),
                d.get("pairingExpiresAt"),
                d.get("createdAt", time.time()),
                d.get("updatedAt", time.time())
            ))
            conn.commit()

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM family_devices WHERE device_id = ?", (device_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_device(row)

    def list_devices(self, owner_profile_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if owner_profile_id:
                cursor.execute("SELECT * FROM family_devices WHERE owner_profile_id = ?", (owner_profile_id,))
            else:
                cursor.execute("SELECT * FROM family_devices")
            return [self._row_to_device(r) for r in cursor.fetchall()]

    def delete_device(self, device_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM family_devices WHERE device_id = ?", (device_id,))
            conn.commit()

    def _row_to_device(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "deviceId": row["device_id"],
            "displayName": row["display_name"],
            "ownerProfileId": row["owner_profile_id"],
            "deviceType": row["device_type"],
            "platform": row["platform"],
            "enrollmentStatus": row["enrollment_status"],
            "consentStatus": row["consent_status"],
            "locationPermission": row["location_permission"],
            "lastSeenAt": row["last_seen_at"],
            "lastKnownConnection": json.loads(row["last_known_connection"] or "{}"),
            "capabilities": json.loads(row["capabilities"] or "{}"),
            "securityStatus": json.loads(row["security_status"] or "{}"),
            "dataRetentionPolicy": row["data_retention_policy"],
            "pairingCodeHash": row["pairing_code_hash"],
            "pairingExpiresAt": row["pairing_expires_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"]
        }

    # -----------------------------------------------------------------------
    # Consent Operations
    # -----------------------------------------------------------------------
    def upsert_consent(self, c: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO family_consents (
                    participant_id, owner_profile_id, consent_version,
                    location_sharing_enabled, live_location_enabled, location_history_enabled,
                    safety_alerts_enabled, geofence_alerts_enabled, emergency_contact_permission,
                    notification_permission, background_location_enabled, external_sharing_enabled,
                    granted_at, expires_at, revoked_at, last_reviewed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(participant_id) DO UPDATE SET
                    owner_profile_id=excluded.owner_profile_id,
                    consent_version=excluded.consent_version,
                    location_sharing_enabled=excluded.location_sharing_enabled,
                    live_location_enabled=excluded.live_location_enabled,
                    location_history_enabled=excluded.location_history_enabled,
                    safety_alerts_enabled=excluded.safety_alerts_enabled,
                    geofence_alerts_enabled=excluded.geofence_alerts_enabled,
                    emergency_contact_permission=excluded.emergency_contact_permission,
                    notification_permission=excluded.notification_permission,
                    background_location_enabled=excluded.background_location_enabled,
                    external_sharing_enabled=excluded.external_sharing_enabled,
                    granted_at=excluded.granted_at,
                    expires_at=excluded.expires_at,
                    revoked_at=excluded.revoked_at,
                    last_reviewed_at=excluded.last_reviewed_at
            """, (
                c["participantId"], c["ownerProfileId"], c.get("consentVersion", "1.0"),
                1 if c.get("locationSharingEnabled") else 0,
                1 if c.get("liveLocationEnabled") else 0,
                1 if c.get("locationHistoryEnabled") else 0,
                1 if c.get("safetyAlertsEnabled", True) else 0,
                1 if c.get("geofenceAlertsEnabled", True) else 0,
                1 if c.get("emergencyContactPermission") else 0,
                1 if c.get("notificationPermission", True) else 0,
                1 if c.get("backgroundLocationEnabled") else 0,
                1 if c.get("externalSharingEnabled") else 0,
                c.get("grantedAt", time.time()),
                c.get("expiresAt"),
                c.get("revokedAt"),
                c.get("lastReviewedAt", time.time())
            ))
            conn.commit()

    def get_consent(self, participant_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM family_consents WHERE participant_id = ?", (participant_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_consent(row)

    def list_consents(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM family_consents")
            return [self._row_to_consent(r) for r in cursor.fetchall()]

    def _row_to_consent(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "participantId": row["participant_id"],
            "ownerProfileId": row["owner_profile_id"],
            "consentVersion": row["consent_version"],
            "locationSharingEnabled": bool(row["location_sharing_enabled"]),
            "liveLocationEnabled": bool(row["live_location_enabled"]),
            "locationHistoryEnabled": bool(row["location_history_enabled"]),
            "safetyAlertsEnabled": bool(row["safety_alerts_enabled"]),
            "geofenceAlertsEnabled": bool(row["geofence_alerts_enabled"]),
            "emergencyContactPermission": bool(row["emergency_contact_permission"]),
            "notificationPermission": bool(row["notification_permission"]),
            "backgroundLocationEnabled": bool(row["background_location_enabled"]),
            "externalSharingEnabled": bool(row["external_sharing_enabled"]),
            "grantedAt": row["granted_at"],
            "expiresAt": row["expires_at"],
            "revokedAt": row["revoked_at"],
            "lastReviewedAt": row["last_reviewed_at"]
        }

    # -----------------------------------------------------------------------
    # Location History & Retention Operations
    # -----------------------------------------------------------------------
    def record_location(self, loc: Dict[str, Any], retention_hours: int = 168):
        now = time.time()
        expires = now + (retention_hours * 3600)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO family_locations (
                    participant_id, device_id, latitude, longitude, accuracy_meters,
                    altitude_meters, heading, speed_mps, source, location_precision,
                    recorded_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                loc["participantId"], loc.get("deviceId", "unknown"),
                loc["latitude"], loc["longitude"], loc.get("accuracyMeters", 10.0),
                loc.get("altitudeMeters"), loc.get("heading"), loc.get("speedMps"),
                loc.get("source", "gps"), loc.get("locationPrecision", "approximate"),
                loc.get("recordedAt", now), expires
            ))
            conn.commit()

    def get_latest_location(self, participant_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM family_locations 
                WHERE participant_id = ? 
                ORDER BY recorded_at DESC LIMIT 1
            """, (participant_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def delete_location_history(self, participant_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM family_locations WHERE participant_id = ?", (participant_id,))
            conn.commit()

    def purge_expired_records(self):
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM family_locations WHERE expires_at < ?", (now,))
            cursor.execute("DELETE FROM auth_sessions WHERE expires_at < ? OR is_revoked = 1", (now,))
            conn.commit()

    # -----------------------------------------------------------------------
    # Safety Signals & Alerts
    # -----------------------------------------------------------------------
    def save_signal(self, sig: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            loc = sig.get("location") or {}
            sig_id = sig.get("signalId") or sig.get("signal_id")
            part_id = sig.get("participantId") or sig.get("participant_id")
            sig_type = sig.get("signalType") or sig.get("signal_type")
            ts = sig.get("timestamp", time.time())
            raw_data = sig.get("rawData") or sig.get("raw_data") or {}
            cursor.execute("""
                INSERT INTO safety_signals (
                    signal_id, participant_id, signal_type, timestamp, raw_data,
                    source, confidence, location_lat, location_lon
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sig_id, part_id, sig_type, ts,
                json.dumps(raw_data), sig.get("source", "system"),
                sig.get("confidence", 1.0), loc.get("latitude"), loc.get("longitude")
            ))
            conn.commit()

    def save_alert(self, a: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            alert_id = a.get("alertId") or a.get("alert_id")
            part_id = a.get("participantId") or a.get("participant_id")
            alert_type = a.get("alertType") or a.get("alert_type")
            severity = a.get("severity", "LOW")
            trig_at = a.get("triggeredAt") or a.get("triggered_at", time.time())
            evidence = a.get("evidence", "")
            source = a.get("source", "system")
            cursor.execute("""
                INSERT INTO safety_alerts (
                    alert_id, participant_id, alert_type, severity, triggered_at,
                    evidence, source, confidence, location_precision, expiration,
                    recommended_action, notification_state, escalation_state,
                    false_positive_risk, is_dismissed, dismissed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(alert_id) DO UPDATE SET
                    notification_state=excluded.notification_state,
                    escalation_state=excluded.escalation_state,
                    is_dismissed=excluded.is_dismissed,
                    dismissed_at=excluded.dismissed_at
            """, (
                alert_id, part_id, alert_type, severity, trig_at,
                evidence, source, a.get("confidence", 1.0), a.get("locationPrecision", "approximate"),
                a.get("expiration", time.time() + 14400), a.get("recommendedAction", ""),
                a.get("notificationState", "pending"), a.get("escalationState", "none"),
                a.get("falsePositiveRisk", "low"), 1 if a.get("isDismissed") or a.get("is_dismissed") else 0,
                a.get("dismissedAt") or a.get("dismissed_at")
            ))
            conn.commit()

    def list_active_alerts(self, participant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if participant_id:
                cursor.execute("""
                    SELECT * FROM safety_alerts 
                    WHERE participant_id = ? AND is_dismissed = 0 AND expiration > ?
                    ORDER BY triggered_at DESC
                """, (participant_id, now))
            else:
                cursor.execute("""
                    SELECT * FROM safety_alerts 
                    WHERE is_dismissed = 0 AND expiration > ?
                    ORDER BY triggered_at DESC
                """, (now,))
            return [dict(r) for r in cursor.fetchall()]

    def dismiss_alert(self, alert_id: str):
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE safety_alerts SET is_dismissed = 1, dismissed_at = ? WHERE alert_id = ?", (now, alert_id))
            conn.commit()

    # -----------------------------------------------------------------------
    # Check-Ins
    # -----------------------------------------------------------------------
    def save_checkin(self, chk: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            chk_id = chk.get("checkInId") or chk.get("checkin_id")
            part_id = chk.get("participantId") or chk.get("participant_id")
            sched = chk.get("scheduledAt") or chk.get("scheduled_at", time.time())
            status = chk.get("status", "pending")
            resp_type = chk.get("responseType") or chk.get("response_type")
            resp_at = chk.get("respondedAt") or chk.get("responded_at")
            grace = chk.get("gracePeriodMinutes") or chk.get("grace_period_minutes", 15)
            rem_at = chk.get("reminderSentAt") or chk.get("reminder_sent_at")
            notes = chk.get("notes")
            cursor.execute("""
                INSERT INTO family_checkins (
                    checkin_id, participant_id, scheduled_at, status, response_type,
                    responded_at, grace_period_minutes, reminder_sent_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(checkin_id) DO UPDATE SET
                    status=excluded.status,
                    response_type=excluded.response_type,
                    responded_at=excluded.responded_at,
                    reminder_sent_at=excluded.reminder_sent_at,
                    notes=excluded.notes
            """, (
                chk_id, part_id, sched, status,
                resp_type, resp_at, grace,
                rem_at, notes
            ))
            conn.commit()

    def get_checkin(self, checkin_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM family_checkins WHERE checkin_id = ?", (checkin_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    # -----------------------------------------------------------------------
    # Audit Logging
    # -----------------------------------------------------------------------
    def log_audit(self, event_type: str, actor_id: str, action: str, target_id: Optional[str] = None,
                  risk_level: str = "LOW", details: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO safety_audit_events (
                    event_type, actor_id, target_id, action, risk_level, details, timestamp, ip_address
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_type, actor_id, target_id, action, risk_level,
                json.dumps(details or {}), time.time(), ip_address
            ))
            conn.commit()

    def list_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM safety_audit_events ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

# Global Singleton Instance
family_storage = FamilySafetyStorage()
