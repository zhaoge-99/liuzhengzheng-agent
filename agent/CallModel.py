"""Compatibility facade for the Agent session and CLI API.

Implementation is organized into configuration, prompts, patch workflow,
session, and CLI modules.
"""

from agent.AgentState import AgentState, StateMachine
from agent.Concurrency import AdmissionRejected, AgentAdmission
from agent.ModelClient import ModelClientError
from agent import Execute_Tool
from .cli import _handle_command, _print_help, main
from .configuration import _env_int, validate_configuration
from .patch_workflow import _confirmation, _post_change_validation
from .prompts import SYSTEM_PROMPT, _redact_for_context, sanitize_prompt
from .session import AgentSession, _ADMISSION, ask_model

__all__ = [
    "AgentSession",
    "AgentState",
    "AdmissionRejected",
    "AgentAdmission",
    "ModelClientError",
    "StateMachine",
    "SYSTEM_PROMPT",
    "ask_model",
    "main",
    "sanitize_prompt",
    "validate_configuration",
]

if __name__ == "__main__":
    main()
