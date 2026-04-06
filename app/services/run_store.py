import json
from pathlib import Path
from uuid import UUID

from app.models.workflow import WorkflowRun


class RunStore:
    def __init__(self, output_path: Path) -> None:
        self._runs: dict[UUID, WorkflowRun] = {}
        self._output_path = output_path
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, run: WorkflowRun) -> None:
        self._runs[run.run_id] = run
        with self._output_path.open("a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(run.model_dump(mode="json")) + "\n")

    def get(self, run_id: UUID) -> WorkflowRun | None:
        return self._runs.get(run_id)
