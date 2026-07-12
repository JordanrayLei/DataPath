const form = document.querySelector("#ask-form");
const queryInput = document.querySelector("#query");
const domainInput = document.querySelector("#domain");
const submitBtn = document.querySelector("#submit-btn");
const pipeline = document.querySelector("#pipeline");
const overallStatus = document.querySelector("#overall-status");
const emptyState = document.querySelector("#empty-state");
const result = document.querySelector("#result");
const message = document.querySelector("#message");
const answerTitle = document.querySelector("#answer-title");
const traceBadge = document.querySelector("#trace-badge");
const findings = document.querySelector("#findings");
const caveats = document.querySelector("#caveats");
const nextActions = document.querySelector("#next-actions");
const chart = document.querySelector("#chart");
const chartTitle = document.querySelector("#chart-title");
const chartType = document.querySelector("#chart-type");
const evidence = document.querySelector("#evidence");
const table = document.querySelector("#table");
const debugJson = document.querySelector("#debug-json");
const feedbackForm = document.querySelector("#feedback-form");
const feedbackType = document.querySelector("#feedback-type");
const feedbackSeverity = document.querySelector("#feedback-severity");
const feedbackMessage = document.querySelector("#feedback-message");
const feedbackExpected = document.querySelector("#feedback-expected");
const feedbackSubmit = document.querySelector("#feedback-submit");
const feedbackStatus = document.querySelector("#feedback-status");
const badcaseFilter = document.querySelector("#badcase-filter");
const badcaseRefresh = document.querySelector("#badcase-refresh");
const badcaseCounts = document.querySelector("#badcase-counts");
const badcaseList = document.querySelector("#badcase-list");
const metricDomainFilter = document.querySelector("#metric-domain-filter");
const metricRefresh = document.querySelector("#metric-refresh");
const metricCounts = document.querySelector("#metric-counts");
const metricList = document.querySelector("#metric-list");
const metricDetail = document.querySelector("#metric-detail");
const evaluationRefresh = document.querySelector("#evaluation-refresh");
const evaluationSummary = document.querySelector("#evaluation-summary");
const evaluationTrend = document.querySelector("#evaluation-trend");
const evaluationCases = document.querySelector("#evaluation-cases");
const evaluationGates = document.querySelector("#evaluation-gates");
const goldenRefresh = document.querySelector("#golden-refresh");
const goldenEvaluate = document.querySelector("#golden-evaluate");
const goldenCounts = document.querySelector("#golden-counts");
const goldenEvalSummary = document.querySelector("#golden-eval-summary");
const goldenList = document.querySelector("#golden-list");
const viewButtons = document.querySelectorAll("[data-view]");
const viewPanels = document.querySelectorAll("[data-view-panel]");
const chatThread = document.querySelector("#chat-thread");
const conversationList = document.querySelector("#conversation-list");
const newConversationButton = document.querySelector("#new-conversation");
const conversationTitle = document.querySelector("#conversation-title");
const conversationTurnCount = document.querySelector("#conversation-turn-count");
const contextChips = document.querySelector("#context-chips");
const contextMemory = document.querySelector("#context-memory");
const evidenceInspector = document.querySelector("#evidence-inspector");
const evidenceCount = document.querySelector("#evidence-count");
const metricAdminNew = document.querySelector("#metric-admin-new");
const metricAdminRefresh = document.querySelector("#metric-admin-refresh");
const metricDraftCount = document.querySelector("#metric-draft-count");
const metricDraftList = document.querySelector("#metric-draft-list");
const metricAdminForm = document.querySelector("#metric-admin-form");
const metricAdminTitle = document.querySelector("#metric-admin-title");
const metricAdminSubtitle = document.querySelector("#metric-admin-subtitle");
const metricAdminStatus = document.querySelector("#metric-admin-status");
const metricAdminId = document.querySelector("#metric-admin-id");
const metricAdminDomain = document.querySelector("#metric-admin-domain");
const metricAdminName = document.querySelector("#metric-admin-name");
const metricAdminType = document.querySelector("#metric-admin-type");
const metricAdminUnit = document.querySelector("#metric-admin-unit");
const metricAdminOwner = document.querySelector("#metric-admin-owner");
const metricAdminDescription = document.querySelector("#metric-admin-description");
const metricAdminAliases = document.querySelector("#metric-admin-aliases");
const metricAdminPositiveExamples = document.querySelector("#metric-admin-positive-examples");
const metricAdminNegativeExamples = document.querySelector("#metric-admin-negative-examples");
const metricAdminModel = document.querySelector("#metric-admin-model");
const metricAdminOperation = document.querySelector("#metric-admin-operation");
const metricAdminField = document.querySelector("#metric-admin-field");
const metricAdminDenominator = document.querySelector("#metric-admin-denominator");
const metricAdminDenominatorWrap = document.querySelector("#metric-admin-denominator-wrap");
const metricAdminScale = document.querySelector("#metric-admin-scale");
const metricAdminScaleWrap = document.querySelector("#metric-admin-scale-wrap");
const metricFormulaPreview = document.querySelector("#metric-formula-preview");
const metricAdminDimensions = document.querySelector("#metric-admin-dimensions");
const metricAdminMessage = document.querySelector("#metric-admin-message");
const metricAdminSave = document.querySelector("#metric-admin-save");
const metricAdminPublish = document.querySelector("#metric-admin-publish");
const joinRefresh = document.querySelector("#join-refresh");
const joinScan = document.querySelector("#join-scan");
const joinSummary = document.querySelector("#join-summary");
const joinModels = document.querySelector("#join-models");
const joinRelations = document.querySelector("#join-relations");
const joinCandidates = document.querySelector("#join-candidates");
const joinForm = document.querySelector("#join-form");
const joinId = document.querySelector("#join-id");
const joinLeft = document.querySelector("#join-left");
const joinRight = document.querySelector("#join-right");
const joinLeftKey = document.querySelector("#join-left-key");
const joinRightKey = document.querySelector("#join-right-key");
const joinCardinality = document.querySelector("#join-cardinality");
const joinStrategy = document.querySelector("#join-strategy");
const joinValidation = document.querySelector("#join-validation");
const joinValidate = document.querySelector("#join-validate");
const joinPublish = document.querySelector("#join-publish");

let currentResult = null;
let activeConversationId = "";
let conversations = [];
let metricManagementOptions = null;
let metricDrafts = [];
let activeMetricDraft = null;
let joinGraph = null;

function joinItem(title, subtitle, status) {
  return `<article class="join-item"><header><strong>${escapeHtml(title)}</strong><span class="pill">${escapeHtml(status)}</span></header><small>${escapeHtml(subtitle)}</small></article>`;
}

function renderJoinGraph(data) {
  joinGraph = data;
  joinSummary.innerHTML = [
    [data.models.length, "语义模型"], [data.entities.length, "业务实体"],
    [data.relations.filter((x) => x.status === "PUBLISHED").length, "已发布关系"], [data.drafts.length, "待治理草稿"],
  ].map(([value, label]) => `<div class="rich-item"><strong>${value}</strong><small>${label}</small></div>`).join("");
  joinModels.innerHTML = data.models.map((m) => joinItem(m.name, `${m.id} · ${m.table}`, m.status)).join("");
  joinRelations.innerHTML = data.relations.map((r) => joinItem(r.id, `${r.left_entity_id} → ${r.right_entity_id} · ${r.relationship_type} · v${r.version}`, r.status)).join("") || '<div class="rich-item">暂无关系。</div>';
  const options = data.entities.map((e) => `<option value="${escapeHtml(e.id)}">${escapeHtml(e.name)} · ${escapeHtml(e.entity_type)}</option>`).join("");
  joinLeft.innerHTML = options; joinRight.innerHTML = options;
  if (data.drafts[0]) fillJoinDraft(data.drafts[0]);
}

function fillJoinDraft(item) {
  const d = item.definition; joinId.value = item.relation_id; joinLeft.value = d.left_entity_id;
  joinRight.value = d.right_entity_id; joinLeftKey.value = (d.left_keys || []).join(",");
  joinRightKey.value = (d.right_keys || []).join(","); joinCardinality.value = d.relationship_type;
  joinStrategy.value = d.fanout_strategy; joinValidate.disabled = false;
  joinPublish.disabled = item.status !== "VALIDATED" || !item.validation?.safe_to_publish;
  joinValidation.textContent = item.validation?.validated_at ? `覆盖率 ${(item.validation.join_coverage * 100).toFixed(2)}% · 唯一率 ${(item.validation.right_key_unique_rate * 100).toFixed(2)}% · Fanout ${item.validation.fanout_multiplier}x · ${item.validation.risk_level}` : "草稿待数据检测";
}

