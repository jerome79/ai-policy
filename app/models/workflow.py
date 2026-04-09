from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.common import (
    PolicyDecisionType,
    RunStatus,
    RuntimeState,
    WorkflowType,
)
from app.models.economics import BudgetConstraint
from app.models.policy import ActorContext


class WorkflowRequest(BaseModel):
    workflow_type: WorkflowType
    input_payload: dict[str, Any]
    actor: ActorContext
    budget: BudgetConstraint
    metadata: dict[str, str] = Field(default_factory=dict)


class WorkflowStepResult(BaseModel):
    step_id: str
    tool_id: str
    success: bool
    policy_decision: PolicyDecisionType
    output_payload: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class WorkflowRun(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    workflow_type: WorkflowType
    status: RunStatus = RunStatus.RUNNING
    current_state: RuntimeState = RuntimeState.RECEIVED
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    steps: list[WorkflowStepResult] = Field(default_factory=list)
    final_output: dict[str, Any] | None = None
