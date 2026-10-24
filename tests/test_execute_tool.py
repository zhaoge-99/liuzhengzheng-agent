import json
import os
import tempfile
import unittest

from agent import Execute_Tool


class ExecuteToolTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["AGENT_WORKSPACE"] = self.temp_dir.name

    def tearDown(self) -> None:
        os.environ.pop("AGENT_WORKSPACE", None)
        self.temp_dir.cleanup()

    def test_unknown_tool_has_structured_error(self) -> None:
        result = json.loads(Execute_Tool.execute_tool("does_not_exist", "{}"))
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "unknown_tool")

    def test_invalid_arguments_have_structured_error(self) -> None:
        result = json.loads(Execute_Tool.execute_tool("calculate", "[]"))
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "invalid_arguments")

    def test_success_preserves_tool_payload(self) -> None:
        self.assertEqual(Execute_Tool.execute_tool("calculate", '{"expression":"2 + 3"}'), "5")

    def test_tool_catalog_matches_registered_functions_and_permissions(self) -> None:
        names = [
            tool["function"]["name"]
            for tool in Execute_Tool.TOOL_DEFINITIONS
        ]
        registered = set(Execute_Tool.TOOL_FUNCTIONS)
        permitted = (
            Execute_Tool.TOOL_PERMISSIONS["read"]
            | Execute_Tool.TOOL_PERMISSIONS["write"]
        )

        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), registered)
        self.assertEqual(registered, permitted)
        self.assertFalse(
            Execute_Tool.TOOL_PERMISSIONS["read"]
            & Execute_Tool.TOOL_PERMISSIONS["write"]
        )
