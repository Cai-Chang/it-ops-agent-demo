from __future__ import annotations

import re
from pathlib import Path

from it_ops_agent.config import AppConfig
from it_ops_agent.hitl import HumanApprovalPolicy
from it_ops_agent.knowledge_base import build_chunks, load_index, save_index
from it_ops_agent.mcp_tools import MCPToolRegistry
from it_ops_agent.retrievers import HybridRetriever, LightweightReranker
from it_ops_agent.router import PromptRouter
from it_ops_agent.schema import AgentResponse


class ITOpsAgent:
    def __init__(
        self,
        config: AppConfig,
        retriever: HybridRetriever,
        reranker: LightweightReranker,
        router: PromptRouter,
        tools: MCPToolRegistry,
        approval: HumanApprovalPolicy,
    ) -> None:
        self.config = config
        self.retriever = retriever
        self.reranker = reranker
        self.router = router
        self.tools = tools
        self.approval = approval

    @classmethod
    def from_config(cls, config: AppConfig) -> "ITOpsAgent":
        if not config.index_file.exists():
            chunks = build_chunks(config.knowledge_dir)
            save_index(chunks, config.index_file)
        chunks = load_index(config.index_file)
        return cls(
            config=config,
            retriever=HybridRetriever(chunks),
            reranker=LightweightReranker(),
            router=PromptRouter(),
            tools=MCPToolRegistry(),
            approval=HumanApprovalPolicy(config.require_human_approval),
        )

    def rebuild_index(self) -> Path:
        chunks = build_chunks(self.config.knowledge_dir)
        save_index(chunks, self.config.index_file)
        return self.config.index_file

    def run(self, user_input: str) -> AgentResponse:
        route = self.router.route(user_input)
        search_query = self.expand_query(route.intent, user_input)
        retrieved = self.reranker.rerank(
            search_query,
            self.retriever.search(search_query, top_k=self.config.top_k),
        )
        tool_call = self.tools.plan_tool_call(route.intent, user_input)
        answer = self.compose_answer(route.intent, user_input, retrieved)

        if not tool_call:
            return AgentResponse(intent=route.intent, answer=answer, citations=retrieved)

        if not self.approval.approve(tool_call):
            approval_text = (
                f"{answer}\n\n已识别到可执行操作 `{tool_call.name}`，风险等级 {tool_call.risk}。"
                "当前 Human-in-the-loop 策略要求人工确认，因此本次只生成执行计划，不直接落地。"
                "设置环境变量 IT_OPS_AGENT_AUTO_APPROVE=true 后可在演示环境自动批准。"
            )
            return AgentResponse(
                intent=route.intent,
                answer=approval_text,
                citations=retrieved,
                tool_call=tool_call,
                approval_required=True,
            )

        result = self.tools.execute(tool_call)
        execution_answer = f"{answer}\n\n执行结果：{result.message}"
        return AgentResponse(
            intent=route.intent,
            answer=execution_answer,
            citations=retrieved,
            tool_call=tool_call,
            tool_result=result,
        )

    def expand_query(self, intent: str, user_input: str) -> str:
        expansions = {
            "password_reset": "密码重置 账号解锁 身份核验 临时密码 MFA 审批",
            "service_control": "服务重启 健康检查 主机 服务名 影响范围 回滚",
            "ticket_query": "工单查询 工单状态 优先级 摘要 L1 自动处置",
            "troubleshooting": "故障排查 SOP 认证失败 网络路径 升级条件",
        }
        return f"{user_input} {expansions.get(intent, '')}".strip()

    def compose_answer(self, intent: str, user_input: str, retrieved) -> str:
        context = "\n".join(f"- {self.excerpt(item.chunk.content)}" for item in retrieved[:3])
        if intent in {"password_reset", "service_control", "ticket_query"}:
            return (
                "我先根据知识库和意图路由生成运维处置计划：\n"
                f"1. 用户请求：{user_input}\n"
                "2. 匹配到的专业知识片段如下，用于约束操作步骤和权限边界：\n"
                f"{context}\n"
                "3. 若需要变更系统状态，将通过 MCP 工具层执行，并受人工确认策略保护。"
            )
        return (
            "根据知识库检索和重排结果，建议按以下方式处理：\n"
            f"{context}\n\n"
            "执行时请先确认影响范围，再按照 SOP 从低风险检查项开始；若涉及账号、服务重启或配置变更，"
            "应升级为 MCP 工具调用并进入人工确认流程。"
        )

    def excerpt(self, text: str, max_chars: int = 360) -> str:
        compact = re.sub(r"\s+", " ", text).strip()
        if len(compact) <= max_chars:
            return compact
        boundary = max(
            compact.rfind("。", 0, max_chars),
            compact.rfind("；", 0, max_chars),
            compact.rfind(".", 0, max_chars),
        )
        if boundary < max_chars * 0.6:
            boundary = max_chars
        return compact[: boundary + 1].rstrip() + "..."
