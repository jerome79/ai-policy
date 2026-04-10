"""Generate observability summary from local runs.jsonl and audit.jsonl."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.observability.summary import build_runtime_summary, render_summary_markdown


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate metrics from artifacts/runs.jsonl and artifacts/audit.jsonl.",
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root (defaults to repository root).",
    )
    parser.add_argument(
        "--runs",
        type=Path,
        default=None,
        help="Override path to runs.jsonl.",
    )
    parser.add_argument(
        "--audit",
        type=Path,
        default=None,
        help="Override path to audit.jsonl.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write JSON summary (default: <base>/artifacts/runtime_summary.json).",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=None,
        help="Write Markdown summary (default: <base>/artifacts/runtime_summary.md).",
    )
    args = parser.parse_args()
    base = args.base_path
    runs_path = args.runs or (base / "artifacts" / "runs.jsonl")
    audit_path = args.audit or (base / "artifacts" / "audit.jsonl")
    json_out = args.json_out or (base / "artifacts" / "runtime_summary.json")
    md_out = args.markdown_out or (base / "artifacts" / "runtime_summary.md")

    summary = build_runtime_summary(runs_path=runs_path, audit_path=audit_path)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(summary.to_json_dict(), indent=2),
        encoding="utf-8",
    )
    md_out.write_text(render_summary_markdown(summary), encoding="utf-8")
    print(json.dumps(summary.to_json_dict(), indent=2))
    print(f"Wrote: {json_out}")
    print(f"Wrote: {md_out}")


if __name__ == "__main__":
    main()
