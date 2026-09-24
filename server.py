import os
import re
import time
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from core import telemetry
from core import pc_controller
from core import voice_engine
from core import ai_brain
from core import native_stt
import asyncio
from typing import Any, Optional
from core import memory_engine
from core import research_engine
from core import antigravity_bridge
from core import omniroute_client
from core.browser_controller import browser_controller
from core.marketing_engine import marketing_engine
from core.proactive_monitor import ProactiveMonitor
from core.proactive_supervisor import proactive_supervisor
from core import rag_engine
from core import code_sandbox
from core import vision_copilot
from core.conversation_controller import conversation_controller, ConversationState
from core.spatial import spatial_service, spatial_session, spatial_query_engine, provider_manager, execute_spatial_tool
from core.family_safety import (
    device_registry, network_discovery, consent_manager,
    safety_signal_engine, safety_alert_engine, checkin_manager,
    family_storage
)
from core.remote import (
    remote_auth, remote_command_gateway, persistent_task_manager,
    reliability_monitor, telephony_gateway, SystemReliabilityState
)

app = FastAPI(title="Shakil's Assistant (J.A.R.V.I.S.)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Active WebSockets
telemetry_clients = set()
chat_clients = set()

async def broadcast_event(event_dict):
    disconnected = set()
    for ws in list(chat_clients):
        try:
            await ws.send_text(json.dumps(event_dict))
        except Exception:
            disconnected.add(ws)
    for ws in disconnected:
        chat_clients.discard(ws)

# Proactive monitor & Spatial Service broadcaster
monitor = ProactiveMonitor(broadcast_callback=broadcast_event)
spatial_service.set_broadcast_callback(broadcast_event)

# Main server event loop reference for thread-safe cross-thread dispatch
MAIN_SERVER_LOOP = None

# REST Endpoints
@app.get("/api/settings")
async def get_settings():
    key = ai_brain.get_gemini_api_key()
    return {
        "has_api_key": True,
        "api_key_masked": "Antigravity Project Linked (Zero Keys Required)",
        "default_voice": voice_engine.DEFAULT_VOICE,
        "voices": voice_engine.get_voice_list()
    }

@app.post("/api/settings")
async def update_settings(req: Request):
    data = await req.json()
    if "api_key" in data and data["api_key"].strip():
        ai_brain.save_gemini_api_key(data["api_key"].strip())
    if "voice" in data and data["voice"].strip():
        voice_engine.DEFAULT_VOICE = data["voice"].strip()
    return {"success": True, "message": "Settings updated, Sir Shakil."}

@app.get("/api/voices")
async def get_voices():
    return voice_engine.get_voice_list()

@app.get("/api/models")
async def get_models():
    return {
        "models": omniroute_client.get_available_models(),
        "default_model": "agy/gemini-3.7-flash-low"
    }

@app.post("/api/tts")
async def text_to_speech(req: Request):
    data = await req.json()
    text = data.get("text", "")
    voice = data.get("voice", voice_engine.DEFAULT_VOICE)
    res = await voice_engine.synthesize_speech_async(text, voice=voice)
    return res

last_speech_cache = {
    "filepath": None,
    "text": None,
    "timestamp": 0
}

@app.post("/api/voice/play_last")
async def play_last_voice():
    fp = last_speech_cache.get("filepath")
    if fp and os.path.exists(fp):
        voice_engine.play_audio_file_on_speakers(fp)
        return {"success": True, "played": True, "filepath": fp, "text": last_speech_cache.get("text")}
    return {"success": False, "error": "No cached audio file available to play."}

@app.get("/api/voice/status")
async def get_voice_status():
    return {
        "is_speaking": voice_engine.is_speaking(),
        "has_last_audio": bool(last_speech_cache.get("filepath")),
        "default_voice": voice_engine.DEFAULT_VOICE
    }

@app.get("/api/orchestrator/status")
async def get_orchestrator_status():
    from core.orchestrator import orchestrator
    return orchestrator.get_diagnostics()

@app.post("/api/orchestrator/approve")
async def approve_orchestrator_task(req: Request):
    body = await req.json()
    task_id = body.get("task_id")
    if not task_id:
        return {"success": False, "error": "task_id required"}
    from core.orchestrator import orchestrator
    task = await orchestrator.approve_task(task_id)
    if not task:
        return {"success": False, "error": f"Task {task_id} not found or not in approval state"}
    return {"success": True, "task": {"id": task.id, "state": task.state.value, "evidence": task.evidence}}

@app.post("/api/orchestrator/reject")
async def reject_orchestrator_task(req: Request):
    body = await req.json()
    task_id = body.get("task_id")
    reason = body.get("reason", "Rejected by user directive")
    if not task_id:
        return {"success": False, "error": "task_id required"}
    from core.orchestrator import orchestrator
    task = await orchestrator.reject_task(task_id, reason=reason)
    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}
    return {"success": True, "task": {"id": task.id, "state": task.state.value, "error": task.error}}

@app.get("/api/specialist/list")
async def list_available_specialists():
    from core.specialists import list_specialists
    return {"success": True, "specialists": list_specialists()}

@app.post("/api/specialist/dispatch")
async def dispatch_specialist(req: Request):
    body = await req.json()
    specialist_id = body.get("specialist_id", "")
    prompt = body.get("prompt", "")
    if not prompt:
        return {"success": False, "error": "Directive prompt required."}
    from core.specialists import get_specialist
    agent = get_specialist(specialist_id)
    if not agent:
        return {"success": False, "error": f"Specialist '{specialist_id}' not found."}
    
    from core.orchestrator import orchestrator, IntentType
    plan = await orchestrator.create_plan(
        turn_id=int(time.time()),
        intent=IntentType.AGENT_DELEGATION,
        title=f"[{agent.role}] {prompt[:40]}",
        specialist=agent.name
    )
    task = await orchestrator.execute_task(plan.id, agent.execute, prompt)
    return {"success": True, "task_id": task.id, "state": task.state.value, "result": task.result, "evidence": task.evidence}

@app.post("/api/desktop/open_folder")
async def open_desktop_artifacts_folder(req: Request = None):
    folder = Path(r"C:\Users\Qbits\Desktop\Jarvis_Created_Files")
    folder.mkdir(parents=True, exist_ok=True)
    try:
        os.startfile(str(folder))
        return {"success": True, "path": str(folder)}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Acoustic Request Deduplication (prevents dual-device echo when phone + PC both hear user in the room)
recent_speech_requests = {}

def is_duplicate_acoustic_request(text: str) -> bool:
    now = time.time()
    clean = text.lower().strip()
    # Prune entries older than 6 seconds
    for k in list(recent_speech_requests.keys()):
        if now - recent_speech_requests[k]["time"] > 6.0:
            recent_speech_requests.pop(k, None)

    for req_id, data in recent_speech_requests.items():
        prev = data["text"]
        # If identical or substring within 4.0 seconds, flag as duplicate from another device
        if (clean == prev or (len(clean) > 5 and clean in prev) or (len(prev) > 5 and prev in clean)) and (now - data["time"] < 4.0):
            return True

    recent_speech_requests[f"req_{now}_{clean[:10]}"] = {"text": clean, "time": now}
    return False

@app.post("/api/voice/test")
async def test_voice(req: Request = None):
    play_speaker = False
    if req:
        try:
            body = await req.json()
            play_speaker = body.get("play_speaker", False)
        except Exception:
            pass
    phrase = "Online and ready, Sir Shakil. All neural systems functioning at peak capacity."
    res = await voice_engine.synthesize_speech_async(phrase)
    if res.get("filepath"):
        last_speech_cache["filepath"] = res["filepath"]
        last_speech_cache["text"] = phrase
        last_speech_cache["timestamp"] = time.time()
        if play_speaker:
            voice_engine.play_audio_file_on_speakers(res.get("filepath"))
    return res

@app.post("/api/voice/stop")
async def stop_voice():
    await conversation_controller.abort_active_turn(reason="User triggered /api/voice/stop")
    return {"success": True, "message": "Voice audio halted, Sir."}

@app.get("/api/voice/devices")
async def get_voice_devices():
    devs = native_stt.list_input_devices()
    current = native_stt.get_stt_device_info()
    return {"devices": devs, "current": current}

@app.get("/api/voice/mic/status")
async def get_mic_status():
    return native_stt.get_stt_device_info()

@app.post("/api/voice/listen/toggle")
async def toggle_voice_listen():
    if native_stt.is_stt_muted():
        native_stt.unmute_stt()
        await broadcast_event({"type": "status", "status": "listening", "subtext": "LISTENING"})
    else:
        native_stt.mute_stt()
        await broadcast_event({"type": "status", "status": "idle", "subtext": "MIC PAUSED"})
    info = native_stt.get_stt_device_info()
    return {"success": True, **info}

@app.post("/api/voice/listen/pause")
async def pause_voice_listen():
    native_stt.pause_listening()
    await broadcast_event({"type": "status", "status": "idle", "subtext": "MIC PAUSED"})
    return {"success": True, "is_muted": True}

