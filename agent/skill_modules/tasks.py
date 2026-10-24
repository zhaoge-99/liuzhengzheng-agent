from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .core import _validate_text, _workspace_root

def _tasks_file() -> Path:
    return _workspace_root() / ".agent_tasks.json"

def _load_tasks() -> list[dict[str, Any]]:
    file_path = _tasks_file()
    if not file_path.exists():
        return []
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("Task store is invalid") from error
    if not isinstance(data, list):
        raise RuntimeError("Task store is invalid")
    return data

def create_task(title: str, description: str = "", priority: str = "normal") -> str:
    title = _validate_text(title, "title", max_length=200)
    description = description.strip() if isinstance(description, str) else ""
    if len(description) > 2000:
        raise ValueError("Description is too long")
    if priority not in {"low", "normal", "high"}:
        raise ValueError("Priority must be low, normal, or high")
    tasks = _load_tasks()
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    task = {"id": f"task-{int(dt.datetime.now().timestamp() * 1000)}", "title": title, "description": description, "priority": priority, "status": "pending", "created_at": now}
    tasks.append(task)
    task_file = _tasks_file()
    payload = json.dumps(tasks, ensure_ascii=False, indent=2)
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=task_file.parent,
            prefix=".agent_tasks.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(payload)
            temporary_path = Path(stream.name)
        os.replace(temporary_path, task_file)
    except OSError as error:
        if "temporary_path" in locals():
            temporary_path.unlink(missing_ok=True)
        raise RuntimeError("Task store could not be updated") from error
    return json.dumps(task, ensure_ascii=False)

def update_task(task_id: str, status: str = "", note: str = "") -> str:
    task_id = _validate_text(task_id, "task_id", max_length=100)
    if status and status not in {"pending", "in_progress", "done", "cancelled"}:
        raise ValueError("Invalid task status")
    if not isinstance(note, str) or len(note) > 2000:
        raise ValueError("Note is too long")
    tasks = _load_tasks()
    for task in tasks:
        if task.get("id") != task_id:
            continue
        if status:
            task["status"] = status
        if note.strip():
            task["notes"] = note.strip()
        task["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        task_file = _tasks_file()
        payload = json.dumps(tasks, ensure_ascii=False, indent=2)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=task_file.parent,
                prefix=".agent_tasks.", suffix=".tmp", delete=False,
            ) as stream:
                stream.write(payload)
                temporary_path = Path(stream.name)
            os.replace(temporary_path, task_file)
        except OSError as error:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise RuntimeError("Task store could not be updated") from error
        return json.dumps(task, ensure_ascii=False)
    raise ValueError("Task does not exist")

def list_tasks(status: str = "") -> str:
    if status and status not in {"pending", "in_progress", "done", "cancelled"}:
        raise ValueError("Invalid task status")
    tasks = _load_tasks()
    if status:
        tasks = [task for task in tasks if task.get("status") == status]
    return json.dumps({"tasks": tasks}, ensure_ascii=False)

def get_active_tasks() -> str:
    tasks = _load_tasks()
    active = [
        task for task in tasks
        if task.get("status") in {"pending", "in_progress"}
    ]
    return json.dumps(
        {"tasks": active[:20], "count": len(active)},
        ensure_ascii=False,
    )
