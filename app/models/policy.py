from typing import Any

from pydantic import BaseModel, Field

from app.models.common import ActorRole, Permission, PolicyDecisionType, RiskLevel, WorkflowType


class ActorContext(BaseModel):
    actor_id: str
    role: ActorRole
    permissions: list[Permission] = Field(default_factory=list)


class PolicyRule(BaseModel):
    rule_id: str
    description: str
    effect: PolicyDecisionType
    tool_ids: list[str] = Field(default_factory=list)
    roles: list[ActorRole] = Field(default_factory=list)
    min_risk_level: RiskLevel | None = None


class PolicyContext(BaseModel):
    workflow_type: WorkflowType
    actor: ActorContext
    tool_id: str
    tool_risk_level: RiskLevel
    spend_to_date: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    decision: PolicyDecisionType
    reasons: list[str] = Field(default_factory=list)
    matched_rules: list[str] = Field(default_factory=list)
    risk_score: float = 0.0
