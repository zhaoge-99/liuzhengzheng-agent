"""Compatibility facade for built-in Agent skills.

Implementations are organized by responsibility in :mod:`agent.skill_modules`.
"""

from .skill_modules.basic import (
    _BINARY_OPERATORS,
    _UNARY_OPERATORS,
    _evaluate,
    calculate,
    get_current_time,
    get_runtime_info,
    get_weather,
    get_workspace_info,
)
from .skill_modules.core import (
    _iter_project_files,
    _safe_workspace_path,
    _validate_text,
    _workspace_relative,
    _workspace_root,
)
from .skill_modules.files import (
    check_python_syntax,
    inspect_python_file,
    list_files,
    read_text_file,
    search_text,
)
from .skill_modules.patches import (
    _git_patch,
    _validate_patch_paths,
    apply_patch,
    preview_patch,
    rollback_patch,
    validate_patch,
)
from .skill_modules.project import (
    analyze_project,
    detect_dangerous_code,
    find_symbol,
    list_project_structure,
    read_config_file,
)
from .skill_modules.quality import (
    _run_fixed_tool,
    _safe_subprocess_env,
    detect_secrets,
    run_linter,
    run_python_tests,
    run_quality_checks,
    run_type_checker,
)
from .skill_modules.tasks import (
    _load_tasks,
    _tasks_file,
    create_task,
    get_active_tasks,
    list_tasks,
    update_task,
)
from .skill_modules.web import _is_public_host, fetch_webpage
