from decimal import Decimal
from uuid import uuid4

from app.economics.budget_guard import BudgetGuard
from app.economics.cost_tracker import CostTracker
from app.models.economics import BudgetConstraint, CostRecord


def test_workflow_stopped_by_hard_budget() -> None:
    run_id = uuid4()
    tracker = CostTracker()
    tracker.add_record(
        CostRecord(
            run_id=run_id,
            step_id="step-1",
            tool_id="validate_invoice_data",
            estimated_cost=Decimal("0.05"),
            actual_cost=Decimal("0.05"),
        )
    )
    budget = BudgetConstraint(max_total=Decimal("0.10"), soft_limit=Decimal("0.08"), currency="USD")
    can_spend, message = BudgetGuard().can_spend(
        spent_total=tracker.spent_total(run_id),
        planned_cost=Decimal("0.10"),
        budget=budget,
    )
    assert can_spend is False
    assert "exceeds hard budget" in message
