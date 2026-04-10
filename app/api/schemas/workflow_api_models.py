from pydantic import BaseModel, Field

from app.models.audit import WorkflowAuditReport
from app.models.workflow import WorkflowRequest, WorkflowRun


class ExecuteWorkflowRequest(BaseModel):
    request: WorkflowRequest


class ExecuteWorkflowResponse(BaseModel):
    run: WorkflowRun


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    decided_by: str
    reason: str
    metadata: dict[str, str] = Field(default_factory=dict)


class AuditReportResponse(BaseModel):
    report: WorkflowAuditReport
