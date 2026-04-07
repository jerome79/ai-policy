# Policy-Governed AI Agent Runtime

This repository defines a portfolio-grade architecture for running autonomous AI workflows under enterprise governance constraints:

- policy constraints
- economic cost controls
- risk thresholds
- auditability requirements
- human-in-the-loop approvals
- evaluation discipline

The strategic intent is to demonstrate production-oriented AI governance architecture, not a toy agent demo.

## Core Thesis

We are building a governed execution environment for AI workflows.

The core challenge is not just tool calling or agent connectivity. It is governance and control:

- controlling agent execution
- governing tool usage
- enforcing cost budgets
- classifying and managing risk
- requiring human approval for high-risk actions
- logging and auditing every decision
- evaluating runtime behavior systematically

## Phase 1 Scope

Phase 1 includes:

- architecture proposal
- folder structure
- domain models
- orchestrator skeleton
- tool registry
- policy engine
- cost tracker
- one mocked invoice governance workflow
- sample YAML config
- basic tests
- README draft

## Non-Goals

- no fancy frontend
- no Kubernetes
- no distributed infrastructure
- no complex cloud deployment
- no chatbot UX
- no unrelated AI features outside governance/economics/control

## Preferred Stack

- Python 3.11+
- FastAPI
- Pydantic
- YAML config
- state machine style orchestration
- pluggable tool registry
- structured logs
- local file persistence acceptable for v1
- Docker-ready structure
- tests included

## Proposed Architecture

The runtime is designed as a layered governance system with strict separation of concerns.

### 1) Inbound Layer (API / Request Handling)

- Receives workflow execution requests (`workflow_type`, `inputs`, `request_context`)
- Validates contracts with Pydantic
- Assigns `workflow_run_id` and correlation metadata
- Delegates execution to orchestrator only (no domain logic in routes)

### 2) Orchestration Layer (State-Machine Runtime)

- Executes workflow via explicit states:
  - `received -> validating -> policy_check -> execute_tool -> evaluate_budget -> completed/blocked/failed`
- Maintains deterministic step-by-step execution trace
- Never calls tools directly; all calls flow through governed registry interface

### 3) Governance Layer (Policy Engine + Approval Gate)

- Evaluates actor permissions, tool allow/deny rules, risk thresholds, and workflow constraints
- Produces `PolicyDecision`:
  - `allow`
  - `deny`
  - `require_approval`
- Captures reasons and matched rules
- Approval service (v1 local stub) pauses/resumes high-risk actions

### 4) Economics Layer (Cost Tracker + Budget Guardrails)

- Tracks estimated and actual run cost per step and per workflow run
- Enforces:
  - soft warning threshold
  - hard stop threshold
- Emits economics events into audit trail

### 5) Tool Execution Layer (Pluggable Tool Registry)

- Central registry for tool definitions and handlers
- Tool metadata includes:
  - tool id/version
  - risk level
  - cost profile
  - required permissions
  - input/output schemas
- Runtime can execute only registered tools through a uniform interface

### 6) Audit & Persistence Layer

- Structured logging for all governance-critical events:
  - request received
  - policy evaluation
  - approval requested/granted/denied
  - tool invocation/result
  - budget update/stop decision
  - run completion/failure
- v1 persistence target: local JSONL (SQLite can be introduced in Phase 2)

### 7) Evaluation Layer (Phase 1 baseline)

- Test harness validates policy outcomes, budget behavior, and state transitions
- Stores execution artifacts for governance review and reproducibility

## Proposed Repository Structure

```text
policy-governed-agent-runtime/
  app/
    api/
      __init__.py
      main.py
      routes/
        __init__.py
        workflow_routes.py
      schemas/
        __init__.py
        workflow_api_models.py

    runtime/
      __init__.py
      orchestrator.py
      state_machine.py
      execution_context.py
      workflow_runner.py

    tools/
      __init__.py
      base.py
      registry.py
      definitions.py
      handlers/
        __init__.py
        invoice_tools.py

    policy/
      __init__.py
      engine.py
      rules.py
      approval.py
      evaluators/
        __init__.py
        risk_evaluator.py
        permission_evaluator.py

    economics/
      __init__.py
      cost_tracker.py
      budget_guard.py
      pricing.py

    models/
      __init__.py
      common.py
      workflow.py
      tool.py
      policy.py
      economics.py
      audit.py
      invoice.py

    services/
      __init__.py
      audit_logger.py
      run_store.py
      config_loader.py
      clock.py

    config/
      policy.yaml
      tools.yaml
      runtime.yaml

  tests/
    unit/
      test_policy_engine.py
      test_cost_tracker.py
      test_tool_registry.py
      test_orchestrator_invoice_flow.py
    integration/
      test_invoice_workflow_end_to_end.py
    fixtures/
      sample_workflow_request.json
      sample_policy.yaml

  docs/
    architecture.md
    governance-model.md
    phase1-decisions.md

  examples/
    invoice_workflow_request.yaml
    invoice_workflow_response.yaml

  scripts/
    run_api.py
    run_invoice_example.py

  README.md
  pyproject.toml
  Dockerfile
  .env.example
```

## Key Domain Models (Pydantic-First)

These are the minimum contracts for a credible governance runtime.

### Workflow Contracts

