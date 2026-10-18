import ast
import datetime as dt
import json
import operator
import os
import ipaddress
import socket
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from typing import Any
import requests


def _validate_text(value: str, field_name: str, max_length: int = 100) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    value = value.strip()
    if not value or len(value) > max_length or any(ord(char) < 32 for char in value):
        raise ValueError(f"{field_name} is invalid")
    return value


def get_weather(city: str) -> str:
    city = _validate_text(city, "city")
    api_key = os.getenv("WEATHER_API_KEY") or os.getenv("weather_api_key")
    if not api_key:
        raise ValueError("Weather API key is not configured")

    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": city,
                "appid": api_key,
                "units": "metric",
                "lang": "zh_cn",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        raise RuntimeError("Weather service request failed") from error
    except (ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("Weather service returned invalid data") from error

    return json.dumps(
        {
            "city": data.get("name", city),
            "country": data.get("sys", {}).get("country"),
            "temperature_c": data.get("main", {}).get("temp"),
            "feels_like_c": data.get("main", {}).get("feels_like"),
            "humidity_percent": data.get("main", {}).get("humidity"),
            "description": (data.get("weather") or [{}])[0].get("description"),
        },
        ensure_ascii=False,
    )


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        if isinstance(node.value, bool):
            raise ValueError("Boolean values are not supported")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("Exponent is too large")
        result = _BINARY_OPERATORS[type(node.op)](left, right)
        if abs(result) > 1e100:
            raise ValueError("Result is too large")
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate(node.operand))
    raise ValueError("Only numeric arithmetic is supported")


def calculate(expression: str) -> str:
    expression = _validate_text(expression, "expression", max_length=200)
    try:
        tree = ast.parse(expression, mode="eval")
        result = _evaluate(tree.body)
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError) as error:
        raise ValueError("Invalid arithmetic expression") from error
    return str(result)


def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    timezone = _validate_text(timezone, "timezone", max_length=64)
    try:
        current = dt.datetime.now(ZoneInfo(timezone))
    except ZoneInfoNotFoundError as error:
        raise ValueError("Unknown timezone") from error
    return current.isoformat(timespec="seconds")


def _workspace_root() -> Path:
    root = Path(os.getenv("AGENT_WORKSPACE", Path.cwd())).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError("Workspace directory is not available")
    return root


def get_workspace_info() -> str:
    root = _workspace_root()
    return json.dumps(
        {
            "workspace": str(root),
            "exists": root.exists(),
            "is_directory": root.is_dir(),
            "note": "All relative file paths are resolved under this directory.",
        },
        ensure_ascii=False,
    )


def get_runtime_info() -> str:
    root = _workspace_root()
    return json.dumps(
        {
            "workspace": str(root),
            "provider": os.getenv("MODEL_PROVIDER", "openai-compatible"),
            "model": (
                os.getenv("MODEL_NAME")
                or "gpt-4o-mini"
            ),
            "base_url": (
                os.getenv("MODEL_BASE_URL")
                or "https://api.openai.com/v1"
            ),
            "api_key_configured": bool(os.getenv("MODEL_API_KEY")),
            "weather_key_configured": bool(
                os.getenv("WEATHER_API_KEY") or os.getenv("weather_api_key")
            ),
            "python": sys.version.split()[0],
        },
        ensure_ascii=False,
    )


