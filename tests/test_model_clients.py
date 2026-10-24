import unittest

from agent.model_clients.base import ModelResponse, ModelToolCall


class ModelClientTypesTest(unittest.TestCase):
    def test_model_tool_call_accepts_fields(self) -> None:
        tool_call = ModelToolCall(
            call_id="call-1",
            name="search",
            arguments_json='{"query":"hello"}',
        )

        self.assertEqual(tool_call.call_id, "call-1")
        self.assertEqual(tool_call.name, "search")
        self.assertEqual(tool_call.arguments_json, '{"query":"hello"}')

    def test_model_response_accepts_content_and_tool_calls(self) -> None:
        tool_call = ModelToolCall(
            call_id="call-1",
            name="search",
            arguments_json="{}",
        )

        response = ModelResponse(content="hello", tool_calls=[tool_call])

        self.assertEqual(response.content, "hello")
        self.assertEqual(response.tool_calls, [tool_call])
