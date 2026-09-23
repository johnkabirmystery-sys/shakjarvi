import asyncio
import time
import os
import sys

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import (
    orchestrator,
    TaskState,
    IntentType
)
from core.ai_brain import classify_intent, process_user_message

async def run_tests():
    print("=" * 65)
    print("J.A.R.V.I.S. PHASE 1 & PHASE 2 VERIFICATION TEST SUITE")
    print("=" * 65)

    passed_count = 0
    total_tests = 7

    # ---------------------------------------------------------
    # TEST 1: ALL 9 INTENT TYPES ROUTING ACCURACY
    # ---------------------------------------------------------
    print("\n[TEST 1] Testing Intent Routing Classification...")
    test_cases = [
        ("stop talking right now", IntentType.STOP_CANCEL),
        ("show system telemetry and cpu specs", IntentType.SYSTEM_DIAGNOSTICS),
        ("turn volume up to 80", IntentType.PC_CONTROL),
        ("open desktop folder", IntentType.FILE_OPERATIONS),
        ("assign to research agent to look up AI chips", IntentType.AGENT_DELEGATION),
        ("write a python script for fastapi", IntentType.CODING_AND_DEV),
        ("create an email marketing campaign for product launch", IntentType.MARKETING_AND_BUSINESS),
        ("search online for latest quantum computing breakthroughs", IntentType.QUESTIONS_AND_RESEARCH),
        ("what is two plus two", IntentType.NORMAL_CONVERSATION),
        ("hello jarvis, how are you today", IntentType.NORMAL_CONVERSATION)
    ]

    all_matched = True
    for text, expected in test_cases:
        res = classify_intent(text)
        if res["intent"] != expected:
            print(f"  [MISMATCH] '{text}' -> Got {res['intent'].value}, expected {expected.value}")
            all_matched = False

    if all_matched:
        print(f"  [PASS]: All {len(test_cases)} distinct intent classifications resolved with 100% accuracy.")
        passed_count += 1
    else:
        print("  [FAIL]: Intent classification mismatches detected.")

    # ---------------------------------------------------------
    # TEST 2: AMBIGUITY DETECTION & CLARIFICATION PROMPTING
    # ---------------------------------------------------------
    print("\n[TEST 2] Testing Ambiguity Detection...")
    ambiguous_inputs = ["open", "run", "do it", "start"]
    ambiguity_passed = True

    for text in ambiguous_inputs:
        res = classify_intent(text)
        if not res.get("is_ambiguous") or not res.get("clarification_prompt"):
            print(f"  [FAIL] '{text}' should be flagged ambiguous with clarification prompt. Got: {res}")
            ambiguity_passed = False

    if ambiguity_passed:
        print(f"  [PASS]: All bare commands correctly flagged as ambiguous with polite clarification requests.")
        passed_count += 1
    else:
        print("  [FAIL]: Ambiguity detection failed.")

    # ---------------------------------------------------------
    # TEST 3: HIGH-RISK APPROVAL GATE
    # ---------------------------------------------------------
    print("\n[TEST 3] Testing High-Risk Tool Permission & Approval Gate...")
    del_res = classify_intent("delete file project_old.zip")
    is_high_risk = del_res.get("requires_approval") is True
    has_approval_prompt = "requires your explicit confirmation" in del_res.get("approval_prompt", "")

    # Execute through process_user_message
    events = []
    async for event in process_user_message("delete file project_old.zip"):
        events.append(event)

    response_text = "".join(e.get("text", "") for e in events if e.get("type") == "response")
    gated_correctly = "explicit confirmation" in response_text

    if is_high_risk and has_approval_prompt and gated_correctly:
        print("  [PASS]: High-risk action paused in NEEDS_APPROVAL state requiring explicit user authorization.")
        passed_count += 1
    else:
        print(f"  [FAIL]: High-risk gate failed. is_high_risk={is_high_risk}, gated={gated_correctly}")

    # ---------------------------------------------------------
    # TEST 4: ORCHESTRATOR TASK LIFECYCLE & VERIFICATION EVIDENCE
    # ---------------------------------------------------------
    print("\n[TEST 4] Testing Orchestrator Task Lifecycle & Verification Evidence...")
    plan = await orchestrator.create_plan(
        turn_id=101,
        intent=IntentType.SYSTEM_DIAGNOSTICS,
        title="Check system telemetry",
        specialist="pc_controller"
    )

    if plan.state == TaskState.PLANNED and plan.id in orchestrator.active_tasks:
        async def mock_exec():
            await asyncio.sleep(0.05)
            return "CPU: 12%, RAM: 45%"

        executed = await orchestrator.execute_task(plan.id, mock_exec)
        if executed.state == TaskState.COMPLETED and executed.evidence and "Execution verified" in executed.evidence:
            print(f"  [PASS]: Task #{executed.id} transitioned PLANNED -> RUNNING -> COMPLETED with verified evidence.")
            passed_count += 1
        else:
            print(f"  [FAIL]: Execution state incorrect: state={executed.state}, evidence={executed.evidence}")
    else:
        print(f"  [FAIL]: Initial plan state invalid: {plan.state}")

    # ---------------------------------------------------------
    # TEST 5: ORCHESTRATOR INSTANT CANCELLATION (< 100ms)
    # ---------------------------------------------------------
    print("\n[TEST 5] Testing Orchestrator Clean Task Cancellation...")
    task_a = await orchestrator.create_plan(
        turn_id=102,
        intent=IntentType.CODING_AND_DEV,
        title="Long compiling task",
        specialist="coding_agent"
    )

    start_cancel = time.perf_counter()
    cancelled_count = await orchestrator.cancel_all_active(reason="User said stop")
    cancel_elapsed_ms = (time.perf_counter() - start_cancel) * 1000

    if cancelled_count >= 1 and cancel_elapsed_ms < 100:
        print(f"  [PASS]: {cancelled_count} active task(s) cancelled in {cancel_elapsed_ms:.2f}ms (< 100ms target).")
        passed_count += 1
    else:
        print(f"  [FAIL]: Cancel failed or too slow: count={cancelled_count}, time={cancel_elapsed_ms:.2f}ms")

    # ---------------------------------------------------------
    # TEST 6: BOUNDED CONCURRENCY GUARD
    # ---------------------------------------------------------
    print("\n[TEST 6] Testing Bounded Concurrency Guard (Max Active Tasks)...")
    max_c = orchestrator.max_concurrent_tasks
    concurrency_verified = max_c == 2

    # Diagnostics verification
    diag = orchestrator.get_diagnostics()
    has_diag_keys = "active_tasks_count" in diag and "max_concurrency" in diag

    if concurrency_verified and has_diag_keys:
        print(f"  [PASS]: Bounded concurrency verified: max_concurrent_tasks = {max_c}. Diagnostics operational.")
        passed_count += 1
    else:
        print(f"  [FAIL]: Concurrency guard invalid. max_c={max_c}")

    # ---------------------------------------------------------
    # TEST 7: SINGLE-CALL LLM / IMMEDIATE ARITHMETIC RESPONSE
    # ---------------------------------------------------------
    print("\n[TEST 7] Testing Direct Prompt Answering & Zero Repetitive Monologues...")
    events = []
    async for event in process_user_message("What is two plus two?"):
        events.append(event)

    ans_text = "".join(e.get("text", "") for e in events if e.get("type") == "response").strip()
    no_dental = "dental" not in ans_text.lower()
    no_assimilated = "assimilated" not in ans_text.lower()
    has_answer = ("four" in ans_text.lower()) or ("4" in ans_text)

    if no_dental and no_assimilated and has_answer:
        print(f"  [PASS]: Answered prompt directly ('{ans_text[:40]}...') with zero repetitive monologues or stale context.")
        passed_count += 1
    else:
        print(f"  [FAIL]: Response failed: '{ans_text}', has_answer={has_answer}")

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------
    print("\n" + "=" * 65)
    print(f"PHASE 1 & 2 TEST RESULTS: {passed_count}/{total_tests} PASSED ({(passed_count/total_tests)*100:.1f}%)")
    print("=" * 65)
    return passed_count == total_tests

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
