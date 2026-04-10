from enum import Enum

from pydantic import BaseModel, Field


class WorkflowRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WorkflowRiskAssessment(BaseModel):
    score: float = Field(ge=0, le=100)
    level: WorkflowRiskLevel
    reasons: list[str] = Field(default_factory=list)
