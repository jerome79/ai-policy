from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyDecisionType(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class RuntimeState(str, Enum):
    RECEIVED = "received"
    VALIDATING = "validating"
    POLICY_CHECK = "policy_check"
    EXECUTE_TOOL = "execute_tool"
    EVALUATE_BUDGET = "evaluate_budget"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
