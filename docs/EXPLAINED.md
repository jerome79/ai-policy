# Policy-Governed Agent Runtime — Explained

This document describes **what the code does**, **how the architecture fits together**, and **how to run and test** the Phase 1 implementation.

---

## 1. Architecture (high level)

The runtime is a **layered governance pipeline**: every tool call goes through policy and budget checks before execution; results and decisions are recorded for audit.

```text
┌─────────────────────────────────────────────────────────────────┐
│  API (optional)          POST /workflows/execute                 │
│  app/api/                                                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  WorkflowRunner / WorkflowOrchestrator  (app/runtime/)           │
│  • Validates input → runs fixed invoice step sequence            │
│  • StateMachine: received → validating → policy → budget →     │
│    execute → … → completed / blocked / failed                    │
└───┬───────────────────────┬───────────────────────┬─────────────┘
    │                       │                       │
    ▼                       ▼                       ▼
┌──────────────┐    ┌──────────────┐       ┌──────────────────────┐
│ PolicyEngine │    │ BudgetGuard  │       │ ToolRegistry         │
│ app/policy/  │    │ app/economics│       │ app/tools/           │
│ allow / deny │    │ soft / hard  │       │ register + execute   │
│ require_     │    │ limits       │       │ handlers (mock tools)│
│ approval     │    │              │       └──────────────────────┘
└──────────────┘    └──────────────┘
    │                       │
    └───────────┬───────────┘
                ▼
┌─────────────────────────────────────────────────────────────────┐
│  CostTracker (actual spend per run)                             │
│  AuditLogger + RunStore → artifacts/audit.jsonl, runs.jsonl     │
└─────────────────────────────────────────────────────────────────┘
```

**Design choices (Phase 1):**

| Layer | Responsibility |
|--------|----------------|
| `app/models/` | Pydantic contracts: workflows, tools, policy, economics, audit |
| `app/policy/` | `PolicyEngine.evaluate()` — central place for allow/deny/require_approval |
| `app/economics/` | `BudgetGuard.can_spend()` + `CostTracker` for recorded spend |
| `app/tools/` | `ToolRegistry` + mock handlers (`validate_invoice_data`, etc.) |
| `app/runtime/` | Orchestration loop and explicit state transitions |
| `app/services/` | YAML load, JSONL audit and run persistence |
| `app/bootstrap.py` | Wires dependencies and loads `app/config/policy.yaml` |

**Policy configuration** lives in `app/config/policy.yaml` (deny rules by role, risk threshold for approval). **Approval** is a stub: `require_approval` stops the run with a message; there is no interactive human flow yet.

---

## 2. What the code does (by area)

### 2.1 Entry points

- **Script:** `scripts/run_invoice_example.py` — builds the runner via `build_runner()`, constructs a `WorkflowRequest` with invoice-shaped `input_payload`, and prints the resulting `WorkflowRun`.
- **API:** `app/api/main.py` exposes FastAPI with `POST /workflows/execute` and `GET /workflows/{run_id}` (minimal; run lookup uses in-memory store populated during the process).

### 2.2 Bootstrap (`app/bootstrap.py`)

1. Loads `app/config/policy.yaml` into `PolicyConfig`.
2. Registers the three tools with `ToolRegistry` (definitions from `app/tools/definitions.py`, handlers from `app/tools/handlers/invoice_tools.py`).
3. Constructs `WorkflowOrchestrator` with policy engine, approval stub, cost tracker, budget guard, audit logger, and run store (paths under `artifacts/`).
4. Returns a `WorkflowRunner` that delegates to the orchestrator.

### 2.3 Orchestrator (`app/runtime/orchestrator.py`)

For the **invoice governance** workflow it runs a fixed sequence:

1. `validate_invoice_data`
2. `check_vendor_risk`
3. `prepare_payment_instruction`

For **each step** it:

