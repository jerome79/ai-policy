from decimal import Decimal
from pathlib import Path

from app.bootstrap import build_runner
from app.models.economics import BudgetConstraint
from app.models.policy import ActorContext
from app.models.workflow import WorkflowRequest


def test_invoice_workflow_end_to_end(tmp_path: Path) -> None:
    base_path = Path(__file__).resolve().parents[2]
    runner = build_runner(base_path=base_path)
    request = WorkflowRequest(
        workflow_type="invoice_governance",
        input_payload={
            "invoice_id": "inv-e2e-1",
            "vendor_id": "vn-500",
            "amount": Decimal("100.00"),
            "currency": "USD",
            "requestor_id": "req-1",
            "line_items": [
                {"description": "Subscription", "amount": Decimal("60.00")},
                {"description": "Support", "amount": Decimal("40.00")},
            ],
        },
        actor=ActorContext(actor_id="user-1", role="finance_manager", permissions=["*"]),
        budget=BudgetConstraint(max_total=Decimal("5.00"), soft_limit=Decimal("2.00"), currency="USD"),
    )
    run = runner.run(request)
    assert run.workflow_type == "invoice_governance"
    assert len(run.steps) >= 2
