from decimal import Decimal

from app.models.economics import BudgetConstraint


class BudgetGuard:
    def can_spend(self, spent_total: Decimal, planned_cost: Decimal, budget: BudgetConstraint) -> tuple[bool, str]:
        projected = spent_total + planned_cost
        if projected > budget.max_total:
            return False, f"Projected spend {projected} exceeds hard budget {budget.max_total}."
        if projected >= budget.soft_limit:
            return True, f"Projected spend {projected} reaches soft budget {budget.soft_limit}."
        return True, "Budget check passed."
