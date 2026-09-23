"""
Google Antigravity SDK Bridge for Shakil's Assistant (J.A.R.V.I.S.)
Integrates the google.antigravity Agent runtime with Windows PC control,
telemetry diagnostics, persistent memory, and autonomous research.
"""

import os
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from pathlib import Path

# Check if SDK is available
try:
    from google.antigravity import (
        Agent,
        LocalAgentConfig,
        CapabilitiesConfig,
        AgentBehavior,
        BuiltinTools
    )
    ANTIGRAVITY_INSTALLED = True
except ImportError:
    ANTIGRAVITY_INSTALLED = False

from core import pc_controller
from core import telemetry
from core import memory_engine
from core import research_engine

def is_antigravity_available() -> bool:
    """Returns True if the google-antigravity SDK is installed."""
    return ANTIGRAVITY_INSTALLED

BRIDGE_DIR = Path("data/antigravity_bridge")
BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
TASKS_FILE = BRIDGE_DIR / "tasks.json"

def log_antigravity_task(directive: str, source: str = "Sir Shakil") -> dict:
    """Logs a directive into the Antigravity project workspace task bridge."""
    import time
    tasks = []
    if TASKS_FILE.exists():
        try:
            tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        except Exception:
            tasks = []
            
    task = {
        "id": len(tasks) + 1,
        "directive": directive,
        "source": source,
        "timestamp": time.time(),
        "status": "pending_execution"
    }
    tasks.append(task)
    TASKS_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    return task

def get_pending_antigravity_tasks():
    if TASKS_FILE.exists():
        try:
            tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
            return [t for t in tasks if t.get("status") == "pending_execution"]
        except Exception:
            return []
    return []

# -------------------------------------------------------------
# Jarvis Custom Tools for Google Antigravity Agent
# -------------------------------------------------------------

def set_workstation_volume(percent: int) -> str:
    """Sets the master system volume of Sir Shakil's Windows PC.

    Args:
        percent: Volume percentage from 0 to 100.
    """
    res = pc_controller.set_volume(percent)
    return json.dumps(res)

def mute_workstation_audio(mute: bool = True) -> str:
    """Mutes or unmutes the audio output on Sir Shakil's Windows PC.

    Args:
        mute: True to mute, False to unmute.
    """
    res = pc_controller.mute_volume(mute)
    return json.dumps(res)

def media_playback_action(action: str) -> str:
    """Controls media playback on Sir Shakil's Windows PC.

    Args:
        action: One of 'play_pause', 'next', 'prev', 'stop'.
    """
    res = pc_controller.media_control(action)
    return json.dumps(res)

def launch_pc_program(program_name: str) -> str:
    """Launches an application or executable on Sir Shakil's Windows PC.

    Args:
        program_name: Name of application (e.g. 'chrome', 'notepad', 'calc', 'code').
    """
    res = pc_controller.launch_app(program_name)
    return json.dumps(res)

def close_pc_program(process_name: str) -> str:
    """Terminates an application process on Sir Shakil's Windows PC.

    Args:
        process_name: Name of process or app to terminate.
    """
    res = pc_controller.close_app(process_name)
    return json.dumps(res)

def capture_desktop_screenshot() -> str:
    """Captures a full screenshot of Sir Shakil's active display."""
    res = pc_controller.take_screenshot()
    return json.dumps(res)

def lock_pc_workstation() -> str:
    """Locks Sir Shakil's Windows PC workstation for security."""
    res = pc_controller.lock_workstation()
    return json.dumps(res)

def run_system_shell(command: str) -> str:
    """Executes a PowerShell shell command on Sir Shakil's Windows PC.

    Args:
        command: The PowerShell command string to execute.
    """
    res = pc_controller.execute_shell(command)
    return json.dumps(res)

def get_workstation_telemetry() -> str:
    """Retrieves live real-time hardware telemetry: CPU load per core, RAM, disk partitions, network I/O, battery, and foreground window."""
    data = telemetry.get_telemetry_data()
    return json.dumps(data)

def remember_user_fact(category: str, key: str, value: str) -> str:
    """Permanently records a preference, fact, or instruction about Sir Shakil in the long-term memory vault.

    Args:
        category: Category (e.g. 'preference', 'project', 'goal', 'financial').
        key: Unique identifier key for this fact.
        value: Fact description or preference value.
    """
    res = memory_engine.save_fact(category, key, value)
    return json.dumps(res)

