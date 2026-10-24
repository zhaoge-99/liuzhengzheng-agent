from __future__ import annotations

import os

from dotenv import load_dotenv

from agent.ModelClient import create_model_client

# Environment variables already present in the parent process take precedence.
load_dotenv(os.path.join(os.getcwd(), "aiden_env"), override=False)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), "aiden_env"), override=False)
load_dotenv(os.path.join(os.path.dirname(__file__), "aiden_env"), override=False)

def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error
    if not minimum <= parsed <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return parsed

def validate_configuration() -> None:
    if not os.getenv("MODEL_API_KEY"):
        raise RuntimeError(
            "未配置 MODEL_API_KEY。请先设置环境变量后再启动 Agent。"
        )
    # create_model_client在验证完要求的环境变量后会返回一个模型客户端对象和模型名称
    create_model_client(_env_int("AGENT_REQUEST_TIMEOUT", 30, 5, 120))
    _env_int("AGENT_MAX_ITERATIONS", 10, 1, 30)
    _env_int("AGENT_REQUEST_TIMEOUT", 30, 5, 120)
