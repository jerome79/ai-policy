from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowType(str, Enum):
    INVOICE_GOVERNANCE = "invoice_governance"


class ActorRole(str, Enum):
    ANALYST = "analyst"
    FINANCE_MANAGER = "finance_manager"


class Permission(str, Enum):
    ALL = "*"
    INVOICE_READ = "invoice:read"
    VENDOR_READ = "vendor:read"
    PAYMENT_WRITE = "payment:write"


class PolicyDecisionType(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class RunStatus(str, Enum):
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class RuntimeState(str, Enum):
    RECEIVED = "received"
    VALIDATING = "validating"
    POLICY_CHECK = "policy_check"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTE_TOOL = "execute_tool"
    EVALUATE_BUDGET = "evaluate_budget"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
