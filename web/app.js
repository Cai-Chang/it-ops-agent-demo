const scenarios = {
  vpn: {
    query: "VPN 无法连接，客户端提示认证失败，应该怎么排查？",
    intent: "troubleshooting",
    risk: "none",
    tool: null,
    steps: [
      "Prompt Router 将请求识别为故障排查，不触发外部系统变更。",
      "Hybrid RAG 召回 VPN 登录故障 SOP，并结合工单自动化边界进行约束。",
      "Agent 建议先检查账号状态、MFA、客户端版本和 DNS/网关网络路径。",
      "连续三次 MFA 失败、疑似账号盗用或同部门大面积失败时升级到 L2 安全组。"
    ],
    citations: [
      ["VPN 登录故障排查 SOP", "账号状态、MFA、客户端版本、网络路径是 L1 首轮排查项。", "0.995"],
      ["工单查询与 L1 自动处置规范", "查询与排查建议可自动执行，高风险动作需要人工确认。", "0.236"],
      ["服务重启处置手册", "涉及服务动作时需要确认影响范围和健康检查。", "0.218"]
    ]
  },
  ticket: {
    query: "帮我查询工单 INC-1001 的状态",
    intent: "ticket_query",
    risk: "low",
    tool: {
      name: "ticket.query",
      args: "{ ticket_id: 'INC-1001' }",
      result: "INC-1001 当前状态：L1处理中，优先级：P2，摘要：VPN 登录失败，疑似 MFA 设备过期"
    },
    steps: [
      "Prompt Router 将请求识别为工单查询。",
      "RAG 引用 L1 自动处置规范，确认查询类动作属于低风险。",
      "MCP 工具层调用 ticket.query 获取工单状态。",
      "Agent 返回当前状态、优先级和摘要，并保留工具调用记录。"
    ],
    citations: [
      ["工单查询与 L1 自动处置规范", "低风险动作包括查询工单、查询知识库、生成排查步骤。", "0.991"],
      ["密码重置与账号解锁流程", "涉及账号动作时必须完成身份核验。", "0.342"],
      ["VPN 登录故障排查 SOP", "该工单摘要与 VPN/MFA 故障相关。", "0.180"]
    ]
  },
  password: {
    query: "重置用户 alice 的密码",
    intent: "password_reset",
    risk: "high",
    tool: {
      name: "iam.password.reset",
      args: "{ username: 'alice' }",
      result: "默认被 Human-in-the-loop 拦截；开启自动批准后生成临时密码并要求首次登录修改。"
    },
    steps: [
      "Prompt Router 将请求识别为密码重置。",
      "RAG 命中账号解锁流程，要求身份核验、审批和工单留痕。",
      "MCP 工具层生成 iam.password.reset 执行计划。",
      "高风险动作默认进入人工确认，不直接返回长期明文密码。"
    ],
    citations: [
      ["密码重置与账号解锁流程", "密码重置必须完成身份核验，并保留工单记录。", "1.016"],
      ["工单查询与 L1 自动处置规范", "密码重置属于高风险动作，必须 Human-in-the-loop。", "0.382"],
      ["VPN 登录故障排查 SOP", "认证失败可能与密码过期、账号锁定或 MFA 状态有关。", "0.279"]
    ]
  },
  service: {
    query: "web-01 的 nginx 异常，重启一下服务",
    intent: "service_control",
    risk: "high",
    tool: {
      name: "system.service.restart",
      args: "{ host: 'web-01', service: 'nginx' }",
      result: "默认被 Human-in-the-loop 拦截；开启自动批准后执行重启并返回健康检查结果。"
    },
    steps: [
      "Prompt Router 将请求识别为服务控制。",
      "RAG 召回服务重启手册，要求确认主机、服务名和影响范围。",
      "MCP 工具层生成 system.service.restart 调用计划。",
      "高风险动作需要人工确认，执行后必须检查端口、接口返回码、错误率和延迟。"
    ],
    citations: [
      ["服务重启处置手册", "重启前确认影响范围，重启后执行健康检查。", "1.011"],
      ["工单查询与 L1 自动处置规范", "服务重启属于高风险动作，必须 Human-in-the-loop。", "0.392"],
      ["VPN 登录故障排查 SOP", "认证类故障可先从低风险检查项开始。", "0.176"]
    ]
  }
};

