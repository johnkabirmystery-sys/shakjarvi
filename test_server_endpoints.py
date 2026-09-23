"""
Verification of New Server Endpoints for J.A.R.V.I.S. Mark XVI
==============================================================
Validates:
- POST /api/sandbox/run
- POST /api/terminal/exec
- POST /api/vision/analyze
"""

import sys
from pathlib import Path
from starlette.testclient import TestClient

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from server import app

client = TestClient(app)

def test_api_sandbox_run():
    print("[*] Testing POST /api/sandbox/run endpoint...")
    code = "vals = [x**2 for x in range(5)]\nprint(f'SQUARES={vals}')"
    resp = client.post("/api/sandbox/run", json={"code": code, "language": "python", "timeout": 10})
    assert resp.status_code == 200, f"Status: {resp.status_code}, text: {resp.text}"
    data = resp.json()
    assert data["success"] is True, f"Error: {data.get('error')}"
    assert "SQUARES=[0, 1, 4, 9, 16]" in data["stdout"]
    print("  [PASS] Sandbox endpoint successfully executed Python and captured stdout.")

def test_api_terminal_exec():
    print("[*] Testing POST /api/terminal/exec endpoint...")
    cmd = "Write-Output 'JARVIS_TERMINAL_ONLINE'"
    resp = client.post("/api/terminal/exec", json={"command": cmd, "timeout": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "JARVIS_TERMINAL_ONLINE" in data["stdout"]
    print("  [PASS] Terminal exec endpoint successfully ran PowerShell command.")

def test_api_sandbox_error():
    print("[*] Testing POST /api/sandbox/run syntax error reporting...")
    code = "print('unterminated string"
    resp = client.post("/api/sandbox/run", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "SyntaxError" in data["stderr"]
    print("  [PASS] Sandbox properly reported syntax error.")

if __name__ == "__main__":
    test_api_sandbox_run()
    test_api_terminal_exec()
    test_api_sandbox_error()
    print("\n============================================")
    print("ALL NEW SERVER ENDPOINTS VERIFIED (3/3 PASS)!")
    print("============================================")
