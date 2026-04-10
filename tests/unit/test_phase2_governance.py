from decimal import Decimal
from pathlib import Path

from app.economics.budget_guard import BudgetGuard
from app.economics.cost_tracker import CostTracker
from app.models.common import RunStatus, RuntimeState, RiskLevel
from app.models.economics import BudgetConstraint
from app.models.policy import ActorContext
from app.models.tool import ToolInvocation
from app.models.tool import ToolResult
from app.models.workflow import WorkflowRequest
from app.policy.approval import ApprovalService
from app.policy.engine import PolicyEngine
from app.policy.risk_engine import RiskEngine
from app.policy.rules import PolicyConfig
from app.runtime.orchestrator import WorkflowOrchestrator
from app.services.audit_logger import AuditLogger
from app.services.run_store import RunStore
from app.tools.definitions import default_tool_definitions
from app.tools.handlers.invoice_tools import check_vendor_risk, prepare_payment_instruction, validate_invoice_data
from app.tools.registry import ToolRegistry


def _request() -> WorkflowRequest:
    return WorkflowRequest(
        workflow_type="invoice_governance",
        input_payload={
            "invoice_id": "inv-2001",
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


def _build_orchestrator(tmp_path: Path, config: PolicyConfig, fail_payment_tool: bool = False) -> WorkflowOrchestrator:
    registry = ToolRegistry()

    def failing_payment_tool(_invocation: ToolInvocation) -> ToolResult:
        raise RuntimeError("payment rail unavailable")

    handlers = {
        "validate_invoice_data": validate_invoice_data,
        "check_vendor_risk": check_vendor_risk,
        "prepare_payment_instruction": failing_payment_tool if fail_payment_tool else prepare_payment_instruction,
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


def test_approval_pause_and_resume_flow(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(
        tmp_path,
        PolicyConfig(deny_tools_by_role={}, approval_required_at_or_above=RiskLevel.HIGH),
    )
    run = orchestrator.execute(_request())
    assert run.status == RunStatus.AWAITING_APPROVAL
    assert run.current_state == RuntimeState.AWAITING_APPROVAL
    assert run.pending_tool_id == "prepare_payment_instruction"

    orchestrator.decide_approval(
        run_id=run.run_id,
        approved=True,
        decided_by="manager-1",
        reason="Approved for payment run.",
        metadata={"ticket_id": "appr-1"},
    )
    resumed = orchestrator.resume(run.run_id)
    assert resumed.status == RunStatus.COMPLETED
    assert resumed.current_state == RuntimeState.COMPLETED
    assert resumed.risk is not None
    assert resumed.risk.level.value in {"medium", "high"}


def test_tool_failure_is_safely_logged_and_failed(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(
        tmp_path,
        PolicyConfig(deny_tools_by_role={}, approval_required_at_or_above=RiskLevel.CRITICAL),
        fail_payment_tool=True,
    )
    run = orchestrator.execute(_request())
    assert run.status == RunStatus.FAILED
    assert run.current_state == RuntimeState.FAILED
    assert "exception" in (run.steps[-1].error or "").lower()

    report = orchestrator.get_audit_report(run.run_id)
    event_types = {event.event_type.value for event in report.events}
    assert "failure" in event_types
    assert "final_outcome" in event_types


def test_malformed_input_fails_safe(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator(
        tmp_path,
        PolicyConfig(deny_tools_by_role={}, approval_required_at_or_above=RiskLevel.CRITICAL),
    )
    request = _request()
    request.input_payload.pop("invoice_id")
    run = orchestrator.execute(request)
    assert run.status == RunStatus.FAILED
    assert run.current_state == RuntimeState.FAILED
