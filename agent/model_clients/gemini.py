from __future__ import annotations

import json
from typing import Any

import requests

from .base import ModelClient, ModelClientError, ModelResponse, ModelToolCall, _tool_description, _tool_name, _tool_parameters

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
