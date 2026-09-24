"""
J.A.R.V.I.S. Mark XVII — Persistent Task Orchestration Subsystem
=================================================================
Manages long-running background tasks, scheduling, pause/resume,
approval gates, failure recovery, and restart safety.
"""

import json
import time
import asyncio
from typing import Dict, List, Optional, Any, Callable

from core.family_safety.storage import family_storage
from core.family_safety.models import RemoteTaskRecord, TaskStatus

class PersistentTaskManager:
    def __init__(self, storage=None):
        self.storage = storage or family_storage
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._recover_stale_tasks_on_startup()

    def _recover_stale_tasks_on_startup(self):
        """Inspects database for tasks left in 'running' state across server restarts."""
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM remote_tasks WHERE status = 'running'")
            rows = cursor.fetchall()
            for r in rows:
                task_id = r["task_id"]
                cursor.execute("""
                    UPDATE remote_tasks 
                    SET status = 'paused', error = 'Host process restarted during execution. Safe resume available.', updated_at = ?
                    WHERE task_id = ?
                """, (time.time(), task_id))
            conn.commit()

    def create_task(self, owner_id: str, title: str, description: str = "",
                    priority: int = 1, schedule: Optional[str] = None,
                    required_permissions: Optional[List[str]] = None) -> Dict[str, Any]:
        """Registers a new approved persistent background task."""
        task = RemoteTaskRecord(
            ownerId=owner_id,
            title=title,
            description=description,
            priority=priority,
            schedule=schedule,
            requiredPermissions=required_permissions or [],
            status=TaskStatus.QUEUED
        )
        task_dict = task.model_dump()
        self._save_task_record(task_dict)

        self.storage.log_audit(
            event_type="REMOTE_TASK_CREATED",
            actor_id=owner_id,
            target_id=task.taskId,
            action=f"Created task '{title}' (Priority: {priority})",
            risk_level="LOW"
        )
        return {"success": True, "task": task_dict}

    def start_task(self, task_id: str, coroutine_fn: Optional[Callable] = None, *args, **kwargs) -> Dict[str, Any]:
        """Transitions a task into 'running' status and attaches asyncio execution."""
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": "Task not found."}

        task["status"] = TaskStatus.RUNNING.value
        task["startedAt"] = time.time()
        task["updatedAt"] = time.time()
        self._save_task_record(task)

        if coroutine_fn:
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

            if loop and loop.is_running():
                t = asyncio.create_task(self._task_runner_wrapper(task_id, coroutine_fn, *args, **kwargs))
                self.running_tasks[task_id] = t

        return {"success": True, "task": task}

    async def _task_runner_wrapper(self, task_id: str, fn: Callable, *args, **kwargs):
        try:
            result = await fn(*args, **kwargs)
            self.complete_task(task_id, result={"output": result})
        except asyncio.CancelledError:
            self.cancel_task(task_id, reason="Task cancelled by user.")
        except Exception as e:
            self.fail_task(task_id, error=str(e))
        finally:
            self.running_tasks.pop(task_id, None)

    def pause_task(self, task_id: str, reason: str = "User paused task") -> Dict[str, Any]:
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": "Task not found."}

        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            self.running_tasks.pop(task_id, None)

        task["status"] = TaskStatus.PAUSED.value
        task["updatedAt"] = time.time()
        task["error"] = reason
        self._save_task_record(task)
        return {"success": True, "task": task}

    def resume_task(self, task_id: str) -> Dict[str, Any]:
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": "Task not found."}

        task["status"] = TaskStatus.QUEUED.value
        task["updatedAt"] = time.time()
        task["error"] = None
        self._save_task_record(task)
        return {"success": True, "task": task}

    def cancel_task(self, task_id: str, reason: str = "User cancelled task") -> Dict[str, Any]:
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": "Task not found."}

        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            self.running_tasks.pop(task_id, None)

        task["status"] = TaskStatus.CANCELLED.value
        task["updatedAt"] = time.time()
        task["cancellationState"] = {"reason": reason, "cancelledAt": time.time()}
        self._save_task_record(task)
        return {"success": True, "task": task}

    def complete_task(self, task_id: str, result: Optional[Dict[str, Any]] = None):
        task = self.get_task(task_id)
        if task:
            task["status"] = TaskStatus.COMPLETED.value
            task["progress"] = 1.0
            task["lastResult"] = result or {}
            task["updatedAt"] = time.time()
            self._save_task_record(task)

    def fail_task(self, task_id: str, error: str):
        task = self.get_task(task_id)
        if task:
            task["status"] = TaskStatus.FAILED.value
            task["error"] = error
            task["updatedAt"] = time.time()
            self._save_task_record(task)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM remote_tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_task(row)

    def list_tasks(self, owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            if owner_id:
                cursor.execute("SELECT * FROM remote_tasks WHERE owner_id = ? ORDER BY created_at DESC", (owner_id,))
            else:
                cursor.execute("SELECT * FROM remote_tasks ORDER BY created_at DESC")
            return [self._row_to_task(r) for r in cursor.fetchall()]

    def _save_task_record(self, t: Dict[str, Any]):
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO remote_tasks (
                    task_id, owner_id, title, description, status, priority,
                    created_at, started_at, updated_at, next_run_at, schedule,
                    progress, required_permissions, tools_used, last_result,
                    error, cancellation_state, audit_trail
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status=excluded.status,
                    priority=excluded.priority,
                    started_at=excluded.started_at,
                    updated_at=excluded.updated_at,
                    next_run_at=excluded.next_run_at,
                    progress=excluded.progress,
                    tools_used=excluded.tools_used,
                    last_result=excluded.last_result,
                    error=excluded.error,
                    cancellation_state=excluded.cancellation_state,
                    audit_trail=excluded.audit_trail
            """, (
                t["taskId"], t["ownerId"], t["title"], t.get("description", ""),
                t["status"], t.get("priority", 1), t["createdAt"], t.get("startedAt"),
                t["updatedAt"], t.get("nextRunAt"), t.get("schedule"),
                t.get("progress", 0.0), json.dumps(t.get("requiredPermissions", [])),
                json.dumps(t.get("toolsUsed", [])), json.dumps(t.get("lastResult", {})),
                t.get("error"), json.dumps(t.get("cancellationState", {})),
                json.dumps(t.get("auditTrail", []))
            ))
            conn.commit()

    def _row_to_task(self, r) -> Dict[str, Any]:
        return {
            "taskId": r["task_id"],
            "ownerId": r["owner_id"],
            "title": r["title"],
            "description": r["description"],
            "status": r["status"],
            "priority": r["priority"],
            "createdAt": r["created_at"],
            "startedAt": r["started_at"],
            "updatedAt": r["updated_at"],
            "nextRunAt": r["next_run_at"],
            "schedule": r["schedule"],
            "progress": r["progress"],
            "requiredPermissions": json.loads(r["required_permissions"] or "[]"),
            "toolsUsed": json.loads(r["tools_used"] or "[]"),
            "lastResult": json.loads(r["last_result"] or "{}"),
            "error": r["error"],
            "cancellationState": json.loads(r["cancellation_state"] or "{}"),
            "auditTrail": json.loads(r["audit_trail"] or "[]")
        }

persistent_task_manager = PersistentTaskManager()