- `WorkflowRequest`
  - `workflow_type: str`
  - `input_payload: dict[str, Any]`
  - `actor: ActorContext`
  - `budget: BudgetConstraint`
  - `risk_tolerance: RiskLevel`
  - `metadata: dict[str, str]`

- `WorkflowRun`
  - `run_id: UUID`
  - `status: RunStatus`
  - `current_state: RuntimeState`
  - `started_at`, `ended_at`
  - `steps: list[WorkflowStepResult]`
  - `final_output: dict[str, Any] | None`

### Tooling Contracts

- `ToolDefinition`
  - `tool_id`
  - `version`
  - `description`
  - `risk_level`
  - `estimated_cost`
  - `input_schema_ref`, `output_schema_ref`
  - `required_permissions`

- `ToolInvocation`
  - `run_id`
  - `step_id`
  - `tool_id`
  - `input_payload`

- `ToolResult`
  - `success: bool`
  - `output_payload`
  - `error`
  - `cost_actual`

### Policy Contracts

- `PolicyContext`
  - actor, tool definition, workflow context, environment, spend-to-date

- `PolicyDecision`
  - `decision: Literal["allow", "deny", "require_approval"]`
  - `reasons: list[str]`
  - `matched_rules: list[str]`
  - `risk_score: float`

- `PolicyRule`
  - rule id, condition config/expression, effect, priority

### Economics Contracts

- `BudgetConstraint`
  - `currency`
  - `max_total`
  - `soft_limit`

- `CostRecord`
  - `run_id`, `step_id`, `tool_id`
  - `estimated_cost`, `actual_cost`, `timestamp`

- `BudgetStatus`
  - `spent_total`
  - `remaining`
  - `is_soft_limit_reached`
  - `is_hard_limit_exceeded`

### Audit Contracts

- `AuditEvent`
  - `event_id`, `run_id`, `event_type`, `timestamp`
  - `actor`
  - `payload: dict[str, Any]`
  - `decision_refs: list[str]`

- `ExecutionTrace`
  - ordered list of audit events for replay and governance review

### Invoice Workflow Contracts (Vertical Anchor)

- `InvoiceWorkflowInput`
  - invoice id/vendor/amount/currency/line items/requestor
- `InvoiceValidationResult`
- `InvoiceApprovalDecision`
- `InvoiceProcessingOutput`
  - final status + policy/economic evidence summary

## Phase 1 Implementation Plan

### Step 1: Project Scaffold + Config

- Create package structure and module stubs
- Add `pyproject.toml` with minimal dependencies
- Add YAML configs:
  - `policy.yaml`
  - `tools.yaml`
  - `runtime.yaml`

### Step 2: Domain Models

- Implement strongly typed Pydantic models in `app/models/`
- Add enums for run state/status/risk/policy decisions
- Add audit-safe serialization helpers

### Step 3: Tool Registry

- Build `ToolRegistry` abstraction and in-memory implementation
- Validate registration metadata and schemas
- Add mocked invoice tools:
  - `validate_invoice_data`
  - `check_vendor_risk`
  - `prepare_payment_instruction` (high-risk mock)

### Step 4: Policy Engine + Approval Stub

- Implement rules evaluation pipeline from YAML
- Return deterministic `PolicyDecision` with reasons/matched rules
- Add approval gate stub for `require_approval` flows

### Step 5: Cost Tracker + Budget Guard

- Track estimated and actual costs by run and step
- Enforce soft/hard budget thresholds before each tool action
- Emit budget events to audit trail

### Step 6: Runtime Orchestrator Skeleton

- Build state-machine execution runner
- Pipeline per step:
  - validate
  - policy check
  - budget check
  - execute tool
  - log/audit
  - continue/stop

### Step 7: Mocked Invoice Governance Workflow

- Implement invoice governance step sequence
- Cover scenarios:
  - normal approval path
  - policy deny path
  - require-approval path
  - budget exceeded stop path

### Step 8: API Surface + Scripts

- FastAPI endpoints:
  - `POST /workflows/execute`
  - `GET /workflows/{run_id}`
- Add scripts for local example execution

### Step 9: Tests

- Unit tests:
  - policy engine
  - cost tracker
  - tool registry
  - orchestrator transitions
- Integration test:
  - invoice workflow end-to-end including audit assertions

### Step 10: Documentation Baseline

- Architecture rationale
- Governance guarantees
- Operational run instructions
- Testing instructions
- Phase 2 roadmap hooks

## Required Modules Checklist

1. runtime / orchestrator
2. tool registry
3. policy engine
4. economics / cost tracker
5. models
6. example workflow
7. tests
8. README

---

Phase 1 scaffold is now implemented in this repository.

For a **guided walkthrough** (architecture, what each part does, how to test), see [`docs/EXPLAINED.md`](docs/EXPLAINED.md).

## Run Example

1. Install dependencies:
   - `python -m pip install -e ".[dev]"`  
     On **PowerShell**, quote `".[dev]"` so `[dev]` is not treated as a wildcard.
2. Run the invoice workflow example:
   - `python scripts/run_invoice_example.py`
3. Inspect generated artifacts:
   - `artifacts/audit.jsonl`
   - `artifacts/runs.jsonl`

## Run Tests

- Run all tests:
  - `pytest`
- Required scenarios covered:
  - allowed tool call
  - denied tool call by policy
  - workflow stopped by hard budget
  - `require_approval` decision surfaced
  - happy path invoice workflow
