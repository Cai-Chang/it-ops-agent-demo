from __future__ import annotations

import os

from it_ops_agent.schema import ToolCall


class HumanApprovalPolicy:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def approve(self, tool_call: ToolCall) -> bool:
        if not self.enabled or not tool_call.requires_approval:
            return True
        if os.getenv("IT_OPS_AGENT_AUTO_APPROVE", "").lower() in {"1", "true", "yes"}:
            return True
        return False
