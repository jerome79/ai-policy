from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.economics.budget_guard import BudgetGuard
from app.economics.cost_tracker import CostTracker
from app.models.audit import AuditEvent, AuditEventType, WorkflowAuditReport
from app.models.common import PolicyDecisionType, RunStatus, RuntimeState
from app.models.invoice import InvoiceProcessingOutput, InvoiceWorkflowInput
from app.models.policy import PolicyContext, PolicyDecision
from app.models.tool import ToolInvocation
from app.models.workflow import WorkflowRequest, WorkflowRun, WorkflowStepResult
from app.policy.approval import ApprovalService
from app.policy.engine import PolicyEngine
from app.policy.risk_engine import RiskEngine
from app.runtime.execution_context import ExecutionContext
from app.runtime.state_machine import StateMachine
from app.services.audit_logger import AuditLogger
from app.services.run_store import RunStore
from app.tools.registry import ToolRegistry


class WorkflowOrchestrator:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        policy_engine: PolicyEngine,
        approval_service: ApprovalService,
        cost_tracker: CostTracker,
        budget_guard: BudgetGuard,
        audit_logger: AuditLogger,
        run_store: RunStore,
        risk_engine: RiskEngine,
    ) -> None:
        self._tool_registry = tool_registry
        self._policy_engine = policy_engine
        self._approval_service = approval_service
        self._cost_tracker = cost_tracker
        self._budget_guard = budget_guard
        self._audit_logger = audit_logger
        self._run_store = run_store
        self._risk_engine = risk_engine
        self._state_machine = StateMachine()
        self._tool_sequence = [
            "validate_invoice_data",
            "check_vendor_risk",
            "prepare_payment_instruction",
        ]

    def execute(self, request: WorkflowRequest) -> WorkflowRun:
        run = WorkflowRun(workflow_type=request.workflow_type)
        context = ExecutionContext(request=request, run=run)
        decisions: list[PolicyDecision] = []

        self._set_state(context, RuntimeState.VALIDATING)
        try:
            invoice_payload = InvoiceWorkflowInput.model_validate(request.input_payload)
        except Exception as exc:  # pydantic validation error
            run.status = RunStatus.FAILED
            run.current_state = RuntimeState.FAILED
            run.ended_at = datetime.now(timezone.utc)
            self._log_event(
                run_id=run.run_id,
                event_type=AuditEventType.FAILURE,
                payload={"error": "Malformed workflow input.", "details": str(exc)},
            )
            self._run_store.save(run)
            return run
        payload_dict = invoice_payload.model_dump(mode="json")

        for idx, tool_id in enumerate(self._tool_sequence, start=1):
            step_id = f"step-{idx}"
            should_pause = self._execute_step(context, payload_dict, step_id, tool_id, decisions)
            if should_pause:
                return run
        return self._complete_run(run=run, invoice_payload=invoice_payload)

    def resume(self, run_id: UUID) -> WorkflowRun:
        run = self._run_store.get(run_id)
        if run is None:
            raise KeyError(f"Workflow run not found: {run_id}")
        if run.status != RunStatus.AWAITING_APPROVAL or not run.pending_tool_id or not run.pending_step_id:
            raise ValueError("Workflow is not awaiting approval.")
        approval = self._approval_service.get_decision(str(run.run_id))
        if approval is None:
            raise ValueError("Approval decision has not been made yet.")
        if not approval.approved:
            run.status = RunStatus.BLOCKED
            run.current_state = RuntimeState.BLOCKED
            run.ended_at = datetime.now(timezone.utc)
            run.steps.append(
                WorkflowStepResult(
                    step_id=run.pending_step_id,
                    tool_id=run.pending_tool_id,
                    success=False,
                    policy_decision=PolicyDecisionType.REQUIRE_APPROVAL,
                    error=approval.reason,
                )
            )
            self._log_event(
                run_id=run.run_id,
                event_type=AuditEventType.APPROVAL_EVENT,
                step_id=run.pending_step_id,
                tool_id=run.pending_tool_id,
                payload={"result": approval.model_dump(mode="json")},
            )
            self._finalize_after_decision(run)
            return run

        request = self._run_store.get_request(run.run_id)
        if request is None:
            raise ValueError("Original workflow request was not found for resume.")
        context = ExecutionContext(request=request, run=run, spent_total=self._cost_tracker.spent_total(run.run_id))
        invoice_payload = InvoiceWorkflowInput.model_validate(request.input_payload)
        payload_dict = invoice_payload.model_dump(mode="json")
        resume_index = self._tool_sequence.index(run.pending_tool_id)

        self._log_event(
            run_id=run.run_id,
            event_type=AuditEventType.APPROVAL_EVENT,
            step_id=run.pending_step_id,
            tool_id=run.pending_tool_id,
            payload={"result": approval.model_dump(mode="json")},
        )
        run.pending_tool_id = None
        run.pending_step_id = None

        decisions: list[PolicyDecision] = []
        for prior_step in run.steps:
            decisions.append(
                PolicyDecision(
                    decision=prior_step.policy_decision,
                    reasons=[],
                    matched_rules=[],
                    risk_score=0,
                )
            )
        decisions.append(
            PolicyDecision(
                decision=PolicyDecisionType.REQUIRE_APPROVAL,
                reasons=[approval.reason],
                matched_rules=["resume_after_approval"],
                risk_score=70,
            )
        )

        forced_allow = PolicyDecision(
            decision=PolicyDecisionType.ALLOW,
            reasons=["Approval granted for pending tool."],
            matched_rules=["human_approval_granted"],
            risk_score=70,
        )
        should_pause = self._execute_step(
            context=context,
            payload_dict=payload_dict,
            step_id=f"step-{resume_index + 1}",
            tool_id=self._tool_sequence[resume_index],
            decisions=decisions,
            precomputed_decision=forced_allow,
        )
        if should_pause:
            return run
        for idx in range(resume_index + 1, len(self._tool_sequence)):
            next_tool = self._tool_sequence[idx]
            should_pause = self._execute_step(
                context=context,
                payload_dict=payload_dict,
                step_id=f"step-{idx + 1}",
                tool_id=next_tool,
                decisions=decisions,
            )
            if should_pause:
                return run
        return self._complete_run(run=run, invoice_payload=invoice_payload)

    def get_run(self, run_id: UUID) -> WorkflowRun | None:
        return self._run_store.get(run_id)

    def get_audit_report(self, run_id: UUID) -> WorkflowAuditReport:
        return self._audit_logger.report_for_run(run_id)

    def decide_approval(
        self,
        run_id: UUID,
        approved: bool,
        decided_by: str,
        reason: str,
        metadata: dict[str, str],
    ) -> WorkflowRun:
        run = self._run_store.get(run_id)
        if run is None:
            raise KeyError(f"Workflow run not found: {run_id}")
        self._approval_service.decide(
            run_id=str(run_id),
            approved=approved,
            decided_by=decided_by,
            reason=reason,
            metadata=metadata,
        )
        return run

    def _set_state(self, context: ExecutionContext, target: RuntimeState) -> None:
        context.run.current_state = self._state_machine.transition(context.run.current_state, target)
        self._log_event(
            run_id=context.run.run_id,
            event_type=AuditEventType.STATE_TRANSITION,
            payload={"state": target.value},
        )

    def _log_event(
        self,
        run_id: UUID,
        event_type: AuditEventType,
        payload: dict[str, object],
        step_id: str | None = None,
        tool_id: str | None = None,
    ) -> None:
        self._audit_logger.log(
            AuditEvent(run_id=run_id, event_type=event_type, step_id=step_id, tool_id=tool_id, payload=payload)
        )

    def _execute_step(
        self,
        context: ExecutionContext,
        payload_dict: dict[str, object],
        step_id: str,
        tool_id: str,
        decisions: list[PolicyDecision],
        precomputed_decision: PolicyDecision | None = None,
    ) -> bool:
        run = context.run
        request = context.request
        self._set_state(context, RuntimeState.POLICY_CHECK)
        tool_def = self._tool_registry.get_definition(tool_id)
        if precomputed_decision is None:
            policy_context = PolicyContext(
                workflow_type=request.workflow_type,
                actor=request.actor,
                tool_id=tool_id,
                tool_risk_level=tool_def.risk_level,
                spend_to_date=float(context.spent_total),
            )
            decision = self._policy_engine.evaluate(policy_context)
        else:
            decision = precomputed_decision
        decisions.append(decision)
        run.risk = self._risk_engine.assess(decisions)
        self._log_event(
            run_id=run.run_id,
            event_type=AuditEventType.POLICY_DECISION,
            step_id=step_id,
            tool_id=tool_id,
            payload={"decision": decision.model_dump(mode="json")},
        )
        self._log_event(
            run_id=run.run_id,
            event_type=AuditEventType.RISK_CLASSIFICATION,
            step_id=step_id,
            tool_id=tool_id,
            payload={"risk": run.risk.model_dump(mode="json")},
        )

        if decision.decision == PolicyDecisionType.DENY:
            run.status = RunStatus.BLOCKED
            run.current_state = RuntimeState.BLOCKED
            run.ended_at = datetime.now(timezone.utc)
            run.steps.append(
                WorkflowStepResult(
                    step_id=step_id,
                    tool_id=tool_id,
                    success=False,
                    policy_decision=decision.decision,
                    error="Tool denied by policy.",
                )
            )
            self._log_event(
                run_id=run.run_id,
                event_type=AuditEventType.FINAL_OUTCOME,
                payload={"status": run.status.value, "reason": "policy_denied"},
            )
            self._run_store.save_with_request(run, request)
            return True

        if decision.decision == PolicyDecisionType.REQUIRE_APPROVAL:
            approval_request = self._approval_service.request_approval(
                str(run.run_id),
                tool_id,
                reason=f"Approval required for tool '{tool_id}'.",
            )
            self._set_state(context, RuntimeState.AWAITING_APPROVAL)
            run.status = RunStatus.AWAITING_APPROVAL
            run.pending_step_id = step_id
            run.pending_tool_id = tool_id
            self._log_event(
                run_id=run.run_id,
                event_type=AuditEventType.APPROVAL_EVENT,
                step_id=step_id,
                tool_id=tool_id,
                payload={"request": approval_request.model_dump(mode="json")},
            )
            self._run_store.save_with_request(run, request)
            return True

        self._set_state(context, RuntimeState.EVALUATE_BUDGET)
        can_spend, message = self._budget_guard.can_spend(
            spent_total=context.spent_total,
            planned_cost=tool_def.estimated_cost,
            budget=request.budget,
        )
        if not can_spend:
            run.status = RunStatus.BLOCKED
            run.current_state = RuntimeState.BLOCKED
            run.ended_at = datetime.now(timezone.utc)
            run.steps.append(
                WorkflowStepResult(
                    step_id=step_id,
                    tool_id=tool_id,
                    success=False,
                    policy_decision=decision.decision,
                    error=message,
                )
            )
            self._log_event(
                run_id=run.run_id,
                event_type=AuditEventType.BUDGET_BLOCKED,
                step_id=step_id,
                tool_id=tool_id,
                payload={"message": message},
            )
            self._log_event(
                run_id=run.run_id,
                event_type=AuditEventType.FINAL_OUTCOME,
                payload={"status": run.status.value, "reason": "budget_blocked"},
            )
            self._run_store.save_with_request(run, request)
            return True

        if "soft budget" in message.lower():
            context.warnings.append(message)

        self._set_state(context, RuntimeState.EXECUTE_TOOL)
        invocation = ToolInvocation(
            run_id=run.run_id,
            step_id=step_id,
            tool_id=tool_id,
            input_payload=payload_dict,
        )
        try:
            result = self._tool_registry.execute(invocation)
        except Exception as exc:
            run.status = RunStatus.FAILED
            run.current_state = RuntimeState.FAILED
            run.ended_at = datetime.now(timezone.utc)
            run.steps.append(
                WorkflowStepResult(
                    step_id=step_id,
                    tool_id=tool_id,
                    success=False,
                    policy_decision=decision.decision,
                    error=f"Tool execution raised exception: {exc}",
                )
            )
            self._log_event(
                run_id=run.run_id,
                event_type=AuditEventType.FAILURE,
                step_id=step_id,
                tool_id=tool_id,
                payload={"error": str(exc)},
            )
            self._finalize_after_decision(run, request=request)
            return True

        self._log_event(
            run_id=run.run_id,
            event_type=AuditEventType.TOOL_CALL,
            step_id=step_id,
            tool_id=tool_id,
            payload={"success": result.success, "error": result.error},
        )
        self._cost_tracker.add_record(
            record=self._build_cost_record(run.run_id, step_id, tool_id, tool_def.estimated_cost, result.cost_actual)
        )
        context.spent_total = self._cost_tracker.spent_total(run.run_id)
        self._log_event(
            run_id=run.run_id,
            event_type=AuditEventType.COST_UPDATE,
            step_id=step_id,
            tool_id=tool_id,
            payload={"spent_total": str(context.spent_total), "actual_cost": str(result.cost_actual)},
        )

        if not result.success:
            run.status = RunStatus.FAILED
            run.current_state = RuntimeState.FAILED
            run.ended_at = datetime.now(timezone.utc)
            run.steps.append(
                WorkflowStepResult(
                    step_id=step_id,
                    tool_id=tool_id,
                    success=False,
                    policy_decision=decision.decision,
                    error=result.error or "Tool execution failed.",
                )
            )
            self._log_event(
                run_id=run.run_id,
                event_type=AuditEventType.FAILURE,
                step_id=step_id,
                tool_id=tool_id,
                payload={"error": result.error or "Tool execution failed."},
            )
            self._finalize_after_decision(run, request=request)
            return True

        run.steps.append(
            WorkflowStepResult(
                step_id=step_id,
                tool_id=tool_id,
                success=True,
                policy_decision=decision.decision,
                output_payload=result.output_payload,
            )
        )
        self._run_store.save_with_request(run, request)
        return False

    def _complete_run(self, run: WorkflowRun, invoice_payload: InvoiceWorkflowInput) -> WorkflowRun:
        run.status = RunStatus.COMPLETED
        run.current_state = RuntimeState.COMPLETED
        run.ended_at = datetime.now(timezone.utc)
        run.final_output = InvoiceProcessingOutput(
            invoice_id=invoice_payload.invoice_id,
            status="completed",
            summary="Invoice governance workflow completed successfully.",
        ).model_dump(mode="json")
        self._log_event(
            run_id=run.run_id,
            event_type=AuditEventType.FINAL_OUTCOME,
            payload={"status": run.status.value},
        )
        self._run_store.save_with_request(run, None)
        return run

    def _finalize_after_decision(self, run: WorkflowRun, request: WorkflowRequest | None = None) -> None:
        self._log_event(
            run_id=run.run_id,
            event_type=AuditEventType.FINAL_OUTCOME,
            payload={"status": run.status.value},
        )
        self._run_store.save_with_request(run, request)

    @staticmethod
    def _build_cost_record(
        run_id: UUID,
        step_id: str,
        tool_id: str,
        estimated_cost: Decimal,
        actual_cost: Decimal,
    ) -> "CostRecord":
        from app.models.economics import CostRecord

        return CostRecord(
            run_id=run_id,
            step_id=step_id,
            tool_id=tool_id,
            estimated_cost=estimated_cost,
            actual_cost=actual_cost,
        )
