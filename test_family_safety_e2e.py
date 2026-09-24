"""
End-to-End Automated Test Suite for J.A.R.V.I.S. Family Safety & Remote Companion
=================================================================================
Verifies real backend logic, database persistence in SQLite, standardized truthful
action contracts, pairing lifecycle, alert segregation, and remote orchestration.
"""

import sys
import os
import time
import json
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import app
from core.family_safety.device_registry import device_registry
from core.family_safety.consent_manager import consent_manager
from core.family_safety.safety_alerts import safety_alert_engine
from core.family_safety.checkin_manager import checkin_manager
from core.remote.task_orchestrator import persistent_task_manager

client = TestClient(app)

def test_01_truthful_action_contract_structure():
    """Verify health & status endpoints adhere to standardized action contract."""
    resp = client.get("/api/remote/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "ok" in body
    assert "executed" in body
    assert "simulated" in body
    assert "commandId" in body
    assert "message" in body
    assert body["ok"] is True
    assert body["executed"] is True
    assert body["simulated"] is False

def test_02_device_pairing_init_and_ttl():
    """Verify pairing code generation, 6-digit formatting, and TTL expiration settings."""
    resp = client.post("/api/family/devices/pair/init", json={
        "device_name": "Shakil Galaxy S24 Ultra",
        "owner_id": "shakil",
        "ttlSeconds": 600
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["executed"] is True
    assert "pairing_code" in body
    code = body["pairing_code"]
    assert len(code) == 6
    assert code.isdigit()
    assert body.get("expires_in_seconds", 0) > 0

def test_03_invalid_pairing_code_rejected():
    """Verify non-existent or malformed pairing codes are rejected with strict errors."""
    resp = client.post("/api/family/devices/pair/complete", json={
        "pairing_code": "000000",
        "device_name": "Fake Attacker Device"
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["executed"] is False
    assert body["errorCode"] == "PAIRING_FAILED"

def test_04_valid_device_enrollment_and_persistence():
    """Verify full enrollment lifecycle and persistence in SQLite database."""
    # 1. Init pairing
    init_resp = client.post("/api/family/devices/pair/init", json={
        "device_name": "Shakil Pixel Fold",
        "owner_id": "shakil"
    })
    assert init_resp.status_code == 200
    code = init_resp.json()["pairing_code"]

    # 2. Complete enrollment
    complete_resp = client.post("/api/family/devices/pair/complete", json={
        "pairing_code": code,
        "device_name": "Shakil Pixel Fold",
        "platform": "android",
        "device_type": "phone"
    })
    assert complete_resp.status_code == 200
    body = complete_resp.json()
    assert body["ok"] is True
    assert body["executed"] is True
    device_data = body["data"]
    device_id = device_data.get("deviceId") or device_data.get("device_id")
    assert device_id is not None

    # 3. Verify device is in SQLite registry
    list_resp = client.get("/api/family/devices")
    assert list_resp.status_code == 200
    devs = list_resp.json().get("devices", [])
    matched = [d for d in devs if (d.get("id") == device_id or d.get("deviceId") == device_id or d.get("device_id") == device_id)]
    assert len(matched) == 1
    assert matched[0]["name"] == "Shakil Pixel Fold"

    # 4. Verify Single-Use Code Enforcement (Reused code must fail)
    reuse_resp = client.post("/api/family/devices/pair/complete", json={
        "pairing_code": code,
        "device_name": "Duplicate Enrollment"
    })
    assert reuse_resp.status_code == 200
    assert reuse_resp.json()["ok"] is False

def test_05_device_revocation():
    """Verify device revocation updates database state."""
    # Create device
    init_resp = client.post("/api/family/devices/pair/init", json={"device_name": "Device to Revoke"})
    code = init_resp.json()["pairing_code"]
    comp_resp = client.post("/api/family/devices/pair/complete", json={"pairing_code": code, "device_name": "Device to Revoke"})
    dev_id = comp_resp.json()["data"]["deviceId"]

    # Revoke device
    revoke_resp = client.post("/api/family/devices/revoke", json={"device_id": dev_id})
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["ok"] is True

    # Check status is revoked
    list_resp = client.get("/api/family/devices")
    devs = list_resp.json().get("devices", [])
    target = [d for d in devs if (d.get("id") == dev_id or d.get("deviceId") == dev_id or d.get("device_id") == dev_id)][0]
    assert target["status"] in ["REVOKED", "revoked"]

def test_06_wifi_network_scan():
    """Verify local network scanner executes ARP/subnet discovery."""
    resp = client.post("/api/family/network/scan")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["executed"] is True
    assert "discovered_nodes" in body or "discovered_nodes" in body.get("data", {})

def test_07_safety_alert_lifecycle_and_test_flag():
    """Verify test alerts carry explicit isTest flag and can be dismissed."""
    # 1. Trigger test alert
    alert_resp = client.post("/api/family/alerts/test", json={
        "severity": "HIGH",
        "message": "Automated verification test alert"
    })
    assert alert_resp.status_code == 200
    body = alert_resp.json()
    assert body["ok"] is True
    alert_id = body["data"].get("alertId") or body["data"].get("alert_id")
    assert alert_id is not None

    # 2. Verify alert list has isTest=True
    list_resp = client.get("/api/family/alerts")
    assert list_resp.status_code == 200
    alerts = list_resp.json().get("alerts", [])
    target_alerts = [a for a in alerts if (a.get("id") == alert_id or a.get("alertId") == alert_id or a.get("alert_id") == alert_id)]
    assert len(target_alerts) == 1
    assert target_alerts[0]["isTest"] is True
    assert "[TEST ALERT]" in target_alerts[0]["message"]

    # 3. Dismiss alert
    dismiss_resp = client.post("/api/family/alerts/dismiss", json={"alert_id": alert_id})
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.json()["ok"] is True

def test_08_voluntary_checkins_and_status():
    """Verify Safe and Emergency SOS check-ins persist and update status."""
    # 1. Safe check-in
    safe_resp = client.post("/api/family/checkins", json={
        "status": "SAFE",
        "note": "Checked in safely from workstation"
    })
    assert safe_resp.status_code == 200
    assert safe_resp.json()["ok"] is True

    # 2. Check status
    status_resp = client.get("/api/family/checkins/status")
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["ok"] is True

    # 3. Emergency SOS check-in
    sos_resp = client.post("/api/family/checkins", json={
        "status": "NEED_HELP",
        "note": "Immediate assistance requested"
    })
    assert sos_resp.status_code == 200
    assert sos_resp.json()["ok"] is True

    # 4. Schedule check-in
    sched_resp = client.post("/api/family/checkins/schedule", json={
        "interval_minutes": 45
    })
    assert sched_resp.status_code == 200
    assert sched_resp.json()["ok"] is True

def test_09_remote_task_orchestration_lifecycle():
    """Verify creating, pausing, resuming, and canceling persistent tasks."""
    # 1. Create task
    create_resp = client.post("/api/remote/tasks/create", json={
        "title": "Autonomous Diagnostic Run",
        "description": "Executing diagnostic routines across neural matrix",
        "priority": 2
    })
    assert create_resp.status_code == 200
    body = create_resp.json()
    assert body["ok"] is True
    task_id = body["data"].get("taskId") or body["data"].get("task_id")
    assert task_id is not None

    # 2. Pause task
    pause_resp = client.post("/api/remote/tasks/pause", json={"task_id": task_id})
    assert pause_resp.status_code == 200
    assert pause_resp.json()["ok"] is True

    # 3. Resume task
    resume_resp = client.post("/api/remote/tasks/resume", json={"task_id": task_id})
    assert resume_resp.status_code == 200
    assert resume_resp.json()["ok"] is True

    # 4. Cancel task
    cancel_resp = client.post("/api/remote/tasks/cancel", json={"task_id": task_id})
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["ok"] is True

def test_10_master_location_kill_switch():
    """Verify Master Location Kill Switch instantly purges consent tokens."""
    resp = client.post("/api/family/consent/kill_switch", json={
        "reason": "Emergency security quarantine test"
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["executed"] is True
    assert "revoked" in body["message"].lower() or "revoked" in body["data"].get("status", "").lower() or "kill_switch" in body["data"].get("status", "").lower()

if __name__ == "__main__":
    tests = [
        ("01_truthful_action_contract_structure", test_01_truthful_action_contract_structure),
        ("02_device_pairing_init_and_ttl", test_02_device_pairing_init_and_ttl),
        ("03_invalid_pairing_code_rejected", test_03_invalid_pairing_code_rejected),
        ("04_valid_device_enrollment_and_persistence", test_04_valid_device_enrollment_and_persistence),
        ("05_device_revocation", test_05_device_revocation),
        ("06_wifi_network_scan", test_06_wifi_network_scan),
        ("07_safety_alert_lifecycle_and_test_flag", test_07_safety_alert_lifecycle_and_test_flag),
        ("08_voluntary_checkins_and_status", test_08_voluntary_checkins_and_status),
        ("09_remote_task_orchestration_lifecycle", test_09_remote_task_orchestration_lifecycle),
        ("10_master_location_kill_switch", test_10_master_location_kill_switch)
    ]
    passed = 0
    failed = 0
    print("\n=======================================================")
    print(" J.A.R.V.I.S. FAMILY SAFETY & REMOTE COMPANION E2E TEST")
    print("=======================================================\n")
    for name, fn in tests:
        try:
            fn()
            print(f" [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f" [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print("\n-------------------------------------------------------")
    print(f" TOTAL: {passed + failed} | PASSED: {passed} | FAILED: {failed}")
    print("-------------------------------------------------------\n")
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)
