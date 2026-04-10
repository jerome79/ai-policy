from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ApprovalResult(BaseModel):
    approved: bool
    reason: str
    decided_by: str | None = None
    decided_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    run_id: str
    tool_id: str
    requested_at: datetime
    status: str
    reason: str
    decision: ApprovalResult | None = None


class ApprovalService:
    """In-memory approval workflow with explicit pause/resume support."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    def request_approval(self, run_id: str, tool_id: str, reason: str) -> ApprovalRequest:
        request = ApprovalRequest(
            run_id=run_id,
            tool_id=tool_id,
            requested_at=datetime.now(timezone.utc),
            status="pending",
            reason=reason,
        )
        self._requests[run_id] = request
        return request

    def decide(self, run_id: str, approved: bool, decided_by: str, reason: str, metadata: dict[str, Any]) -> ApprovalResult:
        request = self._requests.get(run_id)
        if request is None:
            raise KeyError(f"No pending approval request found for run: {run_id}")
        if request.status != "pending":
            raise ValueError(f"Approval for run {run_id} is already decided.")
        decision = ApprovalResult(
            approved=approved,
            reason=reason,
            decided_by=decided_by,
            decided_at=datetime.now(timezone.utc),
            metadata=metadata,
        )
        request.status = "approved" if approved else "rejected"
        request.decision = decision
        return decision

    def get_decision(self, run_id: str) -> ApprovalResult | None:
        request = self._requests.get(run_id)
        if request is None:
            return None
        return request.decision
