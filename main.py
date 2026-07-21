from __future__ import annotations

import argparse
from pathlib import Path

from it_ops_agent.agent import ITOpsAgent
from it_ops_agent.config import AppConfig


def build_agent() -> ITOpsAgent:
    config = AppConfig.from_env()
    return ITOpsAgent.from_config(config)


def run_demo() -> None:
    agent = build_agent()
    questions = [
        "VPN 无法连接，客户端提示认证失败，应该怎么排查？",
        "帮我查询工单 INC-1001 的状态",
        "重置用户 alice 的密码",
        "web-01 的 nginx 异常，重启一下服务",
    ]
    for question in questions:
        print("=" * 80)
        print(f"User: {question}")
        response = agent.run(question)
        print(response.to_markdown())


def ask_once(question: str) -> None:
    agent = build_agent()
    response = agent.run(question)
    print(response.to_markdown())


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG + MCP intelligent IT operations Agent")
    parser.add_argument("--demo", action="store_true", help="Run built-in demo questions")
    parser.add_argument("--ask", type=str, help="Ask one IT operations question")
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Rebuild local knowledge index from data/knowledge",
    )
    args = parser.parse_args()

    if args.rebuild_index:
        agent = build_agent()
        index_file = agent.rebuild_index()
        print(f"Index rebuilt: {Path(index_file).resolve()}")
        return

    if args.demo:
        run_demo()
        return

    if args.ask:
        ask_once(args.ask)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
