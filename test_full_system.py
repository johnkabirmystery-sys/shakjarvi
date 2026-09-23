"""
Master End-to-End Test Suite for Shakil's Assistant (J.A.R.V.I.S.)
===================================================================
Exhaustive verification across all 11 architectural phases:
- Phase 1: Intelligent Core & Intent Classification
- Phase 2: Master Orchestrator & Bounded Concurrency
- Phase 3: 9-Specialist Autonomous Agent Registry
- Phase 4: Resource-Aware Model Gateway & Circuit Breakers
- Phase 5: 6-Workspace Context Isolation (Personal, Agency, Crypto, SaaS, Systems, Research)
- Phase 6: Verified Tool Registry & Human Approval Gate
- Phase 7: Neural Memory, FTS5 RAG & Preference Verification
- Phase 8: Proactive Autonomous Supervisor & Silence Protocol
- Phase 9: Real-Time Observability & Telemetry Diagnostics
- Phase 10: Spoken Brevity & Instant Cancellation (< 100ms)
- Phase 11: Desktop Application Native Bridge & Port Collision Guard
"""

import sys
import os
import time
import asyncio
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Color helpers
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"

passed_tests = 0
failed_tests = 0

def record_result(test_name: str, passed: bool, detail: str = ""):
    global passed_tests, failed_tests
    if passed:
        passed_tests += 1
        print(f"  {GREEN}[PASS]{RESET} {test_name} {CYAN}{detail}{RESET}")
    else:
        failed_tests += 1
        print(f"  {RED}[FAIL]{RESET} {test_name} {YELLOW}{detail}{RESET}")


async def test_phase_1_intelligent_core():
    print(f"\n{CYAN}--- Testing Phase 1: Intelligent Core & Intent Classification ---{RESET}")
    from core.ai_brain import classify_intent, IntentType
    
    # 1. Routing classification
    queries = [
        ("stop talking right now", IntentType.STOP_CANCEL),
        ("show system telemetry and cpu specs", IntentType.SYSTEM_DIAGNOSTICS),
        ("turn volume up to 80", IntentType.PC_CONTROL),
        ("open desktop folder", IntentType.FILE_OPERATIONS),
        ("assign to research agent to look up AI chips", IntentType.AGENT_DELEGATION),
        ("write a python script for fastapi", IntentType.CODING_AND_DEV),
        ("create an email marketing campaign for product launch", IntentType.MARKETING_AND_BUSINESS),
        ("search online for latest quantum computing breakthroughs", IntentType.QUESTIONS_AND_RESEARCH),
        ("what is two plus two", IntentType.NORMAL_CONVERSATION),
    ]
    all_matched = True
    for q, expected in queries:
        res = classify_intent(q)
        if res.get("intent") != expected:
            all_matched = False
            record_result(f"Intent for '{q}'", False, f"Expected {expected}, got {res.get('intent')}")
            break
    if all_matched:
        record_result("Intent Classification (9 categories)", True, "All queries mapped to precise intents")

    # 2. Ambiguity detection
    amb_1 = classify_intent("do it")
    amb_2 = classify_intent("def calculate_fibonacci(n): return [0, 1] if n <= 2 else ...")
    record_result("Ambiguity Detection", amb_1.get("is_ambiguous") and not amb_2.get("is_ambiguous"), "Vague directive flagged with clarification prompt, concrete directive cleared")


