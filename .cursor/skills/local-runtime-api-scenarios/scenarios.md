# Scenario Commands

Use `curl.exe` on Windows PowerShell to avoid alias issues.

## Base Payload Template

```json
{
  "request": {
    "workflow_type": "invoice_governance",
    "input_payload": {
      "invoice_id": "inv-1001",
      "vendor_id": "vn-200",
      "amount": "100.00",
      "currency": "USD",
      "requestor_id": "req-1",
      "line_items": [
        {"description": "Subscription", "amount": "60.00"},
        {"description": "Support", "amount": "40.00"}
      ]
    },
    "actor": {
      "actor_id": "actor-1",
      "role": "finance_manager",
      "permissions": ["*"]
    },
    "budget": {
      "max_total": "5.00",
      "soft_limit": "2.00",
      "currency": "USD"
    }
  }
}
```

## 1) Happy Path

```powershell
curl.exe -s -X POST "http://127.0.0.1:8000/workflows/execute" `
  -H "Content-Type: application/json" `
  -d "{\"request\":{\"workflow_type\":\"invoice_governance\",\"input_payload\":{\"invoice_id\":\"inv-1001\",\"vendor_id\":\"vn-200\",\"amount\":\"100.00\",\"currency\":\"USD\",\"requestor_id\":\"req-1\",\"line_items\":[{\"description\":\"Subscription\",\"amount\":\"60.00\"},{\"description\":\"Support\",\"amount\":\"40.00\"}]},\"actor\":{\"actor_id\":\"actor-1\",\"role\":\"finance_manager\",\"permissions\":[\"*\"]},\"budget\":{\"max_total\":\"5.00\",\"soft_limit\":\"2.00\",\"currency\":\"USD\"}}}"
```

Expected: `run.status=completed`.

## 2) Deny by Role

Use role `analyst` (denied by current policy for payment tool).

```powershell
curl.exe -s -X POST "http://127.0.0.1:8000/workflows/execute" `
  -H "Content-Type: application/json" `
  -d "{\"request\":{\"workflow_type\":\"invoice_governance\",\"input_payload\":{\"invoice_id\":\"inv-1002\",\"vendor_id\":\"vn-200\",\"amount\":\"100.00\",\"currency\":\"USD\",\"requestor_id\":\"req-1\",\"line_items\":[{\"description\":\"Subscription\",\"amount\":\"60.00\"},{\"description\":\"Support\",\"amount\":\"40.00\"}]},\"actor\":{\"actor_id\":\"actor-2\",\"role\":\"analyst\",\"permissions\":[\"*\"]},\"budget\":{\"max_total\":\"5.00\",\"soft_limit\":\"2.00\",\"currency\":\"USD\"}}}"
```

Expected: `run.status=blocked` and payment step denied.

## 3) Approval Branch

Use vendor `hr-777` to increase risk and trigger approval in current config.

```powershell
$resp = curl.exe -s -X POST "http://127.0.0.1:8000/workflows/execute" `
  -H "Content-Type: application/json" `
  -d "{\"request\":{\"workflow_type\":\"invoice_governance\",\"input_payload\":{\"invoice_id\":\"inv-1003\",\"vendor_id\":\"hr-777\",\"amount\":\"100.00\",\"currency\":\"USD\",\"requestor_id\":\"req-1\",\"line_items\":[{\"description\":\"Subscription\",\"amount\":\"60.00\"},{\"description\":\"Support\",\"amount\":\"40.00\"}]},\"actor\":{\"actor_id\":\"actor-1\",\"role\":\"finance_manager\",\"permissions\":[\"*\"]},\"budget\":{\"max_total\":\"5.00\",\"soft_limit\":\"2.00\",\"currency\":\"USD\"}}}" | ConvertFrom-Json
$runId = $resp.run.run_id
$runId
```

Expected initial state: `run.status=awaiting_approval`.

Approve then resume:

```powershell
curl.exe -s -X POST "http://127.0.0.1:8000/workflows/$runId/approval" `
  -H "Content-Type: application/json" `
  -d "{\"approved\":true,\"decided_by\":\"manager-1\",\"reason\":\"Approved for payment run.\",\"metadata\":{\"ticket_id\":\"appr-1\"}}"

curl.exe -s -X POST "http://127.0.0.1:8000/workflows/$runId/resume" `
  -H "Content-Type: application/json" `
  -d "{}"
```

Expected final state: `run.status=completed`.

## 4) Approval Rejected

Create a fresh awaiting-approval run, then reject and resume:

```powershell
$respReject = curl.exe -s -X POST "http://127.0.0.1:8000/workflows/execute" `
  -H "Content-Type: application/json" `
  -d "{\"request\":{\"workflow_type\":\"invoice_governance\",\"input_payload\":{\"invoice_id\":\"inv-1003b\",\"vendor_id\":\"hr-888\",\"amount\":\"100.00\",\"currency\":\"USD\",\"requestor_id\":\"req-1\",\"line_items\":[{\"description\":\"Subscription\",\"amount\":\"60.00\"},{\"description\":\"Support\",\"amount\":\"40.00\"}]},\"actor\":{\"actor_id\":\"actor-1\",\"role\":\"finance_manager\",\"permissions\":[\"*\"]},\"budget\":{\"max_total\":\"5.00\",\"soft_limit\":\"2.00\",\"currency\":\"USD\"}}}" | ConvertFrom-Json
$rejectRunId = $respReject.run.run_id

curl.exe -s -X POST "http://127.0.0.1:8000/workflows/$rejectRunId/approval" `
  -H "Content-Type: application/json" `
  -d "{\"approved\":false,\"decided_by\":\"manager-2\",\"reason\":\"Risk not acceptable.\",\"metadata\":{\"ticket_id\":\"appr-2\"}}"

curl.exe -s -X POST "http://127.0.0.1:8000/workflows/$rejectRunId/resume" `
  -H "Content-Type: application/json" `
  -d "{}"
```

Expected: final state `run.status=blocked`.

## 5) Hard Budget Block

```powershell
curl.exe -s -X POST "http://127.0.0.1:8000/workflows/execute" `
  -H "Content-Type: application/json" `
  -d "{\"request\":{\"workflow_type\":\"invoice_governance\",\"input_payload\":{\"invoice_id\":\"inv-1004\",\"vendor_id\":\"vn-200\",\"amount\":\"100.00\",\"currency\":\"USD\",\"requestor_id\":\"req-1\",\"line_items\":[{\"description\":\"Subscription\",\"amount\":\"60.00\"},{\"description\":\"Support\",\"amount\":\"40.00\"}]},\"actor\":{\"actor_id\":\"actor-1\",\"role\":\"finance_manager\",\"permissions\":[\"*\"]},\"budget\":{\"max_total\":\"0.10\",\"soft_limit\":\"0.08\",\"currency\":\"USD\"}}}"
```

Expected: `run.status=blocked` and budget-related error.

## 6) Malformed Input

Remove required `invoice_id`:

```powershell
curl.exe -s -X POST "http://127.0.0.1:8000/workflows/execute" `
  -H "Content-Type: application/json" `
  -d "{\"request\":{\"workflow_type\":\"invoice_governance\",\"input_payload\":{\"vendor_id\":\"vn-200\",\"amount\":\"100.00\",\"currency\":\"USD\",\"requestor_id\":\"req-1\",\"line_items\":[{\"description\":\"Subscription\",\"amount\":\"60.00\"},{\"description\":\"Support\",\"amount\":\"40.00\"}]},\"actor\":{\"actor_id\":\"actor-1\",\"role\":\"finance_manager\",\"permissions\":[\"*\"]},\"budget\":{\"max_total\":\"5.00\",\"soft_limit\":\"2.00\",\"currency\":\"USD\"}}}"
```

Expected: `run.status=failed`.

## 7) Fetch Run + Audit

```powershell
curl.exe -s "http://127.0.0.1:8000/workflows/$runId"
curl.exe -s "http://127.0.0.1:8000/workflows/$runId/audit"
```

Expected: run details plus audit events (`final_outcome`, and policy/budget events by scenario).
