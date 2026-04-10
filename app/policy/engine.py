from app.models.common import PolicyDecisionType
from app.models.policy import PolicyContext, PolicyDecision
from app.policy.risk_engine import RiskEngine
from app.policy.rules import PolicyConfig


class PolicyEngine:
    def __init__(self, config: PolicyConfig, risk_engine: RiskEngine | None = None) -> None:
        self._config = config
        self._risk_engine = risk_engine or RiskEngine()

    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        context_risk_score = self._risk_engine.score_for_tool_risk(context.tool_risk_level)
        denied_tools = self._config.deny_tools_by_role.get(context.actor.role, [])
        if context.tool_id in denied_tools:
            return PolicyDecision(
                decision=PolicyDecisionType.DENY,
                reasons=[f"Role '{context.actor.role}' cannot use tool '{context.tool_id}'."],
                matched_rules=["deny_tools_by_role"],
                risk_score=context_risk_score,
            )

        if context_risk_score >= self._risk_engine.score_for_tool_risk(self._config.approval_required_at_or_above):
            return PolicyDecision(
                decision=PolicyDecisionType.REQUIRE_APPROVAL,
                reasons=[f"Tool risk '{context.tool_risk_level.value}' requires approval."],
                matched_rules=["approval_required_at_or_above"],
                risk_score=context_risk_score,
            )

        return PolicyDecision(
            decision=PolicyDecisionType.ALLOW,
            reasons=["Policy checks passed."],
            matched_rules=["default_allow"],
            risk_score=context_risk_score,
        )
