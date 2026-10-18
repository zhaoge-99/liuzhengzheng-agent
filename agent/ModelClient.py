from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests
from openai import OpenAI, OpenAIError


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


class OpenAICompatibleClient(ModelClient):
    def __init__(self, api_key: str, timeout: int, base_url: str) -> None:
        super().__init__(api_key, timeout)
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
    ) -> ModelResponse:
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                timeout=self.timeout,
            )
        except OpenAIError as error:
            raise ModelClientError("OpenAI 兼容模型请求失败") from error

        message = response.choices[0].message
        tool_calls = [
            ModelToolCall(
                call_id=tool_call.id,
                name=tool_call.function.name,
                arguments_json=tool_call.function.arguments,
            )
            for tool_call in (message.tool_calls or [])
        ]
        return ModelResponse(content=message.content, tool_calls=tool_calls)


class AnthropicClient(ModelClient):
    def __init__(self, api_key: str, timeout: int, base_url: str) -> None:
        super().__init__(api_key, timeout)
        self.base_url = base_url

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
    ) -> ModelResponse:
        system_parts = [
            str(message.get("content", ""))
            for message in messages
            if message.get("role") == "system"
        ]
        request_messages = [
            self._message(message)
            for message in messages
            if message.get("role") != "system"
        ]
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "messages": request_messages,
            "tools": [
                {
                    "name": _tool_name(tool),
                    "description": _tool_description(tool),
                    "input_schema": _tool_parameters(tool),
                }
                for tool in tools
            ],
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)

        try:
            response = requests.post(
                self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as error:
            raise ModelClientError("Anthropic 模型请求失败") from error

        content_parts = [
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        ]
        tool_calls = []
        for block in data.get("content", []):
            if block.get("type") != "tool_use":
                continue
            tool_calls.append(
                ModelToolCall(
                    call_id=str(block.get("id", "")),
                    name=str(block.get("name", "")),
                    arguments_json=json.dumps(
                        block.get("input", {}),
                        ensure_ascii=False,
                    ),
                )
            )
        return ModelResponse(
            content="\n".join(part for part in content_parts if part) or None,
            tool_calls=tool_calls,
        )

    @staticmethod
    def _message(message: dict[str, Any]) -> dict[str, Any]:
        role = message.get("role")
        if role == "tool":
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": message.get("tool_call_id", ""),
                        "content": message.get("content", ""),
                    }
                ],
            }
        if role == "assistant" and message.get("tool_calls"):
            blocks: list[dict[str, Any]] = []
            if message.get("content"):
                blocks.append({"type": "text", "text": message["content"]})
            for call in message["tool_calls"]:
                function = call["function"]
                try:
                    arguments = json.loads(function["arguments"])
                except (TypeError, json.JSONDecodeError):
                    arguments = {}
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": call["id"],
                        "name": function["name"],
                        "input": arguments,
                    }
                )
            return {"role": "assistant", "content": blocks}
        return {"role": role, "content": message.get("content", "")}


class GeminiClient(ModelClient):
    def __init__(self, api_key: str, timeout: int, base_url: str) -> None:
        super().__init__(api_key, timeout)
        self.base_url = base_url

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
    ) -> ModelResponse:
        system_parts = [
            str(message.get("content", ""))
            for message in messages
            if message.get("role") == "system"
        ]
        contents = [
            self._message(message)
            for message in messages
            if message.get("role") != "system"
        ]
        payload: dict[str, Any] = {
            "contents": contents,
            "tools": [
                {
                    "functionDeclarations": [
                        {
                            "name": _tool_name(tool),
                            "description": _tool_description(tool),
                            "parameters": _tool_parameters(tool),
                        }
                        for tool in tools
                    ]
                }
            ],
        }
        if system_parts:
            payload["systemInstruction"] = {
                "parts": [{"text": "\n\n".join(system_parts)}]
            }

        endpoint = f"{self.base_url}/models/{model}:generateContent"
        try:
            response = requests.post(
                endpoint,
                params={"key": self.api_key},
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as error:
            raise ModelClientError("Gemini 模型请求失败") from error

        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text_parts = [part.get("text", "") for part in parts if "text" in part]
        tool_calls = [
            ModelToolCall(
                call_id=f"gemini-{index}",
                name=part["functionCall"]["name"],
                arguments_json=json.dumps(
                    part["functionCall"].get("args", {}),
                    ensure_ascii=False,
                ),
            )
            for index, part in enumerate(parts)
            if "functionCall" in part
        ]
        return ModelResponse(
            content="\n".join(part for part in text_parts if part) or None,
            tool_calls=tool_calls,
        )

    @staticmethod
    def _message(message: dict[str, Any]) -> dict[str, Any]:
        role = message.get("role")
        if role == "tool":
            try:
                result = json.loads(message.get("content", "{}"))
            except (TypeError, json.JSONDecodeError):
                result = {"data": message.get("content", "")}
            return {
                "role": "user",
                "parts": [
                    {
                        "functionResponse": {
                            "name": message.get("name", "tool"),
                            "response": result,
                        }
                    }
                ],
            }
        if role == "assistant":
            parts: list[dict[str, Any]] = []
            if message.get("content"):
                parts.append({"text": message["content"]})
            for call in message.get("tool_calls", []):
                function = call["function"]
                try:
                    arguments = json.loads(function["arguments"])
                except (TypeError, json.JSONDecodeError):
                    arguments = {}
                parts.append(
                    {
                        "functionCall": {
                            "name": function["name"],
                            "args": arguments,
                        }
                    }
                )
            return {"role": "model", "parts": parts}
        return {"role": "user", "parts": [{"text": message.get("content", "")}]}


def create_model_client(timeout: int) -> tuple[ModelClient, str]:
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
