from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field

from app.bootstrap import build_runner
from app.models.common import RiskLevel, RunStatus
from app.models.audit import AuditEvent, AuditEventType
from app.models.economics import BudgetConstraint
from app.models.policy import ActorContext
from app.models.risk import WorkflowRiskLevel
from app.models.workflow import WorkflowRequest


class EvaluationCase(BaseModel):
    case_id: str
    expected_status: RunStatus
    expected_approval_required: bool
    expected_budget_block: bool
    expected_risk_level: RiskLevel
    expected_policy_rules: list[str] = Field(default_factory=list)
    expected_policy_reason_substrings: list[str] = Field(default_factory=list)
    expected_audit_events: list[AuditEventType] = Field(default_factory=list)
    expected_approval_metadata: dict[str, str] = Field(default_factory=dict)
    validate_approval_branches: bool = False
    request: WorkflowRequest


class EvaluationMetrics(BaseModel):
    total_cases: int
    policy_correctness: float
    approval_routing_correctness: float
    risk_classification_consistency: float
    budget_enforcement_correctness: float
    policy_trace_correctness: float
    approval_lifecycle_correctness: float


class EvaluationResult(BaseModel):
    metrics: EvaluationMetrics
    failed_case_ids: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class RegressionRunner:
    base_path: Path

    @staticmethod
    def _runtime_risk_to_common_level(risk_level: WorkflowRiskLevel | None) -> RiskLevel:
        if risk_level is None:
            return RiskLevel.LOW
        if risk_level == WorkflowRiskLevel.LOW:
            return RiskLevel.LOW
        if risk_level == WorkflowRiskLevel.MEDIUM:
            return RiskLevel.MEDIUM
        return RiskLevel.HIGH

    def run(self, cases: list[EvaluationCase]) -> EvaluationResult:
        runner = build_runner(self.base_path)
        policy_ok = 0
        approval_ok = 0
        risk_ok = 0
        budget_ok = 0
        trace_ok = 0
        approval_lifecycle_ok = 0
        failed_cases: list[str] = []

        for case in cases:
            run = runner.run(case.request)
            case_passed = True
            if run.status == case.expected_status:
                policy_ok += 1
            else:
                case_passed = False

            approval_required = run.status == RunStatus.AWAITING_APPROVAL
            if approval_required == case.expected_approval_required:
                approval_ok += 1
            else:
                case_passed = False

            actual_risk_level = self._runtime_risk_to_common_level(run.risk.level if run.risk is not None else None)
            if actual_risk_level == case.expected_risk_level:
                risk_ok += 1
            else:
                case_passed = False

            budget_blocked = any("hard budget" in (step.error or "").lower() for step in run.steps)
            if budget_blocked == case.expected_budget_block:
                budget_ok += 1
            else:
                case_passed = False

            audit_report = runner.audit_report(run.run_id)
            policy_trace_matches = self._validate_policy_trace(case, audit_report.events)
            if policy_trace_matches:
                trace_ok += 1
            else:
                case_passed = False

            approval_lifecycle_matches = self._validate_approval_lifecycle(case, runner, run)
            if approval_lifecycle_matches:
                approval_lifecycle_ok += 1
            else:
                case_passed = False

            if not case_passed:
                failed_cases.append(case.case_id)

        total = len(cases)
        return EvaluationResult(
            metrics=EvaluationMetrics(
                total_cases=total,
                policy_correctness=policy_ok / total if total else 0.0,
                approval_routing_correctness=approval_ok / total if total else 0.0,
                risk_classification_consistency=risk_ok / total if total else 0.0,
                budget_enforcement_correctness=budget_ok / total if total else 0.0,
                policy_trace_correctness=trace_ok / total if total else 0.0,
                approval_lifecycle_correctness=approval_lifecycle_ok / total if total else 0.0,
            ),
            failed_case_ids=failed_cases,
        )

    @staticmethod
    def _validate_policy_trace(case: EvaluationCase, events: list[AuditEvent]) -> bool:
        if not case.expected_policy_rules and not case.expected_policy_reason_substrings and not case.expected_audit_events:
            return True

        event_types = {event.event_type for event in events}
        for expected_event in case.expected_audit_events:
            if expected_event not in event_types:
                return False

        policy_events = [event for event in events if event.event_type == AuditEventType.POLICY_DECISION]
        matched_rules: set[str] = set()
        reasons: list[str] = []
        for event in policy_events:
            decision_payload = event.payload.get("decision")
            if not isinstance(decision_payload, dict):
                continue
            raw_rules = decision_payload.get("matched_rules", [])
            raw_reasons = decision_payload.get("reasons", [])
            if isinstance(raw_rules, list):
                matched_rules.update(str(rule) for rule in raw_rules)
            if isinstance(raw_reasons, list):
                reasons.extend(str(reason) for reason in raw_reasons)

        for expected_rule in case.expected_policy_rules:
            if expected_rule not in matched_rules:
                return False
        for expected_reason in case.expected_policy_reason_substrings:
            if not any(expected_reason in reason for reason in reasons):
                return False
        return True

    def _validate_approval_lifecycle(self, case: EvaluationCase, runner: "WorkflowRunner", run: "WorkflowRun") -> bool:
        if not case.validate_approval_branches:
            return True
        if run.status != RunStatus.AWAITING_APPROVAL:
            return False

        approval_metadata = case.expected_approval_metadata or {"ticket_id": f"{case.case_id}-approved"}
        runner.decide_approval(
            run_id=run.run_id,
            approved=True,
            decided_by="eval-approver",
            reason="Approved during evaluation lifecycle checks.",
            metadata=approval_metadata,
        )
        resumed = runner.resume(run.run_id)
        if resumed.status != RunStatus.COMPLETED:
            return False

        resumed_events = runner.audit_report(run.run_id).events
        if not self._approval_metadata_present(
            events=resumed_events,
            expected_metadata=approval_metadata,
            expected_approved=True,
        ):
            return False

        reject_run = runner.run(case.request)
        if reject_run.status != RunStatus.AWAITING_APPROVAL:
            return False
        reject_metadata = {"ticket_id": f"{case.case_id}-rejected"}
        runner.decide_approval(
            run_id=reject_run.run_id,
            approved=False,
            decided_by="eval-approver",
            reason="Rejected during evaluation lifecycle checks.",
            metadata=reject_metadata,
        )
        rejected = runner.resume(reject_run.run_id)
        if rejected.status != RunStatus.BLOCKED:
            return False
        rejected_events = runner.audit_report(reject_run.run_id).events
        return self._approval_metadata_present(
            events=rejected_events,
            expected_metadata=reject_metadata,
            expected_approved=False,
        )

    @staticmethod
    def _approval_metadata_present(
        events: list[AuditEvent],
        expected_metadata: dict[str, str],
        expected_approved: bool,
    ) -> bool:
        for event in events:
            if event.event_type != AuditEventType.APPROVAL_EVENT:
                continue
            result = event.payload.get("result")
            if not isinstance(result, dict):
                continue
            if result.get("approved") is not expected_approved:
                continue
            metadata = result.get("metadata")
            if not isinstance(metadata, dict):
                continue
            if all(metadata.get(key) == value for key, value in expected_metadata.items()):
                return True
        return False


