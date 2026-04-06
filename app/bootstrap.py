from pathlib import Path

from app.economics.budget_guard import BudgetGuard
from app.economics.cost_tracker import CostTracker
from app.policy.approval import ApprovalService
from app.policy.engine import PolicyEngine
from app.policy.rules import PolicyConfig
from app.runtime.orchestrator import WorkflowOrchestrator
from app.runtime.workflow_runner import WorkflowRunner
from app.services.audit_logger import AuditLogger
from app.services.config_loader import load_yaml
from app.services.run_store import RunStore
from app.tools.definitions import default_tool_definitions
from app.tools.handlers.invoice_tools import (
    check_vendor_risk,
    prepare_payment_instruction,
    validate_invoice_data,
)
from app.tools.registry import ToolRegistry


def build_runner(base_path: Path) -> WorkflowRunner:
    policy_yaml = load_yaml(base_path / "app" / "config" / "policy.yaml")
    policy_config = PolicyConfig.model_validate(policy_yaml)

    registry = ToolRegistry()
    handlers = {
        "validate_invoice_data": validate_invoice_data,
        "check_vendor_risk": check_vendor_risk,
        "prepare_payment_instruction": prepare_payment_instruction,
    }
    for definition in default_tool_definitions():
        registry.register(definition=definition, handler=handlers[definition.tool_id])

    orchestrator = WorkflowOrchestrator(
        tool_registry=registry,
        policy_engine=PolicyEngine(config=policy_config),
        approval_service=ApprovalService(),
        cost_tracker=CostTracker(),
        budget_guard=BudgetGuard(),
        audit_logger=AuditLogger(output_path=base_path / "artifacts" / "audit.jsonl"),
        run_store=RunStore(output_path=base_path / "artifacts" / "runs.jsonl"),
    )
    return WorkflowRunner(orchestrator=orchestrator)
