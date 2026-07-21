from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    source: str
    content: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    source: str
    content: str


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    bm25_score: float
    vector_score: float
    hybrid_score: float
    rerank_score: float = 0.0


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    requires_approval: bool
    risk: str


@dataclass(frozen=True)
class ToolResult:
    name: str
    ok: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentResponse:
    intent: str
    answer: str
    citations: list[RetrievedChunk] = field(default_factory=list)
    tool_call: ToolCall | None = None
    tool_result: ToolResult | None = None
    approval_required: bool = False

    def to_markdown(self) -> str:
        lines = [f"Intent: {self.intent}", "", self.answer]
        if self.citations:
            lines.extend(["", "References:"])
            for item in self.citations:
                lines.append(
                    f"- {item.chunk.title} ({item.chunk.source}) "
                    f"score={item.rerank_score:.3f}"
                )
        if self.tool_call:
            lines.extend(
                [
                    "",
                    "Tool Call:",
                    f"- name: {self.tool_call.name}",
                    f"- arguments: {self.tool_call.arguments}",
                    f"- risk: {self.tool_call.risk}",
                ]
            )
        if self.tool_result:
            lines.extend(
                [
                    "",
                    "Tool Result:",
                    f"- ok: {self.tool_result.ok}",
                    f"- message: {self.tool_result.message}",
                ]
            )
        if self.approval_required:
            lines.extend(["", "Human-in-the-loop: approval required before execution."])
        return "\n".join(lines)
