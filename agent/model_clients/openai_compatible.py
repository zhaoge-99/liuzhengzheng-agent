from __future__ import annotations

from typing import Any

from openai import OpenAI, OpenAIError

from .base import ModelClient, ModelClientError, ModelResponse, ModelToolCall

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
