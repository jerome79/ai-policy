---
name: local-runtime-api-scenarios
description: Starts the policy runtime locally and exercises API scenarios with reproducible sample requests, including allow, deny, approval, budget, malformed input, and audit checks. Use when the user asks to deploy/run locally, smoke test endpoints, or validate runtime behavior through API calls.
---

# Local Runtime API Scenarios

## Purpose

Run the app locally and validate runtime branches via API calls.

## When to Use

Apply this skill when the user asks to:
- deploy or run the app locally
- test API endpoints with sample requests
- validate runtime behavior across multiple governance scenarios

## Local Run Workflow

Run from repository root.

Task Progress:
- [ ] Step 1: Install dependencies
- [ ] Step 2: Start API server
- [ ] Step 3: Run scenario requests
- [ ] Step 4: Validate outputs and artifacts

### Step 1: Install dependencies

- `python -m pip install -e ".[dev]"`

### Step 2: Start API server

Use either:
- `python scripts/run_api.py`
- `uvicorn app.api.main:app --host 127.0.0.1 --port 8000`

Health check:
- `curl.exe http://127.0.0.1:8000/docs`

### Step 3: Run scenario requests

Use the payloads and commands in [scenarios.md](scenarios.md).

Always include:
- `workflow_type: "invoice_governance"`
- `request.input_payload`
- `request.actor`
- `request.budget`

### Step 4: Validate outputs and artifacts

For each scenario:
- capture `run.run_id`
- check `run.status`, `run.current_state`, `run.pending_tool_id`, `run.steps`
- call `GET /workflows/{run_id}/audit`

Also inspect:
- `artifacts/audit.jsonl`
- `artifacts/runs.jsonl`

## Endpoint Map

- `POST /workflows/execute`
- `GET /workflows/{run_id}`
- `POST /workflows/{run_id}/approval`
- `POST /workflows/{run_id}/resume`
- `GET /workflows/{run_id}/audit`

## Result Expectations by Scenario

- happy path -> `COMPLETED`
- deny tool by role -> `BLOCKED`
- require approval -> `AWAITING_APPROVAL` then `COMPLETED` after approval + resume
- approval rejected -> `BLOCKED`
- hard budget exceeded -> `BLOCKED`
- malformed input -> `FAILED`

## Failure Handling

- Never silently ignore failed requests.
- If an API call returns non-2xx, report request body and response body.
- If observed status differs from expected, mark scenario failed and include `run.steps[-1].error` when present.
