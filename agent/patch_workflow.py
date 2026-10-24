from __future__ import annotations

import json
from typing import Any

from agent import Execute_Tool
from agent.AgentState import AgentState, StateMachine
from agent.AuditLog import record

def _post_change_validation() -> dict[str, Any]:
    return json.loads(
        Execute_Tool.execute_tool(
            "run_quality_checks",
            '{"path":".","test_path":".","run_linter":false}',
        )
    )

def _confirmation(prompt: str) -> bool:
    try:
        answer = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in {"y", "yes", "是", "确认"}

def execute_mutating_tool(
    tool_name: str,
    arguments_json: str,
    state_machine: StateMachine,
) -> str:
    if state_machine.state == AgentState.IDLE:
        state_machine.transition(AgentState.PLANNING)
        state_machine.transition(AgentState.ANALYZING)
    try:
        arguments = json.loads(arguments_json)
    except json.JSONDecodeError:
        return Execute_Tool.execute_tool(tool_name, arguments_json)
    if not isinstance(arguments, dict):
        return Execute_Tool.execute_tool(tool_name, arguments_json)

    patch = arguments.get("patch")
    if not isinstance(patch, str):
        return json.dumps(
            {"status": "error", "code": "invalid_patch", "message": "补丁参数无效"},
            ensure_ascii=False,
        )

    if tool_name == "apply_patch":
        record("patch_requested", tool=tool_name)
        preview = Execute_Tool.execute_tool(
            "preview_patch",
            json.dumps({"patch": patch}, ensure_ascii=False),
        )
        validation = Execute_Tool.execute_tool(
            "validate_patch",
            json.dumps({"patch": patch}, ensure_ascii=False),
        )
        print(f"[Agent]补丁预览:{preview}")
        print(f"[Agent]补丁校验:{validation}")
        try:
            if not json.loads(validation).get("valid", False):
                return json.dumps(
                    {"status": "rejected", "reason": "补丁未通过校验"},
                    ensure_ascii=False,
                )
        except json.JSONDecodeError:
            return json.dumps(
                {"status": "rejected", "reason": "补丁校验结果无效"},
                ensure_ascii=False,
            )
        record("patch_reviewed", tool=tool_name, validation=validation)
        if state_machine.state != AgentState.WAITING_CONFIRMATION:
            state_machine.transition(AgentState.WAITING_CONFIRMATION)
        if not _confirmation("[Agent]补丁将修改项目文件，确认应用吗？(y/N): "):
            record("patch_cancelled", tool=tool_name)
            state_machine.transition(AgentState.COMPLETED)
            return json.dumps({"status": "cancelled"}, ensure_ascii=False)

        state_machine.transition(AgentState.APPLYING)
        record("patch_applying", tool=tool_name)
        result = Execute_Tool.execute_tool(
            "apply_patch",
            json.dumps({"patch": patch, "confirm": True}, ensure_ascii=False),
        )
        try:
            applied = json.loads(result).get("status") == "applied"
        except json.JSONDecodeError:
            applied = False
        if not applied:
            state_machine.transition(AgentState.FAILED)
            record("patch_failed", tool=tool_name, result=result)
            return result

        state_machine.transition(AgentState.VALIDATING)
        record("validation_started", tool=tool_name)
        checks = _post_change_validation()
        if checks["passed"]:
            state_machine.transition(AgentState.COMPLETED)
            record("validation_passed", tool=tool_name, validation=checks)
            return json.dumps(
                {"status": "applied", "validation": checks},
                ensure_ascii=False,
            )

        state_machine.transition(AgentState.ROLLING_BACK)
        record("rollback_started", tool=tool_name, validation=checks)
        rollback = Execute_Tool.execute_tool(
            "rollback_patch",
            json.dumps({"patch": patch, "confirm": True}, ensure_ascii=False),
        )
        state_machine.transition(AgentState.COMPLETED)
        record("rollback_finished", tool=tool_name, rollback=rollback)
        return json.dumps(
            {
                "status": "rolled_back_after_failed_validation",
                "validation": checks,
                "rollback": rollback,
            },
            ensure_ascii=False,
        )

    if not _confirmation("[Agent]确认回滚这个补丁吗？(y/N): "):
        if state_machine.state == AgentState.WAITING_CONFIRMATION:
            state_machine.transition(AgentState.COMPLETED)
        return json.dumps({"status": "cancelled"}, ensure_ascii=False)
    if state_machine.state == AgentState.ANALYZING:
        state_machine.transition(AgentState.WAITING_CONFIRMATION)
    state_machine.transition(AgentState.APPLYING)
    record("rollback_requested", tool=tool_name)
    return Execute_Tool.execute_tool(
        tool_name,
        json.dumps({"patch": patch, "confirm": True}, ensure_ascii=False),
    )
