from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

class ModelClientError(RuntimeError):
    """Raised when a model provider cannot complete a request."""

@dataclass(frozen=True)
class ModelToolCall:
    call_id: str
    name: str
    arguments_json: str

@dataclass(frozen=True)
class ModelResponse:
    content: str | None
    tool_calls: list[ModelToolCall]

class ModelClient(ABC):
    def __init__(self, api_key: str, timeout: int) -> None:
        self.api_key = api_key
        self.timeout = timeout

    @abstractmethod
    def complete(
            self,
            messages: list[dict[str, Any]],
            tools: list[dict[str, Any]],
            model: str,
    ) -> ModelResponse:
        raise NotImplementedError

def _valid_endpoint(value: str, default: str) -> str:
    endpoint = (value or default).strip().rstrip("/")
    # parsed是一个对象
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("模型服务地址必须是有效的 HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("模型服务地址不能包含凭据、查询参数或片段")
    return endpoint

def _tool_name(tool: dict[str, Any]) -> str:
    return str(tool["function"]["name"])

def _tool_description(tool: dict[str, Any]) -> str:
    return str(tool["function"].get("description", ""))

def _tool_parameters(tool: dict[str, Any]) -> dict[str, Any]:
    parameters = tool["function"].get("parameters", {})
    return parameters if isinstance(parameters, dict) else {}
