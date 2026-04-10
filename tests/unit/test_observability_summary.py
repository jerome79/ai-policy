"""Smoke tests for JSONL aggregation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.observability.summary import build_runtime_summary


def test_build_runtime_summary_counts_distinct_runs(tmp_path: Path) -> None:
    runs = tmp_path / "runs.jsonl"
    audit = tmp_path / "audit.jsonl"
    runs.write_text(
        "\n".join(
            [
                json.dumps({"run_id": "a", "status": "running", "risk": {"level": "low"}, "steps": []}),
                json.dumps(
                    {
                        "run_id": "a",
                        "status": "completed",
                        "risk": {"level": "medium"},
                        "steps": [{"x": 1}, {"x": 2}],
                    }
                ),
                json.dumps({"run_id": "b", "status": "failed", "risk": {"level": "high"}, "steps": [{}]}),
            ]
        ),
        encoding="utf-8",
    )
    audit.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "run_id": "a",
                        "event_type": "policy_decision",
                        "payload": {"decision": {"decision": "require_approval"}},
                    }
                ),
                json.dumps(
                    {
                        "run_id": "a",
                        "event_type": "approval_event",
                        "payload": {"result": {"approved": True}},
                    }
                ),
                json.dumps(
                    {
                        "run_id": "a",
                        "event_type": "cost_update",
                        "payload": {"spent_total": "1.0"},
                    }
                ),
                json.dumps(
                    {
                        "run_id": "b",
                        "event_type": "policy_decision",
                        "payload": {"decision": {"decision": "deny"}},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    summary = build_runtime_summary(runs_path=runs, audit_path=audit)
    assert summary.total_workflows == 2
    assert summary.approval_required_runs == 1
    assert summary.policy_deny_events == 1
    assert summary.runs_with_policy_deny == 1
    assert summary.runs_ended_failed == 1
    assert summary.approval_outcomes["approved"] == 1
    assert summary.average_steps_per_run == pytest.approx(1.5)
    assert "failure_count" in summary.to_json_dict()


def test_missing_files_yield_empty_summary(tmp_path: Path) -> None:
    summary = build_runtime_summary(
        runs_path=tmp_path / "missing_runs.jsonl",
        audit_path=tmp_path / "missing_audit.jsonl",
    )
    assert summary.total_workflows == 0
    assert summary.approval_required_rate is None
