from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class BudgetConstraint(BaseModel):
    currency: str = "USD"
    max_total: Decimal = Field(ge=0)
    soft_limit: Decimal = Field(ge=0)


class CostRecord(BaseModel):
    run_id: UUID
    step_id: str
    tool_id: str
    estimated_cost: Decimal = Field(ge=0)
    actual_cost: Decimal = Field(ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BudgetStatus(BaseModel):
    spent_total: Decimal = Field(ge=0)
    remaining: Decimal
    is_soft_limit_reached: bool
    is_hard_limit_exceeded: bool
