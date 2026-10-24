from __future__ import annotations

import os
from pathlib import Path

def _validate_text(value: str, field_name: str, max_length: int = 100) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    value = value.strip()
    if not value or len(value) > max_length or any(ord(char) < 32 for char in value):
        raise ValueError(f"{field_name} is invalid")
    return value

def _workspace_root() -> Path:
    root = Path(os.getenv("AGENT_WORKSPACE", Path.cwd())).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError("Workspace directory is not available")
    return root

def _safe_workspace_path(path: str) -> Path:
    path = _validate_text(path, "path", max_length=260)
    root = _workspace_root()
    candidate = (root / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("Path is outside the configured workspace") from error
    return candidate

def _workspace_relative(path: Path) -> str:
    return str(path.relative_to(_workspace_root()))

def _iter_project_files(root: Path):
    ignored_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules"}
    for path in root.rglob("*"):
        if path.is_file() and not any(part in ignored_dirs for part in path.parts):
            yield path
