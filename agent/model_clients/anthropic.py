from __future__ import annotations

import json
from typing import Any

import requests

from .base import ModelClient, ModelClientError, ModelResponse, ModelToolCall, _tool_description, _tool_name, _tool_parameters

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
