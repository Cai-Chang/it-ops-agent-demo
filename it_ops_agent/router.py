from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    intent: str
    confidence: float


class PromptRouter:
    def route(self, user_input: str) -> Route:
        text = user_input.lower()
        if any(keyword in text for keyword in ["重置", "reset", "改密码", "密码"]):
            return Route("password_reset", 0.92)
        if any(keyword in text for keyword in ["工单", "ticket", "inc-", "查询状态"]):
            return Route("ticket_query", 0.90)
        if any(keyword in text for keyword in ["重启", "restart", "启动", "停止", "服务"]):
            return Route("service_control", 0.88)
        if re.search(r"\b(cpu|memory|disk|nginx|vpn|ssh|dns)\b", text):
            return Route("troubleshooting", 0.76)
        return Route("knowledge_qa", 0.66)