def synthetic_cases() -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    for index in range(24):
        invoice_id = f"inv-eval-{index}"
        hard_budget = Decimal("5.00")
        approval_expected = True
        expected_status = RunStatus.AWAITING_APPROVAL
        expected_budget_block = False
        expected_risk_level = RiskLevel.HIGH
        expected_policy_rules = ["approval_required_at_or_above"]
        expected_policy_reason_substrings = ["requires approval"]
        expected_audit_events = [
            AuditEventType.POLICY_DECISION,
            AuditEventType.RISK_CLASSIFICATION,
            AuditEventType.APPROVAL_EVENT,
            AuditEventType.STATE_TRANSITION,
        ]
        expected_approval_metadata = {"ticket_id": f"case-{index}-approved"}
        validate_approval_branches = index % 4 == 1

        if index % 6 == 0:
            hard_budget = Decimal("0.10")
            expected_status = RunStatus.BLOCKED
            approval_expected = False
            expected_budget_block = True
            # Budget-blocked scenarios halt before the high-risk payment step.
            # The highest observed policy risk remains the medium-risk vendor check.
            expected_risk_level = RiskLevel.MEDIUM
            expected_policy_rules = ["default_allow"]
            expected_policy_reason_substrings = ["Policy checks passed."]
            expected_audit_events = [
                AuditEventType.POLICY_DECISION,
                AuditEventType.RISK_CLASSIFICATION,
                AuditEventType.BUDGET_BLOCKED,
                AuditEventType.FINAL_OUTCOME,
            ]
            expected_approval_metadata = {}
            validate_approval_branches = False

        request = WorkflowRequest(
            workflow_type="invoice_governance",
            input_payload={
                "invoice_id": invoice_id,
                "vendor_id": "hr-vendor" if index % 4 == 0 else "vn-standard",
                "amount": Decimal("100.00"),
                "currency": "USD",
                "requestor_id": "eval-user",
                "line_items": [
                    {"description": "A", "amount": Decimal("60.00")},
                    {"description": "B", "amount": Decimal("40.00")},
                ],
            },
            actor=ActorContext(actor_id=f"eval-{index}", role="finance_manager", permissions=["*"]),
            budget=BudgetConstraint(max_total=hard_budget, soft_limit=Decimal("2.00"), currency="USD"),
        )
        cases.append(
            EvaluationCase(
                case_id=f"case-{index}",
                expected_status=expected_status,
                expected_approval_required=approval_expected,
                expected_budget_block=expected_budget_block,
                expected_risk_level=expected_risk_level,
                expected_policy_rules=expected_policy_rules,
                expected_policy_reason_substrings=expected_policy_reason_substrings,
                expected_audit_events=expected_audit_events,
                expected_approval_metadata=expected_approval_metadata,
                validate_approval_branches=validate_approval_branches,
                request=request,
            )
        )
    return cases
