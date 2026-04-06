from decimal import Decimal
from uuid import uuid4

from app.models.common import RiskLevel
from app.models.tool import ToolDefinition, ToolInvocation, ToolResult
from app.tools.registry import ToolRegistry


def test_allowed_tool_call() -> None:
    registry = ToolRegistry()
    definition = ToolDefinition(
        tool_id="sample_tool",
        version="1.0.0",
        description="test",
        risk_level=RiskLevel.LOW,
        estimated_cost=Decimal("0.1"),
    )

    def handler(invocation: ToolInvocation) -> ToolResult:
        return ToolResult(success=True, output_payload={"ok": invocation.tool_id})

    registry.register(definition, handler)
    result = registry.execute(
        ToolInvocation(run_id=uuid4(), step_id="s1", tool_id="sample_tool", input_payload={})
    )
    assert result.success is True
    assert result.output_payload["ok"] == "sample_tool"
