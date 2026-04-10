from app.models.common import PolicyDecisionType, RiskLevel
from app.models.policy import PolicyDecision
from app.models.risk import WorkflowRiskAssessment, WorkflowRiskLevel

_TOOL_RISK_BASE: dict[RiskLevel, float] = {
    RiskLevel.LOW: 20.0,
    RiskLevel.MEDIUM: 50.0,
    RiskLevel.HIGH: 75.0,
    RiskLevel.CRITICAL: 95.0,
}


class RiskEngine:
    def assess(self, decisions: list[PolicyDecision]) -> WorkflowRiskAssessment:
        if not decisions:
            return WorkflowRiskAssessment(score=0.0, level=WorkflowRiskLevel.LOW, reasons=["No policy decisions yet."])

        score = max((decision.risk_score for decision in decisions), default=0.0)
        reasons: list[str] = []
        for decision in decisions:
            reasons.extend(decision.reasons)
            if decision.decision == PolicyDecisionType.DENY:
                score = max(score, 90.0)
                reasons.append("Policy deny decision increases workflow risk.")
            if decision.decision == PolicyDecisionType.REQUIRE_APPROVAL:
                score = max(score, 70.0)
                reasons.append("Approval-required decision indicates elevated risk.")

        bounded_score = min(100.0, max(0.0, score))
        if bounded_score >= 70:
            level = WorkflowRiskLevel.HIGH
        elif bounded_score >= 40:
            level = WorkflowRiskLevel.MEDIUM
        else:
            level = WorkflowRiskLevel.LOW
        reasons.append(
            f"Risk level '{level.value}' derived from score {bounded_score:.1f} using thresholds: low<40, medium<70, high>=70."
        )
        return WorkflowRiskAssessment(score=bounded_score, level=level, reasons=list(dict.fromkeys(reasons)))

    def score_for_tool_risk(self, tool_risk: RiskLevel) -> float:
        return _TOOL_RISK_BASE[tool_risk]
