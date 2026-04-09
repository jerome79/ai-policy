from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT_DIR: Path = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR: Path = ROOT_DIR / "artifacts"
RUNS_PATH: Path = ARTIFACTS_DIR / "runs.jsonl"
AUDIT_PATH: Path = ARTIFACTS_DIR / "audit.jsonl"
REPORT_PATH: Path = ARTIFACTS_DIR / "week1_validation_report.md"


@dataclass(slots=True)
class CommandResult:
    command: list[str]
    return_code: int
    output: str


@dataclass(slots=True)
class Criterion:
    label: str
    passed: bool
    evidence: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


def run_command(command: list[str]) -> CommandResult:
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        command,
        cwd=ROOT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return CommandResult(command=command, return_code=completed.returncode, output=completed.stdout)


def tail_lines(text: str, max_lines: int = 12) -> str:
    lines: list[str] = [line for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return "<no output>"
    return "\n".join(lines[-max_lines:])


def parse_last_jsonl_record(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    lines: list[str] = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return None


def parse_jsonl_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    parsed: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line: str = raw_line.strip()
        if not line:
            continue
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return parsed


def contains_policy_decisions(records: list[dict[str, Any]]) -> set[str]:
    seen: set[str] = set()
    for event in records:
        if event.get("event_type") != "policy_decision":
            continue
        payload: dict[str, Any] = event.get("payload", {})
        decision_payload: dict[str, Any] = payload.get("decision", {})
        decision: str | None = decision_payload.get("decision")
        if decision in {"allow", "deny", "require_approval"}:
            seen.add(decision)
    return seen


def contains_budget_signals(records: list[dict[str, Any]]) -> tuple[bool, bool]:
    has_blocked_event: bool = False
    has_any_budget_event: bool = False
    budget_keywords: tuple[str, ...] = ("budget", "hard", "soft", "spend", "projected")
    for event in records:
        event_type: str = str(event.get("event_type", "")).lower()
        payload: dict[str, Any] = event.get("payload", {})
        payload_text: str = json.dumps(payload).lower()
        if event_type == "budget_blocked":
            has_blocked_event = True
            has_any_budget_event = True
            continue
        if any(token in event_type for token in budget_keywords) or any(token in payload_text for token in budget_keywords):
            has_any_budget_event = True
    return has_blocked_event, has_any_budget_event


def has_structured_run(record: dict[str, Any] | None) -> bool:
    if not record:
        return False
    required_fields: tuple[str, ...] = ("run_id", "status", "steps", "final_output")
    for field_name in required_fields:
        if field_name not in record:
            return False
    return isinstance(record.get("steps"), list)


def evaluate(args: argparse.Namespace) -> tuple[list[Criterion], list[str], list[str]]:
    criteria: list[Criterion] = []
    command_summaries: list[str] = []
    key_outputs: list[str] = []

    if not args.skip_install:
        install_result: CommandResult = run_command([sys.executable, "-m", "pip", "install", '-e', ".[dev]"])
        command_summaries.append(f"`{' '.join(install_result.command)}` -> exit {install_result.return_code}")
        if install_result.return_code != 0:
            key_outputs.append("Install failed:\n" + tail_lines(install_result.output))
            fail_all: list[Criterion] = [
                Criterion(label="Run one invoice workflow locally", passed=False, blockers=["Dependency install failed."]),
                Criterion(label="See policy allow/deny behavior", passed=False, blockers=["Dependency install failed."]),
                Criterion(label="See budget enforcement behavior", passed=False, blockers=["Dependency install failed."]),
                Criterion(label="Produce a structured workflow result", passed=False, blockers=["Dependency install failed."]),
                Criterion(label="Pass the basic tests", passed=False, blockers=["Dependency install failed."]),
            ]
            return fail_all, command_summaries, key_outputs

    run_result: CommandResult = run_command([sys.executable, "scripts/run_invoice_example.py"])
    command_summaries.append(f"`{' '.join(run_result.command)}` -> exit {run_result.return_code}")
    key_outputs.append("Invoice workflow output:\n" + tail_lines(run_result.output))
    criteria.append(
        Criterion(
            label="Run one invoice workflow locally",
            passed=run_result.return_code == 0,
            evidence=["`scripts/run_invoice_example.py` executed."],
            blockers=[] if run_result.return_code == 0 else ["Invoice workflow command failed."],
        )
    )

    policy_result: CommandResult = run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_policy_engine.py::test_policy_allows_low_risk_tool_when_not_denied",
            "tests/unit/test_policy_engine.py::test_denied_tool_call_by_policy",
            "tests/unit/test_policy_engine.py::test_require_approval_is_surfaced",
            "tests/unit/test_orchestrator_invoice_flow.py::test_happy_path_invoice_workflow",
            "tests/unit/test_orchestrator_invoice_flow.py::test_denied_tool_call_by_policy_in_orchestrator",
            "tests/unit/test_orchestrator_invoice_flow.py::test_require_approval_decision_is_surfaced",
        ]
    )
    command_summaries.append(f"`{' '.join(policy_result.command)}` -> exit {policy_result.return_code}")
    key_outputs.append("Policy test output:\n" + tail_lines(policy_result.output))
    audit_records: list[dict[str, Any]] = parse_jsonl_records(AUDIT_PATH)
    policy_seen_decisions: set[str] = contains_policy_decisions(audit_records)
    has_policy_signal: bool = bool(policy_seen_decisions)
    criteria.append(
        Criterion(
            label="See policy allow/deny/require_approval behavior",
            passed=policy_result.return_code == 0,
            evidence=[
                (
                    "Policy scenario tests passed (allow, deny, require_approval in engine and orchestrator)."
                    if policy_result.return_code == 0
                    else "Policy scenario tests failed."
                ),
                (
                    f"Policy decisions found in `artifacts/audit.jsonl`: {sorted(policy_seen_decisions)}."
                    if has_policy_signal
                    else "No policy decisions found in audit log."
                ),
            ],
            blockers=[] if policy_result.return_code == 0 else ["Policy behavior evidence is incomplete."],
        )
    )

    budget_result: CommandResult = run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_cost_tracker.py::test_budget_passes_under_soft_limit",
            "tests/unit/test_cost_tracker.py::test_budget_soft_limit_warns_but_allows",
            "tests/unit/test_cost_tracker.py::test_workflow_stopped_by_hard_budget",
            "tests/unit/test_orchestrator_invoice_flow.py::test_happy_path_invoice_workflow",
            "tests/unit/test_orchestrator_invoice_flow.py::test_workflow_stopped_by_hard_budget_in_orchestrator",
        ]
    )
    command_summaries.append(f"`{' '.join(budget_result.command)}` -> exit {budget_result.return_code}")
    key_outputs.append("Budget test output:\n" + tail_lines(budget_result.output))
    audit_records = parse_jsonl_records(AUDIT_PATH)
    has_budget_blocked_event, has_budget_signal = contains_budget_signals(audit_records)
    criteria.append(
        Criterion(
            label="See budget pass/soft-warning/hard-block behavior",
            passed=budget_result.return_code == 0,
            evidence=[
                (
                    "Budget scenario tests passed (pass, soft-warning, hard-block)."
                    if budget_result.return_code == 0
                    else "Budget scenario tests failed."
                ),
                (
                    "Budget block event found in `artifacts/audit.jsonl`."
                    if has_budget_blocked_event
                    else "No budget_blocked event found in audit log."
                ),
                (
                    "General budget signal found in `artifacts/audit.jsonl`."
                    if has_budget_signal
                    else "No general budget signal found in audit log."
                ),
            ],
            blockers=[] if budget_result.return_code == 0 else ["Budget behavior evidence is incomplete."],
        )
    )

    run_record: dict[str, Any] | None = parse_last_jsonl_record(RUNS_PATH)
    structured: bool = has_structured_run(run_record)
    criteria.append(
        Criterion(
            label="Produce a structured workflow result",
            passed=structured,
            evidence=[
                "Structured run fields present in `artifacts/runs.jsonl`."
                if structured
                else "Missing expected structured fields in latest run record."
            ],
            blockers=[] if structured else ["Workflow result is not structured or artifacts are missing."],
        )
    )

    basic_tests_result: CommandResult = run_command([sys.executable, "-m", "pytest"])
    command_summaries.append(f"`{' '.join(basic_tests_result.command)}` -> exit {basic_tests_result.return_code}")
    key_outputs.append("Full test output:\n" + tail_lines(basic_tests_result.output))
    criteria.append(
        Criterion(
            label="Pass the basic tests",
            passed=basic_tests_result.return_code == 0,
            evidence=["Full test suite completed."] if basic_tests_result.return_code == 0 else ["Full test suite failed."],
            blockers=[] if basic_tests_result.return_code == 0 else ["`pytest` returned non-zero exit code."],
        )
    )

    return criteria, command_summaries, key_outputs


