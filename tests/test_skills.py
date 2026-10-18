import json
import os
import tempfile
import unittest
from pathlib import Path

from agent import Skills


class SkillsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["AGENT_WORKSPACE"] = self.temp_dir.name

    def tearDown(self) -> None:
        os.environ.pop("AGENT_WORKSPACE", None)
        self.temp_dir.cleanup()

    def test_calculate_only_allows_arithmetic(self) -> None:
        self.assertEqual(Skills.calculate("(12 + 3) * 4"), "60")
        with self.assertRaises(ValueError):
            Skills.calculate("__import__('os').getcwd()")

    def test_current_time_supports_default_timezone(self) -> None:
        value = Skills.get_current_time()
        self.assertRegex(value, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+08:00$")

    def test_workspace_path_cannot_escape_root(self) -> None:
        with self.assertRaises(ValueError):
            Skills.read_text_file("..\\outside.txt")

    def test_read_text_file_returns_json(self) -> None:
        file_path = Path(self.temp_dir.name) / "note.txt"
        file_path.write_text("hello", encoding="utf-8")
        result = json.loads(Skills.read_text_file("note.txt"))
        self.assertEqual(result["content"], "hello")

