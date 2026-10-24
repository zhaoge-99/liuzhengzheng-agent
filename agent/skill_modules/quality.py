from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from .core import _safe_workspace_path, _workspace_root
from .files import check_python_syntax

def run_python_tests(test_path: str = ".", framework: str = "unittest", timeout_seconds: int = 30) -> str:
    test_path = _safe_workspace_path(test_path)
    if not test_path.exists():
        raise ValueError("Test path does not exist")
    if framework not in {"unittest", "pytest"}:
        raise ValueError("Only unittest and pytest are supported")
    if not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 120:
        raise ValueError("timeout_seconds must be between 1 and 120")

    if framework == "unittest":
        command = [sys.executable, "-m", "unittest", "discover", "-s", str(test_path)]
    else:
        command = [sys.executable, "-m", "pytest", str(test_path), "--maxfail=1", "-q"]
    try:
        completed = subprocess.run(
            command,
            cwd=str(_workspace_root()),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
            check=False,
            env=_safe_subprocess_env(),
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "timeout", "timeout_seconds": timeout_seconds}, ensure_ascii=False)
    except OSError as error:
        raise RuntimeError("Test runner is unavailable") from error

    output = (completed.stdout + "\n" + completed.stderr).strip()
    return json.dumps(
        {
            "status": "passed" if completed.returncode == 0 else "failed",
            "return_code": completed.returncode,
            "output": output[-12000:],
        },
        ensure_ascii=False,
    )

def detect_secrets(root: str = ".") -> str:
    search_root = _safe_workspace_path(root)
    if not search_root.is_dir():
        raise ValueError("Directory does not exist")
    patterns = {
        "api_key_assignment": re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?([A-Za-z0-9_./+=-]{8,})"),
        "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        "known_key_prefix": re.compile(r"\b(?:sk|ghp|github_pat|AKIA)[A-Za-z0-9_-]{10,}\b"),
    }
    ignored_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules"}
    findings = []
    for file_path in search_root.rglob("*"):
        if len(findings) >= 100 or not file_path.is_file() or any(part in ignored_dirs for part in file_path.parts):
            continue
        try:
            if file_path.stat().st_size > 500_000:
                continue
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, 1):
            for kind, pattern in patterns.items():
                if pattern.search(line):
                    findings.append(
                        {
                            "path": str(file_path.relative_to(_workspace_root())),
                            "line": line_number,
                            "type": kind,
                            "snippet": pattern.sub("[REDACTED]", line[:300]),
                        }
                    )
                    break
    return json.dumps({"findings": findings}, ensure_ascii=False)

def _run_fixed_tool(tool: str, target: str, timeout_seconds: int, args: list[str]) -> str:
    target_path = _safe_workspace_path(target)
    if not target_path.exists():
        raise ValueError("Target path does not exist")
    if not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 120:
        raise ValueError("timeout_seconds must be between 1 and 120")
    try:
        completed = subprocess.run(
            [sys.executable, "-m", tool, *args, str(target_path)],
            cwd=str(_workspace_root()),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
            check=False,
            env=_safe_subprocess_env(),
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"tool": tool, "status": "timeout"}, ensure_ascii=False)
    except OSError as error:
        raise RuntimeError(f"{tool} is unavailable") from error
    output = (completed.stdout + "\n" + completed.stderr).strip()
    return json.dumps(
        {"tool": tool, "status": "passed" if completed.returncode == 0 else "failed", "return_code": completed.returncode, "output": output[-12000:]},
        ensure_ascii=False,
    )

def _safe_subprocess_env() -> dict[str, str]:
    allowed = {"PATH", "PATHEXT", "SystemRoot", "SYSTEMROOT", "TEMP", "TMP"}
    environment = {key: value for key, value in os.environ.items() if key in allowed}
    environment["AGENT_WORKSPACE"] = str(_workspace_root())
    return environment

def run_linter(path: str = ".", linter: str = "ruff", timeout_seconds: int = 60) -> str:
    if linter not in {"ruff", "flake8", "pylint"}:
        raise ValueError("Only ruff, flake8, and pylint are supported")
    return _run_fixed_tool(linter, path, timeout_seconds, ["--output-format", "text"] if linter == "ruff" else [])

def run_type_checker(path: str = ".", checker: str = "mypy", timeout_seconds: int = 60) -> str:
    if checker not in {"mypy", "pyright"}:
        raise ValueError("Only mypy and pyright are supported")
    return _run_fixed_tool(checker, path, timeout_seconds, [])

def run_quality_checks(
    path: str = ".",
    test_path: str = ".",
    run_linter: bool = False,
    linter: str = "ruff",
    run_type_check: bool = False,
    type_checker: str = "mypy",
) -> str:
    syntax = json.loads(check_python_syntax(path))
    tests = json.loads(run_python_tests(test_path, "unittest", 60))
    no_tests = (
        tests.get("return_code") == 5
        and "NO TESTS RAN" in tests.get("output", "")
    )
    result: dict[str, Any] = {
        "syntax": syntax,
        "tests": tests,
        "linter": None,
        "type_checker": None,
    }
    passed = syntax.get("invalid", 1) == 0 and (
        tests.get("status") == "passed" or no_tests
    )
    if run_linter:
        lint_result = json.loads(
            globals()["run_linter"](path, linter, 60)
        )
        result["linter"] = lint_result
        passed = passed and lint_result.get("status") == "passed"
    if run_type_check:
        type_result = json.loads(
            run_type_checker(path, type_checker, 60)
        )
        result["type_checker"] = type_result
        passed = passed and type_result.get("status") == "passed"
    result["passed"] = passed
    return json.dumps(result, ensure_ascii=False)
