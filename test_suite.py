import os
import sys

def run_tests():
    print("[*] TEST 1: Testing Telemetry Matrix...")
    from core.telemetry import get_telemetry_data
    data = get_telemetry_data()
    assert "cpu" in data, "Missing CPU in telemetry"
    assert "memory" in data, "Missing memory in telemetry"
    assert "disks" in data, "Missing disks in telemetry"
    print(f"    [+] CPU: {data['cpu']['percent']}%, RAM: {data['memory']['percent']}%, Cores: {data['cpu']['count']}")

    print("[*] TEST 2: Testing PC Controller...")
    from core.pc_controller import get_volume, set_volume, media_control
    vol = get_volume()
    print(f"    [+] Current Volume: {vol['level']}%, Muted: {vol['is_muted']}")
    set_res = set_volume(vol['level'])
    assert set_res.get("success"), "Set volume failed"

    print("[*] TEST 3: Testing Neural Voice Engine...")
    from core.voice_engine import synthesize_speech
    tts = synthesize_speech("Diagnostics verified, Sir Shakil.")
    assert tts.get("success"), "TTS generation failed"
    assert os.path.exists(tts["filepath"]), "TTS file not found on disk"
    print(f"    [+] Synthesized TTS audio: {tts['size_bytes']} bytes at {tts['filepath']}")

    print("[*] TEST 4: Testing AI Brain Command Dispatch...")
    import asyncio
    from core.ai_brain import handle_offline_commands
    reply = asyncio.run(handle_offline_commands("Jarvis, report system status"))
    assert "Sir Shakil" in reply, "Offline handler reply missing expected persona greeting"
    print(f"    [+] AI Brain Offline Handler: '{reply}'")

    print("[*] TEST 5: Testing FastAPI Server App...")
    from server import app
    assert app.title == "Shakil's Assistant (J.A.R.V.I.S.)", "Server title mismatch"
    print("    [+] FastAPI Server instance ready and mounted.")

    print("\n=======================================================")
    print("   ALL J.A.R.V.I.S. DIAGNOSTIC TESTS PASSED (5/5)!")
    print("=======================================================")

if __name__ == "__main__":
    run_tests()
