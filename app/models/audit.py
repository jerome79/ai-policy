from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    STATE_TRANSITION = "state_transition"
    POLICY_DECISION = "policy_decision"
    TOOL_CALL = "tool_call"
    COST_UPDATE = "cost_update"
    RISK_CLASSIFICATION = "risk_classification"
    APPROVAL_EVENT = "approval_event"
    BUDGET_BLOCKED = "budget_blocked"
    FINAL_OUTCOME = "final_outcome"
    FAILURE = "failure"


class AuditEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    event_type: AuditEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    step_id: str | None = None
    tool_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowAuditReport(BaseModel):
    run_id: UUID
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    events: list[AuditEvent] = Field(default_factory=list)
