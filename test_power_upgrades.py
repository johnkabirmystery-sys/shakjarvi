"""
Targeted Verification Suite for Jarvis Power Upgrades
=====================================================
Validates:
1. Code Sandbox Python execution
2. Code Sandbox Syntax validation
3. Code Sandbox Timeout safety
4. AI Brain Tool Call Parsing
5. AI Brain Tool Execution
"""

import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import code_sandbox
from core import ai_brain

def test_sandbox_execution():
    print("[*] Testing Code Sandbox Python execution...")
    code = "import math\nprint(f'PI_VAL={round(math.pi, 4)}')"
    res = code_sandbox.run_code(code, language="python")
    assert res["success"] is True, f"Execution failed: {res.get('error')}"
    assert "PI_VAL=3.1416" in res["stdout"], f"Unexpected stdout: {res.get('stdout')}"
    assert res["exit_code"] == 0
    assert res["duration_ms"] > 0
    print("  [PASS] Code Sandbox successfully executed Python snippet.")

def test_sandbox_syntax_error():
    print("[*] Testing Code Sandbox syntax error handling...")
    code = "def broken_func(:\n    pass"
    res = code_sandbox.run_code(code, language="python")
    assert res["success"] is False
    assert "SyntaxError" in res["stderr"]
    print("  [PASS] Code Sandbox properly intercepted SyntaxError.")

def test_sandbox_timeout():
    print("[*] Testing Code Sandbox timeout safety guard...")
    code = "import time\ntime.sleep(5)"
    res = code_sandbox.run_code(code, language="python", timeout=1)
    assert res["success"] is False
    assert "timed out" in res["stderr"].lower() or "timeout" in str(res.get("error")).lower()
    print("  [PASS] Code Sandbox enforced execution timeout safety.")

def test_tool_call_parsing():
    print("[*] Testing AI Brain Tool Call Parsing...")
    sample_text = (
        "Understood, Sir Shakil. I will execute the following:\n"
        "[TOOL: workstation_exec_shell(command=\"Get-Process -Name python\")]\n"
        "[TOOL: set_volume(percent=85)]\n"
        "All commands staged."
    )
    tools = ai_brain.parse_tool_calls(sample_text)
    assert len(tools) == 2, f"Expected 2 tools, got {len(tools)}"
    assert tools[0]["tool"] == "workstation_exec_shell"
    assert tools[0]["args"]["command"] == "Get-Process -Name python"
    assert tools[1]["tool"] == "set_volume"
    assert tools[1]["args"]["percent"] == "85"
    print("  [PASS] AI Brain correctly parsed structured tool calls.")

async def test_tool_execution():
    print("[*] Testing AI Brain Tool Execution...")
    res = await ai_brain.execute_tool_call("code_sandbox", code="print('TOOL_EXEC_OK')", language="python")
    assert res["success"] is True
    assert "TOOL_EXEC_OK" in res["stdout"]
    print("  [PASS] AI Brain successfully executed tool call.")

if __name__ == "__main__":
    test_sandbox_execution()
    test_sandbox_syntax_error()
    test_sandbox_timeout()
    test_tool_call_parsing()
    asyncio.run(test_tool_execution())
    print("\n==========================================")
    print("ALL POWER UPGRADE UNIT TESTS PASSED (5/5)!")
    print("==========================================")