def build_report(criteria: list[Criterion], commands: list[str], outputs: list[str]) -> str:
    score: int = sum(1 for item in criteria if item.passed)
    total: int = len(criteria)
    percent: int = int((score / total) * 100) if total else 0

    if score == total:
        status: str = "COMPLETE"
    elif score >= 4:
        status = "PARTIAL"
    else:
        status = "NOT READY"

    blocker_lines: list[str] = [blocker for criterion in criteria for blocker in criterion.blockers]
    if not blocker_lines:
        blocker_lines = ["None"]

    report_lines: list[str] = [
        "# Week 1 Validation Report",
        "",
        "## Result",
        f"- Status: {status}",
        f"- Score: {score}/{total} ({percent}%)",
        "",
        "## Criteria",
    ]
    for criterion in criteria:
        mark: str = "PASS" if criterion.passed else "FAIL"
        report_lines.append(f"- [{mark}] {criterion.label}")

    report_lines.extend(
        [
            "",
            "## Evidence",
            "- Commands run:",
        ]
    )
    report_lines.extend([f"  - {command}" for command in commands])
    report_lines.extend(["- Key outputs:"])
    report_lines.extend([f"  - {snippet.replace(chr(10), ' | ')}" for snippet in outputs])
    report_lines.extend(
        [
            "- Artifacts inspected:",
            "  - `artifacts/runs.jsonl`",
            "  - `artifacts/audit.jsonl`",
            "",
            "## Blockers",
        ]
    )
    report_lines.extend([f"- {line}" for line in blocker_lines])
    report_lines.extend(["", "## Next Actions"])

    next_actions: list[str] = []
    for criterion in criteria:
        if criterion.passed:
            continue
        next_actions.append(f"Fix: {criterion.label}. Re-run `python scripts/validate_week1.py`.")
    if not next_actions:
        next_actions.append("No action required. Week 1 gate is complete.")
    report_lines.extend([f"- {item}" for item in next_actions])

    return "\n".join(report_lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Validate Week 1 readiness checks.")
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip dependency installation step.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=REPORT_PATH,
        help="Path to write markdown report.",
    )
    return parser.parse_args()


def main() -> int:
    args: argparse.Namespace = parse_args()
    criteria, commands, outputs = evaluate(args)
    report: str = build_report(criteria, commands, outputs)

    output_path: Path = args.report_path if args.report_path.is_absolute() else ROOT_DIR / args.report_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    print(report)
    print(f"Saved report to: {output_path}")

    if all(item.passed for item in criteria):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