@app.post("/api/voice/listen/resume")
async def resume_voice_listen():
    native_stt.resume_listening()
    await broadcast_event({"type": "status", "status": "listening", "subtext": "LISTENING"})
    return {"success": True, "is_muted": False}

@app.post("/api/voice/device/select")
async def select_voice_device(req: Request):
    body = await req.json()
    device_id = body.get("device_id")
    if device_id is not None:
        native_stt.set_stt_device(int(device_id))
    return {"success": True, **native_stt.get_stt_device_info()}

from core import audio_device_manager as adm

@app.get("/api/audio/matrix")
async def get_audio_matrix():
    return adm.get_audio_matrix_status()

@app.post("/api/audio/select")
async def select_audio_devices(req: Request):
    body = await req.json()
    if "input_id" in body:
        inp = body["input_id"]
        adm.set_preferred_input(inp)
        native_stt.set_stt_device(inp)
    if "output_id" in body:
        out = body["output_id"]
        adm.set_preferred_output(out)
    status = adm.get_audio_matrix_status()
    await broadcast_event({
        "type": "audio_matrix_updated",
        "active_input": status["active_input"],
        "active_output": status["active_output"]
    })
    return {"success": True, **status}

@app.post("/api/audio/test_mic")
async def test_audio_mic(req: Request):
    body = await req.json()
    device_id = body.get("device_id")
    if device_id == "auto" or device_id is None:
        best_id, _ = adm.resolve_best_input_device()
        device_id = best_id
    else:
        try:
            device_id = int(device_id)
        except Exception:
            device_id = None
    res = adm.test_input_device_non_blocking(device_id, duration=0.4)
    return res

@app.post("/api/audio/test_speaker")
async def test_audio_speaker(req: Request):
    body = await req.json()
    device_id = body.get("device_id")
    phrase = "Audio output verified on your active speaker device, Sir Shakil."
    res = await voice_engine.synthesize_speech_async(phrase)
    if res.get("filepath"):
        voice_engine.play_audio_file_on_speakers(res["filepath"])
    return {"success": True, "message": phrase}



@app.post("/api/chat")
async def chat_endpoint(req: Request):
    data = await req.json()
    text = (data.get("message") or data.get("text", "")).strip()
    voice_enabled = data.get("voice_enabled", True)
    play_speaker = data.get("play_speaker", False)
    model = data.get("model", "agy/gemini-3.7-flash-low")
    workspace = data.get("workspace", "personal")
    history = data.get("history", [])
    if not history:
        history = rag_engine.get_recent_history(limit=14, workspace=workspace)
    elif len(history) > 16:
        history = history[-16:]

    # Acoustic duplicate filtering (prevents phone + PC simultaneous echo)
    if is_duplicate_acoustic_request(text):
        return {
            "response": "Acoustic link synchronized with your primary device, Sir Shakil.",
            "audio_base64": None,
            "duplicate": True
        }
    
    full_response = ""
    async for event in ai_brain.process_user_message(text, history=history, model=model, workspace=workspace):
        if event.get("type") == "response":
            full_response = event.get("text", "")
            
    audio_base64 = None
    filepath = None
    spoken_summary = ""
    mime_type = "audio/wav"
    duration = 2.0
    
    if voice_enabled and full_response:
        spoken_summary = voice_engine.get_spoken_summary(full_response)
        audio_res = await voice_engine.synthesize_speech_async(spoken_summary)
        if audio_res.get("success"):
            audio_base64 = audio_res.get("base64")
            filepath = audio_res.get("filepath")
            mime_type = audio_res.get("mime", "audio/wav")
            duration = audio_res.get("duration", 2.0)
            if filepath:
                last_speech_cache["filepath"] = filepath
                last_speech_cache["text"] = spoken_summary
                last_speech_cache["timestamp"] = time.time()
                if play_speaker:
                    voice_engine.play_audio_file_on_speakers(filepath)
            
    saved_files = []
    if full_response and "```" in full_response:
        saved_files = auto_save_code_blocks_to_desktop(full_response)
        
    if text and full_response:
        rag_engine.log_conversation("user", text, model=model, workspace=workspace)
        rag_engine.log_conversation("assistant", full_response, model=model, workspace=workspace)
        
    return {
        "response": full_response,
        "audio_base64": audio_base64,
        "mime": mime_type,
        "duration": duration,
        "filepath": filepath,
        "spoken_summary": spoken_summary,
        "saved_files": saved_files,
        "workspace": workspace
    }

@app.post("/api/action")
async def execute_pc_action(req: Request):
    data = await req.json()
    action = data.get("action", "")
    params = data.get("params", {})
    
    if action == "launch":
        return pc_controller.launch_app(params.get("app_name", ""))
    elif action == "close":
        return pc_controller.close_app(params.get("name", ""))
    elif action == "set_volume":
        return pc_controller.set_volume(params.get("percent", 50))
    elif action == "mute":
        return pc_controller.mute_volume(params.get("mute_state"))
    elif action == "media":
        return pc_controller.media_control(params.get("media_action", "play_pause"))
    elif action == "lock":
        return pc_controller.lock_workstation()
    elif action == "screenshot":
        return pc_controller.take_screenshot()
    elif action == "shell":
        return pc_controller.execute_shell(params.get("command", ""))
    elif action == "search":
        return pc_controller.search_web(params.get("query", ""))
    return {"error": f"Unknown action: {action}"}

