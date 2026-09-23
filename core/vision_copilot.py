"""
Screen Vision Copilot for Shakil's Assistant (J.A.R.V.I.S.)
===========================================================
Provides multimodal screen understanding, IDE debugging assistance,
and active workspace visual intelligence for Sir Shakil.
"""

import os
import time
from typing import Dict, Any, Optional
from core import pc_controller
from core import omniroute_client

VISION_PROMPTS = {
    "inspect": (
        "You are Jarvis, Chief Technology Officer and visual executive copilot to Sir Shakil. "
        "Inspect this screenshot of Sir Shakil's active display. "
        "Identify the active applications, window contents, and key focal points. "
        "Provide a concise, sophisticated executive summary of what is currently on screen."
    ),
    "debug": (
        "You are Jarvis, Chief Technology Officer to Sir Shakil. "
        "Analyze the code, terminal errors, or exceptions displayed on this screen. "
        "Point out the exact root cause of the error or bug, and provide the exact fix."
    ),
    "read": (
        "You are Jarvis, executive copilot to Sir Shakil. "
        "Transcribe and summarize the essential text, data points, or documents visible on this screen."
    )
}

async def analyze_active_screen(
    directive: Optional[str] = None,
    mode: str = "inspect",
    model: str = "agy/gemini-3.7-flash-low"
) -> Dict[str, Any]:
    """
    Captures the current workstation screen and performs multimodal vision analysis.
    Returns:
        dict: {
            "success": bool,
            "analysis": str,
            "filepath": str,
            "model_used": str,
            "duration_ms": float,
            "error": Optional[str]
        }
    """
    start_time = time.perf_counter()
    
    # 1. Acquire screenshot
    shot_res = pc_controller.take_screenshot()
    if not shot_res.get("success"):
        return {
            "success": False,
            "analysis": "",
            "filepath": "",
            "model_used": model,
            "duration_ms": 0.0,
            "error": shot_res.get("error", "Failed to capture workstation screen.")
        }

    image_b64 = shot_res.get("base64")
    filepath = shot_res.get("filepath", "")

    # 2. Build system instruction & prompt
    base_instruction = VISION_PROMPTS.get(mode, VISION_PROMPTS["inspect"])
    user_prompt = directive if (directive and directive.strip()) else "Please analyze my current screen."

    # 3. Query OmniRoute Multimodal Vision API
    analysis_text = ""
    model_used = model
    
    try:
        # Collect tokens from streaming vision completion
        async for event in omniroute_client.stream_omniroute_completion(
            prompt=user_prompt,
            system_instruction=base_instruction,
            preferred_model=model,
            image_base64=image_b64
        ):
            if event.get("type") == "response":
                analysis_text = event.get("text", "")
                model_used = event.get("model", model)
            elif event.get("type") == "error":
                return {
                    "success": False,
                    "analysis": "",
                    "filepath": filepath,
                    "model_used": model_used,
                    "duration_ms": round((time.perf_counter() - start_time) * 1000.0, 2),
                    "error": event.get("content", "Vision API streaming failed.")
                }

        if not analysis_text:
            # Fallback non-streaming call if stream didn't yield response
            res = await omniroute_client.generate_omniroute_completion(
                prompt=user_prompt,
                system_instruction=base_instruction,
                preferred_model=model,
                image_base64=image_b64
            )
            analysis_text = res.get("text", "")
            model_used = res.get("model", model)

        duration = (time.perf_counter() - start_time) * 1000.0
        return {
            "success": bool(analysis_text),
            "analysis": analysis_text,
            "filepath": filepath,
            "model_used": model_used,
            "duration_ms": round(duration, 2),
            "error": None if analysis_text else "No analysis produced by model."
        }

    except Exception as e:
        duration = (time.perf_counter() - start_time) * 1000.0
        return {
            "success": False,
            "analysis": "",
            "filepath": filepath,
            "model_used": model_used,
            "duration_ms": round(duration, 2),
            "error": str(e)
        }
