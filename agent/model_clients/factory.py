from __future__ import annotations

import os

from .anthropic import AnthropicClient
from .base import ModelClient, _valid_endpoint
from .gemini import GeminiClient
from .openai_compatible import OpenAICompatibleClient

def create_model_client(timeout: int) -> tuple[ModelClient, str]:
    # 系统环境变量中如果没有MODEL_PROVIDER，则os.getenv("MODEL_PROVIDER", "openai-compatible")会返回默认值"openai-compatible"
    provider = os.getenv("MODEL_PROVIDER", "openai-compatible").strip().lower()
    api_key = os.getenv("MODEL_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("未配置 MODEL_API_KEY")

    model = (
            os.getenv("MODEL_NAME")
            or {
                "openai-compatible": "gpt-4o-mini",
                "anthropic": "claude-3-5-sonnet-latest",
                "gemini": "gemini-2.0-flash",
            }.get(provider, "")
    ).strip()
    if not model:
        raise RuntimeError("未配置 MODEL_NAME")

    if provider == "openai-compatible":
        base_url = _valid_endpoint(
            os.getenv("MODEL_BASE_URL", ""),
            "https://api.openai.com/v1",
        )
        return OpenAICompatibleClient(api_key, timeout, base_url), model
    if provider == "anthropic":
        base_url = _valid_endpoint(
            os.getenv("MODEL_BASE_URL", ""),
            "https://api.anthropic.com/v1/messages",
        )
        return AnthropicClient(api_key, timeout, base_url), model
    if provider == "gemini":
        base_url = _valid_endpoint(
            os.getenv("MODEL_BASE_URL", ""),
            "https://generativelanguage.googleapis.com/v1beta",
        )
        return GeminiClient(api_key, timeout, base_url), model
    raise RuntimeError(
        "MODEL_PROVIDER 只支持 openai-compatible、anthropic 或 gemini"
    )
