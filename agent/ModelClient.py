"""Compatibility facade for model-provider clients.

Provider implementations live in :mod:`agent.model_clients`.
"""

from .model_clients import (
    AnthropicClient,
    GeminiClient,
    ModelClient,
    ModelClientError,
    ModelResponse,
    ModelToolCall,
    OpenAICompatibleClient,
    create_model_client,
)
from .model_clients.base import (
    _tool_description,
    _tool_name,
    _tool_parameters,
    _valid_endpoint,
)

__all__ = [
    "AnthropicClient",
    "GeminiClient",
    "ModelClient",
    "ModelClientError",
    "ModelResponse",
    "ModelToolCall",
    "OpenAICompatibleClient",
    "create_model_client",
]
