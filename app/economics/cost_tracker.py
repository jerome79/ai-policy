from decimal import Decimal
from uuid import UUID

from app.models.economics import BudgetConstraint, BudgetStatus, CostRecord


class CostTracker:
    def __init__(self) -> None:
        self._records: dict[UUID, list[CostRecord]] = {}

    def add_record(self, record: CostRecord) -> None:
        self._records.setdefault(record.run_id, []).append(record)

    def spent_total(self, run_id: UUID) -> Decimal:
        return sum((record.actual_cost for record in self._records.get(run_id, [])), Decimal("0"))

    def status(self, run_id: UUID, budget: BudgetConstraint) -> BudgetStatus:
        spent = self.spent_total(run_id)
        remaining = budget.max_total - spent
        return BudgetStatus(
            spent_total=spent,
            remaining=remaining,
            is_soft_limit_reached=spent >= budget.soft_limit,
            is_hard_limit_exceeded=spent > budget.max_total,
        )
