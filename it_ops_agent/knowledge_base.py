from __future__ import annotations

import json
import re
from pathlib import Path

from it_ops_agent.schema import Chunk, Document


def load_markdown_documents(knowledge_dir: Path) -> list[Document]:
    documents: list[Document] = []
    for path in sorted(knowledge_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = extract_title(text) or path.stem
        documents.append(
            Document(
                doc_id=path.stem,
                title=title,
                source=str(path.relative_to(Path.cwd())) if path.is_relative_to(Path.cwd()) else str(path),
                content=text,
            )
        )
    return documents


def extract_title(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def chunk_document(document: Document, max_chars: int = 720, overlap: int = 120) -> list[Chunk]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", document.content) if p.strip()]
    chunks: list[Chunk] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if not current:
            return
        content = "\n\n".join(current)
        chunks.append(
            Chunk(
                chunk_id=f"{document.doc_id}-{len(chunks)}",
                doc_id=document.doc_id,
                title=document.title,
                source=document.source,
                content=content,
            )
        )
        if overlap > 0 and len(content) > overlap:
            current = [content[-overlap:]]
            current_len = len(current[0])
        else:
            current = []
            current_len = 0

    for paragraph in paragraphs:
        if current_len + len(paragraph) > max_chars:
            flush()
        current.append(paragraph)
        current_len += len(paragraph)
    flush()
    return chunks


def build_chunks(knowledge_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for document in load_markdown_documents(knowledge_dir):
        chunks.extend(chunk_document(document))
    return chunks


def save_index(chunks: list[Chunk], index_file: Path) -> None:
    index_file.parent.mkdir(parents=True, exist_ok=True)
    payload = [chunk.__dict__ for chunk in chunks]
    index_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_index(index_file: Path) -> list[Chunk]:
    payload = json.loads(index_file.read_text(encoding="utf-8"))
    return [Chunk(**item) for item in payload]