async function loadJoinGraph() { const r = await fetch("/api/chatbi/join-graph?workspace_id=demo"); const d = await r.json(); if (!r.ok) throw new Error(d.message || "Join Graph加载失败"); renderJoinGraph(d); }
async function saveJoinDraft() {
  const id = joinId.value.trim().toUpperCase(); const body = {workspace_id:"demo", left_entity_id:joinLeft.value, right_entity_id:joinRight.value, left_keys:joinLeftKey.value.split(",").map(x=>x.trim()).filter(Boolean), right_keys:joinRightKey.value.split(",").map(x=>x.trim()).filter(Boolean), relationship_type:joinCardinality.value, join_type:"left", fanout_strategy:joinStrategy.value, priority:100};
  const r = await fetch(`/api/chatbi/join-graph/drafts/${encodeURIComponent(id)}`, {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)}); const d=await r.json(); if(!r.ok) throw new Error(d.message||"草稿保存失败"); joinValidation.textContent="草稿已保存，请执行数据检测。"; joinValidate.disabled=false; joinPublish.disabled=true; await loadJoinGraph();
}
async function validateJoinDraft() { const r=await fetch(`/api/chatbi/join-graph/drafts/${encodeURIComponent(joinId.value)}/validate`,{method:"POST"}); const d=await r.json(); if(!r.ok) throw new Error(d.message||"检测失败"); const v=d.validation; joinValidation.textContent=`覆盖率 ${(v.join_coverage*100).toFixed(2)}% · 唯一率 ${(v.right_key_unique_rate*100).toFixed(2)}% · Fanout ${v.fanout_multiplier}x · ${v.risk_level}`; joinPublish.disabled=!v.safe_to_publish; await loadJoinGraph(); }
async function publishJoinDraft() { const r=await fetch(`/api/chatbi/join-graph/drafts/${encodeURIComponent(joinId.value)}/publish`,{method:"POST"}); const d=await r.json(); if(!r.ok) throw new Error(d.message||"发布失败"); joinValidation.textContent=`${d.relation_id} v${d.version} 已发布给 Planner。`; joinPublish.disabled=true; await loadJoinGraph(); }
async function scanJoinCandidates() { const r=await fetch("/api/chatbi/join-graph/scan?domain=sales",{method:"POST"}); const d=await r.json(); if(!r.ok) throw new Error(d.message||"扫描失败"); joinCandidates.innerHTML=d.candidates.map((c,i)=>`<article class="join-item"><header><strong>${escapeHtml(c.left_entity_id)} → ${escapeHtml(c.right_entity_id)}</strong><button type="button" data-join-candidate="${i}">创建草稿</button></header><small>${escapeHtml(c.left_keys.join(", "))} · 置信度 ${Math.round(c.confidence*100)}% · ${escapeHtml(c.reason)}</small></article>`).join("")||'<div class="rich-item">没有发现新候选。</div>'; joinCandidates.dataset.items=JSON.stringify(d.candidates); }

const statusText = {
  SUCCESS: "成功",
  CLARIFY: "需澄清",
  REJECT: "未命中",
  BLOCKED: "已拦截",
  ERROR: "异常",
};

