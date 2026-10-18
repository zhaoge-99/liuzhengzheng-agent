import json
import inspect
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

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气。只返回天气数据，不执行其他操作。",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名称"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算基础数学表达式，不访问文件、网络或系统。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "例如 (12 + 3) * 4"}
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "查询指定时区的当前时间，例如 Asia/Shanghai。",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "IANA 时区，默认 Asia/Shanghai",
                    }
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_workspace_info",
            "description": "返回 Agent 当前配置的工作区绝对路径和目录状态，只读。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_runtime_info",
            "description": "返回当前工作区、模型配置和运行环境信息，自动隐藏 API Key 内容，只读。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_text_file",
            "description": "读取工作区内的 UTF-8 文本文件，只读，不写入或删除文件。",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "工作区内相对路径"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": "在工作区内搜索文本，只读，不执行文件内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "root": {"type": "string", "description": "工作区内目录相对路径"},
                    "query": {"type": "string", "description": "要搜索的文本"},
                    "file_pattern": {"type": "string", "description": "文件匹配模式，例如 *.py"},
                },
                "required": ["root", "query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_python_file",
            "description": "分析 Python 文件的导入、函数和类，只读且不会执行代码。",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Python 文件相对路径"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_webpage",
            "description": "读取公开网页文本，只允许 HTTP(S) 公网地址，不访问本机或内网。",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "公开网页 URL"}},
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出工作区文件，只读，不执行文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "root": {"type": "string", "description": "工作区内目录相对路径，默认 ."},
                    "recursive": {"type": "boolean", "description": "是否递归列出，默认 true"},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_python_syntax",
            "description": "检查 Python 文件或目录的语法，只读，不执行代码。",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "文件或目录相对路径，默认 ."}},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python_tests",
            "description": "运行受限的 Python unittest 或 pytest 测试，禁止自定义 Shell 命令。",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_path": {"type": "string", "description": "测试目录或文件相对路径"},
                    "framework": {"type": "string", "enum": ["unittest", "pytest"]},
                    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 120},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_secrets",
            "description": "扫描工作区中疑似 API Key、Token、密码和私钥，只读并自动脱敏结果。",
            "parameters": {
                "type": "object",
                "properties": {"root": {"type": "string", "description": "工作区内目录相对路径，默认 ."}},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_patch",
            "description": "应用用户明确确认过的 unified/git patch。会修改文件，必须传 confirm=true。",
            "parameters": {
                "type": "object",
                "properties": {
                    "patch": {"type": "string", "description": "unified diff 或 git patch"},
                    "confirm": {"type": "boolean", "description": "用户是否已明确确认应用该补丁"},
                },
                "required": ["patch", "confirm"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_project",
            "description": "只读分析项目类型、文件结构、顶层配置和 Python 导入，为规划编程任务提供上下文。",
            "parameters": {
                "type": "object",
                "properties": {
                    "root": {"type": "string", "description": "工作区内项目目录，默认 ."}
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_project_structure",
            "description": "列出项目目录结构、文件类型和文件大小，只读。",
            "parameters": {
                "type": "object",
                "properties": {
                    "root": {"type": "string", "description": "工作区内项目目录，默认 ."},
                    "max_depth": {"type": "integer", "minimum": 0, "maximum": 8},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_config_file",
            "description": "读取安全的项目配置文件，并自动脱敏密钥。禁止读取 ..env。",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "例如 README.md 或 requirements.txt"}},
                "required": ["name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_symbol",
            "description": "在 Python 文件中查找函数或类定义，只读不执行代码。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Python 文件相对路径"},
                    "symbol": {"type": "string", "description": "符号名，留空则列出全部函数和类"},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_dangerous_code",
            "description": "扫描 Python 中的 eval、exec、命令执行和不安全反序列化调用，只读。",
            "parameters": {
                "type": "object",
                "properties": {"root": {"type": "string", "description": "工作区内目录，默认 ."}},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_linter",
            "description": "运行固定白名单中的 Python linter，不接受自定义命令参数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件或目录相对路径"},
                    "linter": {"type": "string", "enum": ["ruff", "flake8", "pylint"]},
                    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 120},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_type_checker",
            "description": "运行固定白名单中的 Python 类型检查器，不接受自定义命令参数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件或目录相对路径"},
                    "checker": {"type": "string", "enum": ["mypy", "pyright"]},
                    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 120},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_patch",
            "description": "检查补丁是否能安全应用，不会修改文件。",
            "parameters": {
                "type": "object",
                "properties": {"patch": {"type": "string", "description": "标准 Git patch"}},
                "required": ["patch"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "preview_patch",
            "description": "预览补丁的修改统计，不会修改文件。",
            "parameters": {
                "type": "object",
                "properties": {"patch": {"type": "string", "description": "标准 Git patch"}},
                "required": ["patch"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rollback_patch",
            "description": "反向应用已确认的标准 Git patch，撤销该补丁造成的修改。",
            "parameters": {
                "type": "object",
                "properties": {
                    "patch": {"type": "string", "description": "需要反向应用的原始 Git patch"},
                    "confirm": {"type": "boolean", "description": "用户是否明确确认回滚"},
                },
                "required": ["patch", "confirm"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "在工作区任务清单中创建任务。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "任务标题"},
                    "description": {"type": "string", "description": "任务描述"},
                    "priority": {"type": "string", "enum": ["low", "normal", "high"]},
                },
                "required": ["title"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "更新工作区任务的状态或记录执行备注。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "任务 ID"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "done", "cancelled"]},
                    "note": {"type": "string", "description": "本次执行结果或阻塞原因"},
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_tasks",
            "description": "读取工作区中尚未完成的任务，用于恢复中断后的工作上下文。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_quality_checks",
            "description": "运行 Python 语法检查、unittest 测试，可选运行白名单 linter。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "检查目录或文件"},
                    "test_path": {"type": "string", "description": "测试目录或文件"},
                    "run_linter": {"type": "boolean", "description": "是否运行 linter"},
                    "linter": {"type": "string", "enum": ["ruff", "flake8", "pylint"]},
                    "run_type_check": {"type": "boolean", "description": "是否运行类型检查"},
                    "type_checker": {"type": "string", "enum": ["mypy", "pyright"]},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "读取工作区任务清单。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "in_progress", "done", "cancelled"]},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
]


def execute_tool(tool_name: str, arguments_json: str) -> str:
    """
    根据模型请求执行工具。
    注意:
    不使用eval,也不允许模型调用任意Python函数。
    只能调用TOOL_FUNCTIONS中注册过的工具。
    """
    if tool_name not in TOOL_FUNCTIONS:
        return "错误:请求的工具不在允许列表中"
    if tool_name not in TOOL_PERMISSIONS["read"] | TOOL_PERMISSIONS["write"]:
        return "错误:工具没有配置权限级别"
    max_arguments_length = 120_000 if tool_name in {"apply_patch", "validate_patch", "preview_patch", "rollback_patch"} else 4_000
    if not isinstance(arguments_json, str) or len(arguments_json) > max_arguments_length:
        return "错误:工具参数过长或格式不正确"

    try:
        arguments = json.loads(arguments_json)
    except json.JSONDecodeError:
        return "错误:模型返回的工具参数不是有效JSON格式"

    if not isinstance(arguments, dict):
        return "错误:工具参数必须是JSON对象"

    function = TOOL_FUNCTIONS[tool_name]

    try:
        inspect.signature(function).bind(**arguments)
        result = function(**arguments)
    except TypeError:
        return "错误:工具参数不正确"
    except ValueError as error:
        return f"错误:参数或路径无效（{type(error).__name__}）"
    except RuntimeError as error:
        return f"错误:工具运行失败（{type(error).__name__}）"
    except OSError as error:
        return f"错误:文件或系统操作失败（{type(error).__name__}）"
    except Exception as error:
        return f"错误:工具执行失败（{type(error).__name__}）"

    result_text = str(result)
    if len(result_text) > 6000:
        return "错误:工具返回结果过大"
    return result_text
