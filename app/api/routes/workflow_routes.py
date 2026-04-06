from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.schemas.workflow_api_models import ExecuteWorkflowRequest, ExecuteWorkflowResponse
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

    return router
