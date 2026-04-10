from uuid import UUID

from app.models.audit import WorkflowAuditReport
from app.models.workflow import WorkflowRequest, WorkflowRun
from app.runtime.orchestrator import WorkflowOrchestrator


class WorkflowRunner:
    def __init__(self, orchestrator: WorkflowOrchestrator) -> None:
        self._orchestrator = orchestrator

    def run(self, request: WorkflowRequest) -> WorkflowRun:
        return self._orchestrator.execute(request)

    def get_run(self, run_id: UUID) -> WorkflowRun | None:
        return self._orchestrator.get_run(run_id)

    def resume(self, run_id: UUID) -> WorkflowRun:
        return self._orchestrator.resume(run_id)

    def audit_report(self, run_id: UUID) -> WorkflowAuditReport:
        return self._orchestrator.get_audit_report(run_id)

    def decide_approval(
        self,
        run_id: UUID,
        approved: bool,
        decided_by: str,
        reason: str,
        metadata: dict[str, str],
    ) -> WorkflowRun:
        return self._orchestrator.decide_approval(run_id, approved, decided_by, reason, metadata)
