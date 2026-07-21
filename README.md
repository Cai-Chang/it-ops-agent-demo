# 基于 RAG 与 MCP 协议的智能 IT 运维 Agent

[在线演示页面](https://Cai-Chang.github.io/it-ops-agent-demo/) · [前端源码](web/index.html)

这是一个可运行的本地原型，用来演示“专业技术手册可检索问答 + MCP 工具执行 + Human-in-the-loop 审批”的智能运维助手。

## 已实现能力

- RAG 知识检索：读取 `data/knowledge/*.md` 运维手册，自动切分并建立本地索引。
- 混合检索：内置 BM25 + 哈希向量检索，按加权分数召回候选知识片段。
- Rerank 重排：根据查询词覆盖率与标题命中，对召回结果二次排序。
- Prompt 意图路由：识别知识问答、工单查询、密码重置、服务重启等意图。
- MCP 工具层模拟：通过统一 ToolCall/ToolResult 接口接入工单系统与系统控制器。
- Human-in-the-loop：高风险操作默认只生成执行计划，不直接执行。

## 技术路线

1. 数据层：将 VPN、密码重置、服务重启、工单规范等专业手册放入 `data/knowledge/`。
2. 索引层：`knowledge_base.py` 负责 Markdown 加载、切分和索引落盘。
3. 检索层：`retrievers.py` 实现 BM25 关键词召回与向量相似度召回，并进行混合排序。
4. 重排层：`LightweightReranker` 对候选片段做查询覆盖率重排，生产环境可替换为 BGE Reranker 或 Cohere Rerank。
5. Agent 层：`router.py` 做意图识别，`agent.py` 组合 RAG 上下文、工具计划与最终响应。
6. MCP 层：`mcp_tools.py` 用 MCP 风格的工具注册表封装工单查询、密码重置、服务重启等动作。
7. 安全层：`hitl.py` 对高风险动作启用人工确认，避免越权执行。

## 生产化替换方案

- LangChain：将当前 `ITOpsAgent` 的编排迁移为 LangChain Runnable/Graph，便于增加多轮记忆和观测。
- Qdrant：将 `storage/knowledge_index.json` 替换为 Qdrant Collection，向量模型使用 bge-m3、text-embedding-3-large 或企业内置 embedding。
- BM25：可使用 Elasticsearch/OpenSearch 或 `rank-bm25` 存储倒排索引。
- Rerank：接入 BGE Reranker、Cohere Rerank 或企业私有 CrossEncoder。
- MCP：将 `MCPToolRegistry` 替换为真实 MCP Server/Client，连接 ServiceNow/Jira、LDAP/IAM、Kubernetes、Ansible 或堡垒机。
- 审批：把 `HumanApprovalPolicy` 对接企业 IM、审批流或工单审批状态。

## 运行方法

要求 Python 3.10+。本原型默认不需要安装第三方依赖。

### 方式一：直接运行

```powershell
python main.py --rebuild-index
python main.py --demo
```

单次提问：

```powershell
python main.py --ask "VPN 无法连接，客户端提示认证失败，应该怎么排查？"
python main.py --ask "帮我查询工单 INC-1001 的状态"
python main.py --ask "重置用户 alice 的密码"
```

默认高风险动作需要人工确认。如果只是本地演示自动执行，可以设置：

```powershell
$env:IT_OPS_AGENT_AUTO_APPROVE="true"
python main.py --ask "web-01 的 nginx 异常，重启一下服务"
```

### 方式二：使用 conda 环境运行

项目已提供 `environment.yml`，可以创建独立 conda 环境：

```powershell
conda env create -f environment.yml
conda activate it-ops-agent
python main.py --rebuild-index
python main.py --demo
pytest -q
```

如果不想创建命名环境，也可以在项目目录下创建本地环境：

```powershell
conda create -p .conda_env python=3.11 pytest -y
conda activate .\.conda_env
python main.py --demo
```

## 目录结构

```text
.
├── main.py
├── it_ops_agent/
│   ├── agent.py
│   ├── config.py
│   ├── hitl.py
│   ├── knowledge_base.py
│   ├── mcp_tools.py
│   ├── retrievers.py
│   ├── router.py
│   └── schema.py
├── data/knowledge/
├── docs/
├── web/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── tests/
├── environment.yml
├── pytest.ini
└── requirements.txt
```

## 验收目标

- 能回答专业 IT 运维知识问题，并给出引用来源。
- 能识别并规划工单查询、密码重置、服务重启等操作。
- 高风险操作默认进入人工确认，不直接执行。
- 自动处理范围聚焦 L1 高频基础工单，目标覆盖约 40% 的常见场景。

## 前端 Demo 展示页

项目提供了一个无需打包的静态前端页面，用于展示 RAG 检索、Prompt 意图路由、MCP 工具调用与 Human-in-the-loop 审批流程。

直接打开：

```text
web/index.html
```

或启动本地静态服务：

```powershell
python -m http.server 8000 --directory web
```

然后访问：

```text
http://localhost:8000
```
