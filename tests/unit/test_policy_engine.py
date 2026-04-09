from app.models.common import PolicyDecisionType, RiskLevel
from app.models.policy import ActorContext, PolicyContext
from app.policy.engine import PolicyEngine
from app.policy.rules import PolicyConfig


def test_denied_tool_call_by_policy() -> None:
    engine = PolicyEngine(
        PolicyConfig(deny_tools_by_role={"analyst": ["prepare_payment_instruction"]}, approval_required_at_or_above=RiskLevel.HIGH)
    )
    context = PolicyContext(
        workflow_type="invoice_governance",
        actor=ActorContext(actor_id="a1", role="analyst", permissions=[]),
        tool_id="prepare_payment_instruction",
        tool_risk_level=RiskLevel.HIGH,
        spend_to_date=0.0,
    )
    decision = engine.evaluate(context)
    assert decision.decision == PolicyDecisionType.DENY


def test_require_approval_is_surfaced() -> None:
    engine = PolicyEngine(
        PolicyConfig(deny_tools_by_role={}, approval_required_at_or_above=RiskLevel.HIGH)
    )
    context = PolicyContext(
        workflow_type="invoice_governance",
        actor=ActorContext(actor_id="a1", role="finance_manager", permissions=[]),
        tool_id="prepare_payment_instruction",
        tool_risk_level=RiskLevel.HIGH,
        spend_to_date=0.0,
    )
    decision = engine.evaluate(context)
    assert decision.decision == PolicyDecisionType.REQUIRE_APPROVAL


def test_policy_allows_low_risk_tool_when_not_denied() -> None:
    engine = PolicyEngine(
        PolicyConfig(deny_tools_by_role={"analyst": ["prepare_payment_instruction"]}, approval_required_at_or_above=RiskLevel.HIGH)
    )
    context = PolicyContext(
        workflow_type="invoice_governance",
        actor=ActorContext(actor_id="a1", role="finance_manager", permissions=[]),
        tool_id="validate_invoice_data",
        tool_risk_level=RiskLevel.LOW,
        spend_to_date=0.0,
    )
    decision = engine.evaluate(context)
    assert decision.decision == PolicyDecisionType.ALLOW
