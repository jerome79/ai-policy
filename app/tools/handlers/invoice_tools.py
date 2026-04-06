from decimal import Decimal

from app.models.tool import ToolInvocation, ToolResult


def validate_invoice_data(invocation: ToolInvocation) -> ToolResult:
    payload = invocation.input_payload
    amount = Decimal(str(payload["amount"]))
    line_total = sum(Decimal(str(item["amount"])) for item in payload.get("line_items", []))

    if line_total and amount != line_total:
        return ToolResult(
            success=False,
            error="Invoice line total does not match invoice amount.",
            cost_actual=Decimal("0.05"),
        )

    return ToolResult(
        success=True,
        output_payload={"validated": True, "invoice_id": payload["invoice_id"]},
        cost_actual=Decimal("0.05"),
    )


def check_vendor_risk(invocation: ToolInvocation) -> ToolResult:
    payload = invocation.input_payload
    vendor_id = payload["vendor_id"]
    is_high_risk = vendor_id.lower().startswith("hr-")
    risk_level = "high" if is_high_risk else "low"
    return ToolResult(
        success=True,
        output_payload={"vendor_id": vendor_id, "vendor_risk": risk_level},
        cost_actual=Decimal("0.20"),
    )


def prepare_payment_instruction(invocation: ToolInvocation) -> ToolResult:
    payload = invocation.input_payload
    return ToolResult(
        success=True,
        output_payload={
            "instruction_id": f"pi-{payload['invoice_id']}",
            "amount": payload["amount"],
            "currency": payload["currency"],
            "vendor_id": payload["vendor_id"],
            "status": "prepared",
        },
        cost_actual=Decimal("1.50"),
    )
