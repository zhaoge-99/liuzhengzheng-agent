from __future__ import annotations

import inspect
import json
import time
from typing import Any

from agent.AuditLog import record
from .registry import TOOL_FUNCTIONS, TOOL_PERMISSIONS

def execute_tool(tool_name: str, arguments_json: str) -> str:
    """
    根据模型请求执行工具。
    注意:
    不使用eval,也不允许模型调用任意Python函数。
    只能调用TOOL_FUNCTIONS中注册过的工具。
    """
    # time.monotonic()返回一个单调递增的时间值(以秒为单位)，用于测量时间间隔
    started_at = time.monotonic()
    record("tool_execution_started", tool=tool_name, arguments=arguments_json)

    def finish(result: str, status: str) -> str:
        record(
            "tool_execution_finished",
            tool=tool_name,
            status=status,
            duration_ms=round((time.monotonic() - started_at) * 1000, 2),
            result=result,
        )
        return result

    def error(code: str, message: str) -> str:
        return finish(
            json.dumps(
                {"status": "error", "code": code, "message": message},
                ensure_ascii=False,
            ),
            "error",
        )

    if tool_name not in TOOL_FUNCTIONS:
        return error("unknown_tool", "请求的工具不在允许列表中")
    if tool_name not in TOOL_PERMISSIONS["read"] | TOOL_PERMISSIONS["write"]:
        return error("permission_unconfigured", "工具没有配置权限级别")
    max_arguments_length = 120_000 if tool_name in {"apply_patch", "validate_patch", "preview_patch", "rollback_patch"} else 4_000
    if not isinstance(arguments_json, str) or len(arguments_json) > max_arguments_length:
        return error("invalid_arguments", "工具参数过长或格式不正确")

    try:
        arguments = json.loads(arguments_json)
    except json.JSONDecodeError:
        return error("invalid_json", "模型返回的工具参数不是有效 JSON 格式")

    if not isinstance(arguments, dict):
        return error("invalid_arguments", "工具参数必须是 JSON 对象")

    function = TOOL_FUNCTIONS[tool_name]

    try:
        inspect.signature(function).bind(**arguments)
        result = function(**arguments)
    except TypeError:
        return error("invalid_arguments", "工具参数不正确")
    except ValueError as exception:
        return error("invalid_value", f"参数或路径无效（{type(exception).__name__}）")
    except RuntimeError as exception:
        return error("tool_runtime_error", f"工具运行失败（{type(exception).__name__}）")
    except OSError as exception:
        return error("system_error", f"文件或系统操作失败（{type(exception).__name__}）")
    except Exception as exception:
        return error("tool_error", f"工具执行失败（{type(exception).__name__}）")

    result_text = str(result)
    if len(result_text) > 6000:
        return error("result_too_large", "工具返回结果过大")
    return finish(result_text, "success")
