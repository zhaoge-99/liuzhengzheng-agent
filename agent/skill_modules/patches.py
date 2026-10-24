from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .core import _workspace_root

def apply_patch(patch: str, confirm: bool = False) -> str:
    if not isinstance(patch, str) or not patch.strip() or len(patch) > 100_000:
        raise ValueError("Patch is empty or too large")
    if not confirm:
        return json.dumps(
            {"status": "confirmation_required", "message": "Set confirm=true only after reviewing the patch."},
            ensure_ascii=False,
        )
    if not patch.startswith("diff --git "):
        raise ValueError("Only a unified or git patch is supported")
    paths = _validate_patch_paths(patch)
    if len(set(paths)) > 20:
        raise ValueError("Patch changes too many files")
    check = _git_patch(patch)
    if check.returncode != 0:
        return json.dumps({"status": "rejected", "message": "Patch did not validate safely."}, ensure_ascii=False)
    try:
        completed = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "-"],
            cwd=str(_workspace_root()),
            input=patch,
            capture_output=True,
            text=True,
            timeout=15,
            shell=False,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Patch application failed") from error
    if completed.returncode != 0:
        return json.dumps(
            {"status": "rejected", "message": "Patch did not apply cleanly."},
            ensure_ascii=False,
        )
    return json.dumps({"status": "applied"}, ensure_ascii=False)

def _validate_patch_paths(patch: str) -> list[str]:
    paths = []
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:].strip()
            if path == "/dev/null" or path.startswith("../") or "/../" in path or Path(path).is_absolute():
                raise ValueError("Patch contains an unsafe path")
            protected_config = "aiden_env" in Path(path).parts
            if protected_config or path in {".git", "SECURITY-REVIEW.md"}:
                raise ValueError("Patch targets a protected file")
            paths.append(path)
    if not paths:
        raise ValueError("Patch contains no file paths")
    return paths

def _git_patch(patch: str, reverse: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    _validate_patch_paths(patch)
    command = ["git", "apply"]
    if check:
        command.append("--check")
    if reverse:
        command.append("--reverse")
    command.extend(["--whitespace=nowarn", "-"])
    try:
        return subprocess.run(
            command,
            cwd=str(_workspace_root()),
            input=patch,
            capture_output=True,
            text=True,
            timeout=20,
            shell=False,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Git patch operation failed") from error

def validate_patch(patch: str) -> str:
    if not isinstance(patch, str) or not patch.strip() or len(patch) > 100_000:
        raise ValueError("Patch is empty or too large")
    result = _git_patch(patch)
    return json.dumps(
        {"valid": result.returncode == 0, "message": "Patch can be applied" if result.returncode == 0 else "Patch cannot be applied safely"},
        ensure_ascii=False,
    )

def preview_patch(patch: str) -> str:
    if not isinstance(patch, str) or not patch.strip() or len(patch) > 100_000:
        raise ValueError("Patch is empty or too large")
    _validate_patch_paths(patch)
    result = _git_patch(patch)
    if result.returncode != 0:
        return json.dumps({"valid": False, "message": "Patch cannot be previewed safely"}, ensure_ascii=False)
    files = []
    additions = 0
    deletions = 0
    current_file = None
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            files.append(current_file)
        elif current_file and line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif current_file and line.startswith("-") and not line.startswith("---"):
            deletions += 1
    return json.dumps(
        {
            "valid": True,
            "files": files,
            "files_changed": len(files),
            "additions": additions,
            "deletions": deletions,
        },
        ensure_ascii=False,
    )

def rollback_patch(patch: str, confirm: bool = False) -> str:
    if not confirm:
        return json.dumps({"status": "confirmation_required"}, ensure_ascii=False)
    if not isinstance(patch, str) or not patch.strip() or len(patch) > 100_000:
        raise ValueError("Patch is empty or too large")
    check = _git_patch(patch, reverse=True)
    if check.returncode != 0:
        return json.dumps({"status": "rejected", "message": "Patch cannot be safely rolled back"}, ensure_ascii=False)
    result = _git_patch(patch, reverse=True, check=False)
    return json.dumps({"status": "rolled_back" if result.returncode == 0 else "failed"}, ensure_ascii=False)
