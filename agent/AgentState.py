from enum import Enum

# AgentState类同时继承了str和Enum,
class AgentState(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    ANALYZING = "analyzing"
    WAITING_CONFIRMATION = "waiting_confirmation"
    APPLYING = "applying"
    VALIDATING = "validating"
    ROLLING_BACK = "rolling_back"
    COMPLETED = "completed"
    FAILED = "failed"


_ALLOWED_TRANSITIONS = {
    AgentState.IDLE: {AgentState.PLANNING},
    AgentState.PLANNING: {AgentState.ANALYZING, AgentState.WAITING_CONFIRMATION, AgentState.COMPLETED, AgentState.FAILED},
    AgentState.ANALYZING: {AgentState.WAITING_CONFIRMATION, AgentState.COMPLETED, AgentState.FAILED},
    AgentState.WAITING_CONFIRMATION: {AgentState.APPLYING, AgentState.COMPLETED, AgentState.FAILED},
    AgentState.APPLYING: {AgentState.VALIDATING, AgentState.FAILED},
    AgentState.VALIDATING: {AgentState.COMPLETED, AgentState.ROLLING_BACK, AgentState.FAILED},
    AgentState.ROLLING_BACK: {AgentState.COMPLETED, AgentState.FAILED},
    AgentState.COMPLETED: {AgentState.PLANNING},
    AgentState.FAILED: {AgentState.PLANNING},
}


class StateMachine:
    def __init__(self) -> None:
        self.state = AgentState.IDLE

    def transition(self, next_state: AgentState) -> AgentState:
        if next_state not in _ALLOWED_TRANSITIONS[self.state]:
            raise RuntimeError(
                f"Invalid agent state transition: {self.state.value} -> {next_state.value}"
            )
        self.state = next_state
        return self.state
