from __future__ import annotations

import random
import re
import secrets
import string
from dataclasses import dataclass
from typing import Callable

from it_ops_agent.schema import ToolCall, ToolResult


@dataclass(frozen=True)
class MCPTool:
    name: str
    description: str
    requires_approval: bool
    risk: str
    handler: Callable[[dict], ToolResult]


class InMemoryWorkOrderSystem:
    def __init__(self) -> None:
        self.tickets = {
            "INC-1001": {
                "status": "L1处理中",
                "priority": "P2",
                "summary": "VPN 登录失败，疑似 MFA 设备过期",
            },
            "INC-1002": {
                "status": "已关闭",
                "priority": "P3",
                "summary": "打印机队列堵塞，已清理缓存",
            },
        }

    def query_ticket(self, ticket_id: str) -> ToolResult:
        item = self.tickets.get(ticket_id.upper())
        if not item:
            return ToolResult("ticket.query", False, f"未找到工单 {ticket_id}")
        return ToolResult(
            "ticket.query",
            True,
            f"{ticket_id.upper()} 当前状态：{item['status']}，优先级：{item['priority']}，摘要：{item['summary']}",
            item,
        )

    def create_ticket_note(self, ticket_id: str, note: str) -> ToolResult:
        if ticket_id.upper() not in self.tickets:
            return ToolResult("ticket.note", False, f"未找到工单 {ticket_id}")
        return ToolResult("ticket.note", True, f"已为 {ticket_id.upper()} 追加备注：{note}")


class MockSystemController:
    def reset_password(self, username: str) -> ToolResult:
        alphabet = string.ascii_letters + string.digits
        temp_password = "".join(secrets.choice(alphabet) for _ in range(12))
        return ToolResult(
            "iam.password.reset",
            True,
            f"已为用户 {username} 生成临时密码，需通过安全渠道发送并要求首次登录修改。",
            {"username": username, "temporary_password": temp_password},
        )

    def restart_service(self, host: str, service: str) -> ToolResult:
        if random.random() < 0.05:
            return ToolResult("system.service.restart", False, f"{host} 上的 {service} 重启失败，请升级到 L2。")
        return ToolResult("system.service.restart", True, f"{host} 上的 {service} 已重启，健康检查通过。")


class MCPToolRegistry:
    def __init__(self) -> None:
        self.work_orders = InMemoryWorkOrderSystem()
        self.system = MockSystemController()
        self.tools = {
            "ticket.query": MCPTool(
                name="ticket.query",
                description="查询企业内部工单状态",
                requires_approval=False,
                risk="low",
                handler=lambda args: self.work_orders.query_ticket(args["ticket_id"]),
            ),
            "ticket.note": MCPTool(
                name="ticket.note",
                description="给工单追加处置备注",
                requires_approval=True,
                risk="medium",
                handler=lambda args: self.work_orders.create_ticket_note(args["ticket_id"], args["note"]),
            ),
            "iam.password.reset": MCPTool(
                name="iam.password.reset",
                description="重置用户密码",
                requires_approval=True,
                risk="high",
                handler=lambda args: self.system.reset_password(args["username"]),
            ),
            "system.service.restart": MCPTool(
                name="system.service.restart",
                description="重启主机上的服务",
                requires_approval=True,
                risk="high",
                handler=lambda args: self.system.restart_service(args["host"], args["service"]),
            ),
        }

    def plan_tool_call(self, intent: str, user_input: str) -> ToolCall | None:
        if intent == "ticket_query":
            ticket_id = extract_ticket_id(user_input)
            return ToolCall("ticket.query", {"ticket_id": ticket_id or "INC-1001"}, False, "low")
        if intent == "password_reset":
            username = extract_username(user_input)
            return ToolCall("iam.password.reset", {"username": username or "unknown-user"}, True, "high")
        if intent == "service_control":
            host = extract_host(user_input)
            service = extract_service(user_input)
            return ToolCall("system.service.restart", {"host": host, "service": service}, True, "high")
        return None

    def execute(self, tool_call: ToolCall) -> ToolResult:
        tool = self.tools[tool_call.name]
        return tool.handler(tool_call.arguments)


def extract_ticket_id(text: str) -> str | None:
    match = re.search(r"\b(?:inc|req|chg)-?\d+\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    value = match.group(0).upper()
    return value if "-" in value else value[:3] + "-" + value[3:]


def extract_username(text: str) -> str | None:
    match = re.search(r"(?:用户|账号|user)\s*([a-zA-Z][a-zA-Z0-9_.-]{1,31})", text)
    return match.group(1) if match else None


def extract_host(text: str) -> str:
    match = re.search(r"\b[a-zA-Z]+-\d+\b", text)
    return match.group(0) if match else "web-01"


def extract_service(text: str) -> str:
    for service in ["nginx", "mysql", "redis", "ssh", "vpn"]:
        if service in text.lower():
            return service
    return "nginx"
