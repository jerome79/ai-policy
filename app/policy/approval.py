from pydantic import BaseModel


class ApprovalResult(BaseModel):
    approved: bool
    reason: str


class ApprovalService:
    """Phase 1 approval stub; defaults to not approved."""

    def request_approval(self, run_id: str, tool_id: str) -> ApprovalResult:
        return ApprovalResult(
            approved=False,
            reason=f"Approval required for {tool_id}; manual approval not implemented in Phase 1.",
        )
