from decimal import Decimal

from app.models.common import RiskLevel
from app.models.tool import ToolDefinition


def default_tool_definitions() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            tool_id="validate_invoice_data",
            version="1.0.0",
            description="Validate invoice schema and numeric consistency.",
            risk_level=RiskLevel.LOW,
            estimated_cost=Decimal("0.05"),
            required_permissions=["invoice:read"],
        ),
        ToolDefinition(
            tool_id="check_vendor_risk",
            version="1.0.0",
            description="Check vendor sanctions and risk posture.",
            risk_level=RiskLevel.MEDIUM,
            estimated_cost=Decimal("0.20"),
            required_permissions=["vendor:read"],
        ),
        ToolDefinition(
            tool_id="prepare_payment_instruction",
            version="1.0.0",
            description="Prepare a payment instruction object for approval.",
            risk_level=RiskLevel.HIGH,
            estimated_cost=Decimal("1.50"),
            required_permissions=["payment:write"],
        ),
    ]