function switchView(viewName, { scroll = true } = {}) {
  viewPanels.forEach((panel) => {
    panel.classList.toggle("view-hidden", panel.dataset.viewPanel !== viewName);
  });
  viewButtons.forEach((button) => {
    const isActive = button.dataset.view === viewName;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-current", isActive ? "page" : "false");
  });
  if (scroll) {
    document.querySelector(".main")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatNumber(value) {
  if (typeof value !== "number") return value ?? "";
  return new Intl.NumberFormat("zh-CN", {
    maximumFractionDigits: Math.abs(value) >= 100 ? 0 : 2,
  }).format(value);
}

function formatCell(value) {
  if (typeof value === "number") return formatNumber(value);
  if (value === null || value === undefined) return "";
  return String(value);
}

function setOverall(status) {
  overallStatus.textContent = statusText[status] || status || "未知";
  overallStatus.className = "status";
  if (status === "SUCCESS") overallStatus.classList.add("success");
  else if (status === "CLARIFY") overallStatus.classList.add("clarify");
  else if (status === "ERROR" || status === "BLOCKED" || status === "REJECT") overallStatus.classList.add("error");
  else overallStatus.classList.add("idle");
}

function renderPipeline(steps = []) {
  if (!steps.length) {
    pipeline.innerHTML = "<li>暂无链路状态。</li>";
    return;
  }
  pipeline.innerHTML = steps
    .map((step) => {
      const cls = `step-${String(step.status || "").toLowerCase()}`;
      return `
        <li>
          <strong>
            <span>${escapeHtml(step.label)}</span>
            <span class="pill ${cls}">${escapeHtml(step.status)}</span>
          </strong>
          <small>${escapeHtml(step.detail || "")}</small>
        </li>
      `;
    })
    .join("");
}

function richItems(items = [], empty = "暂无") {
  if (!items.length) return `<div class="rich-item">${escapeHtml(empty)}</div>`;
  return items
    .map((item) => {
      if (typeof item === "string") return `<div class="rich-item">${escapeHtml(item)}</div>`;
      const text = item.text || item.message || JSON.stringify(item);
      const ids = item.evidence_ids?.length ? `<small>Evidence：${escapeHtml(item.evidence_ids.join("、"))}</small>` : "";
      return `<div class="rich-item">${escapeHtml(text)}${ids}</div>`;
    })
    .join("");
}

function createConversation(title = "新建分析") {
  return {
    id: `frontend_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    title,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    messages: [],
  };
}

function persistConversations() {
  try {
    localStorage.setItem("chatbi_conversations_v1", JSON.stringify(conversations.slice(0, 12)));
    localStorage.setItem("chatbi_active_conversation_v1", activeConversationId);
  } catch (_error) {
    // Conversation persistence is a convenience; the live session still works without it.
  }
}

function loadConversations() {
  localStorage.removeItem("chatbi_conversations_v1");
  localStorage.removeItem("chatbi_active_conversation_v1");
  conversations = [createConversation("真实零售数据分析")];
  activeConversationId = conversations[0].id;
}

function activeConversation() {
  return conversations.find((item) => item.id === activeConversationId) || conversations[0];
}

function conversationMeta(item) {
  const turns = item.messages.filter((message) => message.role === "user").length;
  if (!turns) return "尚未开始";
  const time = new Date(item.updatedAt).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  return `${time} · ${turns} 轮对话`;
}

function renderConversationList() {
  conversationList.innerHTML = [...conversations]
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .map(
      (item) => `<button class="conversation-item ${item.id === activeConversationId ? "active" : ""}" type="button" data-conversation-id="${escapeHtml(item.id)}">
        <strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(conversationMeta(item))}</small>
      </button>`,
    )
    .join("");
}

function userMessageMarkup(text) {
  return `<article class="chat-message user"><span class="chat-avatar">你</span><div class="message-content"><div class="user-bubble">${escapeHtml(text)}</div></div></article>`;
}

function loadingMessageMarkup() {
  return `<article class="chat-message assistant" data-loading-message><span class="chat-avatar">AI</span><div class="message-content"><div class="typing-card"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>正在理解上下文并运行分析</div></div></article>`;
}

function contextFromResult(data) {
  const metric = data.selected_metric;
  const dsl = data.dsl || {};
  const dimensions = (dsl.dimensions || []).map((item) => item.dimension_id).join("、") || "未指定";
  const timeRange = dsl.time_range?.label || dsl.time_range?.preset || dsl.time_range?.start && dsl.time_range?.end
    ? dsl.time_range?.label || dsl.time_range?.preset || `${dsl.time_range?.start || ""} 至 ${dsl.time_range?.end || ""}`
    : "按问题识别";
  return {
    metric: metric ? `${metric.display_name || metric.name || metric.metric_id} · ${metric.metric_id}` : "待确认",
    metricName: metric?.display_name || metric?.name || metric?.metric_id || "当前指标",
    dimensions,
    timeRange,
    intent: dsl.intent || "分析查询",
  };
}

function updateContextPanels(data) {
  const context = contextFromResult(data);
  contextChips.innerHTML = `<span>沿用：${escapeHtml(context.metricName)}</span><span>范围：${escapeHtml(context.timeRange)}</span><span>维度：${escapeHtml(context.dimensions)}</span>`;
  contextMemory.innerHTML = `
    <div class="context-row"><span>指标口径</span><strong>${escapeHtml(context.metric)}</strong></div>
    <div class="context-row"><span>时间范围</span><strong>${escapeHtml(context.timeRange)}</strong></div>
    <div class="context-row"><span>分析维度</span><strong>${escapeHtml(context.dimensions)}</strong></div>
    <div class="context-row"><span>查询意图</span><strong>${escapeHtml(context.intent)}</strong></div>`;
  const items = data.profile?.evidence || [];
  evidenceCount.textContent = `${items.length} 条`;
  evidenceInspector.innerHTML = items.length
    ? items.map((item) => `<button class="evidence-item" type="button" data-evidence-id="${escapeHtml(item.evidence_id)}"><strong>${escapeHtml(item.evidence_id)}</strong><div>${escapeHtml(item.statement)}</div><small>${escapeHtml(item.metric_id)} · rows ${(item.row_refs || []).join(",")}</small></button>`).join("")
    : `<div class="evidence-item">暂无 Evidence。</div>`;
}

function interactiveResultMarkup(data) {
  const interpretation = data.interpretation || {};
  const context = contextFromResult(data);
  const finding = interpretation.findings?.[0];
  const summary = typeof finding === "string" ? finding : finding?.text || data.message || "分析已完成。";
  const rawTitle = String(interpretation.title || "").trim();
  const insightTitle = rawTitle && !rawTitle.includes("证据约束解读")
    ? rawTitle
    : summary.replace(/[。！？!?]+$/, "");
  const rows = data.execution?.rows || [];
  const spec = data.profile?.chart_spec || {};
  const yKey = Array.isArray(spec.y) ? spec.y[0] : spec.y;
  const latest = rows.at(-1)?.[yKey];
  const previous = rows.at(-2)?.[yKey];
  const change = typeof latest === "number" && typeof previous === "number" && previous !== 0 ? ((latest - previous) / Math.abs(previous)) * 100 : null;
  return `<article class="chat-message assistant"><span class="chat-avatar">AI</span><div class="message-content">
    <p class="assistant-copy">${escapeHtml(summary)}</p>
    <section class="interactive-result" data-result-card>
      <header class="interactive-result-head"><div><h3>${escapeHtml(insightTitle || spec.title || "查询结果")}</h3><p>沿用 ${escapeHtml(context.metric)} · ${escapeHtml(context.timeRange)}</p></div><span class="status success">✓ 可信</span></header>
      <div class="result-controls">
        <button class="result-control active" type="button">${escapeHtml(context.dimensions)}</button>
        <button class="result-control" type="button" data-followup-query="各地区${escapeHtml(context.metricName)}排名">地区</button>
        <button class="result-control" type="button" data-followup-query="按渠道拆解${escapeHtml(context.metricName)}">渠道</button>
        <button class="result-control" type="button" data-followup-query="只看最近三个月的${escapeHtml(context.metricName)}">最近 3 个月</button>
        <button class="result-control result-view-control active" type="button" data-result-view="chart">图表</button>
        <button class="result-control" type="button" data-result-view="table">数据表</button>
      </div>
      <div class="result-summary">
        <div class="result-metric"><small>最新值</small><strong>${escapeHtml(formatNumber(latest ?? data.execution?.row_count ?? 0))}</strong><span>${change === null ? "查询完成" : `${change >= 0 ? "↑" : "↓"} ${Math.abs(change).toFixed(1)}% 环比`}</span></div>
        <div class="result-metric"><small>数据行数</small><strong>${escapeHtml(rows.length)}</strong><span>完整返回</span></div>
        <div class="result-metric"><small>可信状态</small><strong>${escapeHtml(data.reflection?.status || "PASS")}</strong><span>${escapeHtml((data.profile?.evidence || []).length)} 条 Evidence</span></div>
      </div>
      <div class="interactive-chart" data-result-chart>${chart.innerHTML}</div>
      <div class="interactive-table result-tab-hidden" data-result-table>${table.innerHTML}</div>
      <div class="result-actions"><button type="button" data-result-view="table">查看明细</button><button type="button">导出</button><button type="button">固定到看板</button></div>
    </section>
    <p class="assistant-meta">${escapeHtml(data.selected_metric?.metric_id || "")} · ${escapeHtml(data.compiled?.query_id || data.trace_id || "")} · Reflection ${escapeHtml(data.reflection?.status || "-")}</p>
  </div></article>`;
}

function clarificationMessageMarkup(data) {
  const candidates = data.retrieval?.mentions?.flatMap((mention) => mention.candidates || []) || [];
  return `<article class="chat-message assistant"><span class="chat-avatar">AI</span><div class="message-content"><p class="assistant-copy">${escapeHtml(data.message || "需要先确认指标口径。")}</p><section class="interactive-result"><h3>请选择指标口径</h3><div class="suggested-followups">${candidates.map((candidate) => `<button type="button" data-followup-query="查询${escapeHtml(candidate.display_name)}">${escapeHtml(candidate.display_name)} · ${escapeHtml(candidate.business_definition || candidate.metric_id)}</button>`).join("")}</div></section></div></article>`;
}

function renderActiveConversation() {
  const conversation = activeConversation();
  conversationTitle.textContent = conversation.title;
  const turns = conversation.messages.filter((item) => item.role === "user").length;
  conversationTurnCount.textContent = `${turns} 轮对话`;
  if (!conversation.messages.length) {
    chatThread.innerHTML = `<section id="empty-state" class="chat-empty"><span class="empty-icon">AI</span><h3>从一个业务问题开始</h3><p>我会记住本次会话中的指标、时间、维度和筛选条件。</p><div class="empty-examples"><button type="button" data-example="2011年每月真实净收入趋势">净收入趋势</button><button type="button" data-example="各国家真实商品销售额排名">国家排名</button><button type="button" data-example="商品真实销售件数排名">商品排名</button></div></section>`;
    contextChips.innerHTML = "<span>新会话 · 暂无继承条件</span>";
    return;
  }
  chatThread.innerHTML = conversation.messages.map((item) => item.role === "user" ? userMessageMarkup(item.text) : item.html).join("");
  const lastAssistant = [...conversation.messages].reverse().find((item) => item.role === "assistant" && item.data);
  if (lastAssistant) {
    renderResult(lastAssistant.data);
    updateContextPanels(lastAssistant.data);
  }
  chatThread.scrollTop = chatThread.scrollHeight;
}

function renderClarification(data) {
  const candidates = data.retrieval?.mentions?.flatMap((mention) => mention.candidates || []) || [];
  answerTitle.textContent = "需要先确认指标口径";
  findings.innerHTML = candidates.length
    ? candidates
        .map(
          (candidate) => `
          <div class="rich-item">
            <strong>${escapeHtml(candidate.display_name)}</strong>
            <small>${escapeHtml(candidate.metric_id)} · 置信度 ${formatNumber(candidate.probability)}</small>
            <div>${escapeHtml(candidate.business_definition)}</div>
          </div>
        `,
        )
        .join("")
    : `<div class="rich-item">${escapeHtml(data.message)}</div>`;
  caveats.innerHTML = `<div class="rich-item">当前版本先安全停止，不在口径不清时执行查询。</div>`;
  nextActions.innerHTML = `<div class="rich-item">请把问题改成更明确的指标，例如“查询毛利率”或“查询毛利额”。</div>`;
  chart.innerHTML = `<div class="empty-state"><p>澄清后才会生成图表。</p></div>`;
  chartTitle.textContent = "指标候选";
  chartType.textContent = "Clarify";
  evidence.innerHTML = `<div class="evidence-item">暂无 Evidence。</div>`;
  table.innerHTML = "";
}

function scale(value, min, max, targetMin, targetMax) {
  if (max === min) return (targetMin + targetMax) / 2;
  return targetMin + ((value - min) / (max - min)) * (targetMax - targetMin);
}

function renderChart(data) {
  const rows = data.execution?.rows || [];
  const spec = data.profile?.chart_spec;
  if (!rows.length || !spec) {
    chart.innerHTML = `<div class="empty-state"><p>暂无可视化数据。</p></div>`;
    return;
  }

  const xKey = spec.x;
  const yKey = Array.isArray(spec.y) ? spec.y[0] : spec.y;
  const values = rows.map((row) => Number(row[yKey] || 0));
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const width = 900;
  const height = 320;
  const padding = { top: 24, right: 22, bottom: 54, left: 78 };
  chartTitle.textContent = spec.title || "图表";
  chartType.textContent = spec.type;

  if (spec.type === "bar") {
    const barGap = 12;
    const plotWidth = width - padding.left - padding.right;
    const barWidth = Math.max(18, (plotWidth - barGap * (rows.length - 1)) / rows.length);
    const bars = rows
      .map((row, index) => {
        const value = Number(row[yKey] || 0);
        const barHeight = height - padding.bottom - scale(value, min, max, height - padding.bottom, padding.top);
        const x = padding.left + index * (barWidth + barGap);
        const y = height - padding.bottom - barHeight;
        return `
          <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="8" fill="#2563eb"></rect>
          <text x="${x + barWidth / 2}" y="${height - 28}" text-anchor="middle" class="axis-label">${escapeHtml(row[xKey])}</text>
          <text x="${x + barWidth / 2}" y="${Math.max(16, y - 8)}" text-anchor="middle" class="axis-label">${formatNumber(value)}</text>
        `;
      })
      .join("");
    chart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(spec.title)}">
      <line x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}" stroke="#cbd5e1"></line>
      ${bars}
    </svg>`;
    return;
  }

  const plotWidth = width - padding.left - padding.right;
  const xStep = rows.length > 1 ? plotWidth / (rows.length - 1) : plotWidth;
  const points = rows
    .map((row, index) => {
      const x = padding.left + index * xStep;
      const y = scale(Number(row[yKey] || 0), min, max, height - padding.bottom, padding.top);
      return { x, y, label: row[xKey], value: row[yKey] };
    });
  const polyline = points.map((point) => `${point.x},${point.y}`).join(" ");
  const circles = points
    .map(
      (point, index) => `
        <circle cx="${point.x}" cy="${point.y}" r="5" fill="#14b8a6"></circle>
        ${index % 2 === 0 ? `<text x="${point.x}" y="${height - 28}" text-anchor="middle" class="axis-label">${escapeHtml(String(point.label).slice(0, 7))}</text>` : ""}
      `,
    )
    .join("");
  chart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(spec.title)}">
    <line x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}" stroke="#cbd5e1"></line>
    <line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}" stroke="#cbd5e1"></line>
    <text x="${padding.left - 14}" y="${padding.top + 4}" text-anchor="end" class="axis-label">${formatNumber(max)}</text>
    <text x="${padding.left - 14}" y="${height - padding.bottom}" text-anchor="end" class="axis-label">${formatNumber(min)}</text>
    <polyline points="${polyline}" fill="none" stroke="#2563eb" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></polyline>
    ${circles}
  </svg>`;
}

function renderEvidence(data) {
  const items = data.profile?.evidence || [];
  evidence.innerHTML = items.length
    ? items
        .map(
          (item) => `
            <div class="evidence-item">
              <strong>${escapeHtml(item.evidence_id)}</strong>
              <div>${escapeHtml(item.statement)}</div>
              <small>${escapeHtml(item.metric_id)} · ${escapeHtml(item.unit)} · rows ${escapeHtml((item.row_refs || []).join(","))}</small>
            </div>
          `,
        )
        .join("")
    : `<div class="evidence-item">暂无 Evidence。</div>`;
}

function renderTable(data) {
  const rows = data.execution?.rows || [];
  if (!rows.length) {
    table.innerHTML = "";
    return;
  }
  const columns = Object.keys(rows[0]);
  table.innerHTML = `
    <table>
      <thead><tr>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr></thead>
      <tbody>
        ${rows
          .map((row) => `<tr>${columns.map((column) => `<td>${escapeHtml(formatCell(row[column]))}</td>`).join("")}</tr>`)
          .join("")}
      </tbody>
    </table>
  `;
}

function typeLabel(type) {
  const labels = {
    METRIC_WRONG: "指标选错",
    DATA_WRONG: "数据不对",
    INTERPRETATION_UNTRUSTED: "解读不可信",
    CHART_WRONG: "图表不合适",
    PERMISSION_ISSUE: "权限/安全",
    UI_ISSUE: "页面体验",
    OTHER: "其他",
  };
  return labels[type] || type;
}

function renderMetricCatalog(data) {
  const counts = data.domain_counts || {};
  metricCounts.innerHTML = Object.entries(counts)
    .map(([domain, count]) => `<span class="pill">${escapeHtml(domain)}: ${escapeHtml(count)}</span>`)
    .join("");

  if (!data.items?.length) {
    metricList.innerHTML = `<div class="rich-item">当前筛选下暂无指标。</div>`;
    return;
  }

  metricList.innerHTML = data.items
    .map(
      (item) => `
        <article class="metric-card" data-metric-id="${escapeHtml(item.metric_id)}">
          <header>
            <div>
              <strong>${escapeHtml(item.name)}</strong>
              <small>${escapeHtml(item.metric_id)} · v${escapeHtml(item.latest_version)}</small>
            </div>
            <span class="pill">${escapeHtml(item.business_domain_id)}</span>
          </header>
          <div class="metric-meta">
            <span class="pill">${escapeHtml(item.metric_type)}</span>
            <span class="pill">${escapeHtml(item.unit)}</span>
            <span class="pill">${escapeHtml(item.owner)}</span>
          </div>
          <p>${escapeHtml(item.description)}</p>
          <button type="button" data-metric-detail="${escapeHtml(item.metric_id)}">查看指标详情</button>
        </article>
      `,
    )
    .join("");
}

function renderMetricDetail(data) {
  const item = data.metric;
  metricDetail.innerHTML = `
    <article class="metric-card">
      <header>
        <div>
          <strong>${escapeHtml(item.name)}</strong>
          <small>${escapeHtml(item.metric_id)} · ${escapeHtml(item.business_domain_name)} · v${escapeHtml(item.latest_version)}</small>
        </div>
        <span class="pill">${escapeHtml(item.status)}</span>
      </header>
      <p>${escapeHtml(item.description)}</p>
      <div class="metric-meta">
        <span class="pill">类型：${escapeHtml(item.metric_type)}</span>
        <span class="pill">单位：${escapeHtml(item.unit)}</span>
        <span class="pill">Owner：${escapeHtml(item.owner)}</span>
      </div>
      <h4>计算公式</h4>
      <div class="formula">${escapeHtml(item.formula_text)}</div>
      <h4>别名</h4>
      <div class="metric-meta">${(item.aliases || []).map((alias) => `<span class="pill">${escapeHtml(alias)}</span>`).join("") || '<span class="pill">暂无</span>'}</div>
      <h4>可用维度</h4>
      <div class="metric-meta">
        ${(item.dimensions || [])
          .map((dimension) => `<span class="pill">${escapeHtml(dimension.dimension_id)} · ${escapeHtml(dimension.name)}</span>`)
          .join("") || '<span class="pill">暂无维度</span>'}
      </div>
      <h4>语义模型与血缘</h4>
      <div class="rich-item">
        <div>模型：${escapeHtml(item.semantic_model.semantic_model_id)} / ${escapeHtml(item.semantic_model.name)}</div>
        <div>数仓：${escapeHtml(item.semantic_model.warehouse)}</div>
        <div>物理表：${escapeHtml(item.semantic_model.physical_table)}</div>
        <div>时间字段：${escapeHtml(item.semantic_model.default_time_field)}</div>
        <div>字段：${escapeHtml((item.lineage.fields || []).join(", ") || "-")}</div>
      </div>
      <h4>示例问题</h4>
      <div class="examples">
        ${(item.example_questions || [])
          .map((question) => `<button type="button" data-metric-example="${escapeHtml(question)}">${escapeHtml(question)}</button>`)
          .join("")}
      </div>
      <h4>发布历史</h4>
      <div class="version-history">
        ${(data.versions || [])
          .map((version) => `<div><strong>v${escapeHtml(version.version)}</strong><span>${escapeHtml(version.formula_text)}</span><small>${escapeHtml(version.published_at)}</small></div>`)
          .join("") || '<div class="rich-item">暂无发布版本。</div>'}
      </div>
      <button type="button" data-metric-edit="${escapeHtml(item.metric_id)}">创建下一版本草稿</button>
    </article>
  `;
}

async function loadMetricCatalog() {
  const domain = metricDomainFilter.value;
  const response = await fetch(`/api/chatbi/metrics/catalog?workspace_id=demo&domain=${encodeURIComponent(domain)}&limit=50`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.detail?.message || "指标目录加载失败");
  renderMetricCatalog(data);
  if (data.items?.length) {
    await loadMetricDetail(data.items[0].metric_id);
  }
}

async function loadMetricDetail(metricId) {
  const response = await fetch(`/api/chatbi/metrics/catalog/${encodeURIComponent(metricId)}?workspace_id=demo`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.detail?.message || "指标详情加载失败");
  renderMetricDetail(data);
  return data;
}

function expressionFromForm() {
  const operation = metricAdminOperation.value;
  if (operation === "ratio") {
    return {
      op: "ratio",
      numerator: { op: "sum", field: metricAdminField.value },
      denominator: { op: "sum", field: metricAdminDenominator.value },
      scale: Number(metricAdminScale.value),
      zero_policy: "null",
    };
  }
  return { op: operation, field: metricAdminField.value };
}

function updateFormulaPreview() {
  const operation = metricAdminOperation.value;
  const isRatio = operation === "ratio";
  metricAdminDenominatorWrap.classList.toggle("hidden", !isRatio);
  metricAdminScaleWrap.classList.toggle("hidden", !isRatio);
  if (!metricAdminField.value) {
    metricFormulaPreview.textContent = "选择模型和字段后生成公式预览";
    return;
  }
  metricFormulaPreview.textContent = isRatio
    ? `SUM(${metricAdminField.value}) / NULLIF(SUM(${metricAdminDenominator.value || "?"}), 0) × ${metricAdminScale.value}`
    : operation === "count_distinct"
      ? `COUNT(DISTINCT ${metricAdminField.value})`
      : `SUM(${metricAdminField.value})`;
}

function selectedDimensionIds() {
  return [...metricAdminDimensions.querySelectorAll("input:checked")].map((item) => item.value);
}

function renderManagementOptions(selectedDimensions = []) {
  if (!metricManagementOptions) return;
  const requestedDomain = metricAdminDomain.value;
  metricAdminDomain.innerHTML = metricManagementOptions.domains
    .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`)
    .join("");
  if (metricManagementOptions.domains.some((item) => item.id === requestedDomain)) {
    metricAdminDomain.value = requestedDomain;
  }
  const domain = metricAdminDomain.value || metricManagementOptions.domains[0]?.id;
  const matchingModels = metricManagementOptions.semantic_models.filter((item) => item.business_domain_id === domain);
  metricAdminModel.innerHTML = matchingModels
    .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} · ${escapeHtml(item.physical_table)}</option>`)
    .join("");
  const model = matchingModels.find((item) => item.id === metricAdminModel.dataset.preferred) || matchingModels[0];
  if (model) metricAdminModel.value = model.id;
  const fields = model?.fields || [];
  const fieldOptions = fields.map((field) => `<option value="${escapeHtml(field)}">${escapeHtml(field)}</option>`).join("");
  metricAdminField.innerHTML = fieldOptions;
  metricAdminDenominator.innerHTML = fieldOptions;
  const compatible = metricManagementOptions.dimensions.filter((item) => (item.fields || []).includes(model?.id));
  metricAdminDimensions.innerHTML = compatible
    .map((item) => {
      const checked = selectedDimensions.includes(item.id) || (!selectedDimensions.length && ["D_DATE", "D_MONTH"].includes(item.id));
      return `<label><input type="checkbox" value="${escapeHtml(item.id)}" ${checked ? "checked" : ""} /> <span>${escapeHtml(item.name)}</span><small>${escapeHtml(item.id)}</small></label>`;
    })
    .join("");
  updateFormulaPreview();
}

async function loadMetricManagementOptions() {
  const response = await fetch("/api/chatbi/metrics/manage/options?workspace_id=demo");
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || "指标配置加载失败");
  metricManagementOptions = data;
  renderManagementOptions(selectedDimensionIds());
}

function resetMetricAdminForm() {
  activeMetricDraft = null;
  metricAdminForm.reset();
  metricAdminId.disabled = false;
  metricAdminOwner.value = "data-platform";
  metricAdminTitle.textContent = "创建指标草稿";
  metricAdminSubtitle.textContent = "发布后生成 v1；后续修改会生成递增版本。";
  metricAdminStatus.textContent = "未保存";
  metricAdminMessage.textContent = "";
  metricAdminPublish.disabled = true;
  metricAdminModel.dataset.preferred = "";
  renderManagementOptions([]);
}

function fillMetricAdminForm(item) {
  activeMetricDraft = item;
  metricAdminId.value = item.metric_id;
  metricAdminId.disabled = true;
  metricAdminDomain.value = item.business_domain_id;
  metricAdminName.value = item.name;
  metricAdminType.value = item.metric_type;
  metricAdminUnit.value = item.unit;
  metricAdminOwner.value = item.owner;
  metricAdminDescription.value = item.description;
  metricAdminAliases.value = (item.aliases || []).join(", ");
  metricAdminPositiveExamples.value = (item.positive_examples || []).join("\n");
  metricAdminNegativeExamples.value = (item.negative_examples || []).join("\n");
  metricAdminModel.dataset.preferred = item.semantic_model_id;
  renderManagementOptions(item.dimension_ids || []);
  metricAdminModel.value = item.semantic_model_id;
  const expression = item.expression || {};
  metricAdminOperation.value = expression.op || "sum";
  if (expression.op === "ratio") {
    metricAdminField.value = expression.numerator?.field || "";
    metricAdminDenominator.value = expression.denominator?.field || "";
    metricAdminScale.value = String(expression.scale || 1);
  } else {
    metricAdminField.value = expression.field || "";
  }
  metricAdminTitle.textContent = item.metric_status === "PUBLISHED" ? `编辑 ${item.name}` : `完善 ${item.name}`;
  metricAdminSubtitle.textContent = `保存后可发布 v${item.next_version}`;
  metricAdminStatus.textContent = `草稿 · 待发布 v${item.next_version}`;
  metricAdminPublish.disabled = false;
  updateFormulaPreview();
}

function renderMetricDrafts(data) {
  metricDrafts = data.items || [];
  metricDraftCount.textContent = String(data.total || 0);
  metricDraftList.innerHTML = metricDrafts.length
    ? metricDrafts.map((item) => `<article class="metric-card"><header><div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.metric_id)}</small></div><span class="pill">v${escapeHtml(item.next_version)}</span></header><p>${escapeHtml(item.description)}</p><button type="button" data-draft-edit="${escapeHtml(item.metric_id)}">继续编辑</button></article>`).join("")
    : '<div class="rich-item">暂无待发布草稿。</div>';
}

async function loadMetricDrafts() {
  const response = await fetch("/api/chatbi/metrics/manage/drafts?workspace_id=demo");
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || "指标草稿加载失败");
  renderMetricDrafts(data);
}

function metricDraftPayload() {
  return {
    workspace_id: "demo",
    metric_id: metricAdminId.value.trim().toUpperCase(),
    business_domain_id: metricAdminDomain.value,
    name: metricAdminName.value.trim(),
    description: metricAdminDescription.value.trim(),
    metric_type: metricAdminType.value,
    unit: metricAdminUnit.value.trim(),
    owner: metricAdminOwner.value.trim(),
    aliases: metricAdminAliases.value.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
    positive_examples: metricAdminPositiveExamples.value.split(/\n/).map((item) => item.trim()).filter(Boolean),
    negative_examples: metricAdminNegativeExamples.value.split(/\n/).map((item) => item.trim()).filter(Boolean),
    semantic_model_id: metricAdminModel.value,
    expression: expressionFromForm(),
    default_aggregation: "default",
    time_dimension_id: selectedDimensionIds().includes("D_DATE") ? "D_DATE" : selectedDimensionIds()[0],
    dimension_ids: selectedDimensionIds(),
  };
}

async function saveMetricDraft() {
  const payload = metricDraftPayload();
  metricAdminSave.disabled = true;
  metricAdminMessage.textContent = "正在校验指标公式与维度映射...";
  const response = await fetch(`/api/chatbi/metrics/manage/drafts/${encodeURIComponent(payload.metric_id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  metricAdminSave.disabled = false;
  if (!response.ok) throw new Error(data.message || "草稿保存失败");
  fillMetricAdminForm(data.draft);
  metricAdminMessage.textContent = `校验通过：${data.draft.formula_text}`;
  await loadMetricDrafts();
}

async function publishMetricDraft() {
  if (!activeMetricDraft) return;
  metricAdminPublish.disabled = true;
  metricAdminMessage.textContent = `正在发布 v${activeMetricDraft.next_version}...`;
  const response = await fetch(`/api/chatbi/metrics/manage/drafts/${encodeURIComponent(activeMetricDraft.metric_id)}/publish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ workspace_id: "demo" }),
  });
  const data = await response.json();
  if (!response.ok) {
    metricAdminPublish.disabled = false;
    throw new Error(data.message || "指标发布失败");
  }
  metricAdminMessage.textContent = `${data.metric_id} v${data.version} 已发布并进入问数指标目录。`;
  metricAdminStatus.textContent = `已发布 v${data.version}`;
  activeMetricDraft = null;
  await Promise.all([loadMetricDrafts(), loadMetricCatalog()]);
}

async function editPublishedMetric(metricId) {
  if (!metricManagementOptions) await loadMetricManagementOptions();
  const data = await loadMetricDetail(metricId);
  const item = data.metric;
  fillMetricAdminForm({
    metric_id: item.metric_id,
    business_domain_id: item.business_domain_id,
    name: item.name,
    description: item.description,
    metric_type: item.metric_type,
    unit: item.unit,
    owner: item.owner,
    metric_status: "PUBLISHED",
    next_version: Number(item.latest_version) + 1,
    aliases: item.aliases,
    positive_examples: item.positive_examples || [],
    negative_examples: item.negative_examples || [],
    semantic_model_id: item.semantic_model.semantic_model_id,
    expression: data.expression,
    dimension_ids: item.dimensions.map((dimension) => dimension.dimension_id),
  });
  metricAdminPublish.disabled = true;
  metricAdminStatus.textContent = `基于 v${item.latest_version}`;
  metricAdminMessage.textContent = "修改后先保存并校验草稿，再发布新版本。";
  switchView("metric-admin");
}

function renderEvaluationReport(data) {
  const summary = data.summary || {};
  const passRate = Math.round((summary.pass_rate || 0) * 10000) / 100;
  evaluationSummary.innerHTML = `
    <div class="rich-item"><strong>${escapeHtml(summary.status || "-")}</strong><small>总体状态</small></div>
    <div class="rich-item"><strong>${escapeHtml(summary.passed ?? "-")} / ${escapeHtml(summary.total ?? "-")}</strong><small>总通过</small></div>
    <div class="rich-item"><strong>${escapeHtml(passRate)}%</strong><small>通过率</small></div>
    <div class="rich-item"><strong>${escapeHtml(data.report_name || "-")}</strong><small>${escapeHtml(data.generated_at || "-")}</small></div>
  `;

  evaluationCases.innerHTML = (data.cases || [])
    .map(
      (item) => `
        <article class="evaluation-card">
          <header>
            <strong>${escapeHtml(item.name)}</strong>
            <span class="pill ${item.passed ? "step-pass" : "step-error"}">${item.passed ? "PASS" : "FAIL"}</span>
          </header>
          <div class="badcase-meta">
            <span class="pill">${escapeHtml(item.status || "-")}</span>
            <span class="pill">${escapeHtml(item.selected_metric_id || "-")}</span>
            <span class="pill">${escapeHtml(item.dsl_intent || "-")}</span>
            <span class="pill">${escapeHtml(item.chart_type || "-")}</span>
            <span class="pill">${escapeHtml(item.latency_ms ?? "-")}ms</span>
          </div>
          ${item.errors?.length ? `<p>${escapeHtml(item.errors.join("；"))}</p>` : ""}
        </article>
      `,
    )
    .join("") || `<div class="rich-item">暂无用例结果。</div>`;

  evaluationGates.innerHTML = (data.gates || [])
    .map(
      (item) => `
        <article class="evaluation-card">
          <header>
            <strong>${escapeHtml(item.name)}</strong>
            <span class="pill ${item.passed ? "step-pass" : "step-error"}">${item.passed ? "PASS" : "FAIL"}</span>
          </header>
          <p>${escapeHtml(item.detail || "")}</p>
        </article>
      `,
    )
    .join("") || `<div class="rich-item">暂无门禁结果。</div>`;
}

function renderEvaluationTrend(data) {
  if (!evaluationTrend) return;
  const items = data.items || [];
  if (!items.length) {
    evaluationTrend.innerHTML = `<div class="rich-item">No evaluation history yet. Run the evaluation script once to create a trend snapshot.</div>`;
    return;
  }

  const latest = data.latest || items[items.length - 1];
  const percent = (value) => `${Math.round((Number(value) || 0) * 10000) / 100}%`;
  const width = 680;
  const height = 168;
  const padding = 24;
  const points = items.map((item, index) => {
    const rate = Math.max(0, Math.min(1, Number(item.pass_rate) || 0));
    const x = items.length === 1 ? width / 2 : padding + (index * (width - padding * 2)) / (items.length - 1);
    const y = padding + (1 - rate) * (height - padding * 2);
    return { x, y, item };
  });
  const polyline = points.map((point) => `${point.x},${point.y}`).join(" ");
  const circles = points
    .map(
      (point) => `
        <circle cx="${point.x}" cy="${point.y}" r="4">
          <title>${escapeHtml(point.item.generated_at || point.item.snapshot_name)} · ${percent(point.item.pass_rate)}</title>
        </circle>
      `,
    )
    .join("");
  const recent = items
    .slice(-6)
    .reverse()
    .map(
      (item) => `
        <article class="trend-snapshot">
          <strong>${escapeHtml(percent(item.pass_rate))}</strong>
          <span>${escapeHtml(item.generated_at || item.snapshot_name || "-")}</span>
          <small>${escapeHtml(item.passed)} / ${escapeHtml(item.total)} checks · ${escapeHtml(item.avg_latency_ms)}ms avg · ${(item.failed_gates || []).length} failed gates</small>
        </article>
      `,
    )
    .join("");

  evaluationTrend.innerHTML = `
    <div class="trend-card">
      <div class="trend-headline">
        <div>
          <strong>${escapeHtml(percent(latest.pass_rate))}</strong>
          <small>Latest pass rate</small>
        </div>
        <div>
          <strong>${escapeHtml(latest.avg_latency_ms ?? "-")}ms</strong>
          <small>Average latency</small>
        </div>
        <div>
          <strong>${escapeHtml((latest.failed_gates || []).length)}</strong>
          <small>Failed gates</small>
        </div>
        <div>
          <strong>${escapeHtml(data.total ?? items.length)}</strong>
          <small>Snapshots</small>
        </div>
      </div>
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Evaluation pass rate trend">
        <line x1="${padding}" y1="${padding}" x2="${width - padding}" y2="${padding}"></line>
        <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}"></line>
        <polyline points="${polyline}"></polyline>
        ${circles}
        <text x="4" y="${padding + 4}">100%</text>
        <text x="10" y="${height - padding + 4}">0%</text>
      </svg>
      <div class="trend-snapshots">${recent}</div>
    </div>
  `;
}

async function loadEvaluationReport() {
  const response = await fetch("/api/chatbi/evaluations/latest");
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.detail?.message || "测评报告加载失败");
  renderEvaluationReport(data);
}

async function loadEvaluationTrend() {
  const response = await fetch("/api/chatbi/evaluations/trends?limit=20");
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.detail?.message || "Evaluation trend failed to load");
  renderEvaluationTrend(data);
}

function renderBadcaseBoard(data) {
  const counts = data.status_counts || {};
  const statuses = ["OPEN", "CONFIRMED", "FIXED", "WONT_FIX"];
  badcaseCounts.innerHTML = statuses
    .map((status) => `<span class="pill">${status}: ${counts[status] || 0}</span>`)
    .join("");

  if (!data.items?.length) {
    badcaseList.innerHTML = `<div class="rich-item">当前筛选下暂无反馈。</div>`;
    return;
  }

  badcaseList.innerHTML = data.items
    .map((item) => {
      const canConfirm = item.status === "OPEN";
      const canFix = item.status === "OPEN" || item.status === "CONFIRMED";
      const canCreateGolden = item.regression_candidate && (item.status === "CONFIRMED" || item.status === "FIXED");
      return `
        <article class="badcase-card" data-feedback-id="${escapeHtml(item.feedback_id)}">
          <header>
            <div>
              <strong>${escapeHtml(typeLabel(item.feedback_type))}</strong>
              <small>${escapeHtml(item.feedback_id)} · ${escapeHtml(item.created_at)}</small>
            </div>
            <span class="pill">${escapeHtml(item.status)}</span>
          </header>
          <div class="badcase-meta">
            <span class="pill">${escapeHtml(item.severity)}</span>
            ${item.regression_candidate ? '<span class="pill step-pass">回归候选</span>' : '<span class="pill">普通反馈</span>'}
            ${item.query_id ? `<span class="pill">${escapeHtml(item.query_id)}</span>` : ""}
          </div>
          <p><strong>问题：</strong>${escapeHtml(item.user_query)}</p>
          <p><strong>反馈：</strong>${escapeHtml(item.message)}</p>
          ${item.expected_behavior ? `<p><strong>期望：</strong>${escapeHtml(item.expected_behavior)}</p>` : ""}
          <footer>
            <button type="button" data-golden-action="CREATE" ${canCreateGolden ? "" : "disabled"}>加入黄金集</button>
            <button type="button" data-feedback-action="CONFIRMED" ${canConfirm ? "" : "disabled"}>确认 Badcase</button>
            <button type="button" data-feedback-action="FIXED" ${canFix ? "" : "disabled"}>标记修复</button>
            <button type="button" data-feedback-action="WONT_FIX">不处理</button>
          </footer>
        </article>
      `;
    })
    .join("");
}

async function loadBadcases() {
  const status = badcaseFilter.value;
  const response = await fetch(`/api/chatbi/feedback?workspace_id=demo&status=${encodeURIComponent(status)}&limit=30`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.detail?.message || "Badcase 看板加载失败");
  renderBadcaseBoard(data);
}

async function updateBadcaseStatus(feedbackId, status) {
  const response = await fetch(`/api/chatbi/feedback/${encodeURIComponent(feedbackId)}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.detail?.message || "状态更新失败");
  await loadBadcases();
}

