from __future__ import annotations

import ast
import json
from pathlib import Path

from .core import _safe_workspace_path, _workspace_root

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
