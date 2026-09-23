import sys
import time
import json
import requests
from pathlib import Path

# Ensure UTF-8 stdout on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TASKS_FILE = Path("data/antigravity_bridge/tasks.json")
JARVIS_API_HTTPS = "https://127.0.0.1:8000/api/broadcast"
JARVIS_API_HTTP = "http://127.0.0.1:8000/api/broadcast"

print("=========================================================")
print("[+] JARVIS BRAIN LINK ESTABLISHED")
print("This Antigravity Chat is now serving as Jarvis's primary neural core.")
print("Waiting for directives from the HUD...")
print("=========================================================")

def get_pending_tasks():
    if not TASKS_FILE.exists():
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        return [t for t in tasks if t.get("status") in ["pending", "pending_execution"]]
    except:
        return []

def mark_task_in_progress(task_id):
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        for t in tasks:
            if t["id"] == task_id:
                t["status"] = "in_progress"
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
    except:
        pass

def mark_task_completed(task_id, response_text):
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        for t in tasks:
            if t["id"] == task_id:
                t["status"] = "completed"
                t["response"] = response_text
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
            
        # Send voice response back to Jarvis HUD (HTTPS or HTTP)
        payload = {
            "text": response_text,
            "level": "info",
            "play_speaker": True
        }
        try:
            requests.post(JARVIS_API_HTTPS, json=payload, verify=False, timeout=5)
        except Exception:
            try:
                requests.post(JARVIS_API_HTTP, json=payload, timeout=5)
            except Exception:
                pass
        print(f"\n[JARVIS SYNTHESIS] Broadcasted response back to HUD for Task #{task_id}.")
    except Exception as e:
        print(f"Failed to complete task: {e}")

# This script is designed to be read by the Antigravity Agent in the "Building A Jarvis Brain" chat.
# AGENT INSTRUCTIONS: 
# 1. Read the pending tasks below.
# 2. Process them using your advanced coding/reasoning tools.
# 3. Use the mark_task_completed function above to send your verbal response back to Sir Shakil's HUD!

if __name__ == "__main__":
    while True:
        pending = get_pending_tasks()
        if pending:
            for task in pending:
                print(f"\n[*] NEW DIRECTIVE FROM HUD [Task {task['id']}]:")
                print(f"   \"{task['directive']}\"")
                print("   Agent: Please process this directive and formulate a response.")
                mark_task_in_progress(task["id"])
                
                # Stop the loop here so the Antigravity Agent can take over and execute tools!
                # The agent should write a python script to call mark_task_completed when done.
                exit(0)
        time.sleep(2)
