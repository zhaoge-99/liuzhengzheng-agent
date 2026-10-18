import unittest

from agent.AgentState import AgentState
from agent.CallModel import AgentSession, sanitize_prompt


class AgentSessionTest(unittest.TestCase):
    def test_sessions_do_not_share_state_or_messages(self) -> None:
        first = AgentSession()
        second = AgentSession()
        first.conversation_messages.append({"role": "user", "content": "one"})
        first.state_machine.transition(AgentState.PLANNING)

        self.assertEqual(second.conversation_messages, [])
        self.assertEqual(second.state_machine.state, AgentState.IDLE)
        self.assertEqual(first.state_machine.state, AgentState.PLANNING)

    def test_clear_resets_only_session_messages(self) -> None:
        session = AgentSession()
        session.conversation_messages.append({"role": "user", "content": "one"})
        session.clear()
        self.assertEqual(session.conversation_messages, [])

    def test_prompt_sanitization_replaces_key_like_values(self) -> None:
        result = sanitize_prompt("MODEL_API_KEY=secret-value")
        self.assertIn("[REDACTED]", result)
        self.assertNotIn("secret-value", result)

