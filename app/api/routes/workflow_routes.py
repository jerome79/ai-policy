from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.schemas.workflow_api_models import (
    ApprovalDecisionRequest,
    AuditReportResponse,
    ExecuteWorkflowRequest,
    ExecuteWorkflowResponse,
)
from app.runtime.workflow_runner import WorkflowRunner


def build_workflow_router(runner: WorkflowRunner) -> APIRouter:
    router = APIRouter(prefix="/workflows", tags=["workflows"])

    @router.post("/execute", response_model=ExecuteWorkflowResponse)
    def execute_workflow(payload: ExecuteWorkflowRequest) -> ExecuteWorkflowResponse:
        run = runner.run(payload.request)
        return ExecuteWorkflowResponse(run=run)

    @router.get("/{run_id}", response_model=ExecuteWorkflowResponse)
    def get_workflow_run(run_id: UUID) -> ExecuteWorkflowResponse:
        run = runner.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Workflow run not found.")
        return ExecuteWorkflowResponse(run=run)

    @router.post("/{run_id}/approval", response_model=ExecuteWorkflowResponse)
    def submit_approval_decision(run_id: UUID, payload: ApprovalDecisionRequest) -> ExecuteWorkflowResponse:
        try:
            run = runner.decide_approval(
                run_id=run_id,
                approved=payload.approved,
                decided_by=payload.decided_by,
                reason=payload.reason,
                metadata=payload.metadata,
            )
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ExecuteWorkflowResponse(run=run)

    @router.post("/{run_id}/resume", response_model=ExecuteWorkflowResponse)
    def resume_workflow(run_id: UUID) -> ExecuteWorkflowResponse:
        try:
            run = runner.resume(run_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ExecuteWorkflowResponse(run=run)

    @router.get("/{run_id}/audit", response_model=AuditReportResponse)
    def get_audit_report(run_id: UUID) -> AuditReportResponse:
        report = runner.audit_report(run_id)
        return AuditReportResponse(report=report)

    return router