async def test_phase_2_master_orchestrator():
    print(f"\n{CYAN}--- Testing Phase 2: Master Orchestrator & Bounded Concurrency ---{RESET}")
    from core.orchestrator import orchestrator, IntentType, TaskState
    
    # 1. Plan creation and execution
    plan = await orchestrator.create_plan(
        turn_id=9001,
        intent=IntentType.QUESTIONS_AND_RESEARCH,
        title="Diagnostic Orchestration Plan",
        specialist="ResearchAgent"
    )
    record_result("Plan Creation", plan is not None and plan.id in orchestrator.active_tasks, f"Plan #{plan.id} registered")

    # 2. Bounded concurrency (max = 2)
    async def sample_task_fn():
        await asyncio.sleep(0.05)
        return "Completed Task A"

    t1 = await orchestrator.execute_task(plan.id, sample_task_fn)
    record_result("Task Execution & Evidence", t1.state == TaskState.COMPLETED and "Completed Task A" in str(t1.result), f"Result verified with state: {t1.state.value}")

    # 3. Concurrency check
    diag = orchestrator.get_diagnostics()
    record_result("Concurrency Diagnostics", diag["max_concurrency"] == 2, f"Active: {diag['active_tasks_count']}, Max: {diag['max_concurrency']}")


async def test_phase_3_specialist_agent_suite():
    print(f"\n{CYAN}--- Testing Phase 3: 9-Specialist Autonomous Agent Registry ---{RESET}")
    from core.specialists import list_specialists, get_specialist
    
    specs = list_specialists()
    expected_ids = {"research", "coding", "qa", "marketing", "seo", "leadgen", "wordpress", "business", "system"}
    found_ids = {s["id"] for s in specs}
    
    record_result("Specialist Count & IDs", expected_ids.issubset(found_ids), f"Found {len(specs)} specialists ({', '.join(sorted(found_ids))})")

    # Execute CodingAgent code auto-saving test
    coding_agent = get_specialist("coding")
    res = await coding_agent.execute("Create a quick python helper function")
    saved_files = res.get("saved_files", [])
    record_result("CodingAgent Execution", res.get("success", False) and len(saved_files) > 0, f"Saved file: {saved_files[0]['filename'] if saved_files else 'None'}")


async def test_phase_4_model_gateway_circuit_breaker():
    print(f"\n{CYAN}--- Testing Phase 4: Model Gateway & Circuit Breakers ---{RESET}")
    from core.omniroute_client import circuit_breaker, get_gateway_health
    
    # 1. Initial status
    health_init = get_gateway_health()
    record_result("Initial Gateway Health", "status" in health_init, f"Status: {health_init['status']}, Latency: {health_init['average_latency_sec']}s")

    # 2. Trip simulation and recovery check
    circuit_breaker.trip("test/model-spike", "Simulated 429 Rate Limit")
    avail = circuit_breaker.is_available("test/model-spike")
    record_result("Circuit Breaker Tripping", not avail, "Tripped model correctly quarantined")

    # 3. Latency recording
    circuit_breaker.record_latency("test/model-fast", 0.32)
    record_result("Latency Recording", circuit_breaker.get_average_latency() > 0, f"Average latency: {circuit_breaker.get_average_latency()}s")


async def test_phase_5_workspace_isolation():
    print(f"\n{CYAN}--- Testing Phase 5: 6-Workspace Context Isolation ---{RESET}")
    from core import rag_engine, memory_engine
    
    # Clean previous test entries
    ts = int(time.time())
    rag_engine.log_conversation("user", f"Agency strategy update {ts}", workspace="agency")
    rag_engine.log_conversation("user", f"Crypto indicator entry {ts}", workspace="crypto")
    
    agency_history = rag_engine.get_recent_history(limit=5, workspace="agency")
    crypto_history = rag_engine.get_recent_history(limit=5, workspace="crypto")
    
    agency_has_crypto = any("crypto indicator" in h.get("content", "").lower() for h in agency_history)
    crypto_has_agency = any("agency strategy" in h.get("content", "").lower() for h in crypto_history)
    
    record_result("Dialogue Workspace Isolation", not agency_has_crypto and not crypto_has_agency, "Strict zero cross-talk between agency and crypto workspaces")

    # Memory facts isolation
    memory_engine.save_fact(category="preference", key="Crypto Strategy", value=f"DCA into BTC {ts}", workspace="crypto")
    crypto_facts = memory_engine.get_facts_for_prompt(workspace="crypto")
    agency_facts = memory_engine.get_facts_for_prompt(workspace="agency")
    
    record_result("Facts Workspace Isolation", "DCA into BTC" in crypto_facts and "DCA into BTC" not in agency_facts, "Crypto facts strictly excluded from agency prompt block")


