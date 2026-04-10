---
name: governance-validation-runtime
description: Validates a policy-governed AI runtime through synthetic scenarios, expected-vs-actual checks, audit verification, and markdown reporting. Use when the user asks for runtime validation, governance acceptance checks, policy/risk/approval behavior verification, or reproducible readiness evidence.
---

# Governance Validation Runtime

## Purpose

Use this skill to validate that a policy-governed workflow runtime behaves correctly under governance constraints.

The validation must prove:
- workflow execution is controlled
- policy decisions are enforced
- risk is classified correctly
- human approval is triggered when required
- failures are handled safely
- events are auditable and traceable
- policy reason codes/events are verifiably traceable

## Quick Workflow

Run this checklist end-to-end:

```markdown
Validation Progress:
- [ ] Define scenarios with explicit expected outcomes
- [ ] Execute scenarios through runtime entrypoints
- [ ] Compare expected vs actual outcomes
- [ ] Validate audit and run artifacts
- [ ] Generate markdown + JSON outputs
- [ ] Document mismatches and conclusion
```

## Validation Dimensions

For every scenario set, verify:

1. Workflow and decision control
   - execution sequence, tool usage, allow/deny behavior, terminal status
   - expected policy rule matches (e.g. `default_allow`, `approval_required_at_or_above`, `deny_tools_by_role`)
   - expected policy reason substrings are present in decision events
2. Edge case handling
   - malformed input, missing fields, threshold boundaries, duplicate/conflicting inputs
3. Human-in-the-loop
   - `AWAITING_APPROVAL`, resume/reject paths, approval metadata
   - explicit approve branch (`decide_approval(..., approved=True)` then `resume`) reaches expected terminal status
   - explicit reject branch (`decide_approval(..., approved=False)` then `resume`) reaches expected terminal status
4. Auditability and traceability
   - decision reasons, risk classification, tool calls, approval events, final outcome
   - required audit event types are present per scenario (policy, risk, approval, budget/final outcome)

## Scenario Contract

Each scenario should define:
- input payload
- expected policy decision
- expected risk level
- expected approval requirement
- expected final status
- expected policy matched rules
- expected policy reason substrings
- expected audit event types
- expected approval metadata (for approval scenarios)
- whether approval lifecycle branches must be validated

## Suggested Project Layout

Use this structure unless the repo already has an equivalent module:

```text
app/validation/
  scenario_generator.py
  runner.py
  validator.py
  report_builder.py
scripts/run_validation.py
artifacts/
  validation_report.md
  validation_results.json
```

Reuse existing runtime artifacts when available:
- `artifacts/audit.jsonl`
- `artifacts/runs.jsonl`

## Report Contract

The generated `artifacts/validation_report.md` should include:
- Summary
- Decision Validation
- Edge Case Validation
- Audit Validation
- Observations
- Conclusion

`artifacts/validation_results.json` should include, at minimum:
- `policy_correctness`
- `approval_routing_correctness`
- `risk_classification_consistency` (exact expected level match)
- `budget_enforcement_correctness`
- `policy_trace_correctness`
- `approval_lifecycle_correctness`
- `failed_case_ids`

Also write machine-readable outcomes to:
- `artifacts/validation_results.json`

## Success Criteria

Validation is complete only when:
- all scenario categories are covered
- runs execute end-to-end
- report and JSON artifacts are generated
- mismatches are clearly identified
- audit logs are verified
- behavior is reproducible

## Additional Reference

For the full framework specification, see `reference.md`.
