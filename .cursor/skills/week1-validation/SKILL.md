---
name: week1-validation
description: Validates Week 1 readiness for the policy-governed invoice workflow by running local checks for workflow execution, policy allow/deny behavior, budget enforcement, structured workflow results, and basic tests. Use when the user asks for Week 1 completion, readiness checks, acceptance validation, or invoice workflow governance verification.
---

# Week 1 Validation

## Purpose

Determine whether Week 1 is complete using reproducible local checks and a scored result.

Week 1 is complete only if all required checks pass:
- run one invoice workflow locally
- see policy allow/deny/require_approval behavior
- see budget pass/soft-warning/hard-block behavior
- produce a structured workflow result
- pass the basic tests

## When to Use

Apply this skill when the user asks to:
- validate Week 1 completion/readiness
- run an acceptance gate for Phase 1
- verify governance behavior for the invoice workflow
- confirm test baseline is passing

## Validation Workflow

Run from repository root.

Preferred one-command execution:
- `python scripts/validate_week1.py`
- optional fast rerun: `python scripts/validate_week1.py --skip-install`

Task Progress:
- [ ] Step 1: Environment and install
- [ ] Step 2: Run invoice workflow locally
- [ ] Step 3: Verify policy allow/deny behavior
- [ ] Step 4: Verify budget enforcement behavior
- [ ] Step 5: Verify structured workflow result
- [ ] Step 6: Run basic tests
- [ ] Step 7: Produce final validation report

### Step 1: Environment and install

1. Install dependencies:
   - `python -m pip install -e ".[dev]"`
2. If install fails, stop and report the exact error.

### Step 2: Run invoice workflow locally

Run:
- `python scripts/run_invoice_example.py`

Pass criteria:
- command exits successfully
- run output is printed without exceptions

### Step 3: Verify policy scenarios (allow, deny, require_approval)

Use tests as authoritative evidence:
- `pytest tests/unit/test_policy_engine.py::test_policy_allows_low_risk_tool_when_not_denied tests/unit/test_policy_engine.py::test_denied_tool_call_by_policy tests/unit/test_policy_engine.py::test_require_approval_is_surfaced tests/unit/test_orchestrator_invoice_flow.py::test_happy_path_invoice_workflow tests/unit/test_orchestrator_invoice_flow.py::test_denied_tool_call_by_policy_in_orchestrator tests/unit/test_orchestrator_invoice_flow.py::test_require_approval_decision_is_surfaced`

Pass criteria:
- tests pass
- output shows all three policy branches are covered: allow, deny, require_approval

If test filtering is brittle, run the full files:
- `pytest tests/unit/test_policy_engine.py tests/unit/test_orchestrator_invoice_flow.py`

### Step 4: Verify budget scenarios (pass, soft-warning, hard-block)

Run:
- `pytest tests/unit/test_cost_tracker.py::test_budget_passes_under_soft_limit tests/unit/test_cost_tracker.py::test_budget_soft_limit_warns_but_allows tests/unit/test_cost_tracker.py::test_workflow_stopped_by_hard_budget tests/unit/test_orchestrator_invoice_flow.py::test_happy_path_invoice_workflow tests/unit/test_orchestrator_invoice_flow.py::test_workflow_stopped_by_hard_budget_in_orchestrator`

Pass criteria:
- tests pass
- all three budget outcomes are covered: pass, soft-warning, hard-block

If test filtering is brittle, run the full files:
- `pytest tests/unit/test_cost_tracker.py tests/unit/test_orchestrator_invoice_flow.py`

### Step 5: Verify structured workflow result

After running `python scripts/run_invoice_example.py`, inspect:
- `artifacts/runs.jsonl`
- `artifacts/audit.jsonl`

Pass criteria:
- `artifacts/runs.jsonl` contains at least one JSONL run record
- run record contains structured fields (for example: run id, status, steps, final output)
- `artifacts/audit.jsonl` contains governance/audit events for policy and/or budget decisions

If needed, also verify API shape using models in:
- `app/api/schemas/workflow_api_models.py`

### Step 6: Run basic tests

Run:
- `pytest`

Pass criteria:
- full test suite passes

## Scoring and Completion Rules

Score each required criterion as:
- `PASS` = 1 point
- `FAIL` = 0 points

Criteria:
1. invoice workflow runs locally
2. policy allow/deny/require_approval behavior is demonstrated
3. budget pass/soft-warning/hard-block behavior is demonstrated
4. structured workflow result is produced
5. basic tests pass

Compute:
- `score = earned_points / 5`

Interpretation:
- `Ready`: score >= 0.8 and no critical blockers
- `Not Ready`: score < 0.8

Strict completion gate:
- Week 1 is `COMPLETE` only when all 5 criteria are `PASS`.
- If score >= 0.8 but any criterion fails, report `PARTIAL` with explicit blockers.

## Output Format

Use this exact report shape:

```markdown
# Week 1 Validation Report

## Result
- Status: COMPLETE | PARTIAL | NOT READY
- Score: X/5 (Y%)

## Criteria
- [PASS|FAIL] Run one invoice workflow locally
- [PASS|FAIL] See policy allow/deny behavior
- [PASS|FAIL] See budget enforcement behavior
- [PASS|FAIL] Produce a structured workflow result
- [PASS|FAIL] Pass the basic tests

## Evidence
- Commands run:
  - `...`
- Key outputs:
  - `...`
- Artifacts inspected:
  - `artifacts/runs.jsonl`
  - `artifacts/audit.jsonl`

## Blockers
- None | list of concrete failures

## Next Actions
- Actionable fixes for each failed criterion
```

## Failure Handling

- Never silently pass a failed check.
- If a command fails, capture error output and mark the related criterion as `FAIL`.
- If evidence is missing, mark as `FAIL` and explain what was missing.
- Keep recommendations concrete and command-oriented.

## Utility Script

Use the validator script to run the full gate and generate a report:
- `scripts/validate_week1.py`
- report output: `artifacts/week1_validation_report.md`