const queryInput = document.querySelector("#queryInput");
const runBtn = document.querySelector("#runBtn");
const clearBtn = document.querySelector("#clearBtn");
const approvalToggle = document.querySelector("#approvalToggle");
const intentBadge = document.querySelector("#intentBadge");
const riskBadge = document.querySelector("#riskBadge");
const timeline = document.querySelector("#timeline");
const citationList = document.querySelector("#citationList");
const toolCard = document.querySelector("#toolCard");
const scenarioButtons = [...document.querySelectorAll("[data-scenario]")];
const stages = [...document.querySelectorAll("[data-stage]")];

let currentScenario = "ticket";

function detectScenario(query) {
  const text = query.toLowerCase();
  if (text.includes("重置") || text.includes("密码")) return "password";
  if (text.includes("工单") || text.includes("inc-")) return "ticket";
  if (text.includes("重启") || text.includes("nginx") || text.includes("服务")) return "service";
  return "vpn";
}

function renderScenario(key) {
  currentScenario = key;
  const scenario = scenarios[key];
  intentBadge.textContent = scenario.intent;
  riskBadge.textContent = scenario.risk;
  riskBadge.className = scenario.risk === "high" ? "badge danger" : "badge safe";

  timeline.innerHTML = scenario.steps.map((step) => `<li>${step}</li>`).join("");
  citationList.innerHTML = scenario.citations
    .map(
      ([title, body, score]) => `
        <div class="citation">
          <strong>${title}</strong>
          <p>${body}</p>
          <span class="score">score ${score}</span>
        </div>
      `
    )
    .join("");

  renderTool(scenario);
  scenarioButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.scenario === key);
  });
  animateStages(scenario);
}

function renderTool(scenario) {
  if (!scenario.tool) {
    toolCard.innerHTML = `
      <div class="tool-row"><span>mode</span><span>knowledge_qa</span></div>
      <div class="tool-row"><span>action</span><span>仅生成排查建议，不调用外部工具。</span></div>
      <div class="tool-row"><span>result</span><span>无系统状态变更。</span></div>
    `;
    return;
  }

  const approved = approvalToggle.checked || scenario.risk !== "high";
  const result = approved
    ? scenario.tool.result.replace("默认被 Human-in-the-loop 拦截；开启自动批准后", "")
    : scenario.tool.result;

  toolCard.innerHTML = `
    <div class="tool-row"><span>name</span><span>${scenario.tool.name}</span></div>
    <div class="tool-row"><span>args</span><span>${scenario.tool.args}</span></div>
    <div class="tool-row"><span>risk</span><span>${scenario.risk}</span></div>
    <div class="tool-row"><span>result</span><span>${result}</span></div>
  `;
}

function animateStages(scenario) {
  stages.forEach((stage) => stage.classList.remove("active"));
  const active = ["router", "rag", "rerank"];
  if (scenario.tool) active.push("mcp");
  if (scenario.risk === "high") active.push("hitl");
  active.forEach((name, index) => {
    window.setTimeout(() => {
      document.querySelector(`[data-stage="${name}"]`)?.classList.add("active");
    }, index * 130);
  });
}

scenarioButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const key = button.dataset.scenario;
    queryInput.value = scenarios[key].query;
    renderScenario(key);
  });
});

runBtn.addEventListener("click", () => {
  renderScenario(detectScenario(queryInput.value));
});

approvalToggle.addEventListener("change", () => renderScenario(currentScenario));

clearBtn.addEventListener("click", () => {
  queryInput.value = "";
  queryInput.focus();
});

renderScenario(currentScenario);