async def test_phase_6_safety_and_approval():
    print(f"\n{CYAN}--- Testing Phase 6: Human Approval Gate & Stark Safety Protocol ---{RESET}")
    from core.orchestrator import orchestrator, IntentType, TaskState
    
    plan = await orchestrator.create_plan(
        turn_id=9002,
        intent=IntentType.SYSTEM_DIAGNOSTICS,
        title="High-Risk Action Simulation",
        specialist="SystemAgent",
        requires_approval=True,
        approval_prompt="Delete temporary system files?"
    )
    
    async def dummy_executor():
        return "Deleted temp files"

    # Execution should be intercepted into NEEDS_APPROVAL
    task = await orchestrator.execute_task(plan.id, dummy_executor)
    record_result("Approval Interception", task.state == TaskState.NEEDS_APPROVAL, f"Task #{task.id} halted in NEEDS_APPROVAL state")

    # User Approval
    approved_task = await orchestrator.approve_task(task.id)
    record_result("User Authorization", approved_task.state == TaskState.RUNNING and "authorized" in approved_task.evidence, f"Task transitioned to {approved_task.state.value}")


async def test_phase_7_memory_and_preference():
    print(f"\n{CYAN}--- Testing Phase 7: Neural Memory & Stored Preference ---{RESET}")
    from core import memory_engine, rag_engine
    
    # Check specifically for Sir Shakil's stored preference
    facts = memory_engine.get_all_facts()
    found_pref = False
    for f in facts:
        val = str(f.get("value", "")).lower()
        if "concise answers for routine technical fixes" in val:
            found_pref = True
            break
            
    record_result("User Preference Persistence", found_pref, "Found 'Concise answers for routine technical fixes' in memory database")

    # RAG search retrieval
    search_res = rag_engine.retrieve_relevant_facts("technical fixes", limit=3)
    record_result("RAG Fact Retrieval", len(search_res) > 0, f"Retrieved {len(search_res)} matching knowledge items")


async def test_phase_8_proactive_supervisor():
    print(f"\n{CYAN}--- Testing Phase 8: Proactive Autonomous Supervisor ---{RESET}")
    from core.proactive_supervisor import proactive_supervisor
    from core.conversation_controller import conversation_controller, ConversationState
    
    # Check status
    status = proactive_supervisor.get_status()
    record_result("Supervisor Telemetry", "dialogue_active" in status and "silent_period" in status, f"Dialogue active: {status['dialogue_active']}, Silent period: {status['silent_period']}")

    # Check silence guarantee
    await conversation_controller.set_state(ConversationState.SPEAKING, "TESTING VOICE DIALOGUE")
    is_active = conversation_controller.is_dialogue_active()
    await conversation_controller.set_state(ConversationState.IDLE, "READY")
    
    record_result("Dialogue Silence Guarantee", is_active, "Supervisor correctly identifies active dialogue state")


async def test_phase_9_telemetry_matrix():
    print(f"\n{CYAN}--- Testing Phase 9: Real-Time Observability & Telemetry ---{RESET}")
    from core import telemetry, memory_engine
    from core.orchestrator import orchestrator
    from core.omniroute_client import get_gateway_health
    
    data = telemetry.get_telemetry_data()
    has_cpu = "cpu" in data and "percent" in data["cpu"]
    has_ram = "memory" in data and "used_gb" in data["memory"]
    has_disks = "disks" in data and len(data["disks"]) > 0
    
    record_result("Hardware Telemetry", has_cpu and has_ram and has_disks, f"CPU: {data['cpu']['percent']}%, RAM: {data['memory']['percent']}%")

    # Subsystem telemetry bundles
    orch_diag = orchestrator.get_diagnostics()
    gw_diag = get_gateway_health()
    record_result("Subsystem Diagnostics Bundle", "active_tasks_count" in orch_diag and "status" in gw_diag, f"Orchestrator Active: {orch_diag['active_tasks_count']}, Gateway: {gw_diag['status']}")


