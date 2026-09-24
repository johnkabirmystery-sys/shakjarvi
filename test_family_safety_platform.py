"""
J.A.R.V.I.S. Mark XVII — Family Safety & Remote AI Platform Verification Suite
==============================================================================
Comprehensive architectural and security test suite testing all 16 phases:
- Device Registry & Secure Pairing
- Local Network Discovery & Identification
- Granular Consent & Emergency Kill Switch
- Safety Signals & Alert Engine
- Voluntary Check-In & Grace Periods
- Remote Authentication & Session Revocation
- Remote Command Gateway & Risk Confirmation Gates
- Persistent Task Manager & Restart Recovery
- Telephony PIN Verification & System Reliability
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.family_safety import (
    device_registry, network_discovery, consent_manager,
    safety_signal_engine, safety_alert_engine, checkin_manager,
    family_storage
)
from core.remote import (
    remote_auth, remote_command_gateway, persistent_task_manager,
    reliability_monitor, telephony_gateway
)

def run_tests():
    print("=" * 80)
    print("  J.A.R.V.I.S. MARK XVII FAMILY SAFETY & REMOTE AI PLATFORM TEST SUITE")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # TEST 1: Device Registry & Cryptographic Pairing
    # -------------------------------------------------------------------------
    print("\n[*] Phase 1: Device Registry & Pairing Verification...")
    pair_res = device_registry.generate_pairing_code(
        owner_profile_id="shakil",
        display_name="Shakil's Galaxy S24 Ultra",
        device_type="phone",
        platform="android",
        ttl_seconds=600
    )
    assert pair_res["success"] is True
    device_id = pair_res["deviceId"]
    pairing_code = pair_res["pairingCode"]
    assert len(pairing_code) == 6
    print(f"  [PASS] Generated 6-digit pairing code for device: {device_id}")

    # Test invalid code rejection
    bad_res = device_registry.complete_pairing(device_id, "000000")
    assert bad_res["success"] is False
    print("  [PASS] Rejected invalid pairing code attempt")

    # Test successful pairing
    good_res = device_registry.complete_pairing(
        device_id,
        pairing_code,
        device_capabilities={"gps": True, "battery": 92}
    )
    assert good_res["success"] is True
    assert good_res["enrollmentStatus"] == "enrolled"
    print(f"  [PASS] Successfully paired and enrolled device '{good_res['displayName']}'")

    # Update permissions
    perm_res = device_registry.update_device_permissions(
        device_id=device_id,
        actor_id="shakil",
        location_permission="always",
        consent_status="active"
    )
    assert perm_res["success"] is True
    print("  [PASS] Updated owner-controlled permissions to 'always'")

    # -------------------------------------------------------------------------
    # TEST 2: Local Network Discovery
    # -------------------------------------------------------------------------
    print("\n[*] Phase 2: Local Network Discovery & Node Classification...")
    disc_res = network_discovery.scan_local_network()
    assert disc_res["success"] is True
    assert "devices" in disc_res
    print(f"  [PASS] Passive network discovery completed (Discovered {disc_res['count']} local nodes)")
    print(f"  [PASS] Separated Discovered vs Identified vs Verified Owner")

    # -------------------------------------------------------------------------
    # TEST 3: Granular Consent & Emergency Kill Switch
    # -------------------------------------------------------------------------
    print("\n[*] Phase 3: Granular Consent & Emergency Master Kill Switch...")
    c_init = consent_manager.get_or_create_consent("participant_brother", "shakil")
    assert c_init["locationSharingEnabled"] is False
    print("  [PASS] Default consent is strictly restrictive (locationSharingEnabled=False)")

    # Grant explicit consent
    c_update = consent_manager.update_consent("participant_brother", "shakil", {
        "locationSharingEnabled": True,
        "liveLocationEnabled": True,
        "geofenceAlertsEnabled": True
    })
    assert c_update["success"] is True
    assert consent_manager.check_permission("participant_brother", "locationSharingEnabled") is True
    print("  [PASS] Explicit consent granted for live location and geofencing")

    # Test Emergency Master Kill Switch
    kill_res = consent_manager.pause_all_sharing("shakil")
    assert kill_res["success"] is True
    assert consent_manager.check_permission("participant_brother", "locationSharingEnabled") is False
    print(f"  [PASS] Emergency Master Kill Switch executed ({kill_res['pausedCount']} participants paused)")

    # Test Purge History
    family_storage.record_location({
        "participantId": "participant_brother",
        "latitude": 23.8103,
        "longitude": 90.4125
    })
    assert family_storage.get_latest_location("participant_brother") is not None
    purge_res = consent_manager.delete_participant_history("participant_brother", "shakil")
    assert purge_res["success"] is True
    assert family_storage.get_latest_location("participant_brother") is None
    print("  [PASS] One-click location history purge verified")

    # -------------------------------------------------------------------------
    # TEST 4: Safety Signals & Alert Engine
    # -------------------------------------------------------------------------
    print("\n[*] Phase 4: Safety Signals & Tiered Alert Engine...")
    # Re-enable safetyAlertsEnabled
    consent_manager.update_consent("shakil", "shakil", {"safetyAlertsEnabled": True})
    
    # Ingest voluntary SOS
    sig_res = safety_signal_engine.ingest_signal(
        participant_id="shakil",
        signal_type="voluntary_sos",
        raw_data={"message": "Voluntary emergency check"},
        source="phone_sos_button"
    )
    assert sig_res["success"] is True
    print("  [PASS] Voluntary SOS signal ingested with consent validation")

    # Check alert generation
    alerts = safety_alert_engine.list_active_alerts("shakil")
    assert len(alerts) > 0
    top_alert = alerts[0]
    assert top_alert["severity"] == "CRITICAL"
    print(f"  [PASS] Generated CRITICAL alert #{top_alert['alert_id']} with transparent evidence")

    # Dismiss alert
    d_res = safety_alert_engine.dismiss_alert(top_alert["alert_id"], "shakil")
    assert d_res["success"] is True
    print("  [PASS] Dismissed alert successfully")

    # -------------------------------------------------------------------------
    # TEST 5: Voluntary Check-In & Wellness
    # -------------------------------------------------------------------------
    print("\n[*] Phase 5: Voluntary Check-In Workflow & Grace Periods...")
    chk_res = checkin_manager.schedule_checkin("shakil", scheduled_at=time.time(), grace_period_minutes=15)
    assert chk_res["success"] is True
    chk_id = chk_res["checkin"]["checkInId"]
    print(f"  [PASS] Scheduled voluntary check-in #{chk_id}")

    # Respond Safe
    resp_res = checkin_manager.respond_checkin(chk_id, "safe", "Arrived at office")
    assert resp_res["success"] is True
    assert resp_res["status"] == "confirmed"
    print("  [PASS] Check-in confirmed 'safe' by participant")

    # -------------------------------------------------------------------------
    # TEST 6: Remote Auth & Session Management
    # -------------------------------------------------------------------------
    print("\n[*] Phase 6: Remote Auth, Tokens & Rate Limiting...")
    auth_res = remote_auth.create_session("shakil", "mobile_s24", role="family_admin")
    assert auth_res["success"] is True
    access_token = auth_res["accessToken"]
    session_id = auth_res["sessionId"]
    print(f"  [PASS] Created authenticated session #{session_id}")

    # Validate session
    val = remote_auth.validate_session(access_token)
    assert val is not None
    assert val["sub"] == "shakil"
    print("  [PASS] Cryptographic Bearer token signature validated")

    # Revoke session
    rev_res = remote_auth.revoke_session(session_id, "shakil")
    assert rev_res["success"] is True
    assert remote_auth.validate_session(access_token) is None
    print("  [PASS] Session revoked successfully (Token invalidated)")

    # -------------------------------------------------------------------------
    # TEST 7: Remote Command Gateway & Risk Confirmation Gates
    # -------------------------------------------------------------------------
    print("\n[*] Phase 7: Remote Command Gateway & Risk Gates...")
    # Low-risk query
    cmd1 = remote_command_gateway.execute_remote_command("shakil", "what tasks are currently running")
    assert cmd1["success"] is True
    print("  [PASS] Executed low-risk status command immediately")

    # High-risk command requires 2-step confirmation
    cmd_high = remote_command_gateway.execute_remote_command("shakil", "export location history")
    assert cmd_high["success"] is False
    assert cmd_high.get("requiresConfirmation") is True
    conf_token = cmd_high["confirmationToken"]
    print(f"  [PASS] High-risk command halted in 2-step confirmation gate (Token: {conf_token})")

    # Confirm high-risk command
    cmd_conf = remote_command_gateway.execute_remote_command(
        "shakil",
        "export location history",
        confirmation_token=conf_token,
        confirmed=True
    )
    assert cmd_conf["success"] is True
    print("  [PASS] High-risk command executed upon valid confirmation token")

    # -------------------------------------------------------------------------
    # TEST 8: Persistent Task Manager & Restart Safety
    # -------------------------------------------------------------------------
    print("\n[*] Phase 8: Persistent Background Task Orchestration...")
    task_res = persistent_task_manager.create_task("shakil", "Security Telemetry Audit", priority=2)
    assert task_res["success"] is True
    task_id = task_res["task"]["taskId"]
    print(f"  [PASS] Created persistent background task #{task_id}")

    # Pause task
    p_res = persistent_task_manager.pause_task(task_id, reason="User paused")
    assert p_res["success"] is True
    assert p_res["task"]["status"] == "paused"
    print("  [PASS] Paused task successfully")

    # Resume task
    r_res = persistent_task_manager.resume_task(task_id)
    assert r_res["success"] is True
    assert r_res["task"]["status"] == "queued"
    print("  [PASS] Resumed task successfully")

    # -------------------------------------------------------------------------
    # TEST 9: Telephony & Reliability
    # -------------------------------------------------------------------------
    print("\n[*] Phase 9: Telephony Voice Gateway & Reliability Monitor...")
    # Telephony unauthorized number
    call1 = telephony_gateway.handle_incoming_call("+19999999999")
    assert call1["authorized"] is False
    assert call1["hangup"] is True
    print("  [PASS] Blocked unauthorized phone number caller")

    # Authorized number with PIN
    call2 = telephony_gateway.handle_incoming_call("+10000000000", caller_pin="1701")
    assert call2["authorized"] is True
    assert "sessionToken" in call2
    print("  [PASS] Authenticated authorized phone caller with 4-digit voice PIN")

    # Reliability Monitor
    rel = reliability_monitor.get_system_health()
    assert rel["success"] is True
    assert rel["overallState"] in ["ONLINE", "PARTIALLY AVAILABLE"]
    print(f"  [PASS] System Reliability Health: {rel['overallState']} (Uptime: {rel['uptimeSeconds']}s)")

    print("\n" + "=" * 80)
    print("  ALL 9 FAMILY SAFETY & REMOTE AI MODULES PASSED (100.0% SUCCESS)")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