1. Moves state (via `StateMachine`) toward `POLICY_CHECK`.
2. Builds `PolicyContext` and calls `PolicyEngine.evaluate()`.
3. If **deny** → marks run blocked, records step, saves, returns.
4. If **require_approval** → calls approval stub, marks blocked, records step, saves, returns.
5. If **allow** → `EVALUATE_BUDGET`: `BudgetGuard.can_spend()` using estimated tool cost; if over hard budget → blocked and return.
6. If budget OK → `EXECUTE_TOOL`: `ToolRegistry.execute()` with `ToolInvocation`.
7. Appends `CostRecord` to `CostTracker`, updates spent total.

On success through all steps, it sets **completed** and attaches a small `InvoiceProcessingOutput` as `final_output`.

### 2.4 Policy engine (`app/policy/engine.py`)

- **Deny:** if the actor’s role has this tool in `deny_tools_by_role` (from YAML).
- **Require approval:** if tool risk is at or above `approval_required_at_or_above`.
- **Allow:** otherwise.

### 2.5 Tools (`app/tools/`)

Handlers are **pure mock logic**: validate numbers, mock vendor risk prefix `hr-`, mock payment instruction payload. They return `ToolResult` with `cost_actual`; they do **not** call policy or orchestration.

### 2.6 Persistence

- `AuditLogger` appends JSON lines to `artifacts/audit.jsonl`.
- `RunStore` appends workflow run snapshots to `artifacts/runs.jsonl` and keeps the latest run in memory for `GET /workflows/{run_id}` in the same process.

---

## 3. How to test

### 3.1 Install

From the repository root:

```bash
python -m pip install -e .[dev]
```

### 3.2 Run the full test suite

```bash
pytest
```

Tests live under `tests/unit/` and `tests/integration/`.

### 3.3 What the tests cover (governance-focused)

| Area | File | What it checks |
|------|------|----------------|
| Tool registry | `tests/unit/test_tool_registry.py` | Registered tool executes and returns expected payload |
| Policy engine | `tests/unit/test_policy_engine.py` | Deny by role; require_approval at high risk |
| Budget | `tests/unit/test_cost_tracker.py` | Hard budget blocks projected spend |
| Orchestrator | `tests/unit/test_orchestrator_invoice_flow.py` | Happy path (3 steps); policy deny on payment tool; require_approval surfaced; hard budget stop |
| End-to-end | `tests/integration/test_invoice_workflow_end_to_end.py` | Bootstrap + runner with default config |

### 3.4 Run a manual smoke test

```bash
python scripts/run_invoice_example.py
```

Then inspect `artifacts/audit.jsonl` and `artifacts/runs.jsonl` for decision and state events.

### 3.5 Optional API smoke test

```bash
python scripts/run_api.py
```

Then `POST` to `http://127.0.0.1:8000/workflows/execute` with a body matching `ExecuteWorkflowRequest` (see `app/api/schemas/workflow_api_models.py`).

---

## 4. File map (quick reference)

| Path | Role |
|------|------|
| `app/runtime/orchestrator.py` | Main governance loop |
| `app/runtime/state_machine.py` | Allowed state transitions |
| `app/policy/engine.py` | Policy decisions |
| `app/economics/budget_guard.py` | Pre-execution budget check |
| `app/economics/cost_tracker.py` | Accumulated actual costs |
| `app/tools/registry.py` | Tool registration and dispatch |
| `app/tools/handlers/invoice_tools.py` | Mock invoice tools |
| `app/config/policy.yaml` | Policy YAML |
| `app/bootstrap.py` | Dependency wiring |

---

## 5. Where to go next (Phase 2 preview)

- Richer policy (amount thresholds, permissions beyond deny lists).
- Real approval workflow (async, persist pending state).
- Config-driven workflow graphs instead of a fixed list in the orchestrator.
- Stronger audit/query and optional SQLite.

For the original product thesis and Phase 1 checklist, see `README.md`.
