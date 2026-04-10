from decimal import Decimal
from pathlib import Path

from app.economics.budget_guard import BudgetGuard
from app.economics.cost_tracker import CostTracker
from app.models.common import RunStatus, RuntimeState, RiskLevel
from app.models.economics import BudgetConstraint
from app.models.policy import ActorContext
from app.models.workflow import WorkflowRequest
from app.policy.approval import ApprovalService
from app.policy.engine import PolicyEngine
from app.policy.risk_engine import RiskEngine
from app.policy.rules import PolicyConfig
from app.runtime.orchestrator import WorkflowOrchestrator
from app.services.audit_logger import AuditLogger
from app.services.run_store import RunStore
from app.tools.definitions import default_tool_definitions
from app.tools.handlers.invoice_tools import (
    check_vendor_risk,
    prepare_payment_instruction,
    validate_invoice_data,
)
from app.tools.registry import ToolRegistry


def _build_orchestrator(tmp_path: Path, config: PolicyConfig) -> WorkflowOrchestrator:
    registry = ToolRegistry()
    handlers = {
        "validate_invoice_data": validate_invoice_data,
        "check_vendor_risk": check_vendor_risk,
        "prepare_payment_instruction": prepare_payment_instruction,
    }
    for definition in default_tool_definitions():
        registry.register(definition=definition, handler=handlers[definition.tool_id])

    risk_engine = RiskEngine()
    return WorkflowOrchestrator(
        tool_registry=registry,
        policy_engine=PolicyEngine(config=config, risk_engine=risk_engine),
        approval_service=ApprovalService(),
        cost_tracker=CostTracker(),
        budget_guard=BudgetGuard(),
        audit_logger=AuditLogger(output_path=tmp_path / "audit.jsonl"),
        run_store=RunStore(output_path=tmp_path / "runs.jsonl"),
        risk_engine=risk_engine,
    )


def _request() -> WorkflowRequest:
    return WorkflowRequest(
        workflow_type="invoice_governance",
        input_payload={
            "invoice_id": "inv-1001",
            "vendor_id": "vn-200",
            "amount": Decimal("100.00"),
            "currency": "USD",
            "requestor_id": "req-1",
            "line_items": [
                {"description": "Subscription", "amount": Decimal("60.00")},
                {"description": "Support", "amount": Decimal("40.00")},
            ],
        },
        actor=ActorContext(actor_id="actor-1", role="finance_manager", permissions=["*"]),
        budget=BudgetConstraint(max_total=Decimal("5.00"), soft_limit=Decimal("2.00"), currency="USD"),
    )


def test_happy_path_invoice_workflow(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(
        tmp_path,
        PolicyConfig(deny_tools_by_role={}, approval_required_at_or_above=RiskLevel.CRITICAL),
    )
    run = orchestrator.execute(_request())
    assert run.status == RunStatus.COMPLETED
    assert run.current_state == RuntimeState.COMPLETED
    assert len(run.steps) == 3


def test_denied_tool_call_by_policy_in_orchestrator(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(
        tmp_path,
        PolicyConfig(
            deny_tools_by_role={"finance_manager": ["prepare_payment_instruction"]},
            approval_required_at_or_above=RiskLevel.CRITICAL,
        ),
    )
    run = orchestrator.execute(_request())
    assert run.status == RunStatus.BLOCKED
    assert run.steps[-1].tool_id == "prepare_payment_instruction"
    assert "denied" in (run.steps[-1].error or "").lower()


def test_require_approval_decision_is_surfaced(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(
        tmp_path,
        PolicyConfig(deny_tools_by_role={}, approval_required_at_or_above=RiskLevel.HIGH),
    )
    run = orchestrator.execute(_request())
    assert run.status == RunStatus.AWAITING_APPROVAL
    assert run.pending_tool_id == "prepare_payment_instruction"


def test_workflow_stopped_by_hard_budget_in_orchestrator(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(
        tmp_path,
        PolicyConfig(deny_tools_by_role={}, approval_required_at_or_above=RiskLevel.CRITICAL),
    )
    request = _request()
    request.budget = BudgetConstraint(max_total=Decimal("0.10"), soft_limit=Decimal("0.08"), currency="USD")
    run = orchestrator.execute(request)
    assert run.status == RunStatus.BLOCKED
    assert "hard budget" in (run.steps[-1].error or "").lower()