@app.post("/api/code/save")
async def save_code_to_desktop(req: Request):
    try:
        data = await req.json()
        code = data.get("code", "")
        filename = data.get("filename", "").strip()
        folder = data.get("folder", "Jarvis_Generated_Code").strip()
        
        desktop_dir = Path.home() / "Desktop" / folder
        desktop_dir.mkdir(parents=True, exist_ok=True)
        
        if not filename:
            filename = f"script_{int(time.time())}.txt"
            
        file_path = desktop_dir / filename
        file_path.write_text(code, encoding="utf-8")
        
        return {
            "success": True,
            "filename": filename,
            "folder": folder,
            "path": str(file_path),
            "folder_path": str(desktop_dir),
            "message": f"Saved {filename} to Desktop\\{folder}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def auto_save_code_blocks_to_desktop(text: str) -> list:
    """Extracts all multi-line code blocks from Jarvis's response and saves them to Desktop\\Jarvis_Generated_Code."""
    if not text:
        return []
    matches = list(re.finditer(r"```([a-zA-Z0-9_\-\+]*)\n([\s\S]*?)```", text))
    if not matches:
        return []

    saved_files = []
    folder_name = "Jarvis_Generated_Code"
    desktop_dir = Path.home() / "Desktop" / folder_name
    desktop_dir.mkdir(parents=True, exist_ok=True)

    ext_map = {
        "python": "py", "py": "py", "javascript": "js", "js": "js",
        "html": "html", "css": "css", "json": "json", "batch": "bat",
        "bat": "bat", "powershell": "ps1", "ps1": "ps1", "sh": "sh",
        "bash": "sh", "sql": "sql", "typescript": "ts", "ts": "ts"
    }

    for i, m in enumerate(matches):
        lang = (m.group(1) or "").lower().strip()
        code = m.group(2).strip()
        if len(code) < 15:
            continue
        ext = ext_map.get(lang, "txt")
        ts = int(time.time())
        filename = f"code_{ts}_{i+1}.{ext}"
        fpath = desktop_dir / filename
        try:
            fpath.write_text(code, encoding="utf-8")
            saved_files.append({"filename": filename, "folder": folder_name, "path": str(fpath)})
            print(f"[Code Auto-Save] Saved code snippet to: {fpath}", flush=True)
        except Exception as err:
            print(f"[Code Auto-Save Error] {err}", flush=True)
    return saved_files

@app.post("/api/code/open")
async def open_code_folder(req: Request):
    try:
        data = await req.json()
        folder = data.get("folder", "Jarvis_Generated_Code").strip()
        target_dir = Path.home() / "Desktop" / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(target_dir))
        return {"success": True, "path": str(target_dir)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/sandbox/run")
async def run_sandbox_code(req: Request):
    """Executes Python or PowerShell code safely in the local workstation sandbox."""
    try:
        data = await req.json()
        code = data.get("code", "")
        language = data.get("language", "python")
        timeout = int(data.get("timeout", 15))
        save_to_desktop = bool(data.get("save_to_desktop", False))
        filename = data.get("filename")

        res = code_sandbox.run_code(
            code=code,
            language=language,
            timeout=timeout,
            save_to_desktop=save_to_desktop,
            filename=filename
        )

        # Broadcast execution log to HUD terminal drawer
        await broadcast_event({
            "type": "terminal_log",
            "source": "sandbox",
            "language": language,
            "stdout": res.get("stdout", ""),
            "stderr": res.get("stderr", ""),
            "exit_code": res.get("exit_code", 0),
            "duration_ms": res.get("duration_ms", 0.0),
            "success": res.get("success", False)
        })

        return res
    except Exception as e:
        return {"success": False, "error": str(e), "stdout": "", "stderr": str(e), "exit_code": -1}

@app.post("/api/vision/analyze")
async def analyze_screen_vision(req: Request):
    """Performs multimodal vision analysis of Sir Shakil's active display."""
    try:
        data = await req.json()
        directive = data.get("directive")
        mode = data.get("mode", "inspect")
        model = data.get("model", "agy/gemini-3.7-flash-low")

        res = await vision_copilot.analyze_active_screen(directive=directive, mode=mode, model=model)
        return res
    except Exception as e:
        return {"success": False, "error": str(e), "analysis": ""}

@app.post("/api/terminal/exec")
async def execute_terminal_command(req: Request):
    """Executes a direct shell command from the HUD cybernetic terminal drawer."""
    try:
        data = await req.json()
        command = data.get("command", "").strip()
        timeout = int(data.get("timeout", 20))
        if not command:
            return {"success": False, "error": "Empty command"}

        res = pc_controller.execute_shell(command, timeout=timeout)

        # Broadcast to HUD terminal
        await broadcast_event({
            "type": "terminal_log",
            "source": "cli",
            "command": command,
            "stdout": res.get("stdout", ""),
            "stderr": res.get("stderr", ""),
            "exit_code": res.get("exit_code", 0),
            "success": res.get("success", False)
        })

        return res
    except Exception as e:
        return {"success": False, "error": str(e), "stdout": "", "stderr": str(e), "exit_code": -1}

# ==============================================================================
# SPATIAL INTELLIGENCE / GOD'S EYE VIEW ENDPOINTS
# ==============================================================================
@app.post("/api/spatial/command")
async def execute_spatial_command_endpoint(req: Request):
    try:
        data = await req.json()
        tool_name = data.get("tool_name") or data.get("tool") or data.get("command") or data.get("action") or ""
        args = data.get("arguments") or data.get("args") or data.get("params") or data.get("target") or {}
        res = await spatial_service.execute_command(tool_name, args)
        return res
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/api/spatial/state")
async def get_spatial_state_endpoint():
    return spatial_session.to_dict()

@app.get("/api/spatial/health")
async def get_spatial_health_endpoint():
    return spatial_service.get_health()

@app.get("/api/spatial/session")
async def get_spatial_session_endpoint():
    return {
        "session": spatial_session.to_dict(),
        "summary": spatial_session.get_summary_context()
    }

@app.get("/api/spatial/providers")
async def get_spatial_providers_endpoint():
    return {
        "providers": provider_manager.get_all_providers(),
        "health": provider_manager.get_health_summary()
    }

@app.post("/api/spatial/query")
async def post_spatial_query_endpoint(req: Request):
    try:
        data = await req.json()
        category = data.get("category", "entities")
        center_lat = float(data.get("latitude", 20.0))
        center_lon = float(data.get("longitude", 0.0))
        radius_km = float(data.get("radius_km", 50.0))
        entities = data.get("entities", [])
        res = spatial_query_engine.aggregate_and_summarize(
            category=category,
            entities=entities,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km
        )
        return res
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/api/spatial/geojson/validate")
async def validate_geojson_endpoint(req: Request):
    """Validates GeoJSON data server-side before rendering on the globe."""
    try:
        data = await req.json()
        geojson = data.get("geojson", data)

        # Validate structure
        geojson_type = geojson.get("type", "")
        if geojson_type not in ("FeatureCollection", "Feature", "Point", "LineString",
                                "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"):
            return {"ok": False, "error": f"Invalid GeoJSON type: '{geojson_type}'"}

        features = []
        if geojson_type == "FeatureCollection":
            features = geojson.get("features", [])
            if not isinstance(features, list):
                return {"ok": False, "error": "FeatureCollection 'features' must be an array."}
        elif geojson_type == "Feature":
            features = [geojson]
        else:
            features = [{"type": "Feature", "geometry": geojson, "properties": {}}]

        # Validate coordinates
        invalid_features = []
        for i, feature in enumerate(features):
            geom = feature.get("geometry")
            if not geom or not geom.get("type") or not geom.get("coordinates"):
                invalid_features.append({"index": i, "reason": "Missing geometry, type, or coordinates"})

        return {
            "ok": len(invalid_features) == 0,
            "type": geojson_type,
            "feature_count": len(features),
            "invalid_features": invalid_features,
            "valid": len(features) - len(invalid_features),
            "summary": f"GeoJSON validated: {len(features)} features, {len(invalid_features)} invalid."
        }
    except Exception as e:
        return {"ok": False, "error": f"GeoJSON validation failed: {str(e)}"}


# Memory & Evolution Endpoints
@app.get("/api/memory")
async def get_memory():
    return {
        "stats": memory_engine.get_evolution_stats(),
        "facts": memory_engine.get_all_facts(),
        "knowledge": memory_engine.get_all_knowledge(limit=50)
    }

@app.post("/api/memory/fact")
async def add_fact(req: Request):
    data = await req.json()
    return memory_engine.save_fact(
        category=data.get("category", "general"),
        key=data.get("key", ""),
        value=data.get("value", "")
    )

@app.delete("/api/memory/fact/{fact_id}")
async def delete_fact(fact_id: int):
    return memory_engine.delete_fact(fact_id)

@app.post("/api/rag/search")
async def rag_search_endpoint(req: Request):
    data = await req.json()
    query = data.get("query", "").strip()
    return {
        "dialogue": rag_engine.retrieve_relevant_dialogue(query, limit=5),
        "knowledge": rag_engine.retrieve_relevant_knowledge(query, limit=5),
        "facts": rag_engine.retrieve_relevant_facts(query, limit=5),
        "context_block": rag_engine.build_rag_context_block(query)
    }

@app.post("/api/research/trigger")
async def trigger_research(req: Request):
    data = await req.json()
    topic = data.get("topic", "")
    res = await research_engine.conduct_deep_research(topic)
    await broadcast_event({
        "type": "proactive_update",
        "level": "info",
        "text": f"Sir Shakil, I have completed deep research on '{res['topic']}' and integrated a new knowledge node into my vault. Current rating: Evolution Level {res['stats']['level']}.",
        "timestamp": time.time()
    })
    return res

@app.get("/api/antigravity/status")
async def get_antigravity_status():
    available = antigravity_bridge.is_antigravity_available()
    return {
        "installed": available,
        "version": "0.1.16" if available else "1.0",
        "status": "ONLINE",
        "mode": "Antigravity Project Workspace Integrated",
        "requires_api_key": False,
        "tools_count": len(antigravity_bridge.JARVIS_ANTIGRAVITY_TOOLS) if available else 12,
        "active_workspace": "FULL ON SHAKILS ASSISTANT"
    }

@app.post("/api/broadcast")
async def api_broadcast(req: Request):
    data = await req.json()
    text = data.get("text", "")
    level = data.get("level", "info")
    play_speaker = data.get("play_speaker", True)
    tts_res = await voice_engine.synthesize_speech_async(text)
    event = {
        "type": "proactive_update",
        "level": level,
        "text": text,
        "audio_base64": tts_res.get("base64"),
        "timestamp": time.time()
    }
    await broadcast_event(event)
    
    if play_speaker and tts_res.get("filepath"):
        def _play():
            try:
                abs_path = str(Path(tts_res["filepath"]).resolve())
                ps_cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = New-Object -ComObject wmplayer.ocx; $p.URL = \'{abs_path}\'; $p.controls.play(); Start-Sleep -Seconds 6; [System.Runtime.InteropServices.Marshal]::ReleaseComObject($p) | Out-Null"'
                os.system(ps_cmd)
            except Exception:
                pass
        import threading
        threading.Thread(target=_play, daemon=True).start()

    return {"success": True, "event": event}

# OmniRoute Free Model Network Status
@app.get("/api/omniroute/status")
async def get_omniroute_status():
    return omniroute_client.get_omniroute_stats()

# Dedicated Chrome Profile & Email Endpoints
@app.post("/api/browser/launch")
async def launch_browser(req: Request):
    try:
        data = await req.json()
    except Exception:
        data = {}
    target_url = data.get("url", "https://mail.google.com")
    return browser_controller.launch_browser(target_url=target_url)

@app.get("/api/browser/emails")
async def check_emails():
    return await browser_controller.check_emails()

@app.post("/api/browser/email/reply")
async def stage_or_send_reply(req: Request):
    data = await req.json()
    action = data.get("action", "stage")
    if action == "confirm_send":
        return await browser_controller.execute_confirmed_send()
    else:
        return await browser_controller.stage_email_reply(
            recipient=data.get("recipient", ""),
            subject=data.get("subject", ""),
            body_text=data.get("body", "")
        )

# Autonomous Browser Online Research Endpoints
@app.post("/api/browser/search")
async def browser_search(req: Request):
    data = await req.json()
    query = data.get("query", "")
    return await browser_controller.search_web_in_browser(query)

@app.post("/api/browser/browse")
async def browser_browse(req: Request):
    data = await req.json()
    url = data.get("url", "")
    return await browser_controller.browse_url_and_extract(url, keep_tab=data.get("keep_tab", False))

@app.post("/api/browser/research")
async def browser_research(req: Request):
    data = await req.json()
    topic = data.get("topic", "")
    return await research_engine.conduct_deep_research(topic, use_browser=True)

@app.get("/api/browser/screenshot")
async def browser_screenshot():
    return await browser_controller.take_browser_screenshot()

# Eventbrite & Multi-Channel Marketing Endpoints
@app.post("/api/marketing/eventbrite")
async def optimize_eventbrite(req: Request):
    data = await req.json()
    topic = data.get("topic", "AI Mastery Masterclass")
    target_audience = data.get("target_audience", "Entrepreneurs & Creators")
    location = data.get("location", "Online / Global")
    res = await marketing_engine.optimize_eventbrite_listing(topic, target_audience=target_audience, location=location)
    return res.get("data", res)

@app.post("/api/marketing/campaign")
async def generate_campaign(req: Request):
    data = await req.json()
    product_name = data.get("product_name", "Flagship Offer")
    campaign_type = data.get("type", "all")
    target_audience = data.get("target_audience", "High-ticket clients")
    value_prop = data.get("value_prop", "Multiply ROI and scale rapidly")

    results = {}
    if campaign_type in ["email", "all"]:
        r = await marketing_engine.generate_email_campaign(product_name, audience=target_audience, goal=value_prop)
        results["email"] = r.get("data", r)
    if campaign_type in ["sms", "all"]:
        r = await marketing_engine.generate_sms_campaign(product_name, link="https://bit.ly/vip-access")
        results["sms"] = r.get("data", r)
    if campaign_type in ["google", "all"]:
        r = await marketing_engine.generate_google_ads_campaign(product_name, target_url="https://mysite.com")
        results["google_ads"] = r.get("data", r)
    if campaign_type in ["meta", "all"]:
        r = await marketing_engine.generate_meta_ads_campaign(product_name, avatar=target_audience)
        results["meta_ads"] = r.get("data", r)
    return results


# WebSocket for Real-time Telemetry (2Hz)
@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    telemetry_clients.add(websocket)
    try:
        while True:
            data = telemetry.get_telemetry_data()
            data["evolution"] = memory_engine.get_evolution_stats()
            try:
                from core.orchestrator import orchestrator
                data["orchestrator"] = orchestrator.get_diagnostics()
            except Exception:
                pass
            try:
                data["gateway"] = omniroute_client.get_gateway_health()
            except Exception:
                pass
            try:
                data["supervisor"] = proactive_supervisor.get_status()
            except Exception:
                pass
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(0.5)
    except (WebSocketDisconnect, Exception):
        telemetry_clients.discard(websocket)

# Background Memory Extraction and Continuous Learning
async def extract_and_learn(user_text: str):
    try:
        from core import omniroute_client
        from core import memory_engine
        import json
        
        prompt = """Analyze this message from Sir Shakil. Extract any new, permanent facts, goals, or preferences about him that should be saved to long-term memory.
User Message: "{}"
If a clear new fact is present, reply with EXACTLY ONE line of JSON: {{"category": "preference|goal|fact", "key": "Brief Key", "value": "Detailed fact"}}
If no new facts, reply with EXACTLY: {{"none": true}}
Do not write anything else.""".format(user_text.replace('"', "'"))
        
        result = ""
        async for chunk in omniroute_client.stream_omniroute_agent(prompt, system_instruction="You are a JSON memory extractor.", preferred_model="auto/fast"):
            if chunk["type"] == "response":
                result = chunk["text"]
        
        if result:
            try:
                clean_json = result.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                if not data.get("none") and "key" in data and "value" in data:
                    cat = data.get("category", "fact")
                    memory_engine.save_fact(cat, data["key"], data["value"])
                    print(f"[Continuous Learning] Assumed new fact: {data['key']} = {data['value']}")
            except Exception:
                pass
    except Exception:
        pass

async def dispatch_tts(websocket: Optional[WebSocket], text: str, play_speaker: bool, turn_id: Optional[int] = None):
    try:
        # Check turn validity before expensive synthesis
        if turn_id is not None and not conversation_controller.is_turn_current(turn_id):
            return

        tts_res = await voice_engine.synthesize_speech_async(text, voice=voice_engine.DEFAULT_VOICE)
        
        # Check turn validity again after synthesis
        if turn_id is not None and not conversation_controller.is_turn_current(turn_id):
            return

        filepath = tts_res.get("filepath")
        est_duration = tts_res.get("duration", voice_engine.get_audio_duration_estimate(text))
        
        await conversation_controller.set_state(ConversationState.SPEAKING, f"SPEAKING (Turn #{turn_id})")

        # STRICT CHANNEL EXCLUSIVITY:
        if play_speaker:
            # 1. Play directly on Windows audio output (Speakers / Headset)
            if filepath and os.path.exists(filepath):
                voice_engine.play_audio_file_on_speakers(filepath)
                last_speech_cache["filepath"] = filepath
            
            # 2. Inform HUD of speaking status, but do NOT send audio_base64 to prevent browser echo!
            target_ws_list = [websocket] if websocket else list(chat_clients)
            for ws in target_ws_list:
                if ws:
                    try:
                        await ws.send_text(json.dumps({
                            "type": "status",
                            "status": "speaking",
                            "duration": est_duration,
                            "text": text,
                            "turn_id": turn_id
                        }))
                    except Exception:
                        pass
        else:
            # Browser HTML5 audio mode:
            # 1. Do NOT play on PC hardware speakers
            # 2. Send audio_base64 to HUD websocket for browser playback
            target_ws_list = [websocket] if websocket else list(chat_clients)
            for ws in target_ws_list:
                if ws:
                    try:
                        await ws.send_text(json.dumps({
                            "type": "audio",
                            "audio_base64": tts_res.get("base64"),
                            "mime": "audio/wav",
                            "duration": est_duration,
                            "text": text,
                            "turn_id": turn_id
                        }))
                    except Exception:
                        pass
    except Exception as e:
        print(f"[TTS Dispatch Error] {e}")

# WebSocket for Interactive Voice/Chat

async def execute_turn_pipeline(
    turn_id: int,
    prompt: str,
    source: str = "native",
    voice_enabled: bool = True,
    play_speaker: bool = False,
    model: Optional[str] = None,
    history: Optional[list] = None,
    workspace: str = "personal"
):
    try:
        # Pause microphone input while speaking to prevent self-trigger echo
        native_stt.pause_listening()

        # Broadcast user prompt to all HUD clients so chat shows the transcript
        for ws in list(chat_clients):
            try:
                await ws.send_text(json.dumps({
                    "type": "user_speech",
                    "text": prompt,
                    "turn_id": turn_id,
                    "workspace": workspace
                }))
            except Exception:
                pass

        selected_model = model or "auto/best-fast"
        if not history:
            history = rag_engine.get_recent_history(limit=8, workspace=workspace)
        elif len(history) > 12:
            history = history[-12:]

        full_response = ""
        tts_buffer = ""
        in_code_block = False

        await conversation_controller.set_state(ConversationState.THINKING, "PROCESSING DIRECTIVE")

        async for event in ai_brain.process_user_message(prompt, history=history, model=selected_model, workspace=workspace):
            # Check turn_id validity: if superseded or aborted, exit immediately!
            if turn_id != conversation_controller.current_turn_id:
                print(f"[Pipeline] Turn #{turn_id} superseded by #{conversation_controller.current_turn_id}. Exiting.", flush=True)
                return

            event["turn_id"] = turn_id
            for ws in list(chat_clients):
                try:
                    await ws.send_text(json.dumps(event))
                except Exception:
                    pass

            if event.get("type") == "chunk":
                chunk_text = event.get("content", "")
                full_response += chunk_text

                if "```" in chunk_text:
                    in_code_block = not in_code_block

                # Streaming TTS sentence chunking
                if voice_enabled and not in_code_block and "```" not in full_response:
                    tts_buffer += chunk_text
                    match = re.search(r'(?<=[.!?\n])\s+', tts_buffer)
                    while match:
                        split_idx = match.end()
                        sentence = tts_buffer[:split_idx].strip()
                        tts_buffer = tts_buffer[split_idx:]
                        clean_sentence = voice_engine.clean_text_for_speech(sentence)
                        if len(clean_sentence) > 2:
                            asyncio.create_task(dispatch_tts(None, clean_sentence, play_speaker, turn_id=turn_id))
                        match = re.search(r'(?<=[.!?\n])\s+', tts_buffer)

            elif event.get("type") == "response":
                full_response = event.get("text", "")

        # Check turn_id validity before finalizing
        if turn_id != conversation_controller.current_turn_id:
            return

        # Speak remainder or concise summary
        if voice_enabled:
            if "```" in full_response:
                clean_speech = voice_engine.clean_text_for_speech(voice_engine.get_spoken_summary(full_response))
                if len(clean_speech) > 2:
                    await dispatch_tts(None, clean_speech, play_speaker, turn_id=turn_id)
            else:
                clean_remainder = voice_engine.clean_text_for_speech(tts_buffer)
                if len(clean_remainder) > 2:
                    await dispatch_tts(None, clean_remainder, play_speaker, turn_id=turn_id)
                elif full_response and not tts_buffer:
                    clean_speech = voice_engine.clean_text_for_speech(voice_engine.get_spoken_summary(full_response))
                    if len(clean_speech) > 2:
                        await dispatch_tts(None, clean_speech, play_speaker, turn_id=turn_id)

        saved_files = []
        if full_response and "```" in full_response:
            saved_files = auto_save_code_blocks_to_desktop(full_response)

        if prompt and full_response:
            rag_engine.log_conversation("user", prompt, model=selected_model, workspace=workspace)
            rag_engine.log_conversation("assistant", full_response, model=selected_model, workspace=workspace)
            
            # Auto-distill session summaries every 20 conversation turns (Mark XVII Memory)
            turn_count = rag_engine.get_conversation_turn_count(workspace=workspace)
            if turn_count > 0 and turn_count % 20 == 0:
                asyncio.create_task(rag_engine.auto_distill_session(workspace=workspace))

        for ws in list(chat_clients):
            try:
                await ws.send_text(json.dumps({
                    "type": "response",
                    "text": full_response,
                    "saved_files": saved_files,
                    "turn_id": turn_id,
                    "workspace": workspace
                }))
            except Exception:
                pass

        # Background continuous memory extraction
        asyncio.create_task(extract_and_learn(prompt))

    except asyncio.CancelledError:
        print(f"[Pipeline] Turn #{turn_id} cancelled.")
        raise
    except Exception as e:
        print(f"[Pipeline Error on Turn #{turn_id}] {e}")
    finally:
        # Re-arm microphone when turn finishes
        if turn_id == conversation_controller.current_turn_id:
            native_stt.resume_listening()
            await conversation_controller.set_state(ConversationState.IDLE, "READY FOR SIR SHAKIL")

def on_native_speech(text):
    global MAIN_SERVER_LOOP
    text = (text or "").strip()
    if not text:
        return
    print(f"\n[JARVIS EARS NATIVE] Heard: '{text}'", flush=True)

    if not MAIN_SERVER_LOOP or not MAIN_SERVER_LOOP.is_running():
        print("[!] Server loop not ready yet, skipping native speech dispatch", flush=True)
        return

    async def _handle():
        await conversation_controller.handle_user_prompt(
            prompt=text,
            source="native",
            voice_enabled=True,
            play_speaker=True,
            process_callback=execute_turn_pipeline
        )

    asyncio.run_coroutine_threadsafe(_handle(), MAIN_SERVER_LOOP)

# ==============================================================================
# FAMILY SAFETY & DEVICE REGISTRY ENDPOINTS (STANDARDIZED ACTION CONTRACT)
# ==============================================================================

def make_api_response(ok: bool = True, executed: bool = True, simulated: bool = False,
                      command_id: Optional[str] = None, error_code: Optional[str] = None,
                      message: str = "", data: Any = None):
    res = {
        "ok": ok,
        "executed": executed,
        "simulated": simulated,
        "commandId": command_id or f"cmd_{int(time.time()*1000)}",
        "errorCode": error_code,
        "message": message,
        "data": data if data is not None else {},
        "success": ok  # Backwards compatibility
    }
    if isinstance(data, dict):
        for k, v in data.items():
            if k not in res:
                res[k] = v
    if not ok and error_code:
        res["error"] = message or error_code
    return res

# SECURITY: Until a verified authentication system is in place, all mutating
# family-safety operations derive the actor identity from a fixed server-side
# constant. The request body 'actorId' is IGNORED for authorization decisions.
# This prevents clients from impersonating users by submitting arbitrary IDs.
SERVER_AUTHORIZED_ACTOR = "shakil"

def _get_verified_actor(data: dict) -> str:
    """Return the server-verified actor identity.
    
    Currently returns the fixed server-side owner identity.
    When real authentication is implemented, this should derive
    the identity from the verified session/token instead.
    
    The client-provided actorId is logged but NOT used for authorization.
    """
    client_claimed = data.get("actorId") or data.get("actor_id")
    if client_claimed and client_claimed != SERVER_AUTHORIZED_ACTOR:
        print(f"[SECURITY] Client claimed actorId='{client_claimed}' — overridden by server identity '{SERVER_AUTHORIZED_ACTOR}'", flush=True)
    return SERVER_AUTHORIZED_ACTOR

@app.get("/api/family/devices")
async def list_family_devices(owner_profile_id: Optional[str] = None):
    devices = device_registry.list_devices(owner_profile_id)
    normalized = []
    for d in devices:
        # Extract real battery level — never fabricate
        caps = d.get("capabilities") if isinstance(d.get("capabilities"), dict) else {}
        raw_battery = caps.get("batteryLevel") if caps else None
        # Extract real connection info — never fabricate
        conn = d.get("lastKnownConnection") if isinstance(d.get("lastKnownConnection"), dict) else {}
        raw_ip = conn.get("ip") if conn else None
        # Extract real timestamps — never fabricate
        raw_last_seen = d.get("lastSeenAt") or d.get("last_seen_at")
        # Determine data quality
        has_telemetry = raw_battery is not None or raw_last_seen is not None or raw_ip is not None
        data_quality = "live" if has_telemetry else "unknown"

        item = {
            "id": d.get("deviceId") or d.get("device_id"),
            "deviceId": d.get("deviceId") or d.get("device_id"),
            "device_id": d.get("deviceId") or d.get("device_id"),
            "displayName": d.get("displayName") or d.get("display_name", "Unknown Device"),
            "display_name": d.get("displayName") or d.get("display_name", "Unknown Device"),
            "device_name": d.get("displayName") or d.get("display_name", "Unknown Device"),
            "name": d.get("displayName") or d.get("display_name", "Unknown Device"),
            "ownerProfileId": d.get("ownerProfileId") or d.get("owner_profile_id"),
            "ownerId": d.get("ownerProfileId") or d.get("owner_profile_id"),
            "member_name": d.get("ownerProfileId") or d.get("owner_profile_id"),
            "deviceType": d.get("deviceType") or d.get("device_type", "phone"),
            "device_type": d.get("deviceType") or d.get("device_type", "phone"),
            "platform": d.get("platform", "android"),
            "enrollmentStatus": d.get("enrollmentStatus") or d.get("enrollment_status", "pending_pairing"),
            "enrollment_status": d.get("enrollmentStatus") or d.get("enrollment_status", "pending_pairing"),
            "status": (d.get("enrollmentStatus") or d.get("enrollment_status", "PENDING")).upper(),
            "consentStatus": d.get("consentStatus") or d.get("consent_status", "pending_review"),
            "consent_status": d.get("consentStatus") or d.get("consent_status", "pending_review"),
            "locationPermission": d.get("locationPermission") or d.get("location_permission", "none"),
            "location_permission": d.get("locationPermission") or d.get("location_permission", "none"),
            "lastSeenAt": raw_last_seen,
            "last_seen_at": raw_last_seen,
            "batteryLevel": raw_battery,
            "battery_level": raw_battery,
            "ip_address": raw_ip,
            "location": d.get("location"),
            "dataQuality": data_quality,
            "data_quality": data_quality
        }
        normalized.append(item)
    return make_api_response(
        ok=True,
        executed=True,
        simulated=False,
        message=f"Retrieved {len(normalized)} registered family device(s)",
        data={"devices": normalized, "count": len(normalized)}
    )

@app.post("/api/family/devices/pair/init")
async def init_device_pairing(req: Request):
    data = {}
    if req.headers.get("content-type") == "application/json":
        try:
            data = await req.json()
        except Exception:
            pass
    owner_id = data.get("ownerProfileId") or data.get("owner_profile_id") or "shakil"
    display_name = data.get("displayName") or data.get("display_name") or data.get("device_name") or "Personal Phone Companion"
    device_type = data.get("deviceType") or data.get("device_type") or "phone"
    platform = data.get("platform", "android")
    ttl = int(data.get("ttlSeconds") or data.get("ttl_seconds") or 600)

    res = device_registry.generate_pairing_code(
        owner_profile_id=owner_id,
        display_name=display_name,
        device_type=device_type,
        platform=platform,
        ttl_seconds=ttl
    )

    if res.get("success"):
        res_data = {
            "deviceId": res["deviceId"],
            "device_id": res["deviceId"],
            "pairingCode": res["pairingCode"],
            "pairing_code": res["pairingCode"],
            "expiresAt": res["expiresAt"],
            "expires_at": res["expiresAt"],
            "expiresInSeconds": res["expiresInSeconds"],
            "expires_in_seconds": res["expiresInSeconds"],
            "displayName": res["displayName"],
            "display_name": res["displayName"]
        }
        return make_api_response(
            ok=True,
            executed=True,
            simulated=False,
            message=f"Pairing code generated for '{display_name}'. Valid for {ttl}s.",
            data=res_data
        )
    return make_api_response(
        ok=False,
        executed=False,
        simulated=False,
        error_code="PAIRING_INIT_FAILED",
        message=res.get("error", "Failed to initiate pairing")
    )

@app.post("/api/family/devices/pair/complete")
async def complete_device_pairing(req: Request):
    data = {}
    if req.headers.get("content-type") == "application/json":
        try:
            data = await req.json()
        except Exception:
            pass
    device_id = data.get("deviceId") or data.get("device_id")
    pairing_code = data.get("pairingCode") or data.get("pairing_code", "")
    capabilities = data.get("capabilities", {})
    client_ip = req.client.host if req.client else "127.0.0.1"

    if not pairing_code:
        return make_api_response(
            ok=False,
            executed=False,
            simulated=False,
            error_code="MISSING_PARAMETERS",
            message="Both deviceId and pairingCode are required."
        )

    res = device_registry.complete_pairing(
        device_id=device_id,
        pairing_code=pairing_code,
        device_capabilities=capabilities,
        ip_address=client_ip
    )

    if res.get("success"):
        return make_api_response(
            ok=True,
            executed=True,
            simulated=False,
            message=f"Device '{res.get('displayName')}' successfully paired and enrolled.",
            data=res
        )
    return make_api_response(
        ok=False,
        executed=False,
        simulated=False,
        error_code="PAIRING_FAILED",
        message=res.get("error", "Pairing validation failed.")
    )

@app.put("/api/family/devices/{device_id}/permissions")
async def update_device_permissions_endpoint(device_id: str, req: Request):
    data = await req.json()
    actor_id = _get_verified_actor(data)
    location_perm = data.get("locationPermission", "none")
    consent_stat = data.get("consentStatus")
    res = device_registry.update_device_permissions(
        device_id=device_id,
        actor_id=actor_id,
        location_permission=location_perm,
        consent_status=consent_stat
    )
    if res.get("success"):
        return make_api_response(ok=True, executed=True, message="Device permissions updated", data=res)
    return make_api_response(ok=False, executed=False, error_code="PERMISSION_UPDATE_FAILED", message=res.get("error", "Failed"))

@app.post("/api/family/devices/{device_id}/revoke")
@app.post("/api/family/devices/revoke")
async def revoke_device_endpoint(device_id: Optional[str] = None, req: Request = None):
    data = {}
    if req and req.headers.get("content-type") == "application/json":
        try:
            data = await req.json()
        except Exception:
            pass
    target_id = device_id or data.get("deviceId") or data.get("device_id")
    if not target_id:
        return make_api_response(ok=False, executed=False, error_code="MISSING_DEVICE_ID", message="device_id is required")
    actor_id = _get_verified_actor(data)
    reason = data.get("reason", "Revoked via J.A.R.V.I.S. HUD")
    res = device_registry.revoke_device(device_id=target_id, actor_id=actor_id, reason=reason)
    if res.get("success"):
        return make_api_response(ok=True, executed=True, message=f"Device '{target_id}' revoked.", data=res)
    return make_api_response(ok=False, executed=False, error_code="REVOKE_FAILED", message=res.get("error", "Revocation failed"))

@app.delete("/api/family/devices/{device_id}")
async def remove_device_endpoint(device_id: str, req: Request):
    actor_id = SERVER_AUTHORIZED_ACTOR
    res = device_registry.remove_device(device_id=device_id, actor_id=actor_id)
    if res.get("success"):
        return make_api_response(ok=True, executed=True, message=f"Device '{device_id}' removed.", data=res)
    return make_api_response(ok=False, executed=False, error_code="REMOVE_FAILED", message=res.get("error", "Remove failed"))

@app.post("/api/family/discovery/scan")
@app.post("/api/family/network/scan")
async def scan_local_network_endpoint():
    res = network_discovery.scan_local_network()
    nodes = res.get("discoveredNodes") or res.get("discovered_nodes") or []
    return make_api_response(
        ok=True,
        executed=True,
        simulated=False,
        message=f"Subnet scan completed. Discovered {len(nodes)} active LAN device(s).",
        data={"discoveredNodes": nodes, "discovered_nodes": nodes, "count": len(nodes)}
    )

@app.get("/api/family/consent")
async def list_family_consents():
    consents = consent_manager.list_consents()
    return make_api_response(ok=True, executed=True, message="Retrieved consents", data={"consents": consents, "count": len(consents)})

@app.get("/api/family/consent/{participant_id}")
async def get_participant_consent(participant_id: str):
    res = consent_manager.get_or_create_consent(participant_id, owner_profile_id=participant_id)
    return make_api_response(ok=True, executed=True, data={"consent": res})

@app.put("/api/family/consent/{participant_id}")
async def update_participant_consent(participant_id: str, req: Request):
    data = await req.json()
    actor_id = _get_verified_actor(data)
    permissions = data.get("permissions", {})
    res = consent_manager.update_consent(participant_id, actor_id=actor_id, permissions=permissions)
    if res.get("success"):
        return make_api_response(ok=True, executed=True, message="Consent updated", data=res)
    return make_api_response(ok=False, executed=False, error_code="CONSENT_UPDATE_FAILED", message=res.get("error", "Failed"))

@app.post("/api/family/consent/kill_switch")
@app.post("/api/family/consent/pause_all")
async def pause_all_family_sharing(req: Request):
    data = {}
    if req.headers.get("content-type") == "application/json":
        try:
            data = await req.json()
        except Exception:
            pass
    actor_id = _get_verified_actor(data)
    res = consent_manager.pause_all_sharing(actor_id=actor_id)
    return make_api_response(
        ok=True,
        executed=True,
        simulated=False,
        message=res.get("message", "Master location kill switch executed. All sharing revoked and paused."),
        data={**res, "status": "REVOKED"}
    )

@app.delete("/api/family/consent/{participant_id}/history")
async def purge_participant_history(participant_id: str, req: Request):
    actor_id = SERVER_AUTHORIZED_ACTOR
    res = consent_manager.delete_participant_history(participant_id, actor_id=actor_id)
    return make_api_response(ok=True, executed=True, message="Location history purged.", data=res)

@app.post("/api/family/signals")
async def ingest_safety_signal_endpoint(req: Request):
    data = await req.json()
    participant_id = data.get("participantId") or data.get("participant_id")
    signal_type = data.get("signalType") or data.get("signal_type")
    raw_data = data.get("rawData") or data.get("raw_data", {})
    source = data.get("source", "telemetry")
    confidence = float(data.get("confidence", 1.0))
    location = data.get("location")
    res = safety_signal_engine.ingest_signal(
        participant_id=participant_id,
        signal_type=signal_type,
        raw_data=raw_data,
        source=source,
        confidence=confidence,
        location=location
    )
    return make_api_response(ok=True, executed=True, message="Signal ingested", data=res)

@app.get("/api/family/alerts")
async def list_safety_alerts(participant_id: Optional[str] = None):
    raw_alerts = safety_alert_engine.list_active_alerts(participant_id)
    normalized = []
    for a in raw_alerts:
        normalized.append({
            "id": a.get("alertId") or a.get("alert_id"),
            "alertId": a.get("alertId") or a.get("alert_id"),
            "alert_id": a.get("alertId") or a.get("alert_id"),
            "participantId": a.get("participantId") or a.get("participant_id", "shakil"),
            "participant_id": a.get("participantId") or a.get("participant_id", "shakil"),
            "alertType": a.get("alertType") or a.get("alert_type", "safety_signal"),
            "alert_type": a.get("alertType") or a.get("alert_type", "safety_signal"),
            "type": a.get("alertType") or a.get("alert_type", "safety_signal"),
            "severity": (a.get("severity") or "LOW").upper(),
            "triggeredAt": a.get("triggeredAt") or a.get("triggered_at"),
            "triggered_at": a.get("triggeredAt") or a.get("triggered_at"),
            "createdAt": a.get("triggeredAt") or a.get("triggered_at"),
            "created_at": a.get("triggeredAt") or a.get("triggered_at"),
            "evidence": a.get("evidence", ""),
            "message": a.get("evidence") or a.get("alert_type", "Safety Alert"),
            "title": a.get("alert_type", "Safety Alert").replace("_", " ").upper(),
            "source": a.get("source", "SafetySignalEngine"),
            "confidence": a.get("confidence", 1.0),
            "isTest": bool("[TEST ALERT]" in str(a.get("evidence", "")) or a.get("isTest")),
            "status": "ACTIVE" if not a.get("is_dismissed") else "DISMISSED",
            "recommendedAction": a.get("recommendedAction") or a.get("recommended_action", "Review status")
        })
    return make_api_response(
        ok=True,
        executed=True,
        simulated=False,
        message=f"Retrieved {len(normalized)} active safety alert(s)",
        data={"alerts": normalized, "count": len(normalized)}
    )

@app.post("/api/family/alerts/test")
@app.post("/api/family/alerts/manual")
async def create_manual_test_alert(req: Request):
    data = {}
    if req.headers.get("content-type") == "application/json":
        try:
            data = await req.json()
        except Exception:
            pass
    severity = data.get("severity", "HIGH").upper()
    user_msg = data.get("message") or "Manual test alert triggered from J.A.R.V.I.S. HUD"
    evidence_text = f"[TEST ALERT] {user_msg}"
    res = safety_alert_engine.trigger_manual_alert(
        participant_id=data.get("participantId") or data.get("participant_id") or "shakil",
        alert_type="manual_test_alert",
        severity=severity,
        evidence=evidence_text,
        recommended_action="Verification test. No emergency response required."
    )
    if res.get("success"):
        alert_info = res.get("alert", {})
        alert_id = alert_info.get("alertId") or alert_info.get("alert_id")
        res_data = {
            "alertId": alert_id,
            "alert_id": alert_id,
            "alert": alert_info,
            "success": True
        }
        return make_api_response(
            ok=True,
            executed=True,
            simulated=False,
            message=f"Test alert dispatched with severity {severity}.",
            data=res_data
        )
    return make_api_response(ok=False, executed=False, error_code="ALERT_DISPATCH_FAILED", message="Failed to create test alert")

@app.post("/api/family/alerts/{alert_id}/dismiss")
@app.post("/api/family/alerts/dismiss")
async def dismiss_safety_alert_endpoint(alert_id: Optional[str] = None, req: Request = None):
    data = {}
    if req and req.headers.get("content-type") == "application/json":
        try:
            data = await req.json()
        except Exception:
            pass
    target_id = alert_id or data.get("alertId") or data.get("alert_id")
    if not target_id:
        return make_api_response(ok=False, executed=False, error_code="MISSING_ALERT_ID", message="alert_id required")
    actor_id = _get_verified_actor(data)
    res = safety_alert_engine.dismiss_alert(target_id, actor_id=actor_id)
    if res.get("success"):
        return make_api_response(ok=True, executed=True, message=f"Alert '{target_id}' dismissed.", data=res)
    return make_api_response(ok=False, executed=False, error_code="DISMISS_FAILED", message=res.get("error", "Failed to dismiss alert"))

@app.post("/api/family/checkins")
@app.post("/api/family/checkin/respond")
async def respond_checkin_direct(req: Request):
    data = await req.json() if req.headers.get("content-type") == "application/json" else {}
    part_id = data.get("participantId") or data.get("participant_id") or "shakil"
    status_raw = data.get("status") or data.get("responseType") or data.get("response_type") or "safe"
    note = data.get("note") or data.get("notes")
    
    chk_id = data.get("checkInId") or data.get("checkin_id")
    if chk_id:
        res = checkin_manager.respond_checkin(checkin_id=chk_id, response_type=status_raw, notes=note)
    else:
        res = checkin_manager.record_direct_checkin(participant_id=part_id, response_type=status_raw, notes=note)

    if res.get("success"):
        return make_api_response(
            ok=True,
            executed=True,
            simulated=False,
            message=res.get("message", "Check-in recorded."),
            data=res
        )
    return make_api_response(ok=False, executed=False, error_code="CHECKIN_FAILED", message=res.get("error", "Check-in failed."))

@app.post("/api/family/checkins/schedule")
@app.post("/api/family/checkin/schedule")
async def schedule_checkin_endpoint(req: Request):
    data = await req.json() if req.headers.get("content-type") == "application/json" else {}
    part_id = data.get("participantId") or data.get("participant_id") or "shakil"
    mins = int(data.get("intervalMinutes") or data.get("interval_minutes") or 60)
    scheduled_at = float(data.get("scheduledAt") or data.get("scheduled_at") or (time.time() + mins * 60))
    grace_mins = int(data.get("gracePeriodMinutes") or data.get("grace_period_minutes") or 15)
    note = data.get("notes") or data.get("note")
    
    res = checkin_manager.schedule_checkin(
        participant_id=part_id,
        scheduled_at=scheduled_at,
        grace_period_minutes=grace_mins,
        notes=note
    )
    if res.get("success"):
        return make_api_response(
            ok=True,
            executed=True,
            simulated=False,
            message=f"Check-in scheduled in {mins} minutes.",
            data=res
        )
    return make_api_response(ok=False, executed=False, error_code="SCHEDULE_FAILED", message="Failed to schedule check-in")

@app.get("/api/family/checkins/status")
@app.get("/api/family/checkin/status")
async def get_checkin_status_endpoint(participant_id: Optional[str] = None):
    res = checkin_manager.get_status(participant_id)
    return make_api_response(
        ok=True,
        executed=True,
        simulated=False,
        message="Check-in status retrieved",
        data=res
    )

@app.get("/api/family/checkin/evaluate")
async def evaluate_checkins_endpoint():
    missed = checkin_manager.evaluate_pending_checkins()
    return make_api_response(ok=True, executed=True, data={"missedCount": len(missed), "missed": missed})

# ==============================================================================
# REMOTE COMPANION, AUTH, TASKS & TELEPHONY ENDPOINTS (STANDARDIZED)
# ==============================================================================

@app.post("/api/remote/auth/login")
async def remote_login(req: Request):
    data = await req.json()
    user_id = data.get("userId", "shakil")
    device_id = data.get("deviceId", "mobile_companion")
    role = data.get("role", "family_admin")
    client_ip = req.client.host if req.client else "127.0.0.1"
    
    if not remote_auth.check_rate_limit(client_ip):
        return make_api_response(ok=False, executed=False, error_code="RATE_LIMIT_EXCEEDED", message="Too many login attempts. Try again in 15 minutes.")

    res = remote_auth.create_session(
        user_id=user_id,
        device_id=device_id,
        role=role,
        ip_address=client_ip,
        user_agent=req.headers.get("user-agent")
    )
    return make_api_response(ok=True, executed=True, message="Session authenticated", data=res)

@app.post("/api/remote/auth/revoke")
async def remote_revoke_session(req: Request):
    data = await req.json()
    session_id = data.get("sessionId")
    actor_id = _get_verified_actor(data)
    res = remote_auth.revoke_session(session_id, actor_id=actor_id)
    return make_api_response(ok=True, executed=True, message="Session revoked", data=res)

@app.post("/api/remote/auth/revoke_all")
async def remote_revoke_all_sessions(req: Request):
    data = await req.json()
    user_id = data.get("userId", "shakil")
    actor_id = _get_verified_actor(data)
    res = remote_auth.revoke_all_user_sessions(user_id, actor_id=actor_id)
    return make_api_response(ok=True, executed=True, message="All sessions revoked", data=res)

@app.post("/api/remote/command")
async def execute_remote_command_endpoint(req: Request):
    auth_header = req.headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else None
    
    data = await req.json()
    user_id = data.get("userId", "shakil")
    role = data.get("role", "family_admin")

    if token:
        sess = remote_auth.validate_session(token)
        if not sess:
            return make_api_response(ok=False, executed=False, error_code="UNAUTHORIZED", message="Invalid or expired authorization token.")
        user_id = sess.get("sub", user_id)
        role = sess.get("role", role)

    command_text = data.get("command", "")
    conf_token = data.get("confirmationToken")
    confirmed = bool(data.get("confirmed", False))
    client_ip = req.client.host if req.client else None

    res = remote_command_gateway.execute_remote_command(
        user_id=user_id,
        command_text=command_text,
        role=role,
        confirmation_token=conf_token,
        confirmed=confirmed,
        source_channel=data.get("channel", "mobile_app"),
        ip_address=client_ip
    )
    return make_api_response(ok=res.get("success", False), executed=res.get("executed", False), simulated=False, message=res.get("message", "Command evaluated"), data=res)

@app.get("/api/remote/tasks")
async def list_remote_tasks(owner_id: Optional[str] = None):
    raw_tasks = persistent_task_manager.list_tasks(owner_id)
    normalized = []
    for t in raw_tasks:
        normalized.append({
            "id": t.get("taskId") or t.get("task_id"),
            "taskId": t.get("taskId") or t.get("task_id"),
            "task_id": t.get("taskId") or t.get("task_id"),
            "name": t.get("title", "Background Task"),
            "title": t.get("title", "Background Task"),
            "description": t.get("description", ""),
            "status": (t.get("status") or "QUEUED").upper(),
            "progress": float(t.get("progress", 0.0)),
            "progress_pct": int(float(t.get("progress", 0.0))),
            "priority": int(t.get("priority", 1)),
            "createdAt": t.get("createdAt") or t.get("created_at", time.time()),
            "updatedAt": t.get("updatedAt") or t.get("updated_at", time.time())
        })
    return make_api_response(
        ok=True,
        executed=True,
        simulated=False,
        message=f"Retrieved {len(normalized)} task(s)",
        data={"tasks": normalized, "count": len(normalized)}
    )

@app.post("/api/remote/tasks/create")
async def create_remote_task_endpoint(req: Request):
    data = await req.json()
    res = persistent_task_manager.create_task(
        owner_id=data.get("ownerId", "shakil"),
        title=data.get("title", "Background Task"),
        description=data.get("description", ""),
        priority=int(data.get("priority", 1)),
        schedule=data.get("schedule")
    )
    if res.get("success"):
        task_info = res.get("task", {})
        task_id = task_info.get("taskId") or task_info.get("task_id")
        res_data = {
            "taskId": task_id,
            "task_id": task_id,
            "task": task_info,
            "success": True
        }
        return make_api_response(ok=True, executed=True, message=f"Task '{task_id}' created", data=res_data)
    return make_api_response(ok=False, executed=False, error_code="TASK_CREATE_FAILED", message=res.get("error", "Failed to create task"))

@app.post("/api/remote/tasks/{task_id}/pause")
@app.post("/api/remote/tasks/pause")
async def pause_remote_task(task_id: Optional[str] = None, req: Request = None):
    data = {}
    if req and req.headers.get("content-type") == "application/json":
        try:
            data = await req.json()
        except Exception:
            pass
    target_id = task_id or data.get("taskId") or data.get("task_id")
    if not target_id:
        return make_api_response(ok=False, executed=False, error_code="MISSING_TASK_ID", message="task_id required")
    res = persistent_task_manager.pause_task(target_id)
    if res.get("success"):
        return make_api_response(ok=True, executed=True, message=f"Task '{target_id}' paused.", data=res)
    return make_api_response(ok=False, executed=False, error_code="PAUSE_FAILED", message=res.get("error", "Failed to pause task"))

@app.post("/api/remote/tasks/{task_id}/resume")
@app.post("/api/remote/tasks/resume")
async def resume_remote_task(task_id: Optional[str] = None, req: Request = None):
    data = {}
    if req and req.headers.get("content-type") == "application/json":
        try:
            data = await req.json()
        except Exception:
            pass
    target_id = task_id or data.get("taskId") or data.get("task_id")
    if not target_id:
        return make_api_response(ok=False, executed=False, error_code="MISSING_TASK_ID", message="task_id required")
    res = persistent_task_manager.resume_task(target_id)
    if res.get("success"):
        return make_api_response(ok=True, executed=True, message=f"Task '{target_id}' resumed.", data=res)
    return make_api_response(ok=False, executed=False, error_code="RESUME_FAILED", message=res.get("error", "Failed to resume task"))

@app.post("/api/remote/tasks/{task_id}/cancel")
@app.post("/api/remote/tasks/cancel")
async def cancel_remote_task(task_id: Optional[str] = None, req: Request = None):
    data = {}
    if req and req.headers.get("content-type") == "application/json":
        try:
            data = await req.json()
        except Exception:
            pass
    target_id = task_id or data.get("taskId") or data.get("task_id")
    if not target_id:
        return make_api_response(ok=False, executed=False, error_code="MISSING_TASK_ID", message="task_id required")
    res = persistent_task_manager.cancel_task(target_id)
    if res.get("success"):
        return make_api_response(ok=True, executed=True, message=f"Task '{target_id}' canceled.", data=res)
    return make_api_response(ok=False, executed=False, error_code="CANCEL_FAILED", message=res.get("error", "Failed to cancel task"))

@app.get("/api/remote/health")
@app.get("/api/remote/reliability")
async def get_system_reliability_endpoint():
    res = reliability_monitor.get_system_health()
    return make_api_response(
        ok=True,
        executed=True,
        simulated=False,
        message="System reliability telemetry retrieved",
        data=res
    )

@app.post("/api/remote/telephony/call")
async def telephony_call_endpoint(req: Request):
    data = await req.json()
    caller = data.get("callerNumber", "")
    pin = data.get("callerPin")
    res = telephony_gateway.handle_incoming_call(caller, caller_pin=pin)
    return make_api_response(ok=res.get("authenticated", False), executed=True, message="Telephony call processed", data=res)

@app.post("/api/remote/telephony/command")
async def telephony_command_endpoint(req: Request):
    data = await req.json()
    token = data.get("sessionToken", "")
    transcript = data.get("transcript", "")
    res = telephony_gateway.process_voice_call_command(token, transcript)
    return make_api_response(ok=res.get("success", False), executed=True, message="Telephony voice directive processed", data=res)

@app.get("/api/family/spatial/layers")
async def get_family_spatial_layers():
    """Generates privacy-filtered spatial overlay layers for God's Eye View."""
    devices = device_registry.list_devices()
    features = []
    now = time.time()

    for d in devices:
        participant_id = d["ownerProfileId"]
        # Check if live or history sharing is enabled in consent
        if not consent_manager.check_permission(participant_id, "locationSharingEnabled"):
            continue

        loc = family_storage.get_latest_location(participant_id)
        if not loc:
            continue

        age_seconds = now - loc["recorded_at"]
        freshness = "LIVE" if age_seconds < 120 else ("LAST KNOWN" if age_seconds < 3600 else "STALE")
        if d["enrollmentStatus"] == "revoked":
            freshness = "PERMISSION REVOKED"

        features.append({
            "type": "Feature",
            "properties": {
                "id": f"fam_{participant_id}",
                "participantId": participant_id,
                "displayName": d["displayName"],
                "freshness": freshness,
                "accuracyMeters": loc.get("accuracy_meters", 15.0),
                "lastUpdated": loc["recorded_at"],
                "deviceType": d["deviceType"],
                "platform": d["platform"]
            },
            "geometry": {
                "type": "Point",
                "coordinates": [loc["longitude"], loc["latitude"], loc.get("altitude_meters", 0.0)]
            }
        })

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    return make_api_response(
        ok=True,
        executed=True,
        simulated=False,
        message=f"Generated {len(features)} privacy-filtered spatial overlay(s)",
        data={"geojson": geojson, "featureCount": len(features)}
    )

def on_stt_status(status: str, label: str):
    if MAIN_SERVER_LOOP and MAIN_SERVER_LOOP.is_running():
        asyncio.run_coroutine_threadsafe(
            broadcast_event({"type": "status", "status": status, "subtext": label}),
            MAIN_SERVER_LOOP
        )

@app.on_event("startup")
async def startup_event():
    global MAIN_SERVER_LOOP
    MAIN_SERVER_LOOP = asyncio.get_running_loop()
    print("[+] Main server event loop registered.", flush=True)
    conversation_controller.set_broadcast_fn(broadcast_event)
    native_stt.start_stt(on_native_speech, status_callback=on_stt_status)
    asyncio.create_task(monitor.start())
    proactive_supervisor.start()
    asyncio.create_task(voice_engine.prewarm_voice_cache())

@app.on_event("shutdown")
async def shutdown_event():
    native_stt.stop_stt()
    monitor.stop()
    proactive_supervisor.stop()


active_ws_tasks = {}

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    chat_clients.add(websocket)
    session_id = id(websocket)

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            msg_type = data.get("type", "message")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "ts": time.time()}))
            
            elif msg_type == "cancel":
                await conversation_controller.abort_active_turn(reason="User cancelled via WebSocket")
                await websocket.send_text(json.dumps({"type": "status", "status": "idle"}))
                
            elif msg_type == "message":
                user_text = data.get("text", "").strip()
                if not user_text:
                    continue

                # Stop command check (instant abort - top priority)
                if conversation_controller.is_stop_command(user_text):
                    await conversation_controller.abort_active_turn(reason=f"Stop command '{user_text}' via WebSocket")
                    await websocket.send_text(json.dumps({"type": "status", "status": "idle"}))
                    continue

                # Acoustic Deduplication (suppress dual-device/echo duplicate triggers)
                if conversation_controller.is_duplicate_acoustic_request(user_text):
                    await websocket.send_text(json.dumps({
                        "type": "response",
                        "text": "Acoustic link synchronized with your active device, Sir Shakil."
                    }))
                    await websocket.send_text(json.dumps({"type": "status", "status": "idle"}))
                    continue

                voice_enabled = data.get("voice_enabled", True)
                play_speaker = data.get("play_speaker", False)
                model = data.get("model", "auto/best-fast")
                workspace = data.get("workspace", "personal")
                history = data.get("history", [])

                # Unified dispatch through conversation_controller
                await conversation_controller.handle_user_prompt(
                    prompt=user_text,
                    source="websocket",
                    voice_enabled=voice_enabled,
                    play_speaker=play_speaker,
                    model=model,
                    history=history,
                    workspace=workspace,
                    process_callback=execute_turn_pipeline
                )

    except WebSocketDisconnect:
        chat_clients.discard(websocket)
    except Exception as ws_err:
        print(f"[WebSocket Chat Error] {ws_err}", flush=True)
        chat_clients.discard(websocket)

# Static HUD Mount
static_dir = Path("frontend")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Static Spatial / God's Eye View Mounts
gev_dist = Path("vendor/gods-eye-view/dist")
if gev_dist.exists():
    app.mount("/spatial", StaticFiles(directory=str(gev_dist), html=True), name="spatial_dist")
    cesium_dir = gev_dist / "cesium"
    if cesium_dir.exists():
        app.mount("/cesium", StaticFiles(directory=str(cesium_dir)), name="cesium_dist")
    assets_dir = gev_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets_dist")
    events_dir = gev_dist / "events"
    if events_dir.exists():
        app.mount("/events", StaticFiles(directory=str(events_dir)), name="events_dist")
    models_dir = gev_dist / "models"
    if models_dir.exists():
        app.mount("/models", StaticFiles(directory=str(models_dir)), name="models_dist")

@app.get("/")
async def serve_index():
    index_file = Path("frontend/index.html")
    if index_file.exists():
        return HTMLResponse(index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>J.A.R.V.I.S. Core Online. Interface loading...</h1>")
