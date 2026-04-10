# Policy-Governed AI Agent Runtime

A **portfolio-grade backend reference** for running LLM-adjacent workflows under explicit **policy**, **economics**, **risk**, **human approval**, and **audit** constraints. The emphasis is on *governed execution*—not chat UX, not model training, and not hand-wavy “safety” copy.

---

## Project thesis

Autonomous agents fail in production for the same reasons other distributed systems fail: unclear control points, unbounded side effects, opaque decisions, and weak evidence trails. This repository models AI workflow execution as an **operable system**: every tool transition is validated, policy-scored, budget-checked, optionally human-approved, and logged with structured reasons. Prompting matters; **runtime governance** is what makes behavior reviewable and repeatable.

---

## Architecture overview

| Layer | Responsibility |
|--------|------------------|
| **API** (`app/api/`) | Validates requests, delegates to the orchestrator, no domain logic in routes. |
| **Runtime** (`app/runtime/`) | State-machine execution: validate → policy → budget → execute → terminal states. |
| **Policy & risk** (`app/policy/`) | `PolicyDecision` (`allow` / `deny` / `require_approval`), rules from YAML, risk classification. |
| **Economics** (`app/economics/`) | Cost tracking and soft/hard budget enforcement. |
| **Tools** (`app/tools/`) | Registry + mocked invoice workflow handlers. |
| **Services** (`app/services/`) | Audit logger and JSONL run store under `artifacts/`. |
| **Evaluation** (`app/evaluation/`) | Synthetic scenario harness for regression-style governance checks. |
| **Observability** (`app/observability/`) | Aggregates metrics from `artifacts/*.jsonl` for reporting. |

```text
Request → Orchestrator → PolicyEngine / Risk → BudgetGuard → ToolRegistry → Audit + RunStore
                ↘ Approval gate (require_approval) ↙
```

For a guided walkthrough of modules and the invoice workflow, see [`docs/EXPLAINED.md`](docs/EXPLAINED.md).

---

## Governance primitives

- **Policy decisions** with `reasons` and `matched_rules` (traceable to configuration).
- **Risk levels** derived from scoring thresholds (configurable), aligned with tool and workflow context.
- **Approvals** for high-impact steps: pause, decide, resume; outcomes recorded in audit events.
- **Budget guardrails** with soft warnings and hard stops; per-step `cost_update` events.
- **Audit trail** (`artifacts/audit.jsonl`) and **run history** (`artifacts/runs.jsonl`) correlated by `run_id`.

---

## Validation results (Phase 2 / Week 2)

Synthetic governance validation (evaluation harness + audit checks) on the reference runtime:

| Metric | Result |
|--------|--------|
| Scenarios executed | 24 |
| Failed scenarios | 0 |
| Policy correctness | 1.00 |
| Approval routing correctness | 1.00 |
| Risk classification consistency | 1.00 |
| Budget enforcement correctness | 1.00 |
| Policy trace correctness | 1.00 |
| Approval lifecycle correctness | 1.00 |

Artifacts: `artifacts/validation_report.md`, `artifacts/validation_results.json`, `artifacts/phase2_evaluation.json`.

---

## Observability and summary reporting

Aggregate operational metrics from local JSONL logs:

- Total workflows (distinct `run_id` in `runs.jsonl`)
- Risk distribution (latest snapshot per run—see report footnote)
- Approval-required rate and approval outcomes (from audit events)
- Policy deny counts (audit `policy_decision` with `deny`)
- Failure and terminal status counts (`failed`, `blocked`, etc.)
- Average cost per run (from audit `cost_update` rollups) and average steps per run

**Generate reports:**

```bash
python scripts/generate_runtime_summary.py
```

Outputs:

- `artifacts/runtime_summary.json`
- `artifacts/runtime_summary.md`

Optional paths: `--runs`, `--audit`, `--json-out`, `--markdown-out`, `--base-path`.

---

## Business value

A concise, non-hyped framing for operators and stakeholders is in [`docs/business_summary.md`](docs/business_summary.md) (operational control, governance, risk reduction, auditability).

---

## Limitations (intentional for v1)

- **Reference implementation**, not a hosted product: single-process, JSONL persistence, mocked tools.
- **No production identity/IAM**, no multi-tenant isolation, no HA deployment story in-repo.
- **Risk and policy YAML** are illustrative; real enterprises need joint review with legal/compliance.
- **Latest-run risk metrics** in summaries reflect the last persisted snapshot, not necessarily ingress-only risk.

---

## Roadmap (v2 directions)

- Durable store (SQLite/Postgres) and retention policies for audit.
- Pluggable policy backends (OPA, enterprise IAM) and secret management.
- Richer approval UX (tickets, SLAs) and idempotent webhooks.
- OpenTelemetry metrics/traces alongside JSONL.
- Additional vertical workflows sharing the same governance spine.

---

## Quick start

**Install** (quote `".[dev]"` in PowerShell so `[dev]` is not treated as a wildcard):

```bash
python -m pip install -e ".[dev]"
```

**Run the invoice example**

```bash
python scripts/run_invoice_example.py
```

**Run governance evaluation (Phase 2)**

```bash
python scripts/run_phase2_evaluation.py
```

**Start the API** (optional)

```bash
python scripts/run_api.py
```

**Tests**

```bash
pytest
```

**Artifacts** (after runs): `artifacts/audit.jsonl`, `artifacts/runs.jsonl`.

---

## Portfolio collateral

Drafts for external publication (edit before posting):

- [`docs/portfolio/medium_article_draft.md`](docs/portfolio/medium_article_draft.md)
- [`docs/portfolio/linkedin_post_draft.md`](docs/portfolio/linkedin_post_draft.md)
- [`docs/portfolio/upwork_case_study_summary.md`](docs/portfolio/upwork_case_study_summary.md)

---

## Tech stack

- Python 3.11+
- FastAPI, Pydantic v2, PyYAML, Uvicorn
- pytest

---

## License / use

Treat this repository as an **engineering showcase**. Adapt patterns responsibly; production deployments require threat modeling, access control, and organizational process beyond this codebase.
