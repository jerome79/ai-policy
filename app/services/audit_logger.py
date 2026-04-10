import json
from pathlib import Path
from uuid import UUID

from app.models.audit import AuditEvent, WorkflowAuditReport


class AuditLogger:
    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._events_by_run: dict[UUID, list[AuditEvent]] = {}

    def log(self, event: AuditEvent) -> None:
        self._events_by_run.setdefault(event.run_id, []).append(event)
        with self._output_path.open("a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(event.model_dump(mode="json")) + "\n")

    def report_for_run(self, run_id: UUID) -> WorkflowAuditReport:
        return WorkflowAuditReport(run_id=run_id, events=list(self._events_by_run.get(run_id, [])))