function renderGoldenQuestions(data) {
  const counts = data.status_counts || {};
  goldenCounts.innerHTML = ["ACTIVE", "ARCHIVED"]
    .map((status) => `<span class="pill">${status}: ${counts[status] || 0}</span>`)
    .join("");

  if (!data.items?.length) {
    goldenList.innerHTML = `<div class="rich-item">暂无黄金问题。先在 Badcase 看板确认问题，再加入黄金集。</div>`;
    return;
  }

  goldenList.innerHTML = data.items
    .map(
      (item) => `
        <article class="badcase-card">
          <header>
            <div>
              <strong>${escapeHtml(item.user_query)}</strong>
              <small>${escapeHtml(item.golden_id)} · source ${escapeHtml(item.source_feedback_id || "-")}</small>
            </div>
            <span class="pill">${escapeHtml(item.status)}</span>
          </header>
          <div class="badcase-meta">
            <span class="pill">${escapeHtml(item.expected_metric_id || "metric:any")}</span>
            <span class="pill">${escapeHtml(item.expected_intent || "intent:any")}</span>
            <span class="pill">${escapeHtml(item.expected_chart_type || "chart:any")}</span>
            ${item.expected_row_count !== null ? `<span class="pill">rows:${escapeHtml(item.expected_row_count)}</span>` : ""}
          </div>
          ${item.expected_notes ? `<p><strong>备注：</strong>${escapeHtml(item.expected_notes)}</p>` : ""}
        </article>
      `,
    )
    .join("");
}

