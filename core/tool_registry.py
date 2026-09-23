"""
tool_registry.py

Centralized tool definition registry for J.A.R.V.I.S. Mark XVI.
Defines all available tools as OpenAI-compatible JSON function schemas
and provides a dispatch function to execute them.
"""

from typing import List, Dict, Any

# Define the OpenAI-compatible tool schemas
JARVIS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "workstation_exec_shell",
            "description": "Execute a PowerShell command on Sir Shakil's Windows PC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The PowerShell command to execute."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_sandbox",
            "description": "Run Python or PowerShell code in an isolated sandbox with a 15s timeout.",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "The programming language to use.",
                        "enum": ["python", "powershell"],
                        "default": "python"
                    },
                    "code": {
                        "type": "string",
                        "description": "The code to execute."
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Capture the current screen.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "vision_analyze",
            "description": "Analyze the current screen with multimodal AI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directive": {
                        "type": "string",
                        "description": "Optional specific instructions or questions about the screen."
                    },
                    "mode": {
                        "type": "string",
                        "description": "The mode of analysis.",
                        "enum": ["inspect", "debug", "read"],
                        "default": "inspect"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memory_save",
            "description": "Save a fact to Jarvis's permanent memory vault.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category of the memory.",
                        "default": "preference"
                    },
                    "key": {
                        "type": "string",
                        "description": "The key under which to save the memory."
                    },
                    "value": {
                        "type": "string",
                        "description": "The value of the memory to save."
                    }
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memory_query",
            "description": "Search the knowledge vault for relevant facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "launch_app",
            "description": "Open an application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "The name of the application to launch."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_app",
            "description": "Close an application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "The name of the application to close."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Set system volume.",
            "parameters": {
                "type": "object",
                "properties": {
                    "percent": {
                        "type": "integer",
                        "description": "Volume percentage from 0 to 100."
                    }
                },
                "required": ["percent"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "navigate_to_location",
            "description": "Navigate the God's Eye View 3D globe to a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The location to navigate to."
                    },
                    "view_mode": {
                        "type": "string",
                        "description": "The view mode of the globe.",
                        "enum": ["overview", "street", "aerial"],
                        "default": "overview"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "toggle_layer",
            "description": "Enable or disable a God's Eye View data layer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Whether to enable or disable the layer.",
                        "enum": ["enable", "disable"]
                    },
                    "layer_id": {
                        "type": "string",
                        "description": "The ID of the layer.",
                        "enum": ["flights", "ships", "satellites", "weather", "fires", "quakes", "cctv", "radio"]
                    }
                },
                "required": ["action", "layer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "track_entity",
            "description": "Track a specific entity on the globe.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The ID of the entity to track."
                    },
                    "layer_id": {
                        "type": "string",
                        "description": "The layer the entity belongs to."
                    }
                },
                "required": ["entity_id", "layer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "untrack_entity",
            "description": "Stop tracking the current entity.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "switch_visual_mode",
            "description": "Change the globe's visual rendering style.",
            "parameters": {
                "type": "object",
                "properties": {
                    "style": {
                        "type": "string",
                        "description": "The visual rendering style to apply.",
                        "enum": ["normal", "thermal", "nightvision", "crt", "noir"]
                    }
                },
                "required": ["style"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "measure_distance",
            "description": "Measure the distance between two locations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_location": {
                        "type": "string",
                        "description": "The starting location."
                    },
                    "to_location": {
                        "type": "string",
                        "description": "The ending location."
                    }
                },
                "required": ["from_location", "to_location"]
            }
        }
    }
]


def get_tool_schemas() -> List[Dict[str, Any]]:
    """Returns the list of tool definitions for injection into OmniRoute API calls."""
    return JARVIS_TOOLS


def get_tool_names() -> List[str]:
    """Returns just the list of tool name strings."""
    return [tool["function"]["name"] for tool in JARVIS_TOOLS]


async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatches a tool call by name, calling the existing execute_tool_call
    from core.ai_brain to avoid code duplication.
    """
    try:
        from core.ai_brain import execute_tool_call
        result = await execute_tool_call(tool_name, **arguments)
        return {
            "success": True,
            "tool": tool_name,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "tool": tool_name,
            "error": str(e)
        }