def search_knowledge_vault(query: str) -> str:
    """Searches Jarvis's permanent knowledge vault for past research, blueprints, and tech strategies.

    Args:
        query: Search term or topic.
    """
    res = memory_engine.search_knowledge(query, limit=5)
    return json.dumps(res)

def conduct_deep_research_task(topic: str) -> str:
    """Initiates an autonomous deep research cycle across the Web and GitHub, synthesizing findings into a new permanent knowledge node.

    Args:
        topic: The topic, tech stack, or monetization blueprint to research.
    """
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(research_engine.conduct_deep_research(topic), loop)
        res = future.result(timeout=60)
    except RuntimeError:
        res = asyncio.run(research_engine.conduct_deep_research(topic))
    return json.dumps(res)

JARVIS_ANTIGRAVITY_TOOLS = [
    set_workstation_volume,
    mute_workstation_audio,
    media_playback_action,
    launch_pc_program,
    close_pc_program,
    capture_desktop_screenshot,
    lock_pc_workstation,
    run_system_shell,
    get_workstation_telemetry,
    remember_user_fact,
    search_knowledge_vault,
    conduct_deep_research_task
]

# -------------------------------------------------------------
# Antigravity Agent Session Management
# -------------------------------------------------------------

def get_antigravity_config(api_key: str, system_instructions: str):
    """Builds a LocalAgentConfig for the Google Antigravity Agent."""
    if not ANTIGRAVITY_INSTALLED:
        return None
        
    return LocalAgentConfig(
        api_key=api_key,
        system_instructions=system_instructions,
        tools=JARVIS_ANTIGRAVITY_TOOLS,
        capabilities=CapabilitiesConfig(
            agent_behavior=AgentBehavior.AUTONOMOUS
        )
    )

async def stream_antigravity_agent(
    prompt: str,
    api_key: str,
    system_instructions: str,
    history=None
) -> AsyncGenerator[Dict[str, Any], None]:
    """Streams thoughts, tool execution events, and final response from the Google Antigravity Agent."""
    if not ANTIGRAVITY_INSTALLED:
        yield {"type": "thought", "content": "Google Antigravity SDK is not installed."}
        return

    config = get_antigravity_config(api_key, system_instructions)
    if not config:
        yield {"type": "thought", "content": "Failed to initialize Antigravity configuration."}
        return

    yield {"type": "thought", "content": "Spawning Google Antigravity Agent runtime with Jarvis executive tools..."}

    try:
        async with Agent(config) as agent:
            # Dispatch prompt to Antigravity Agent
            response = await agent.chat(prompt)

            # Stream thinking deltas if available
            try:
                if hasattr(response, "thoughts"):
                    async for thought in response.thoughts:
                        if thought:
                            yield {"type": "thought", "content": str(thought)}
            except Exception:
                pass

            # Stream tool call events if available
            try:
                if hasattr(response, "tool_calls"):
                    async for call in response.tool_calls:
                        yield {
                            "type": "tool_call",
                            "tool": getattr(call, "name", str(call)),
                            "args": getattr(call, "args", {})
                        }
            except Exception:
                pass

            # Stream or retrieve final text
            full_text = ""
            try:
                async for token in response:
                    text_chunk = str(token)
                    full_text += text_chunk
                    yield {"type": "chunk", "text": text_chunk}
            except TypeError:
                if hasattr(response, "text"):
                    res_val = response.text()
                    if asyncio.iscoroutine(res_val):
                        full_text = await res_val
                    else:
                        full_text = str(res_val)

            if not full_text.strip() and hasattr(response, "text"):
                res_val = response.text()
                if asyncio.iscoroutine(res_val):
                    full_text = await res_val
                else:
                    full_text = str(res_val)

            yield {"type": "response", "text": full_text or "Directive processed by Google Antigravity Agent."}

    except Exception as e:
        yield {"type": "thought", "content": f"Antigravity Agent runtime error: {str(e)}"}
        yield {"type": "response", "text": f"Sir Shakil, an issue occurred in the Antigravity Agent execution: {str(e)}"}
