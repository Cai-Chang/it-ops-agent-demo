from it_ops_agent.agent import ITOpsAgent
from it_ops_agent.config import AppConfig


def make_agent(tmp_path):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "sop.md").write_text("# VPN SOP\n\nVPN 认证失败先检查账号和 MFA。", encoding="utf-8")
    config = AppConfig(
        root_dir=tmp_path,
        knowledge_dir=knowledge_dir,
        index_file=tmp_path / "storage" / "index.json",
        require_human_approval=True,
    )
    return ITOpsAgent.from_config(config)


def test_knowledge_qa(tmp_path):
    agent = make_agent(tmp_path)
    response = agent.run("VPN 认证失败怎么办")
    assert response.citations
    assert "MFA" in response.answer


def test_password_reset_requires_approval(tmp_path):
    agent = make_agent(tmp_path)
    response = agent.run("重置用户 alice 的密码")
    assert response.approval_required
    assert response.tool_call.name == "iam.password.reset"
