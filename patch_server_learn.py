import re

with open("server.py", "r") as f:
    code = f.read()

learning_logic = """
async def extract_and_learn(user_text: str):
    try:
        from core import omniroute_client
        from core import memory_engine
        import json
        
        prompt = \"\"\"Analyze this message from Sir Shakil. Extract any new, permanent facts, goals, or preferences about him that should be saved to long-term memory.
User Message: "{}"
If a clear new fact is present, reply with EXACTLY ONE line of JSON: {{"category": "preference|goal|fact", "key": "Brief Key", "value": "Detailed fact"}}
If no new facts, reply with EXACTLY: {{"none": true}}
Do not write anything else.\"\"\".format(user_text.replace('"', "'"))
        
        # Use a lightweight fast model for background extraction
        result = ""
        async for chunk in omniroute_client.stream_omniroute_agent(prompt, system_instruction="You are a JSON memory extractor.", preferred_model="agy/gemini-3.7-flash-low"):
            if chunk["type"] == "response":
                result = chunk["text"]
        
        if result:
            try:
                # Strip markdown code blocks if any
                clean_json = result.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                if not data.get("none") and "key" in data and "value" in data:
                    cat = data.get("category", "fact")
                    memory_engine.save_fact(cat, data["key"], data["value"])
                    print(f"[Continuous Learning] Assumed new fact: {data['key']} = {data['value']}")
            except Exception as e:
                pass
    except Exception as e:
        pass
"""

# Hook it into headless_process
headless_process_old = """        clean_remainder = voice_engine.clean_text_for_speech(tts_buffer)
        if len(clean_remainder) > 2:
            await dispatch_tts(None, clean_remainder, True)
            
    finally:"""

headless_process_new = """        clean_remainder = voice_engine.clean_text_for_speech(tts_buffer)
        if len(clean_remainder) > 2:
            await dispatch_tts(None, clean_remainder, True)
            
        asyncio.create_task(extract_and_learn(text))
        
    finally:"""

# Hook it into websocket_chat -> process_chat_message
chat_process_old = """                if len(remainder) > 3:
                    await dispatch_tts(websocket, remainder, play_speaker)
                
                filepath = last_speech_cache.get("filepath")
                if filepath:
                    last_speech_cache["filepath"] = filepath
                    last_speech_cache["text"] = full_response
                    last_speech_cache["timestamp"] = time.time()
                    
            await websocket.send_text(json.dumps({"type": "status", "status": "idle"}))"""

chat_process_new = """                if len(remainder) > 3:
                    await dispatch_tts(websocket, remainder, play_speaker)
                
                filepath = last_speech_cache.get("filepath")
                if filepath:
                    last_speech_cache["filepath"] = filepath
                    last_speech_cache["text"] = full_response
                    last_speech_cache["timestamp"] = time.time()
                    
            asyncio.create_task(extract_and_learn(user_text))
            await websocket.send_text(json.dumps({"type": "status", "status": "idle"}))"""


if "def extract_and_learn" not in code:
    code = code.replace("async def dispatch_tts", learning_logic + "\nasync def dispatch_tts")
    code = code.replace(headless_process_old, headless_process_new)
    code = code.replace(chat_process_old, chat_process_new)

with open("server.py", "w") as f:
    f.write(code)
