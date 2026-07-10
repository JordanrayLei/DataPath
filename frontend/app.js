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

let currentResult = null;

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
  submitBtn.disabled = true;
  submitBtn.textContent = "运行中...";
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
        conversation_id: "frontend_demo",
        timezone: "Asia/Shanghai",
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || data.detail?.message || "请求失败");
    renderResult(data);
  } catch (error) {
    setOverall("ERROR");
    emptyState.classList.add("hidden");
    result.classList.remove("hidden");
    message.textContent = `运行失败：${error.message}`;
    answerTitle.textContent = "运行失败";
    renderPipeline([{ label: "前端请求", status: "ERROR", detail: error.message }]);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "运行分析";
  }
}

viewButtons.forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  runAsk();
});

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
  const button = event.target.closest("button[data-metric-example]");
  if (!button) return;
  queryInput.value = button.dataset.metricExample;
  switchView("workspace");
  runAsk();
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

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = button.dataset.example;
    switchView("workspace");
    runAsk();
  });
});

switchView("workspace", { scroll: false });

loadMetricCatalog().catch((error) => {
  metricList.innerHTML = `<div class="rich-item">指标目录加载失败：${escapeHtml(error.message)}</div>`;
});

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
