"""
J.A.R.V.I.S. Desktop Launcher & Runtime Lifecycle Validation Suite
===================================================================
Tests and verifies:
1. Shortcut properties & path resolution.
2. Launching from arbitrary working directories (e.g., Desktop).
3. Backend readiness on port 8000 (HTTP 200 on / and /api/spatial/health).
4. No duplicate processes on port 8000.
5. 3 cycles of Launch -> Verify Ready -> Clean Teardown -> Verify Port Release -> Relaunch.
6. Machine-readable JSON evidence generation.
"""

import os
import sys
import time
import json
import socket
import urllib.request
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = REPORTS_DIR / "desktop_launcher_validation_report.json"

PORT = 8000
SERVER_URL = f"http://127.0.0.1:{PORT}"


def is_port_in_use(port: int = PORT) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def get_pids_on_port(port: int = PORT) -> list[int]:
    pids = []
    try:
        output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True, text=True, errors="replace")
        for line in output.strip().splitlines():
            if "LISTENING" in line:
                parts = line.strip().split()
                pid = int(parts[-1])
                if pid not in pids and pid > 0:
                    pids.append(pid)
    except Exception:
        pass
    return pids


def kill_pids(pids: list[int]):
    for pid in pids:
        try:
            subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
        except Exception:
            pass


def wait_for_endpoint(url: str, timeout: float = 12.0) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-Validation/1.0"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    body = resp.read().decode("utf-8", errors="replace")
                    return {"ok": True, "status": resp.status, "body_length": len(body), "elapsed": round(time.time() - start, 2)}
        except Exception:
            time.sleep(0.3)
    return {"ok": False, "error": f"Timed out waiting for {url} ({timeout}s)"}


def run_desktop_validation():
    print("================================================================================")
    print("  J.A.R.V.I.S. DESKTOP LAUNCHER & LIFECYCLE E2E VALIDATION")
    print("================================================================================")

    # 1. Inspect Git revision
    commit_sha = subprocess.check_output("git rev-parse HEAD", shell=True, text=True).strip()
    git_status = subprocess.check_output("git status --short", shell=True, text=True).strip()
    print(f"[*] Commit SHA: {commit_sha}")
    print(f"[*] Git Status: {git_status or '[CLEAN]'}")

    # 2. Inspect Desktop Shortcut properties
    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
    shortcut_path = os.path.join(desktop, "J.A.R.V.I.S.lnk")
    
    shortcut_info = {}
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        sc = shell.CreateShortCut(shortcut_path)
        shortcut_info = {
            "exists": os.path.exists(shortcut_path),
            "path": shortcut_path,
            "target": sc.TargetPath,
            "working_directory": sc.WorkingDirectory,
            "icon_location": sc.IconLocation,
            "window_style": sc.WindowStyle
        }
        print(f"[*] Shortcut Exists: {shortcut_info['exists']}")
        print(f"[*] Target: {shortcut_info['target']}")
        print(f"[*] Working Directory: {shortcut_info['working_directory']}")
    except Exception as e:
        shortcut_info = {"error": str(e)}
        print(f"[!] Error inspecting shortcut: {e}")

    # Ensure clean starting state
    existing_pids = get_pids_on_port(PORT)
    if existing_pids:
        print(f"[*] Cleaning up {len(existing_pids)} existing process(es) on port {PORT}...")
        kill_pids(existing_pids)
        time.sleep(1.0)

    results = {
        "commit": commit_sha,
        "git_status": git_status,
        "shortcut_info": shortcut_info,
        "shortcut_target": shortcut_info.get("target"),
        "working_directory": shortcut_info.get("working_directory"),
        "launch_success": False,
        "backend_ready": False,
        "spatial_health_ready": False,
        "hud_ready": False,
        "duplicate_processes": False,
        "clean_shutdown": False,
        "relaunch_success": False,
        "relaunch_cycles": [],
        "errors": []
    }

    # 3. Test Multi-Cycle Launch -> Verify -> Teardown -> Re-launch
    cycles_passed = 0
    total_cycles = 3

    for cycle in range(1, total_cycles + 1):
        print(f"\n[*] --- Running Lifecycle Launch Cycle {cycle}/{total_cycles} ---")
        cycle_log = {"cycle": cycle, "launched": False, "ready": False, "pids": [], "stopped_cleanly": False}

        # Launch start_jarvis.bat from a different directory (Desktop)
        start_t = time.time()
        proc = subprocess.Popen(
            [str(PROJECT_ROOT / "start_jarvis.bat")],
            cwd=desktop,  # Launch from Desktop working directory to test cd /d %~dp0
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        cycle_log["launched"] = True
        cycle_log["proc_pid"] = proc.pid
        print(f"  [PASS] Launched batch process (PID: {proc.pid}) from cwd='{desktop}'")

        # Wait for backend readiness on port 8000
        backend_check = wait_for_endpoint(f"{SERVER_URL}/api/settings", timeout=15.0)
        spatial_check = wait_for_endpoint(f"{SERVER_URL}/api/spatial/health", timeout=10.0)
        hud_check = wait_for_endpoint(f"{SERVER_URL}/", timeout=10.0)

        if backend_check["ok"] and spatial_check["ok"] and hud_check["ok"]:
            pids = get_pids_on_port(PORT)
            cycle_log["ready"] = True
            cycle_log["pids"] = pids
            cycle_log["startup_time_sec"] = round(time.time() - start_t, 2)
            cycle_log["duplicate_pids"] = len(pids) > 1
            print(f"  [PASS] Backend ONLINE in {cycle_log['startup_time_sec']}s (Listening PIDs: {pids})")
            print(f"  [PASS] Spatial Health OK: {spatial_check['status']} | HUD Body Length: {hud_check['body_length']} bytes")

            if cycle == 1:
                results["launch_success"] = True
                results["backend_ready"] = True
                results["spatial_health_ready"] = True
                results["hud_ready"] = True
                results["duplicate_processes"] = len(pids) > 1

            # Teardown process
            kill_pids(pids + [proc.pid])
            time.sleep(1.0)

            # Verify port release
            pids_after = get_pids_on_port(PORT)
            if len(pids_after) == 0:
                cycle_log["stopped_cleanly"] = True
                print("  [PASS] Clean shutdown: Port 8000 released with 0 orphan processes.")
                cycles_passed += 1
            else:
                cycle_log["stopped_cleanly"] = False
                cycle_log["orphan_pids"] = pids_after
                print(f"  [FAIL] Orphan PIDs remained: {pids_after}")
        else:
            err = f"Cycle {cycle} failed: backend={backend_check}, spatial={spatial_check}, hud={hud_check}"
            print(f"  [FAIL] {err}")
            results["errors"].append(err)
            kill_pids([proc.pid] + get_pids_on_port(PORT))

        results["relaunch_cycles"].append(cycle_log)

    results["clean_shutdown"] = cycles_passed == total_cycles
    results["relaunch_success"] = cycles_passed == total_cycles

    # 4. Save JSON Report
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n================================================================================")
    print(f"  VALIDATION RESULT: {'[SUCCESS] 3/3 CYCLES PASSED' if results['relaunch_success'] else '[FAILED]'}")
    print(f"  Report written to: {REPORT_PATH}")
    print("================================================================================")

    return results


if __name__ == "__main__":
    res = run_desktop_validation()
    if not res["relaunch_success"]:
        sys.exit(1)
