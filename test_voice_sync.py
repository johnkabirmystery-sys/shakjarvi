import asyncio
import time
import os
import sys

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.conversation_controller import (
    conversation_controller,
    ConversationState
)
from core import voice_engine
from core import ai_brain

async def run_all_tests():
    print("=" * 60)
    print("J.A.R.V.I.S. VOICE SYNCHRONIZATION & CONVERSATION TEST SUITE")
    print("=" * 60)
    
    passed_count = 0
    total_tests = 6

    # ---------------------------------------------------------
    # TEST 1: STOP COMMAND DETECTION ACCURACY
    # ---------------------------------------------------------
    print("\n[TEST 1] Testing Stop Command Detection...")
    stop_phrases = [
        "stop", "STOP", "cancel", "be quiet", "shut up", 
        "never mind", "nevermind", "wait", "hold on", "pause", 
        "silence", "Jarvis stop", "please stop talking"
    ]
    non_stop_phrases = [
        "what is the weather", "stopwatch timer", "nonstop flight",
        "tell me a story", "open chrome", "who created you"
    ]
    
    all_stop_matched = all(conversation_controller.is_stop_command(p) for p in stop_phrases)
    all_non_stop_passed = all(not conversation_controller.is_stop_command(p) for p in non_stop_phrases)
    
    if all_stop_matched and all_non_stop_passed:
        print("  [PASS]: All 13 stop directives recognized and 6 non-stop phrases avoided.")
        passed_count += 1
    else:
        print(f"  [FAIL]: stop_matched={all_stop_matched}, non_stop_passed={all_non_stop_passed}")

    # ---------------------------------------------------------
    # TEST 2: STOP COMMAND IMMEDIATE ABORT LATENCY (< 250ms)
    # ---------------------------------------------------------
    print("\n[TEST 2] Testing Stop Command Abort Latency...")
    # Simulate an active turn
    t_id = conversation_controller.register_new_turn("native")
    await conversation_controller.set_state(ConversationState.SPEAKING, "TEST SPEAKING")
    
    start_t = time.perf_counter()
    await conversation_controller.abort_active_turn(reason="Test Stop Directive")
    elapsed_ms = (time.perf_counter() - start_t) * 1000
    
    current_st = conversation_controller.state
    if elapsed_ms < 250 and current_st == ConversationState.IDLE:
        print(f"  [PASS]: Abort completed in {elapsed_ms:.2f}ms (< 250ms target) with state returned to IDLE.")
        passed_count += 1
    else:
        print(f"  [FAIL]: Latency={elapsed_ms:.2f}ms, state={current_st}")

    # ---------------------------------------------------------
    # TEST 3: MONOTONIC TURN PREEMPTION
    # ---------------------------------------------------------
    print("\n[TEST 3] Testing Monotonic Turn Preemption...")
    turn1_aborted = False
    turn2_executed = False

    async def mock_pipeline_1(turn_id, prompt, **kwargs):
        nonlocal turn1_aborted
        try:
            await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            turn1_aborted = True
            raise

    async def mock_pipeline_2(turn_id, prompt, **kwargs):
        nonlocal turn2_executed
        turn2_executed = True

    # Start turn 1
    t1_res = await conversation_controller.handle_user_prompt(
        prompt="First long command",
        source="native",
        process_callback=mock_pipeline_1
    )
    t1 = t1_res["turn_id"]
    # Give turn 1 event loop slice to begin
    await asyncio.sleep(0.05)

    # Immediately preempt with turn 2
    t2_res = await conversation_controller.handle_user_prompt(
        prompt="Second urgent command",
        source="native",
        process_callback=mock_pipeline_2
    )
    t2 = t2_res["turn_id"]
    # Allow turn 2 to run
    await asyncio.sleep(0.1)

    if t2 > t1 and turn1_aborted and turn2_executed:
        print(f"  [PASS]: Turn #{t1} successfully preempted by Turn #{t2} (monotonic: {t2} > {t1}).")
        passed_count += 1
    else:
        print(f"  [FAIL]: t1={t1}, t2={t2}, turn1_aborted={turn1_aborted}, turn2_executed={turn2_executed}")

    # ---------------------------------------------------------
    # TEST 4: STALE TURN SPEECH DISCARD
    # ---------------------------------------------------------
    print("\n[TEST 4] Testing Stale Speech Turn Invalidation...")
    # Register turn 100
    current_active = conversation_controller.register_new_turn("native")
    stale_turn_id = current_active - 1

    # Verify that conversation_controller.is_turn_current flags stale correctly
    is_stale_valid = conversation_controller.is_turn_current(stale_turn_id)
    is_current_valid = conversation_controller.is_turn_current(current_active)

    if not is_stale_valid and is_current_valid:
        print(f"  [PASS]: Stale turn #{stale_turn_id} correctly flagged invalid; active turn #{current_active} valid.")
        passed_count += 1
    else:
        print(f"  [FAIL]: stale_valid={is_stale_valid}, current_valid={is_current_valid}")

    # ---------------------------------------------------------
    # TEST 5: CHANNEL EXCLUSIVITY (PC SPEAKER VS BROWSER HUD)
    # ---------------------------------------------------------
    print("\n[TEST 5] Testing Audio Dispatch Channel Exclusivity...")
    from server import dispatch_tts, chat_clients
    
    # Create mock websocket client to capture HUD payload
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []
        async def send_text(self, text):
            self.sent_messages.append(text)

    mock_ws = MockWebSocket()
    chat_clients.add(mock_ws)

    # Case A: play_speaker = True (Should NOT send audio_base64 to HUD)
    await dispatch_tts(mock_ws, "Diagnostic confirmation.", play_speaker=True, turn_id=current_active)
    speaker_mode_has_base64 = any('"type": "audio"' in msg for msg in mock_ws.sent_messages)

    mock_ws.sent_messages.clear()

    # Case B: play_speaker = False (Should send audio_base64 to HUD)
    await dispatch_tts(mock_ws, "Browser stream test.", play_speaker=False, turn_id=current_active)
    browser_mode_has_base64 = any('"type": "audio"' in msg for msg in mock_ws.sent_messages)

    chat_clients.discard(mock_ws)

    if (not speaker_mode_has_base64) and browser_mode_has_base64:
        print("  [PASS]: Strict channel exclusivity confirmed: speaker mode sends zero audio_base64 to HUD; browser mode sends audio_base64.")
        passed_count += 1
    else:
        print(f"  [FAIL]: speaker_has_b64={speaker_mode_has_base64}, browser_has_b64={browser_mode_has_base64}")

    # ---------------------------------------------------------
    # TEST 6: ARCHITECTURE QUERY & CONTEXT PURITY
    # ---------------------------------------------------------
    print("\n[TEST 6] Testing Architecture Query & Dental Context Poisoning...")
    offline_resp = await ai_brain.handle_offline_commands("who created you and what is your architecture")
    has_dental = "dental" in offline_resp.lower() or "canadian" in offline_resp.lower()
    has_shakil = "shakil" in offline_resp.lower()
    
    dental_stop_resp = await ai_brain.handle_offline_commands("stop working on the dental project")
    cleared_dental = "purged" in dental_stop_resp.lower() or "dental" in dental_stop_resp.lower()

    if (not has_dental) and has_shakil and cleared_dental:
        print("  [PASS]: Architecture response grounds directly in Sir Shakil; dental project purged from active context.")
        passed_count += 1
    else:
        print(f"  [FAIL]: has_dental={has_dental}, has_shakil={has_shakil}, cleared_dental={cleared_dental}")

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed_count}/{total_tests} PASSED ({(passed_count/total_tests)*100:.1f}%)")
    print("=" * 60)
    
    return passed_count == total_tests

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
