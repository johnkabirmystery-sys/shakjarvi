"""
Mark XVII Structured Function Calling & Tool Registry Test Suite
================================================================
Validates:
1. Tool Registry schemas compliance with OpenAI Function Calling JSON standard
2. Tool Name extraction and lookup
3. Direct execution dispatch with arguments unpacking via execute_tool
4. Spatial and Workstation tool mapping correctness
5. OmniRoute Client payload schema injection with tools parameter
"""

import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import tool_registry
from core import omniroute_client

def test_tool_schemas_format():
    print("[*] Testing Tool Registry schema compliance with OpenAI standards...")
    schemas = tool_registry.get_tool_schemas()
    assert isinstance(schemas, list), "Schemas must be a list"
    assert len(schemas) >= 15, f"Expected at least 15 tools, got {len(schemas)}"
    
    names = tool_registry.get_tool_names()
    assert len(names) == len(schemas)
    assert "workstation_exec_shell" in names
    assert "code_sandbox" in names
    assert "set_volume" in names
    assert "memory_save" in names
    assert "navigate_to_location" in names
    assert "measure_distance" in names

    for s in schemas:
        assert s.get("type") == "function", f"Invalid type in {s}"
        fn = s.get("function", {})
        assert "name" in fn, "Missing function name"
        assert "description" in fn, "Missing function description"
        assert "parameters" in fn, "Missing parameters schema"
        assert fn["parameters"].get("type") == "object"
    print(f"  [PASS] All {len(schemas)} tools match strict OpenAI schema specifications.")

async def test_tool_execution_dispatch():
    print("[*] Testing Tool Registry execute_tool dispatch...")
    
    # Test Sandbox code execution through tool registry
    res = await tool_registry.execute_tool("code_sandbox", {
        "language": "python",
        "code": "result = 40 + 2\nprint(f'VAL={result}')"
    })
    assert res.get("success") is True, f"Execution failed: {res}"
    assert "VAL=42" in res.get("result", {}).get("stdout", ""), f"Unexpected output: {res}"
    print("  [PASS] execute_tool successfully dispatched code_sandbox.")

    # Test Memory save tool
    res_mem = await tool_registry.execute_tool("memory_save", {
        "category": "system_test",
        "key": "TestKey_XVII",
        "value": "Mark XVII Verified"
    })
    assert res_mem.get("success") is True, f"Memory save failed: {res_mem}"
    print("  [PASS] execute_tool successfully dispatched memory_save.")

    # Test unknown tool handling
    res_unknown = await tool_registry.execute_tool("non_existent_tool_xyz", {})
    assert res_unknown.get("result", {}).get("success") is False or res_unknown.get("success") is False
    print("  [PASS] execute_tool safely handled unknown tool exception.")

def test_omniroute_tool_payload():
    print("[*] Testing OmniRoute Client tools parameter handling...")
    # Verify generate_omniroute_completion signature has 'tools'
    import inspect
    sig = inspect.signature(omniroute_client.generate_omniroute_completion)
    assert "tools" in sig.parameters, "generate_omniroute_completion missing tools parameter"
    print("  [PASS] OmniRoute client signature supports structured tools injection.")

async def main():
    print("\n" + "="*60)
    print("  MARK XVII STRUCTURED FUNCTION CALLING VERIFICATION")
    print("="*60)
    test_tool_schemas_format()
    await test_tool_execution_dispatch()
    test_omniroute_tool_payload()
    print("="*60)
    print("  ALL FUNCTION CALLING TESTS PASSED (100%)\n")

if __name__ == "__main__":
    asyncio.run(main())