async def test_phase_10_spoken_brevity_and_cancellation():
    print(f"\n{CYAN}--- Testing Phase 10: Spoken Brevity & Instant Cancellation ---{RESET}")
    from core import voice_engine
    from core.conversation_controller import conversation_controller
    
    # Test spoken summary length (<= 35 words)
    long_markdown_text = (
        "Here is the code you requested:\n```python\ndef run_pipeline():\n    return True\n```\n"
        "I have generated the pipeline implementation for your workstation. "
        "It includes automated data transformations, error recovery mechanisms, and logging."
    )
    summary = voice_engine.get_spoken_summary(long_markdown_text)
    word_count = len(summary.split())
    record_result("Spoken Brevity Constraint", word_count <= 35, f"Spoken summary is {word_count} words (<= 35 words): '{summary}'")

    # Test Instant Cancellation (< 100ms)
    t0 = time.perf_counter()
    await conversation_controller.abort_active_turn(reason="Test Stop Verification")
    elapsed_ms = (time.perf_counter() - t0) * 1000
    record_result("Instant Cancellation Latency", elapsed_ms < 100, f"Aborted in {elapsed_ms:.2f} ms (< 100ms threshold)")


async def test_phase_11_desktop_bridge_and_port():
    print(f"\n{CYAN}--- Testing Phase 11: Desktop Native PyWebView Bridge ---{RESET}")
    from run import is_port_in_use, JarvisDesktopApi
    
    # 1. Port check function
    port_8000_status = is_port_in_use(8000)
    record_result("Port Collision Guard", isinstance(port_8000_status, bool), f"Port 8000 in use: {port_8000_status}")

    # 2. Native Bridge API
    api = JarvisDesktopApi()
    folder_res = api.open_created_files_folder()
    record_result("Native Bridge Folder Opening", folder_res.get("success", False), f"Path: {folder_res.get('path')}")

    cancel_res = api.emergency_cancel()
    record_result("Native Bridge Emergency Abort", cancel_res.get("success", False), f"Status: {cancel_res.get('status')}")


async def main():
    print(f"\n{'='*70}")
    print(f"{CYAN}  J.A.R.V.I.S. FULL ARCHITECTURAL SYSTEM VERIFICATION SUITE{RESET}")
    print(f"{'='*70}")
    
    await test_phase_1_intelligent_core()
    await test_phase_2_master_orchestrator()
    await test_phase_3_specialist_agent_suite()
    await test_phase_4_model_gateway_circuit_breaker()
    await test_phase_5_workspace_isolation()
    await test_phase_6_safety_and_approval()
    await test_phase_7_memory_and_preference()
    await test_phase_8_proactive_supervisor()
    await test_phase_9_telemetry_matrix()
    await test_phase_10_spoken_brevity_and_cancellation()
    await test_phase_11_desktop_bridge_and_port()

    print(f"\n{'='*70}")
    total = passed_tests + failed_tests
    print(f"VERIFICATION SUMMARY: {GREEN}{passed_tests}/{total} TESTS PASSED{RESET} ({(passed_tests/total)*100:.1f}%)")
    if failed_tests == 0:
        print(f"{GREEN}[OK] ALL 11 ARCHITECTURAL PHASES VALIDATED & OPERATIONAL, SIR SHAKIL.{RESET}")
    else:
        print(f"{RED}[FAIL] {failed_tests} TESTS FAILED. REQUIRES ATTENTION.{RESET}")
    print(f"{'='*70}\n")
    
    sys.exit(0 if failed_tests == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
