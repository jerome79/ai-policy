from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.common import Permission, RiskLevel


class ToolDefinition(BaseModel):
    tool_id: str
    version: str
    description: str
    risk_level: RiskLevel
    estimated_cost: Decimal = Field(ge=0)
    required_permissions: list[Permission] = Field(default_factory=list)


class ToolInvocation(BaseModel):
    run_id: UUID
    step_id: str
    tool_id: str
    input_payload: dict[str, Any]


class ToolResult(BaseModel):
    success: bool
    output_payload: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    cost_actual: Decimal = Field(default=Decimal("0"), ge=0)
