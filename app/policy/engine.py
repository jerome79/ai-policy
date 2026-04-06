from app.models.common import PolicyDecisionType, RiskLevel
from app.models.policy import PolicyContext, PolicyDecision
from app.policy.rules import PolicyConfig

_RISK_ORDER: dict[RiskLevel, int] = {
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


class PolicyEngine:
    def __init__(self, config: PolicyConfig) -> None:
        self._config = config

    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        denied_tools = self._config.deny_tools_by_role.get(context.actor.role, [])
        if context.tool_id in denied_tools:
            return PolicyDecision(
                decision=PolicyDecisionType.DENY,
                reasons=[f"Role '{context.actor.role}' cannot use tool '{context.tool_id}'."],
                matched_rules=["deny_tools_by_role"],
                risk_score=float(_RISK_ORDER[context.tool_risk_level]),
            )

        if _RISK_ORDER[context.tool_risk_level] >= _RISK_ORDER[self._config.approval_required_at_or_above]:
            return PolicyDecision(
                decision=PolicyDecisionType.REQUIRE_APPROVAL,
                reasons=[f"Tool risk '{context.tool_risk_level.value}' requires approval."],
                matched_rules=["approval_required_at_or_above"],
                risk_score=float(_RISK_ORDER[context.tool_risk_level]),
            )

        return PolicyDecision(
            decision=PolicyDecisionType.ALLOW,
            reasons=["Policy checks passed."],
            matched_rules=["default_allow"],
            risk_score=float(_RISK_ORDER[context.tool_risk_level]),
        )
