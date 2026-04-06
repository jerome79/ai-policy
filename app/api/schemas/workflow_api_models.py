from pydantic import BaseModel

from app.models.workflow import WorkflowRequest, WorkflowRun


class ExecuteWorkflowRequest(BaseModel):
    request: WorkflowRequest


class ExecuteWorkflowResponse(BaseModel):
    run: WorkflowRun
