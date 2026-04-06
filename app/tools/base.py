from typing import Protocol

from app.models.tool import ToolInvocation, ToolResult


class ToolHandler(Protocol):
    def __call__(self, invocation: ToolInvocation) -> ToolResult:
        ...
