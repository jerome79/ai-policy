from uuid import UUID

from app.models.workflow import WorkflowRequest, WorkflowRun
from app.runtime.orchestrator import WorkflowOrchestrator


class WorkflowRunner:
    def __init__(self, orchestrator: WorkflowOrchestrator) -> None:
        self._orchestrator = orchestrator

    def run(self, request: WorkflowRequest) -> WorkflowRun:
        return self._orchestrator.execute(request)

    def get_run(self, run_id: UUID) -> WorkflowRun | None:
        return self._orchestrator.get_run(run_id)
