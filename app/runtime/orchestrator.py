from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.economics.budget_guard import BudgetGuard
from app.economics.cost_tracker import CostTracker
from app.models.audit import AuditEvent
from app.models.common import PolicyDecisionType, RunStatus, RuntimeState
from app.models.invoice import InvoiceProcessingOutput, InvoiceWorkflowInput
from app.models.policy import PolicyContext
from app.models.tool import ToolInvocation
from app.models.workflow import WorkflowRequest, WorkflowRun, WorkflowStepResult
from app.policy.approval import ApprovalService
from app.policy.engine import PolicyEngine
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
    ) -> None:
        self._tool_registry = tool_registry
        self._policy_engine = policy_engine
        self._approval_service = approval_service
        self._cost_tracker = cost_tracker
        self._budget_guard = budget_guard
        self._audit_logger = audit_logger
        self._run_store = run_store
        self._state_machine = StateMachine()

    def execute(self, request: WorkflowRequest) -> WorkflowRun:
        run = WorkflowRun(workflow_type=request.workflow_type)
        context = ExecutionContext(request=request, run=run)

        self._set_state(context, RuntimeState.VALIDATING)
        invoice_payload = InvoiceWorkflowInput.model_validate(request.input_payload)
        payload_dict = invoice_payload.model_dump(mode="json")

        tool_sequence = [
            "validate_invoice_data",
            "check_vendor_risk",
            "prepare_payment_instruction",
        ]

        for idx, tool_id in enumerate(tool_sequence, start=1):
            step_id = f"step-{idx}"
            self._set_state(context, RuntimeState.POLICY_CHECK)
            tool_def = self._tool_registry.get_definition(tool_id)
            policy_context = PolicyContext(
                workflow_type=request.workflow_type,
                actor=request.actor,
                tool_id=tool_id,
                tool_risk_level=tool_def.risk_level,
                spend_to_date=float(context.spent_total),
            )
            decision = self._policy_engine.evaluate(policy_context)
            self._log_event(
                run_id=run.run_id,
                event_type="policy_decision",
                payload={"tool_id": tool_id, "decision": decision.model_dump(mode="json")},
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
                self._run_store.save(run)
                return run

            if decision.decision == PolicyDecisionType.REQUIRE_APPROVAL:
                approval_result = self._approval_service.request_approval(str(run.run_id), tool_id)
                run.status = RunStatus.BLOCKED
                run.current_state = RuntimeState.BLOCKED
                run.ended_at = datetime.now(timezone.utc)
                run.steps.append(
                    WorkflowStepResult(
                        step_id=step_id,
                        tool_id=tool_id,
                        success=False,
                        policy_decision=decision.decision,
                        error=approval_result.reason,
                    )
                )
                self._run_store.save(run)
                return run

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
                    event_type="budget_blocked",
                    payload={"tool_id": tool_id, "message": message},
                )
                self._run_store.save(run)
                return run

            if "soft budget" in message.lower():
                context.warnings.append(message)

            self._set_state(context, RuntimeState.EXECUTE_TOOL)
            invocation = ToolInvocation(
                run_id=run.run_id,
                step_id=step_id,
                tool_id=tool_id,
                input_payload=payload_dict,
            )
            result = self._tool_registry.execute(invocation)
            self._cost_tracker.add_record(
                record=self._build_cost_record(run.run_id, step_id, tool_id, tool_def.estimated_cost, result.cost_actual)
            )
            context.spent_total = self._cost_tracker.spent_total(run.run_id)

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
                self._run_store.save(run)
                return run

            run.steps.append(
                WorkflowStepResult(
                    step_id=step_id,
                    tool_id=tool_id,
                    success=True,
                    policy_decision=decision.decision,
                    output_payload=result.output_payload,
                )
            )

        run.status = RunStatus.COMPLETED
        run.current_state = RuntimeState.COMPLETED
        run.ended_at = datetime.now(timezone.utc)
        run.final_output = InvoiceProcessingOutput(
            invoice_id=invoice_payload.invoice_id,
            status="completed",
            summary="Invoice governance workflow completed successfully.",
        ).model_dump(mode="json")
        self._run_store.save(run)
        return run

    def get_run(self, run_id: UUID) -> WorkflowRun | None:
        return self._run_store.get(run_id)

    def _set_state(self, context: ExecutionContext, target: RuntimeState) -> None:
        context.run.current_state = self._state_machine.transition(context.run.current_state, target)
        self._log_event(
            run_id=context.run.run_id,
            event_type="state_transition",
            payload={"state": target.value},
        )

    def _log_event(self, run_id: UUID, event_type: str, payload: dict[str, object]) -> None:
        self._audit_logger.log(AuditEvent(run_id=run_id, event_type=event_type, payload=payload))

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
