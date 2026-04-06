from pydantic import BaseModel, Field

from app.models.common import RiskLevel


class PolicyConfig(BaseModel):
    deny_tools_by_role: dict[str, list[str]] = Field(default_factory=dict)
    approval_required_at_or_above: RiskLevel = RiskLevel.HIGH
