from app.models.tool import ToolDefinition, ToolInvocation, ToolResult
from app.tools.base import ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        if definition.tool_id in self._definitions:
            raise ValueError(f"Tool already registered: {definition.tool_id}")
        self._definitions[definition.tool_id] = definition
        self._handlers[definition.tool_id] = handler

    def get_definition(self, tool_id: str) -> ToolDefinition:
        try:
            return self._definitions[tool_id]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {tool_id}") from exc

    def execute(self, invocation: ToolInvocation) -> ToolResult:
        handler = self._handlers.get(invocation.tool_id)
        if handler is None:
            raise KeyError(f"No handler for tool: {invocation.tool_id}")
        return handler(invocation)
