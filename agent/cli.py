from __future__ import annotations

import json

from openai import OpenAIError

from agent import Execute_Tool
from agent.AuditLog import record
from agent.ModelClient import ModelClientError
from agent.configuration import validate_configuration
from agent.session import AgentSession

def _print_help() -> None:
    print("可用命令: /workspace 工作区 | /status 状态 | /tasks 未完成任务 | /clear 清空对话 | /help 帮助 | /quit 退出")

def _handle_command(command: str, session: AgentSession) -> bool | None:
    normalized = command.strip().lower()
    if normalized in {"/quit", "/exit", "/q"}:
        print("程序已退出")
        return True
    if normalized == "/clear":
        session.clear()
        print("当前对话已清空,新对话已开启，上下文记忆已清除")
        return False
    if normalized == "/help":
        _print_help()
        return False
    if normalized == "/workspace":
        print(Execute_Tool.execute_tool("get_workspace_info", "{}"))
        return False
    if normalized == "/tasks":
        print(Execute_Tool.execute_tool("get_active_tasks", "{}"))
        return False
    if normalized == "/status":
        workspace = Execute_Tool.execute_tool("get_workspace_info", "{}")
        print(json.dumps({
            "state": session.state_machine.state.value,
            "conversation_messages": len(session.conversation_messages),
            "workspace": json.loads(workspace).get("workspace", "[unavailable]"),
            "admission": session.admission_stats(),
        }, ensure_ascii=False))
        return False
    return None

def main() -> None:
    try:
        """
        检查1:检查aiden_env文件中是否配置了MODEL_API_KEY环境变量
        检查2:检查aiden_env文件中的AGENT_MAX_ITERATIONSH和AGENT_REQUEST_TIMEOUT
        是否为处在有效范围内的可被转换为有效整数的值
        """
        validate_configuration()
        """
        下面的except专门来捕捉validate_configuration()中可能抛出的统一的RuntimeError异常，
        使程序不会因为配置问题而直接崩溃，而是给出友好的提示信息。
        """
    except RuntimeError as error:
        print(f"[Agent]{error}")
        # return的作用是:当配置文件出现问题时，直接返回，不执行后续的agent启动程序，但并不绝对意味着python进程的退出
        return
    session = AgentSession()
    print("环境配置无问题")
    print("Aiden 已启动，按 Q/q 退出")
    print("提示:用户输入和必要的工具结果可能会发送到配置的模型服务，请勿输入未脱敏的敏感信息。")
    logo = r"""
              /\
             /  \
            / /\ \
           / /  \ \
          / / /\ \ \
         / / /  \ \ \             |            | | |    |  |          | | | | | |    |             |
        /_/ /____\ \_\           | |             |      |    |        |              | |           |
        \ \ \    / / /          |   |            |      |      |      |              |   |         |
         \ \ \  / / /          |     |           |      |        |    |              |     |       |
          \ \ \/ / /         | | | | | |         |      |        |    | | | | | |    |       |     |
            \ \/ /          |           |        |      |      |      |              |         |   |
             \  /          |             |       |      |    |        |              |           | |
              \/          |               |    | | |    |  |          | | | | | |    |             |

        A   I   D   E   N
    """
    print(logo)
    while True:
        try:
            user_input = input("我:").strip()
        # 键盘中断异常:KeyboardInterrupt,当用户按下Ctrl+c时，会打印"\n程序已退出"并退出while循环
        except KeyboardInterrupt:
            print("\n程序已退出")
            break
        # EOF异常:EOFError,当用户按下Ctrl+d时，会打印"\n程序已退出"并退出while循环
        except EOFError:
            print("\n程序已退出")
            break
        if not user_input:
            continue
        command_result = _handle_command(user_input, session)
        if command_result is True:
            break
        if command_result is False:
            continue
        try:
            answer = session.ask_model(user_input)
            print(f"Aiden: {answer}")
        except (RuntimeError, ValueError, OpenAIError, ModelClientError) as error:
            record("request_failed", reason=type(error).__name__)
            print("Aiden 执行任务失败，请检查配置或稍后重试")
