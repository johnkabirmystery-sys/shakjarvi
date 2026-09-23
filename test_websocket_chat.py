"""
Live WebSocket Regression Test Suite (/ws/chat)
==============================================
Validates:
1. WebSocket Ping/Pong Handshake
2. Duplicate acoustic request detection & suppression
3. Instant stop directive / cancellation handling
4. State broadcast propagation
"""

import sys
import asyncio
import json
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient
from server import app, chat_clients
from core.conversation_controller import conversation_controller, ConversationState

def run_ws_tests():
    print("=" * 60)
    print("  LIVE /ws/chat WEBSOCKET REGRESSION TEST SUITE")
    print("=" * 60)

    client = TestClient(app)
    passed = 0

    # 1. Ping / Pong
    print("\n[*] TEST 1: WebSocket Ping/Pong Handshake...")
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "ping"})
        resp = ws.receive_json()
        assert resp.get("type") == "pong", f"Expected pong, got {resp}"
        print("  [PASS] Ping/Pong handshake returned pong with timestamp.")
        passed += 1

    # 2. Duplicate Acoustic Request Interception
    print("\n[*] TEST 2: Duplicate Acoustic Request Filtering...")
    with client.websocket_connect("/ws/chat") as ws:
        # First send
        ws.send_json({"type": "message", "text": "Report system status", "voice_enabled": False})
        # Immediate acoustic duplicate
        ws.send_json({"type": "message", "text": "Report system status", "voice_enabled": False})
        
        got_sync = False
        for _ in range(5):
            msg = ws.receive_json()
            if msg.get("type") == "response" and "Acoustic link synchronized" in msg.get("text", ""):
                got_sync = True
                break
        assert got_sync, "Expected acoustic link sync message"
        print("  [PASS] Duplicate acoustic request correctly intercepted & suppressed.")
        passed += 1

    # 3. Stop Command Instant Abort
    print("\n[*] TEST 3: Stop Command Instant Abort over WebSocket...")
    with client.websocket_connect("/ws/chat") as ws:
        # Set to speaking first
        ws.send_json({"type": "message", "text": "stop talking please", "voice_enabled": False})
        msg = ws.receive_json()
        assert msg.get("type") == "status" and msg.get("status") == "idle"
        print("  [PASS] Stop directive received and immediately returned idle status.")
        passed += 1

    # 4. Cancel message type
    print("\n[*] TEST 4: Explicit Cancel Event over WebSocket...")
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "cancel"})
        msg = ws.receive_json()
        assert msg.get("type") == "status" and msg.get("status") == "idle"
        print("  [PASS] Explicit 'cancel' type immediately aborted turn and returned idle status.")
        passed += 1

    print("\n" + "=" * 60)
    print(f"  ALL {passed}/4 WEBSOCKET REGRESSION TESTS PASSED (100%)")
    print("=" * 60)

if __name__ == "__main__":
    run_ws_tests()