async function loadGoldenQuestions() {
  const response = await fetch("/api/chatbi/golden-questions?workspace_id=demo&status=ACTIVE&limit=30");
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.detail?.message || "黄金集加载失败");
  renderGoldenQuestions(data);
}

async function createGoldenQuestion(feedbackId) {
  const response = await fetch(`/api/chatbi/golden-questions/from-feedback/${encodeURIComponent(feedbackId)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ biz_domain: domainInput.value || "auto" }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.detail?.message || "加入黄金集失败");
  goldenEvalSummary.textContent = data.created ? "已加入黄金问题集。" : "该 Badcase 已在黄金问题集中。";
  await loadGoldenQuestions();
}

function renderGoldenEvaluation(data) {
  goldenEvalSummary.className = `rich-item ${data.status === "PASS" ? "step-pass" : data.status === "FAIL" ? "step-error" : "step-clarify"}`;
  goldenEvalSummary.innerHTML = `
    <strong>回归评测：${escapeHtml(data.status)}</strong>
    <div>通过 ${escapeHtml(data.passed)} / ${escapeHtml(data.total)}，通过率 ${escapeHtml(Math.round((data.pass_rate || 0) * 10000) / 100)}%</div>
  `;
  if (data.results?.length) {
    goldenList.innerHTML = data.results
      .map(
        (item) => `
          <article class="badcase-card">
            <header>
              <div>
                <strong>${escapeHtml(item.user_query)}</strong>
                <small>${escapeHtml(item.golden_id)} · ${escapeHtml(item.latency_ms)}ms</small>
              </div>
              <span class="pill ${item.passed ? "step-pass" : "step-error"}">${item.passed ? "PASS" : "FAIL"}</span>
            </header>
            <div class="badcase-meta">
              <span class="pill">${escapeHtml(item.observed_metric_id || "-")}</span>
              <span class="pill">${escapeHtml(item.observed_intent || "-")}</span>
              <span class="pill">${escapeHtml(item.observed_chart_type || "-")}</span>
              <span class="pill">rows:${escapeHtml(item.observed_row_count ?? "-")}</span>
              <span class="pill">reflection:${escapeHtml(item.observed_reflection_status || "-")}</span>
            </div>
            ${item.errors?.length ? `<p><strong>失败原因：</strong>${escapeHtml(item.errors.join("；"))}</p>` : ""}
          </article>
        `,
      )
      .join("");
  }
}

async function evaluateGoldenQuestions() {
  goldenEvaluate.disabled = true;
  goldenEvalSummary.textContent = "回归评测运行中...";
  try {
    const response = await fetch("/api/chatbi/golden-questions/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: "demo", status: "ACTIVE", limit: 30 }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || data.detail?.message || "回归评测失败");
    renderGoldenEvaluation(data);
  } finally {
    goldenEvaluate.disabled = false;
  }
}

function renderResult(data) {
  currentResult = data;
  emptyState.classList.add("hidden");
  result.classList.remove("hidden");
  setOverall(data.status);
  feedbackStatus.textContent = "待提交";
  feedbackStatus.className = "pill";
  feedbackMessage.value = "";
  feedbackExpected.value = "";
  renderPipeline(data.steps || []);
  message.textContent = data.message || "";
  traceBadge.textContent = data.compiled?.query_id || data.trace_id || "";
  debugJson.textContent = JSON.stringify(
    {
      status: data.status,
      request_id: data.request_id,
      trace_id: data.trace_id,
      selected_metric: data.selected_metric,
      dsl: data.dsl,
      compiled: data.compiled
        ? {
            query_id: data.compiled.query_id,
            status: data.compiled.status,
            estimated_cost: data.compiled.estimated_cost,
            lineage: data.compiled.lineage,
          }
        : null,
      reflection: data.reflection,
    },
    null,
    2,
  );

  if (data.status === "CLARIFY" || data.status === "REJECT") {
    renderClarification(data);
    return;
  }

  const interpretation = data.interpretation || {};
  answerTitle.textContent = interpretation.title || "查询结果";
  findings.innerHTML = richItems(interpretation.findings, "暂无发现");
  caveats.innerHTML = richItems(interpretation.caveats || data.profile?.caveats, "暂无额外限制");
  nextActions.innerHTML = `<h4>建议下一步</h4>${richItems(interpretation.next_actions, "暂无建议")}`;
  renderChart(data);
  renderEvidence(data);
  renderTable(data);
}

async function submitFeedback() {
  if (!currentResult) return;
  const message = feedbackMessage.value.trim();
  if (!message) {
    feedbackStatus.textContent = "请填写描述";
    feedbackStatus.className = "pill step-clarify";
    return;
  }

  feedbackSubmit.disabled = true;
  feedbackStatus.textContent = "提交中";
  feedbackStatus.className = "pill";
  try {
    const payload = {
      workspace_id: currentResult.workspace_id || "demo",
      conversation_id: currentResult.conversation_id || "frontend_demo",
      query_id: currentResult.compiled?.query_id || null,
      user_query: currentResult.query || queryInput.value.trim(),
      feedback_type: feedbackType.value,
      severity: feedbackSeverity.value,
      message,
      expected_behavior: feedbackExpected.value.trim(),
      page_context: {
        status: currentResult.status,
        selected_metric: currentResult.selected_metric,
        dsl: currentResult.dsl,
        reflection: currentResult.reflection,
        trace_id: currentResult.trace_id,
      },
    };
    const response = await fetch("/api/chatbi/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || data.detail?.message || "反馈提交失败");
    feedbackStatus.textContent = data.regression_candidate ? "已进入候选" : "已记录";
    feedbackStatus.className = "pill step-pass";
    feedbackMessage.value = "";
    feedbackExpected.value = "";
    await loadBadcases();
  } catch (error) {
    feedbackStatus.textContent = "提交失败";
    feedbackStatus.className = "pill step-error";
    feedbackExpected.value = error.message;
  } finally {
    feedbackSubmit.disabled = false;
  }
}

async function runAsk() {
  const query = queryInput.value.trim();
  if (!query) return;

  switchView("workspace");
  const conversation = activeConversation();
  conversation.messages.push({ role: "user", text: query, createdAt: Date.now() });
  conversation.updatedAt = Date.now();
  if (conversation.messages.filter((item) => item.role === "user").length === 1) {
    conversation.title = query.length > 18 ? `${query.slice(0, 18)}…` : query;
  }
  chatThread.querySelector("#empty-state")?.remove();
  chatThread.insertAdjacentHTML("beforeend", userMessageMarkup(query));
  chatThread.insertAdjacentHTML("beforeend", loadingMessageMarkup());
  chatThread.scrollTop = chatThread.scrollHeight;
  conversationTitle.textContent = conversation.title;
  conversationTurnCount.textContent = `${conversation.messages.filter((item) => item.role === "user").length} 轮对话`;
  renderConversationList();
  persistConversations();
  submitBtn.disabled = true;
  submitBtn.textContent = "…";
  setOverall("RUNNING");
  renderPipeline([{ label: "请求已提交", status: "PASS", detail: "正在等待服务端返回完整链路。" }]);

  try {
    const response = await fetch("/api/chatbi/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        biz_domain: domainInput.value,
        workspace_id: "demo",
        conversation_id: activeConversationId,
        timezone: "Asia/Shanghai",
      }),
    });
    const responseText = await response.text();
    let data;
    try {
      data = JSON.parse(responseText);
    } catch {
      throw new Error(response.ok ? "服务返回格式异常，请稍后重试" : "问数服务暂时不可用，请稍后重试");
    }
    if (!response.ok) throw new Error(data.message || data.detail?.message || "请求失败");
    renderResult(data);
    updateContextPanels(data);
    const html = data.status === "CLARIFY" || data.status === "REJECT" ? clarificationMessageMarkup(data) : interactiveResultMarkup(data);
    chatThread.querySelector("[data-loading-message]")?.remove();
    chatThread.insertAdjacentHTML("beforeend", html);
    conversation.messages.push({ role: "assistant", html, data, createdAt: Date.now() });
    conversation.updatedAt = Date.now();
    persistConversations();
    renderConversationList();
    chatThread.scrollTop = chatThread.scrollHeight;
    queryInput.value = "";
  } catch (error) {
    setOverall("ERROR");
    chatThread.querySelector("[data-loading-message]")?.remove();
    const errorHtml = `<article class="chat-message assistant"><span class="chat-avatar">AI</span><div class="message-content"><p class="assistant-copy">运行失败：${escapeHtml(error.message)}</p></div></article>`;
    chatThread.insertAdjacentHTML("beforeend", errorHtml);
    conversation.messages.push({ role: "assistant", html: errorHtml, createdAt: Date.now() });
    persistConversations();
    renderPipeline([{ label: "前端请求", status: "ERROR", detail: error.message }]);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "↑";
  }
}

viewButtons.forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  runAsk();
});

queryInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    runAsk();
  }
});

newConversationButton.addEventListener("click", () => {
  const conversation = createConversation();
  conversations.unshift(conversation);
  activeConversationId = conversation.id;
  currentResult = null;
  setOverall("IDLE");
  pipeline.innerHTML = "<li>提交问题后展示完整链路。</li>";
  contextMemory.innerHTML = "<p>完成第一轮分析后显示继承条件。</p>";
  evidenceInspector.innerHTML = '<div class="evidence-item">暂无 Evidence。</div>';
  evidenceCount.textContent = "0 条";
  queryInput.value = "";
  persistConversations();
  renderConversationList();
  renderActiveConversation();
  queryInput.focus();
});

conversationList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-conversation-id]");
  if (!button) return;
  activeConversationId = button.dataset.conversationId;
  persistConversations();
  renderConversationList();
  renderActiveConversation();
});

function handleConversationAction(event) {
  const example = event.target.closest("[data-example]");
  if (example) {
    queryInput.value = example.dataset.example;
    runAsk();
    return;
  }
  const followup = event.target.closest("[data-followup-query]");
  if (followup) {
    queryInput.value = followup.dataset.followupQuery;
    runAsk();
    return;
  }
  const viewButton = event.target.closest("[data-result-view]");
  if (viewButton) {
    const card = viewButton.closest("[data-result-card]");
    if (!card) return;
    const view = viewButton.dataset.resultView;
    card.querySelector("[data-result-chart]")?.classList.toggle("result-tab-hidden", view !== "chart");
    card.querySelector("[data-result-table]")?.classList.toggle("result-tab-hidden", view !== "table");
    card.querySelectorAll("[data-result-view]").forEach((button) => button.classList.toggle("active", button.dataset.resultView === view));
    return;
  }
  const evidenceButton = event.target.closest("[data-evidence-id]");
  if (evidenceButton) {
    evidenceInspector.querySelectorAll("[data-evidence-id]").forEach((item) => item.classList.toggle("evidence-active", item === evidenceButton));
  }
}

chatThread.addEventListener("click", handleConversationAction);
evidenceInspector.addEventListener("click", handleConversationAction);

feedbackForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitFeedback();
});

metricRefresh.addEventListener("click", () => {
  loadMetricCatalog().catch((error) => {
    metricList.innerHTML = `<div class="rich-item">指标目录加载失败：${escapeHtml(error.message)}</div>`;
  });
});

metricDomainFilter.addEventListener("change", () => {
  loadMetricCatalog().catch((error) => {
    metricList.innerHTML = `<div class="rich-item">指标目录加载失败：${escapeHtml(error.message)}</div>`;
  });
});

metricList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-metric-detail]");
  if (!button) return;
  loadMetricDetail(button.dataset.metricDetail).catch((error) => {
    metricDetail.innerHTML = `<div class="rich-item">指标详情加载失败：${escapeHtml(error.message)}</div>`;
  });
});

metricDetail.addEventListener("click", (event) => {
  const editButton = event.target.closest("button[data-metric-edit]");
  if (editButton) {
    editPublishedMetric(editButton.dataset.metricEdit).catch((error) => {
      metricDetail.insertAdjacentHTML("afterbegin", `<div class="rich-item">创建版本草稿失败：${escapeHtml(error.message)}</div>`);
    });
    return;
  }
  const button = event.target.closest("button[data-metric-example]");
  if (!button) return;
  queryInput.value = button.dataset.metricExample;
  switchView("workspace");
  runAsk();
});

metricAdminNew.addEventListener("click", resetMetricAdminForm);
metricAdminRefresh.addEventListener("click", () => {
  loadMetricDrafts().catch((error) => {
    metricDraftList.innerHTML = `<div class="rich-item">草稿加载失败：${escapeHtml(error.message)}</div>`;
  });
});
metricAdminDomain.addEventListener("change", () => {
  metricAdminModel.dataset.preferred = "";
  renderManagementOptions([]);
});
metricAdminModel.addEventListener("change", () => {
  metricAdminModel.dataset.preferred = metricAdminModel.value;
  renderManagementOptions([]);
});
[metricAdminOperation, metricAdminField, metricAdminDenominator, metricAdminScale].forEach((control) => {
  control.addEventListener("change", updateFormulaPreview);
});
metricAdminOperation.addEventListener("change", () => {
  if (metricAdminOperation.value === "ratio") metricAdminType.value = "ratio";
  if (metricAdminOperation.value === "count_distinct") metricAdminType.value = "count";
});
metricAdminForm.addEventListener("submit", (event) => {
  event.preventDefault();
  saveMetricDraft().catch((error) => {
    metricAdminSave.disabled = false;
    metricAdminMessage.textContent = `保存失败：${error.message}`;
  });
});
metricAdminPublish.addEventListener("click", () => {
  publishMetricDraft().catch((error) => {
    metricAdminPublish.disabled = false;
    metricAdminMessage.textContent = `发布失败：${error.message}`;
  });
});
metricDraftList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-draft-edit]");
  if (!button) return;
  const item = metricDrafts.find((draft) => draft.metric_id === button.dataset.draftEdit);
  if (item) fillMetricAdminForm(item);
});

evaluationRefresh.addEventListener("click", () => {
  loadEvaluationReport().catch((error) => {
    evaluationSummary.innerHTML = `<div class="rich-item">测评报告加载失败：${escapeHtml(error.message)}</div>`;
  });
});

evaluationRefresh.addEventListener("click", () => {
  loadEvaluationTrend().catch((error) => {
    if (evaluationTrend) {
      evaluationTrend.innerHTML = `<div class="rich-item">Evaluation trend failed to load: ${escapeHtml(error.message)}</div>`;
    }
  });
});

badcaseRefresh.addEventListener("click", () => {
  loadBadcases().catch((error) => {
    badcaseList.innerHTML = `<div class="rich-item">加载失败：${escapeHtml(error.message)}</div>`;
  });
});

badcaseFilter.addEventListener("change", () => {
  loadBadcases().catch((error) => {
    badcaseList.innerHTML = `<div class="rich-item">加载失败：${escapeHtml(error.message)}</div>`;
  });
});

badcaseList.addEventListener("click", (event) => {
  const goldenButton = event.target.closest("button[data-golden-action]");
  if (goldenButton && !goldenButton.disabled) {
    const card = goldenButton.closest("[data-feedback-id]");
    const feedbackId = card?.dataset.feedbackId;
    if (!feedbackId) return;
    createGoldenQuestion(feedbackId).catch((error) => {
      goldenEvalSummary.textContent = `加入黄金集失败：${error.message}`;
      goldenEvalSummary.className = "rich-item step-error";
    });
    return;
  }

  const button = event.target.closest("button[data-feedback-action]");
  if (!button || button.disabled) return;
  const card = button.closest("[data-feedback-id]");
  const feedbackId = card?.dataset.feedbackId;
  const nextStatus = button.dataset.feedbackAction;
  if (!feedbackId || !nextStatus) return;
  updateBadcaseStatus(feedbackId, nextStatus).catch((error) => {
    badcaseList.insertAdjacentHTML("afterbegin", `<div class="rich-item">状态更新失败：${escapeHtml(error.message)}</div>`);
  });
});

goldenRefresh.addEventListener("click", () => {
  loadGoldenQuestions().catch((error) => {
    goldenList.innerHTML = `<div class="rich-item">黄金集加载失败：${escapeHtml(error.message)}</div>`;
  });
});

goldenEvaluate.addEventListener("click", () => {
  evaluateGoldenQuestions().catch((error) => {
    goldenEvalSummary.textContent = `回归评测失败：${error.message}`;
    goldenEvalSummary.className = "rich-item step-error";
  });
});

joinRefresh?.addEventListener("click", () => loadJoinGraph().catch((e) => { joinValidation.textContent=e.message; }));
joinScan?.addEventListener("click", () => scanJoinCandidates().catch((e) => { joinValidation.textContent=e.message; }));
joinForm?.addEventListener("submit", (event) => { event.preventDefault(); saveJoinDraft().catch((e) => { joinValidation.textContent=e.message; }); });
joinValidate?.addEventListener("click", () => validateJoinDraft().catch((e) => { joinValidation.textContent=e.message; }));
joinPublish?.addEventListener("click", () => publishJoinDraft().catch((e) => { joinValidation.textContent=e.message; }));
joinCandidates?.addEventListener("click", (event) => {
  const button=event.target.closest("[data-join-candidate]"); if(!button) return;
  const item=JSON.parse(joinCandidates.dataset.items||"[]")[Number(button.dataset.joinCandidate)]; if(!item) return;
  joinId.value=`J_CANDIDATE_${Date.now()}`; joinLeft.value=item.left_entity_id; joinRight.value=item.right_entity_id;
  joinLeftKey.value=item.left_keys.join(","); joinRightKey.value=item.right_keys.join(","); joinValidation.textContent="候选已带入，请确认业务粒度后保存。";
});

loadConversations();
renderConversationList();
renderActiveConversation();
switchView("workspace", { scroll: false });

loadMetricCatalog().catch((error) => {
  metricList.innerHTML = `<div class="rich-item">指标目录加载失败：${escapeHtml(error.message)}</div>`;
});

loadMetricManagementOptions()
  .then(() => {
    resetMetricAdminForm();
    return loadMetricDrafts();
  })
  .catch((error) => {
    metricDraftList.innerHTML = `<div class="rich-item">指标管理加载失败：${escapeHtml(error.message)}</div>`;
  });

loadJoinGraph().catch((error) => { if (joinValidation) joinValidation.textContent = `Join Graph加载失败：${error.message}`; });

loadEvaluationReport().catch((error) => {
  evaluationSummary.innerHTML = `<div class="rich-item">测评报告加载失败：${escapeHtml(error.message)}</div>`;
});

loadEvaluationTrend().catch((error) => {
  if (evaluationTrend) {
    evaluationTrend.innerHTML = `<div class="rich-item">Evaluation trend failed to load: ${escapeHtml(error.message)}</div>`;
  }
});

loadBadcases().catch((error) => {
  badcaseList.innerHTML = `<div class="rich-item">加载失败：${escapeHtml(error.message)}</div>`;
});
loadGoldenQuestions().catch((error) => {
  goldenList.innerHTML = `<div class="rich-item">黄金集加载失败：${escapeHtml(error.message)}</div>`;
});
