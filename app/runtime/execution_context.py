from dataclasses import dataclass, field
from decimal import Decimal

from app.models.workflow import WorkflowRequest, WorkflowRun


@dataclass(slots=True)
class ExecutionContext:
    request: WorkflowRequest
    run: WorkflowRun
    spent_total: Decimal = Decimal("0")
    warnings: list[str] = field(default_factory=list)
