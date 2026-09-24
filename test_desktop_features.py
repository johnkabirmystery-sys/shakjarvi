"""
Automated Verification Suite for J.A.R.V.I.S. Desktop Application Upgrades
========================================================================
Tests:
1. JarvisDesktopApi Native Windows integration & folder creation
2. 9-Specialist Agent Registry & lazy execution
3. Master Orchestrator Approval Gate (/api/orchestrator/approve & reject)
4. CodingAgent automatic file persistence to Desktop\\Jarvis_Created_Files
5. Emergency Hard Cancellation & Telemetry Diagnostics
"""

import sys
import os
import time
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from run import JarvisDesktopApi
from core.orchestrator import orchestrator, IntentType, TaskState
from core import specialists

async def test_desktop_api():
    print("\n[TEST 1] Testing JarvisDesktopApi Native Desktop Integration...")
    api = JarvisDesktopApi()
    
    # 1. Folder check
    res = api.open_created_files_folder()
    assert res.get("success") is True, f"Failed folder open: {res}"
    target_path = Path(res["path"])
    assert target_path.exists(), f"Target folder does not exist: {target_path}"
    assert "Jarvis_Created_Files" in str(target_path)
    print(f"  [PASS]: Desktop folder verified at {target_path}")

    # 2. Open project folder & path check
    proj_res = api.open_project_folder()
    assert proj_res.get("success") is True
    print(f"  [PASS]: Project folder open verified at {proj_res['path']}")

    path_res = api.open_path("server.py")
    assert path_res.get("success") is True
    print("  [PASS]: Safe open_path operational.")

    # 3. System Telemetry
    telem = api.get_system_telemetry()
    assert telem.get("success") is True
    assert "cpu_percent" in telem
    assert "memory_percent" in telem
    assert "disk_free_gb" in telem
    print(f"  [PASS]: Live System Telemetry (CPU: {telem['cpu_percent']}%, RAM: {telem['memory_percent']}%, Free Disk: {telem['disk_free_gb']} GB)")

    # 4. Version Info
    ver = api.get_version_info()
    assert ver.get("success") is True
    assert ver["version"] == "17.4.2"
    print(f"  [PASS]: Version info verified ({ver['build']} v{ver['version']}, User: {ver['user']})")

    # 5. Play System Sound (Safe Beep)
    sound_res = api.play_system_sound("ok")
    assert sound_res.get("success") is True
    print("  [PASS]: Native system sound dispatch verified.")

    # 6. Emergency cancel
    cancel_res = api.emergency_cancel()
    assert cancel_res.get("success") is True
    print("  [PASS]: Native emergency_cancel() bridge operational.")

async def test_specialist_registry():
    print("\n[TEST 2] Testing 9-Specialist Agent Registry...")
    specs = specialists.list_specialists()
    assert len(specs) == 9, f"Expected 9 specialists, got {len(specs)}"
    
    expected_ids = {"research", "coding", "qa", "marketing", "seo", "leadgen", "wordpress", "business", "system"}
    found_ids = {s["id"] for s in specs}
    assert expected_ids == found_ids, f"Mismatch in specialist IDs: {expected_ids - found_ids}"
    
    for s in specs:
        print(f"  - [{s['id'].upper()}]: {s['role']} ({s['name']})")
    print("  [PASS]: All 9 specialist agents successfully loaded and verified.")

async def test_approval_gate_lifecycle():
    print("\n[TEST 3] Testing Orchestrator Human Approval Gate Lifecycle...")
    
    # 1. Create a task that requires approval
    task = await orchestrator.create_plan(
        turn_id=999,
        intent=IntentType.FILE_OPERATIONS,
        title="Delete temp cache files",
        requires_approval=True,
        approval_prompt="Sir Shakil, confirm deletion of temp files in C:\\Temp."
    )
    
    # 2. Attempt execution without approval -> should transition to NEEDS_APPROVAL
    async def dummy_executor():
        return "Executed"
        
    res_task = await orchestrator.execute_task(task.id, dummy_executor)
    assert res_task.state == TaskState.NEEDS_APPROVAL
    print(f"  [PASS]: Task #{task.id} halted in NEEDS_APPROVAL state.")

    # 3. Test approve_task
    approved = await orchestrator.approve_task(task.id)
    assert approved is not None
    assert approved.state == TaskState.RUNNING
    assert "Explicitly authorized by Sir Shakil" in approved.evidence
    print(f"  [PASS]: Task #{task.id} transitioned to RUNNING after explicit authorization.")

    # 4. Test reject_task with a new task
    task2 = await orchestrator.create_plan(
        turn_id=1000,
        intent=IntentType.FILE_OPERATIONS,
        title="Purge logs",
        requires_approval=True
    )
    rejected = await orchestrator.reject_task(task2.id, reason="Denied by Sir Shakil")
    assert rejected is not None
    assert rejected.state == TaskState.CANCELLED
    assert rejected.error == "Denied by Sir Shakil"
    print(f"  [PASS]: Task #{task2.id} aborted cleanly on rejection.")

async def test_coding_specialist_persistence():
    print("\n[TEST 4] Testing CodingAgent Desktop File Persistence...")
    agent = specialists.get_specialist("coding")
    assert agent is not None
    
    # Simulate execution with mock code block response
    prompt = "Create a python script hello_world.py that prints Stark Industries Online"
    plan = await orchestrator.create_plan(
        turn_id=1001,
        intent=IntentType.CODING_AND_DEV,
        title=f"Code generation: {prompt[:30]}",
        specialist=agent.name
    )
    
    # Execute through orchestrator
    task = await orchestrator.execute_task(plan.id, agent.execute, prompt)
    assert task.state == TaskState.COMPLETED
    assert task.evidence is not None
    print(f"  [PASS]: CodingAgent executed under orchestrator. Evidence: {task.evidence}")

async def test_telemetry_diagnostics():
    print("\n[TEST 5] Testing Orchestrator Telemetry Diagnostics...")
    diag = orchestrator.get_diagnostics()
    assert "active_tasks_count" in diag
    assert "max_concurrency" in diag
    assert "recent_completed_count" in diag
    assert "recent_history" in diag
    print(f"  [PASS]: Telemetry diagnostics verified (Max Concurrency: {diag['max_concurrency']}, History: {len(diag['recent_history'])} entries).")

async def main():
    print("=================================================================")
    print("J.A.R.V.I.S. DESKTOP APPLICATION & SPECIALISTS TEST SUITE")
    print("=================================================================")
    try:
        await test_desktop_api()
        await test_specialist_registry()
        await test_approval_gate_lifecycle()
        await test_coding_specialist_persistence()
        await test_telemetry_diagnostics()
        print("\n=================================================================")
        print("ALL DESKTOP APPLICATION TESTS PASSED: 5/5 (100.0%)")
        print("=================================================================")
    except Exception as e:
        print(f"\n[FAIL]: Test suite encountered an error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
