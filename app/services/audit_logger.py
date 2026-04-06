import json
from pathlib import Path

from app.models.audit import AuditEvent


class AuditLogger:
    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: AuditEvent) -> None:
        with self._output_path.open("a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(event.model_dump(mode="json")) + "\n")
