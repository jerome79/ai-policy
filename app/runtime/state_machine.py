from app.models.common import RuntimeState


class StateMachine:
    _allowed_transitions: dict[RuntimeState, set[RuntimeState]] = {
        RuntimeState.RECEIVED: {RuntimeState.VALIDATING},
        RuntimeState.VALIDATING: {RuntimeState.POLICY_CHECK, RuntimeState.FAILED},
        RuntimeState.POLICY_CHECK: {RuntimeState.EVALUATE_BUDGET, RuntimeState.BLOCKED},
        RuntimeState.EVALUATE_BUDGET: {RuntimeState.EXECUTE_TOOL, RuntimeState.BLOCKED},
        RuntimeState.EXECUTE_TOOL: {
            RuntimeState.POLICY_CHECK,
            RuntimeState.COMPLETED,
            RuntimeState.FAILED,
        },
        RuntimeState.COMPLETED: set(),
        RuntimeState.BLOCKED: set(),
        RuntimeState.FAILED: set(),
    }

    def transition(self, current: RuntimeState, target: RuntimeState) -> RuntimeState:
        if target not in self._allowed_transitions[current]:
            raise ValueError(f"Invalid transition: {current.value} -> {target.value}")
        return target
