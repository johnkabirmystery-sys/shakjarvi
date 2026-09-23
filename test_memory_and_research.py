import asyncio
from core import memory_engine
from core import research_engine
from core import ai_brain

def test_memory():
    print("[*] TEST 1: Testing SQLite Memory Engine...")
    memory_engine.init_db()
    
    # Save fact
    save_res = memory_engine.save_fact("preferences", "Preferred Model", "Gemini 2.5 Flash")
    assert save_res["success"], "Save fact failed"
    
    # Retrieve facts
    facts = memory_engine.get_all_facts()
    assert any(f["key"] == "Preferred Model" for f in facts), "Fact not found in DB"
    print(f"    [+] Total Stored Facts for Sir Shakil: {len(facts)}")
    
    # Check evolution stats
    stats = memory_engine.get_evolution_stats()
    print(f"    [+] Current Evolution Level: {stats['level']}, Nodes: {stats['knowledge_nodes']}")
    assert stats["level"] >= 1, "Invalid level"

async def test_research():
    print("[*] TEST 2: Testing Autonomous Research Engine...")
    res = await research_engine.conduct_deep_research("High performance Python async")
    assert res["success"], "Research cycle failed"
    print(f"    [+] Autonomous Research Topic: {res['topic']}")
    print(f"    [+] Synthesized Summary: {res['summary'][:90]}...")
    print(f"    [+] Updated Stats: Level {res['stats']['level']}, {res['stats']['knowledge_nodes']} Nodes")

async def test_brain_memory():
    print("[*] TEST 3: Testing AI Brain Memory & Research Directives...")
    
    # Remember command
    async for event in ai_brain.process_user_message("Jarvis, remember my goal is to build an autonomous AI enterprise"):
        if event["type"] == "response":
            print(f"    [+] Remember Command Response: '{event['text']}'")
            assert "Sir Shakil" in event["text"]

    # Recall command
    async for event in ai_brain.process_user_message("Jarvis, what do you know about me?"):
        if event["type"] == "response":
            print(f"    [+] Recall Command Response: '{event['text'][:120]}...'")
            assert "Sir Shakil" in event["text"]

    # Evolution report
    async for event in ai_brain.process_user_message("Jarvis, report your evolution stats"):
        if event["type"] == "response":
            print(f"    [+] Evolution Report Response: '{event['text']}'")
            assert "Level" in event["text"]

def run_all():
    test_memory()
    asyncio.run(test_research())
    asyncio.run(test_brain_memory())
    print("\n=======================================================")
    print("   ALL MEMORY & EVOLUTION TESTS PASSED (3/3)!")
    print("=======================================================")

if __name__ == "__main__":
    run_all()
