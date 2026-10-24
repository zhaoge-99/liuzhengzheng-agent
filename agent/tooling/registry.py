from __future__ import annotations

from typing import Any, Callable

from agent import Skills

TOOL_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "get_weather": Skills.get_weather,
    "calculate": Skills.calculate,
    "get_current_time": Skills.get_current_time,
    "get_workspace_info": Skills.get_workspace_info,
    "get_runtime_info": Skills.get_runtime_info,
    "read_text_file": Skills.read_text_file,
    "search_text": Skills.search_text,
    "inspect_python_file": Skills.inspect_python_file,
    "fetch_webpage": Skills.fetch_webpage,
    "list_files": Skills.list_files,
    "check_python_syntax": Skills.check_python_syntax,
    "run_python_tests": Skills.run_python_tests,
    "detect_secrets": Skills.detect_secrets,
    "apply_patch": Skills.apply_patch,
    "list_project_structure": Skills.list_project_structure,
    "analyze_project": Skills.analyze_project,
    "read_config_file": Skills.read_config_file,
    "find_symbol": Skills.find_symbol,
    "detect_dangerous_code": Skills.detect_dangerous_code,
    "run_linter": Skills.run_linter,
    "run_type_checker": Skills.run_type_checker,
    "validate_patch": Skills.validate_patch,
    "preview_patch": Skills.preview_patch,
    "rollback_patch": Skills.rollback_patch,
    "create_task": Skills.create_task,
    "update_task": Skills.update_task,
    "list_tasks": Skills.list_tasks,
    "get_active_tasks": Skills.get_active_tasks,
    "run_quality_checks": Skills.run_quality_checks,
}

TOOL_PERMISSIONS = {
    "read": {
        "get_weather", "calculate", "get_current_time", "read_text_file",
        "get_workspace_info",
        "get_runtime_info",
        "search_text", "inspect_python_file", "fetch_webpage", "list_files",
        "check_python_syntax", "run_python_tests", "detect_secrets",
        "list_project_structure", "analyze_project", "read_config_file",
        "find_symbol", "detect_dangerous_code", "run_linter",
        "run_type_checker", "validate_patch", "preview_patch",
        "list_tasks", "get_active_tasks", "run_quality_checks",
    },
    "write": {"apply_patch", "rollback_patch", "create_task", "update_task"},
}
