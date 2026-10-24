from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from .core import (
    _iter_project_files,
    _safe_workspace_path,
    _validate_text,
    _workspace_relative,
    _workspace_root,
)

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
        "aiden_env.example",
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
