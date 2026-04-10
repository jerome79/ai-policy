"""Aggregate workflow and audit metrics from runs.jsonl and audit.jsonl."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _latest_run_snapshots(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """runs.jsonl appends a row on each save; last row per run_id wins."""
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        rid = row.get("run_id")
        if rid is None:
            continue
        by_id[str(rid)] = row
    return by_id


def _policy_decision_from_payload(payload: dict[str, Any]) -> str | None:
    inner = payload.get("decision")
    if not isinstance(inner, dict):
        return None
    d = inner.get("decision")
    return str(d) if d is not None else None


def _parse_cost_spent(payload: dict[str, Any]) -> float | None:
    raw = payload.get("spent_total")
    if raw is None:
        return None
    try:
        return float(str(raw))
    except ValueError:
        return None


@dataclass
class RuntimeSummary:
    """Machine- and human-readable summary of local runtime artifacts."""

    generated_at: str
    sources: dict[str, str]
    total_workflows: int
    risk_distribution: dict[str, int]
    approval_required_runs: int
    approval_required_rate: float | None
    approval_outcomes: dict[str, int]
    policy_deny_events: int
    runs_with_policy_deny: int
    runs_ended_failed: int
    runs_ended_blocked: int
    runs_ended_completed: int
    runs_ended_awaiting_approval: int
    runs_ended_running: int
    average_cost_per_run: float | None
    average_steps_per_run: float | None
    total_cost_observed: float | None
    notes: list[str] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        base = asdict(self)
        base["failure_count"] = self.runs_ended_failed
        base["governed_stop_runs"] = self.runs_ended_blocked + self.runs_ended_failed
        return base


def build_runtime_summary(
    runs_path: Path,
    audit_path: Path,
) -> RuntimeSummary:
    """Build summary from JSONL paths (missing files yield empty aggregates)."""
    generated_at = datetime.now(timezone.utc).isoformat()
    sources = {
        "runs_jsonl": str(runs_path.resolve()),
        "audit_jsonl": str(audit_path.resolve()),
    }
    notes: list[str] = []

    run_rows = _read_jsonl(runs_path)
    audit_rows = _read_jsonl(audit_path)

    latest = _latest_run_snapshots(run_rows)
    total_workflows = len(latest)

    risk_distribution: dict[str, int] = {}
    runs_ended_failed = 0
    runs_ended_blocked = 0
    runs_ended_completed = 0
    runs_ended_awaiting_approval = 0
    runs_ended_running = 0
    step_counts: list[int] = []

    for snap in latest.values():
        risk = snap.get("risk") or {}
        level = risk.get("level")
        if isinstance(level, str) and level:
            risk_distribution[level] = risk_distribution.get(level, 0) + 1
        else:
            risk_distribution["unknown"] = risk_distribution.get("unknown", 0) + 1

        status = str(snap.get("status") or "")
        if status == "failed":
            runs_ended_failed += 1
        elif status == "blocked":
            runs_ended_blocked += 1
        elif status == "completed":
            runs_ended_completed += 1
        elif status == "awaiting_approval":
            runs_ended_awaiting_approval += 1
        elif status == "running":
            runs_ended_running += 1

        steps = snap.get("steps")
        if isinstance(steps, list):
            step_counts.append(len(steps))

    # Audit-derived metrics
    runs_with_require_approval: set[str] = set()
    policy_deny_events = 0
    runs_with_policy_deny: set[str] = set()
    approval_outcomes: dict[str, int] = {"approved": 0, "rejected": 0, "request_logged": 0}

    cost_by_run: dict[str, float] = {}

    for ev in audit_rows:
        rid = ev.get("run_id")
        run_key = str(rid) if rid is not None else ""
        et = ev.get("event_type")
        payload = ev.get("payload")
        if not isinstance(payload, dict):
            continue

        if et == "policy_decision":
            decision = _policy_decision_from_payload(payload)
            if decision == "require_approval" and run_key:
                runs_with_require_approval.add(run_key)
            if decision == "deny":
                policy_deny_events += 1
                if run_key:
                    runs_with_policy_deny.add(run_key)

        if et == "approval_event":
            if "result" in payload:
                res = payload.get("result")
                if isinstance(res, dict) and "approved" in res:
                    if res.get("approved") is True:
                        approval_outcomes["approved"] += 1
                    else:
                        approval_outcomes["rejected"] += 1
                else:
                    approval_outcomes["request_logged"] += 1
            elif "request" in payload:
                approval_outcomes["request_logged"] += 1

        if et == "cost_update" and run_key:
            spent = _parse_cost_spent(payload)
            if spent is not None:
                prev = cost_by_run.get(run_key, 0.0)
                if spent >= prev:
                    cost_by_run[run_key] = spent

    approval_required_runs = len(runs_with_require_approval)
    if total_workflows > 0:
        approval_required_rate = approval_required_runs / total_workflows
    else:
        approval_required_rate = None

    if not cost_by_run and audit_rows:
        notes.append(
            "No cost_update events found; average_cost_per_run is null.",
        )
    total_cost = sum(cost_by_run.values()) if cost_by_run else None
    if total_workflows > 0 and cost_by_run:
        # Average cost over all workflows seen in runs file; missing runs count as 0 cost
        total_cost_all_runs = sum(cost_by_run.get(rid, 0.0) for rid in latest.keys())
        average_cost = total_cost_all_runs / total_workflows
    else:
        average_cost = None

    if step_counts:
        average_steps = sum(step_counts) / len(step_counts)
    else:
        average_steps = None

    if total_workflows == 0:
        notes.append("No workflow rows in runs.jsonl (or file missing).")

    return RuntimeSummary(
        generated_at=generated_at,
        sources=sources,
        total_workflows=total_workflows,
        risk_distribution=dict(sorted(risk_distribution.items())),
        approval_required_runs=approval_required_runs,
        approval_required_rate=approval_required_rate,
        approval_outcomes=approval_outcomes,
        policy_deny_events=policy_deny_events,
        runs_with_policy_deny=len(runs_with_policy_deny),
        runs_ended_failed=runs_ended_failed,
        runs_ended_blocked=runs_ended_blocked,
        runs_ended_completed=runs_ended_completed,
        runs_ended_awaiting_approval=runs_ended_awaiting_approval,
        runs_ended_running=runs_ended_running,
        average_cost_per_run=average_cost,
        average_steps_per_run=average_steps,
        total_cost_observed=total_cost,
        notes=notes,
    )


def render_summary_markdown(summary: RuntimeSummary) -> str:
    """Readable report for stakeholders and portfolio use."""
    lines = [
        "# Runtime observability summary",
        "",
        f"Generated (UTC): `{summary.generated_at}`",
        "",
        "## Sources",
        "",
        f"- Runs: `{summary.sources['runs_jsonl']}`",
        f"- Audit: `{summary.sources['audit_jsonl']}`",
        "",
        "## Volume",
        "",
        f"- **Total workflows (distinct run ids):** {summary.total_workflows}",
        "",
        "## Risk distribution (latest snapshot per workflow)",
        "",
    ]
    if summary.risk_distribution:
        for level, count in summary.risk_distribution.items():
            lines.append(f"- **{level}:** {count}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append(
        "*Risk levels use the last persisted snapshot per workflow; late-stage "
        "classifications can differ from the first step.*",
    )
    lines.extend(
        [
            "",
            "## Approvals",
            "",
            f"- **Runs with at least one `require_approval` policy decision:** "
            f"{summary.approval_required_runs}",
        ]
    )
    if summary.approval_required_rate is not None:
        lines.append(
            f"- **Approval-required rate:** {summary.approval_required_rate:.2%}",
        )
    else:
        lines.append("- **Approval-required rate:** n/a (no workflows)")
    lines.extend(
        [
            "- **Approval outcomes (audit `approval_event` with `result`):**",
            f"  - approved: {summary.approval_outcomes.get('approved', 0)}",
            f"  - rejected: {summary.approval_outcomes.get('rejected', 0)}",
            f"  - request-only / other: {summary.approval_outcomes.get('request_logged', 0)}",
            "",
            "## Policy",
            "",
            f"- **Policy deny events (audit):** {summary.policy_deny_events}",
            f"- **Runs touching a policy deny:** {summary.runs_with_policy_deny}",
            "",
            "## Terminal status (latest snapshot)",
            "",
            f"- completed: {summary.runs_ended_completed}",
            f"- blocked (budget/policy stop, etc.): {summary.runs_ended_blocked}",
            f"- failed (`failure_count` in JSON): {summary.runs_ended_failed}",
            f"- governed stops (blocked + failed): "
            f"{summary.runs_ended_blocked + summary.runs_ended_failed}",
            f"- awaiting_approval: {summary.runs_ended_awaiting_approval}",
            f"- running (incomplete in log): {summary.runs_ended_running}",
            "",
            "## Economics & depth",
            "",
        ]
    )
    if summary.average_cost_per_run is not None:
        lines.append(f"- **Average cost per run:** {summary.average_cost_per_run:.4f}")
    else:
        lines.append("- **Average cost per run:** n/a")
    if summary.total_cost_observed is not None:
        lines.append(f"- **Total observed spend (sum of last cost per run):** {summary.total_cost_observed:.4f}")
    if summary.average_steps_per_run is not None:
        lines.append(f"- **Average steps per run (latest snapshot):** {summary.average_steps_per_run:.2f}")
    else:
        lines.append("- **Average steps per run:** n/a")
    if summary.notes:
        lines.extend(["", "## Notes", ""])
        for n in summary.notes:
            lines.append(f"- {n}")
    lines.append("")
    return "\n".join(lines)