def _safe_workspace_path(path: str) -> Path:
    path = _validate_text(path, "path", max_length=260)
    root = _workspace_root()
    candidate = (root / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("Path is outside the configured workspace") from error
    return candidate


def read_text_file(path: str) -> str:
    file_path = _safe_workspace_path(path)
    if not file_path.is_file():
        raise ValueError("File does not exist")
    if file_path.stat().st_size > 200_000:
        raise ValueError("File is too large")
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("File is not UTF-8 text") from error
    return json.dumps(
        {"path": str(file_path), "content": content},
        ensure_ascii=False,
    )


def search_text(root: str, query: str, file_pattern: str = "*") -> str:
    search_root = _safe_workspace_path(root)
    query = _validate_text(query, "query", max_length=200)
    file_pattern = _validate_text(file_pattern, "file_pattern", max_length=80)
    if not search_root.is_dir():
        raise ValueError("Search root is not a directory")

    results = []
    ignored_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules"}
    for file_path in search_root.rglob(file_pattern):
        if len(results) >= 50:
            break
        if not file_path.is_file() or any(part in ignored_dirs for part in file_path.parts):
            continue
        try:
            if file_path.stat().st_size > 200_000:
                continue
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(content.splitlines(), 1):
            if query.casefold() in line.casefold():
                results.append(
                    {
                        "path": str(file_path.relative_to(_workspace_root())),
                        "line": line_number,
                        "text": line[:500],
                    }
                )
                if len(results) >= 50:
                    break
    return json.dumps({"matches": results}, ensure_ascii=False)


def inspect_python_file(path: str) -> str:
    file_path = _safe_workspace_path(path)
    if file_path.suffix.lower() != ".py" or not file_path.is_file():
        raise ValueError("Path must be an existing Python file")
    if file_path.stat().st_size > 200_000:
        raise ValueError("File is too large")
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError) as error:
        raise ValueError("Python file cannot be analyzed") from error

    imports = []
    functions = []
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(f"{node.module or ''}.{node.names[0].name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({"name": node.name, "line": node.lineno})
        elif isinstance(node, ast.ClassDef):
            classes.append({"name": node.name, "line": node.lineno})
    return json.dumps(
        {
            "path": str(file_path),
            "imports": sorted(set(imports)),
            "functions": functions,
            "classes": classes,
        },
        ensure_ascii=False,
    )


def list_files(root: str = ".", recursive: bool = True) -> str:
    search_root = _safe_workspace_path(root)
    if not search_root.is_dir():
        raise ValueError("Directory does not exist")

    ignored_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules"}
    paths = search_root.rglob("*") if recursive else search_root.glob("*")
    files = []
    workspace = _workspace_root()
    for path in paths:
        if len(files) >= 500:
            break
        if not path.is_file() or any(part in ignored_dirs for part in path.parts):
            continue
        files.append(str(path.relative_to(workspace)))
    return json.dumps(
        {"root": str(search_root.relative_to(workspace)), "files": files},
        ensure_ascii=False,
    )


def check_python_syntax(path: str = ".") -> str:
    target = _safe_workspace_path(path)
    python_files = [target] if target.is_file() else list(target.rglob("*.py"))
    results = []
    for file_path in python_files[:500]:
        if any(part in {".git", ".venv", "venv", "__pycache__", "node_modules"} for part in file_path.parts):
            continue
        try:
            ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
            results.append({"path": str(file_path.relative_to(_workspace_root())), "valid": True})
        except (OSError, UnicodeDecodeError) as error:
            results.append({"path": str(file_path.relative_to(_workspace_root())), "valid": False, "error": "unreadable"})
        except SyntaxError as error:
            results.append(
                {
                    "path": str(file_path.relative_to(_workspace_root())),
                    "valid": False,
                    "line": error.lineno,
                    "column": error.offset,
                    "error": error.msg,
                }
            )
    return json.dumps(
        {"checked": len(results), "invalid": sum(not item["valid"] for item in results), "results": results},
        ensure_ascii=False,
    )


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


def _workspace_relative(path: Path) -> str:
    return str(path.relative_to(_workspace_root()))


def _iter_project_files(root: Path):
    ignored_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules"}
    for path in root.rglob("*"):
        if path.is_file() and not any(part in ignored_dirs for part in path.parts):
            yield path


def list_project_structure(root: str = ".", max_depth: int = 4) -> str:
    project_root = _safe_workspace_path(root)
    if not project_root.is_dir():
        raise ValueError("Project root is not a directory")
    if not isinstance(max_depth, int) or not 0 <= max_depth <= 8:
        raise ValueError("max_depth must be between 0 and 8")

    entries = []
    workspace = _workspace_root()
    for path in project_root.rglob("*"):
        if any(part in {".git", ".venv", "venv", "__pycache__", "node_modules"} for part in path.parts):
            continue
        relative = path.relative_to(project_root)
        if len(relative.parts) > max_depth:
            continue
        item = {"path": str(path.relative_to(workspace)), "type": "directory" if path.is_dir() else "file"}
        if path.is_file():
            item["size"] = path.stat().st_size
        entries.append(item)
        if len(entries) >= 1000:
            break
    return json.dumps({"root": _workspace_relative(project_root), "entries": entries}, ensure_ascii=False)


def analyze_project(root: str = ".") -> str:
    """生成有限大小的项目概况，供模型在修改代码前建立上下文。"""
    project_root = _safe_workspace_path(root)
    if not project_root.is_dir():
        raise ValueError("Project root is not a directory")

    files = list(_iter_project_files(project_root))
    suffixes = {path.suffix.lower() for path in files}
    names = {path.name.lower() for path in files}
    project_types = []
    if ".py" in suffixes or "requirements.txt" in names or "pyproject.toml" in names:
        project_types.append("Python")
    if any(item in suffixes for item in {".js", ".jsx", ".ts", ".tsx"}) or "package.json" in names:
        project_types.append("JavaScript/TypeScript")
    if ".java" in suffixes or "pom.xml" in names or "build.gradle" in names:
        project_types.append("Java")
    if ".go" in suffixes or "go.mod" in names:
        project_types.append("Go")
    if ".rs" in suffixes or "cargo.toml" in names:
        project_types.append("Rust")

    config_names = {
        "README.md", "pyproject.toml", "requirements.txt", "package.json",
        "pom.xml", "go.mod", "Cargo.toml",
    }
    configs = []
    for path in files:
        if path.parent != project_root or path.name not in config_names:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        configs.append({"path": _workspace_relative(path), "preview": content[:1200]})

    python_files = []
    for path in files:
        if path.suffix.lower() != ".py" or len(python_files) >= 40:
            continue
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        python_files.append({
            "path": _workspace_relative(path),
            "lines": len(content.splitlines()),
            "imports": sorted(set(imports))[:20],
        })

    return json.dumps({
        "root": _workspace_relative(project_root),
        "project_types": project_types or ["Unknown"],
        "file_count": len(files),
        "files": [_workspace_relative(path) for path in files[:200]],
        "configs": configs,
        "python_files": python_files,
        "next_steps": [
            "阅读相关 README 和配置文件",
            "定位与需求直接相关的源码和测试",
            "修改前生成并校验补丁，修改后运行语法检查和测试",
        ],
    }, ensure_ascii=False)


def read_config_file(name: str) -> str:
    name = _validate_text(name, "name", max_length=100)
    allowed_names = {
        "README.md",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "setup.cfg",
        "tox.ini",
        "pytest.ini",
        "..env.example",
    }
    if Path(name).name != name or name not in allowed_names:
        raise ValueError("Only safe project configuration files can be read")
    file_path = _safe_workspace_path(name)
    if not file_path.is_file() or file_path.stat().st_size > 200_000:
        raise ValueError("Configuration file does not exist or is too large")
    content = file_path.read_text(encoding="utf-8")
    content = re.sub(
        r"(?im)^(\s*(?:export\s+)?[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*\s*=\s*).*$",
        r"\1[REDACTED]",
        content,
    )
    return json.dumps({"name": name, "content": content}, ensure_ascii=False)


def find_symbol(path: str, symbol: str = "") -> str:
    file_path = _safe_workspace_path(path)
    symbol = symbol.strip() if isinstance(symbol, str) else ""
    if not file_path.is_file() or file_path.suffix.lower() != ".py":
        raise ValueError("Path must be an existing Python file")
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except (OSError, UnicodeDecodeError, SyntaxError) as error:
        raise ValueError("Python file cannot be analyzed") from error
    matches = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not symbol or node.name == symbol:
                matches.append(
                    {
                        "name": node.name,
                        "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                        "line": node.lineno,
                        "end_line": getattr(node, "end_lineno", node.lineno),
                    }
                )
    return json.dumps({"path": _workspace_relative(file_path), "matches": matches}, ensure_ascii=False)


def detect_dangerous_code(root: str = ".") -> str:
    project_root = _safe_workspace_path(root)
    if not project_root.is_dir():
        raise ValueError("Directory does not exist")
    findings = []
    dangerous_calls = {"eval", "exec", "compile", "system", "popen", "run", "call", "check_call", "check_output"}
    for file_path in _iter_project_files(project_root):
        if file_path.suffix.lower() != ".py" or len(findings) >= 200:
            continue
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else (
                    node.func.attr if isinstance(node.func, ast.Attribute) else ""
                )
                if name in dangerous_calls:
                    findings.append({"path": _workspace_relative(file_path), "line": node.lineno, "pattern": name})
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"loads", "load"} and isinstance(node.func.value, ast.Name) and node.func.value.id in {"pickle", "dill"}:
                    findings.append({"path": _workspace_relative(file_path), "line": node.lineno, "pattern": f"{node.func.value.id}.{node.func.attr}"})
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


def _validate_patch_paths(patch: str) -> list[str]:
    paths = []
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:].strip()
            if path == "/dev/null" or path.startswith("../") or "/../" in path or Path(path).is_absolute():
                raise ValueError("Patch contains an unsafe path")
            if path.startswith("..env") or path in {".git", "SECURITY-REVIEW.md"}:
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


def _is_public_host(hostname: str) -> bool:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as error:
        raise ValueError("URL host cannot be resolved") from error
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            return False
    return True


def fetch_webpage(url: str) -> str:
    url = _validate_text(url, "url", max_length=2_000)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only HTTP(S) URLs are supported")
    if not _is_public_host(parsed.hostname):
        raise ValueError("Private or local network addresses are not allowed")

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "SafeAgent/1.0"},
            timeout=10,
            allow_redirects=False,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError("Web request failed") from error
    if len(response.content) > 500_000:
        raise ValueError("Web response is too large")
    content_type = response.headers.get("content-type", "").lower()
    if "text" not in content_type and "json" not in content_type:
        raise ValueError("URL did not return text content")
    return json.dumps(
        {
            "url": url,
            "content_type": content_type,
            "content": response.text[:100_000],
        },
        ensure_ascii=False,
    )
