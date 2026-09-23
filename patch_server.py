import re

with open("server.py", "r") as f:
    code = f.read()

# Add imports
if "from core import native_stt" not in code:
    code = code.replace("from core import ai_brain", "from core import ai_brain\nfrom core import native_stt\nimport asyncio\nfrom typing import Optional")

# Modify dispatch_tts
dispatch_tts_old = """async def dispatch_tts(websocket: WebSocket, text: str, play_speaker: bool):
    try:
        tts_res = await voice_engine.synthesize_speech_async(text, voice=voice_engine.DEFAULT_VOICE)
        filepath = tts_res.get("filepath")
        est_duration = tts_res.get("duration", voice_engine.get_audio_duration_estimate(text))
        
        await websocket.send_text(json.dumps({
            "type": "status", 
            "status": "speaking", 
            "duration": est_duration,
            "text": text
        }))

        if play_speaker and filepath and os.path.exists(filepath):
            voice_engine.play_audio_file_on_speakers(filepath)
            await websocket.send_text(json.dumps({
                "type": "audio",
                "audio_base64": None,
                "mime": "audio/wav",
                "duration": est_duration,
                "text": text
            }))
        elif tts_res.get("base64"):
            await websocket.send_text(json.dumps({
                "type": "audio",
                "audio_base64": tts_res["base64"],
                "mime": "audio/wav",
                "duration": est_duration,
                "text": text
            }))
            
        if filepath:
            last_speech_cache["filepath"] = filepath
    except Exception as e:
        print(f"[TTS Dispatch Error] {e}")"""

dispatch_tts_new = """async def dispatch_tts(websocket: Optional[WebSocket], text: str, play_speaker: bool):
    try:
        tts_res = await voice_engine.synthesize_speech_async(text, voice=voice_engine.DEFAULT_VOICE)
        filepath = tts_res.get("filepath")
        est_duration = tts_res.get("duration", voice_engine.get_audio_duration_estimate(text))
        
        if websocket:
            try:
                await websocket.send_text(json.dumps({
                    "type": "status", "status": "speaking", "duration": est_duration, "text": text
                }))
            except: pass

        if play_speaker and filepath and os.path.exists(filepath):
            voice_engine.play_audio_file_on_speakers(filepath)
            if websocket:
                try:
                    await websocket.send_text(json.dumps({
                        "type": "audio", "audio_base64": None, "mime": "audio/wav", "duration": est_duration, "text": text
                    }))
                except: pass
        elif tts_res.get("base64") and websocket:
            try:
                await websocket.send_text(json.dumps({
                    "type": "audio", "audio_base64": tts_res["base64"], "mime": "audio/wav", "duration": est_duration, "text": text
                }))
            except: pass
            
        if filepath:
            last_speech_cache["filepath"] = filepath
    except Exception as e:
        print(f"[TTS Dispatch Error] {e}")"""

code = code.replace(dispatch_tts_old, dispatch_tts_new)

# Add startup event and headless process
native_stt_logic = """
def on_native_speech(text):
    text = text.strip()
    if not text: return
    check_text = re.sub(r'[^a-z\s]', '', text.lower())
    if check_text in ["cancel", "stop", "abort", "never mind", "nevermind", "stop processing", "cancel that"]:
        for task in active_ws_tasks.values():
            if not task.done():
                task.cancel()
        voice_engine.stop_local_audio()
        return

    native_stt.mute_stt()
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
        
    async def _broadcast_and_process():
        for ws in chat_clients:
            try:
                await ws.send_text(json.dumps({"type": "transcript", "text": text}))
            except Exception: pass
        task = asyncio.create_task(headless_process(text))
        active_ws_tasks["native"] = task

    asyncio.run_coroutine_threadsafe(_broadcast_and_process(), loop)

async def headless_process(text: str):
    try:
        if is_duplicate_acoustic_request(text):
            return
            
        full_response = ""
        tts_buffer = ""
        
        async for event in ai_brain.process_user_message(text, history=[], model="agy/gemini-3.7-flash-low"):
            for ws in chat_clients:
                try: await ws.send_text(json.dumps(event))
                except: pass
                
            if event["type"] == "chunk":
                full_response += event["content"]
                tts_buffer += event["content"]
                match = re.search(r'(?<=[.!?\n])\s+', tts_buffer)
                while match:
                    split_idx = match.end()
                    sentence = tts_buffer[:split_idx].strip()
                    tts_buffer = tts_buffer[split_idx:]
                    clean_sentence = voice_engine.clean_text_for_speech(sentence)
                    if len(clean_sentence) > 2:
                        asyncio.create_task(dispatch_tts(None, clean_sentence, True))
                    match = re.search(r'(?<=[.!?\n])\s+', tts_buffer)
        
        clean_remainder = voice_engine.clean_text_for_speech(tts_buffer)
        if len(clean_remainder) > 2:
            await dispatch_tts(None, clean_remainder, True)
            
    finally:
        native_stt.unmute_stt()
        for ws in chat_clients:
            try: await ws.send_text(json.dumps({"type": "status", "status": "idle"}))
            except: pass

@app.on_event("startup")
async def startup_event():
    native_stt.start_stt(on_native_speech)

@app.on_event("shutdown")
async def shutdown_event():
    native_stt.stop_stt()

"""

if "def on_native_speech" not in code:
    code = code.replace("active_ws_tasks = {}", native_stt_logic + "\nactive_ws_tasks = {}")

with open("server.py", "w") as f:
    f.write(code)
