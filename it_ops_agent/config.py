from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    root_dir: Path
    knowledge_dir: Path
    index_file: Path
    require_human_approval: bool = True
    top_k: int = 4

    @classmethod
    def from_env(cls) -> "AppConfig":
        root_dir = Path(os.getenv("IT_OPS_AGENT_ROOT", Path.cwd())).resolve()
        return cls(
            root_dir=root_dir,
            knowledge_dir=root_dir / "data" / "knowledge",
            index_file=root_dir / "storage" / "knowledge_index.json",
            require_human_approval=os.getenv("IT_OPS_AGENT_HITL", "true").lower()
            not in {"0", "false", "no"},
            top_k=int(os.getenv("IT_OPS_AGENT_TOP_K", "4")),
        )
