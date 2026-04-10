# Validation Skill Framework

## Objectives

The validation system should:
1. Generate synthetic scenarios
2. Execute workflows through the runtime
3. Validate expected vs actual behavior
4. Capture execution and audit logs
5. Produce a structured markdown report

## Dimensions

### 1) Workflow and Decision Control
- correct execution sequence
- correct tool usage
- correct policy allow/deny decisions
- correct workflow termination
- exact expected risk level matching (not minimum-threshold only)
- expected policy matched rules are present
- expected policy reason substrings are present

### 2) Edge Case Handling
- malformed input handling
- missing data scenarios
- borderline risk thresholds
- duplicate or repeated workflows
- conflicting signals

### 3) Human-in-the-Loop
- approval triggered correctly for high-risk actions
- workflow pauses in `AWAITING_APPROVAL`
- workflow resumes after approval
- rejection leads to correct termination
- approval metadata captured
- approve branch and reject branch are both explicitly exercised where required

### 4) Auditability and Traceability
- all key events are logged
- policy decisions include reasons
- risk classification is recorded
- tool calls are logged
- approval events are tracked
- final outcome is recorded
- required event types are validated per scenario (policy/risk/approval/budget/final outcome)

## Components

### Scenario Generator
Generates synthetic workflow inputs:
- normal scenarios
- risk scenarios
- policy violation scenarios
- failure scenarios

Scenario fields:
- input payload
- expected policy decision
- expected risk level
- expected approval requirement
- expected final status
- expected policy matched rules
- expected policy reason substrings
- expected audit event types
- expected approval metadata
- validate approval branches (approve + reject)

### Validation Runner
Executes scenarios through the runtime.

### Validator
Compares expected vs actual behavior.

### Report Builder
Generates markdown validation report:
- `artifacts/validation_report.md`

## Output Artifacts

- `artifacts/validation_report.md`
- `artifacts/validation_results.json`

Recommended machine-readable metrics in `validation_results.json`:
- `policy_correctness`
- `approval_routing_correctness`
- `risk_classification_consistency`
- `budget_enforcement_correctness`
- `policy_trace_correctness`
- `approval_lifecycle_correctness`
- `failed_case_ids`

Reuse if present:
- `artifacts/audit.jsonl`
- `artifacts/runs.jsonl`

## Report Structure

- Summary
- Decision Validation
- Edge Case Validation
- Audit Validation
- Observations
- Conclusion

## Success Criteria

- all scenario types covered
- validation runs end-to-end
- markdown report generated
- mismatches identified
- audit logs validated
- behavior reproducible

## Future Extensions

- adversarial scenarios
- probabilistic risk
- CI integration
