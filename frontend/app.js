const form = document.querySelector("#ask-form");
const queryInput = document.querySelector("#query");
const domainInput = document.querySelector("#domain");
const demoRoleInput = document.querySelector("#demo-role");
const sidebarOperatorId = document.querySelector("#sidebar-operator-id");
const submitBtn = document.querySelector("#submit-btn");
const pipeline = document.querySelector("#pipeline");
const overallStatus = document.querySelector("#overall-status");
const emptyState = document.querySelector("#empty-state");
const result = document.querySelector("#result");
const message = document.querySelector("#message");
const answerTitle = document.querySelector("#answer-title");
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
const chatFeedbackPanel = document.querySelector("#chat-feedback-panel");
const chatFeedbackClose = document.querySelector("#chat-feedback-close");
const resultAdoptionStatus = document.querySelector("#result-adoption-status");
const badcaseFilter = document.querySelector("#badcase-filter");
const badcaseRefresh = document.querySelector("#badcase-refresh");
const badcaseCounts = document.querySelector("#badcase-counts");
const badcaseList = document.querySelector("#badcase-list");
const badcaseDetail = document.querySelector("#badcase-detail");
const metricDomainFilter = document.querySelector("#metric-domain-filter");
const metricSearch = document.querySelector("#metric-search");
const metricTypeFilter = document.querySelector("#metric-type-filter");
const metricStatusFilter = document.querySelector("#metric-status-filter");
const metricCatalogNew = document.querySelector("#metric-catalog-new");
const metricRefresh = document.querySelector("#metric-refresh");
const metricCounts = document.querySelector("#metric-counts");
const metricList = document.querySelector("#metric-list");
const metricDetail = document.querySelector("#metric-detail");
const evaluationRefresh = document.querySelector("#evaluation-refresh");
const evaluationSummary = document.querySelector("#evaluation-summary");
const evaluationCases = document.querySelector("#evaluation-cases");
const evaluationGates = document.querySelector("#evaluation-gates");
const evaluationTabs = document.querySelectorAll("[data-evaluation-tab]");
const evaluationDashboardGrid = document.querySelector(".evaluation-dashboard-grid");
const goldenRefresh = document.querySelector("#golden-refresh");
const goldenEvaluate = document.querySelector("#golden-evaluate");
const goldenCounts = document.querySelector("#golden-counts");
const goldenEvalSummary = document.querySelector("#golden-eval-summary");
const goldenList = document.querySelector("#golden-list");
const opsRefresh = document.querySelector("#ops-refresh");
const opsDataNote = document.querySelector("#ops-data-note");
const opsFunnel = document.querySelector("#ops-funnel");
const opsQuality = document.querySelector("#ops-quality");
const opsPerformance = document.querySelector("#ops-performance");
const viewButtons = document.querySelectorAll("[data-view]");
const viewPanels = document.querySelectorAll("[data-view-panel]");
const subtabButtons = document.querySelectorAll("[data-subtab]");
const chatThread = document.querySelector("#chat-thread");
const conversationList = document.querySelector("#conversation-list");
const newConversationButton = document.querySelector("#new-conversation");
const conversationTitle = document.querySelector("#conversation-title");
const conversationTurnCount = document.querySelector("#conversation-turn-count");
const conversationShare = document.querySelector("#conversation-share");
const conversationMore = document.querySelector("#conversation-more");
const conversationMenu = document.querySelector("#conversation-menu");
const conversationActionStatus = document.querySelector("#conversation-action-status");
const contextChips = document.querySelector("#context-chips");
const contextMemory = document.querySelector("#context-memory");
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
const metricSemanticReadinessScore = document.querySelector("#metric-semantic-readiness-score");
const metricSemanticReadinessBar = document.querySelector("#metric-semantic-readiness-bar");
const metricSemanticReadinessDetail = document.querySelector("#metric-semantic-readiness-detail");
const metricAliasConflicts = document.querySelector("#metric-alias-conflicts");
const metricSemanticFamilyInput = document.querySelector("#metric-semantic-family-input");
const metricSemanticFamilyApply = document.querySelector("#metric-semantic-family-apply");
const metricSemanticFamilyResult = document.querySelector("#metric-semantic-family-result");
const scopeExampleDomain = document.querySelector("#scope-example-domain");
const scopeExampleInput = document.querySelector("#scope-example-input");
const scopeExampleCount = document.querySelector("#scope-example-count");
const scopeExampleStatus = document.querySelector("#scope-example-status");
const scopeExampleSave = document.querySelector("#scope-example-save");
const scopeNegativeThreshold = document.querySelector("#scope-negative-threshold");
const scopeMargin = document.querySelector("#scope-margin");
const scopePreviewInput = document.querySelector("#scope-preview-input");
const scopePreviewRun = document.querySelector("#scope-preview-run");
const scopePreviewResult = document.querySelector("#scope-preview-result");
const ambiguityExampleInput = document.querySelector("#ambiguity-example-input");
const ambiguityExampleCount = document.querySelector("#ambiguity-example-count");
const ambiguityExampleStatus = document.querySelector("#ambiguity-example-status");
const ambiguityExampleSave = document.querySelector("#ambiguity-example-save");
const selectionMargin = document.querySelector("#selection-margin");
const ambiguityThreshold = document.querySelector("#ambiguity-threshold");
const ambiguityMargin = document.querySelector("#ambiguity-margin");
const specificityExampleInput = document.querySelector("#specificity-example-input");
const specificityThreshold = document.querySelector("#specificity-threshold");
const specificityMargin = document.querySelector("#specificity-margin");
const metricAdminModel = document.querySelector("#metric-admin-model");
const metricAdminLeftModel = document.querySelector("#metric-admin-left-model");
const metricAdminRightModel = document.querySelector("#metric-admin-right-model");
const metricAdminRightModelWrap = document.querySelector("#metric-admin-right-model-wrap");
const metricAdminOperation = document.querySelector("#metric-admin-operation");
const metricAdminField = document.querySelector("#metric-admin-field");
const metricAdminDenominator = document.querySelector("#metric-admin-denominator");
const metricAdminDenominatorWrap = document.querySelector("#metric-admin-denominator-wrap");
const metricAdminScale = document.querySelector("#metric-admin-scale");
const metricAdminScaleWrap = document.querySelector("#metric-admin-scale-wrap");
const metricFormulaPreview = document.querySelector("#metric-formula-preview");
const metricPreheatStatus = document.querySelector("#metric-preheat-status");
const metricPreheatPreview = document.querySelector("#metric-preheat-preview");
const metricPreheatGenerate = document.querySelector("#metric-preheat-generate");
const metricPreheatApply = document.querySelector("#metric-preheat-apply");
const metricAdminDimensions = document.querySelector("#metric-admin-dimensions");
const metricAdminMessage = document.querySelector("#metric-admin-message");
const metricAdminSave = document.querySelector("#metric-admin-save");
const metricAdminPublish = document.querySelector("#metric-admin-publish");
const metricClosurePanel = document.querySelector("#metric-closure-panel");
const metricClosureStatus = document.querySelector("#metric-closure-status");
const metricClosureContext = document.querySelector("#metric-closure-context");
const metricClosureExpectedStatus = document.querySelector("#metric-closure-expected-status");
const metricClosureExpectedMetric = document.querySelector("#metric-closure-expected-metric");
const metricClosureExpectedIntent = document.querySelector("#metric-closure-expected-intent");
const metricClosureExpectedDimension = document.querySelector("#metric-closure-expected-dimension");
const metricClosureExpectedChart = document.querySelector("#metric-closure-expected-chart");
const metricClosureExpectedRows = document.querySelector("#metric-closure-expected-rows");
const metricClosureNotes = document.querySelector("#metric-closure-notes");
const metricClosureResult = document.querySelector("#metric-closure-result");
const metricClosureRun = document.querySelector("#metric-closure-run");
const joinRefresh = document.querySelector("#join-refresh");
const joinScan = document.querySelector("#join-scan");
const joinSummary = document.querySelector("#join-summary");
const joinGraphCanvas = document.querySelector("#join-graph-canvas");
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
const sourceForm = document.querySelector("#source-form");
const sourceId = document.querySelector("#source-id");
const sourceName = document.querySelector("#source-name");
const sourceHost = document.querySelector("#source-host");
const sourcePort = document.querySelector("#source-port");
const sourceDatabase = document.querySelector("#source-database");
const sourceUsername = document.querySelector("#source-username");
const sourceCredentialEnv = document.querySelector("#source-credential-env");
const sourceStatus = document.querySelector("#source-status");
const sourceConnectionTitle = document.querySelector("#source-connection-title");
const sourceStepButtons = document.querySelectorAll("[data-source-step]");
const sourceStepPanels = document.querySelectorAll("[data-source-step-panel]");
const sourceScan = document.querySelector("#source-scan");
const sourceScanSummary = document.querySelector("#source-scan-summary");
const sourceScanDatabase = document.querySelector("#source-scan-database");
const sourceDomainId = document.querySelector("#source-domain-id");
const sourceDomainName = document.querySelector("#source-domain-name");
const sourceDomainContext = document.querySelector("#source-domain-context");
const sourceTables = document.querySelector("#source-tables");
const sourceTableDetail = document.querySelector("#source-table-detail");
const sourceDimensionsJson = document.querySelector("#source-dimensions-json");
const sourceDimensionId = document.querySelector("#source-dimension-id");
const sourceDimensionName = document.querySelector("#source-dimension-name");
const sourceDimensionType = document.querySelector("#source-dimension-type");
const sourceDimensionModel = document.querySelector("#source-dimension-model");
const sourceDimensionField = document.querySelector("#source-dimension-field");
const sourceDimensionGrain = document.querySelector("#source-dimension-grain");
const sourceDimensionAdd = document.querySelector("#source-dimension-add");
const sourceDimensionList = document.querySelector("#source-dimension-list");
const sourceMessage = document.querySelector("#source-message");
const sourceConfirm = document.querySelector("#source-confirm");
const sourcePublish = document.querySelector("#source-publish");
const sourcePublishSummary = document.querySelector("#source-publish-summary");
const sourceAssetsRefresh = document.querySelector("#source-assets-refresh");
const sourceAssetSummary = document.querySelector("#source-asset-summary");
const sourceAssetInventory = document.querySelector("#source-asset-inventory");
const schemaImpactCount = document.querySelector("#schema-impact-count");
const schemaImpactSummary = document.querySelector("#schema-impact-summary");
const schemaImpactList = document.querySelector("#schema-impact-list");
const sourceOpenDomains = document.querySelector("#source-open-domains");
const domainNew = document.querySelector("#domain-new");
const domainRefresh = document.querySelector("#domain-refresh");
const domainSearch = document.querySelector("#domain-search");
const domainStatusFilter = document.querySelector("#domain-status-filter");
const domainList = document.querySelector("#domain-list");
const domainEmpty = document.querySelector("#domain-empty");
const domainDetail = document.querySelector("#domain-detail");
const domainDetailStatus = document.querySelector("#domain-detail-status");
const domainDetailName = document.querySelector("#domain-detail-name");
const domainDetailDescription = document.querySelector("#domain-detail-description");
const domainSummary = document.querySelector("#domain-summary");
const domainModelList = document.querySelector("#domain-model-list");
const domainRelationSummary = document.querySelector("#domain-relation-summary");
const domainMetricList = document.querySelector("#domain-metric-list");
const domainAddModel = document.querySelector("#domain-add-model");
const domainCreateMetric = document.querySelector("#domain-create-metric");
const domainOpenJoin = document.querySelector("#domain-open-join");
const domainEdit = document.querySelector("#domain-edit");
const domainDialog = document.querySelector("#domain-dialog");
const domainForm = document.querySelector("#domain-form");
const domainFormTitle = document.querySelector("#domain-form-title");
const domainId = document.querySelector("#domain-id");
const domainName = document.querySelector("#domain-name");
const domainOwner = document.querySelector("#domain-owner");
const domainGoal = document.querySelector("#domain-goal");
const domainDescription = document.querySelector("#domain-description");
const domainFormMessage = document.querySelector("#domain-form-message");
const domainDialogClose = document.querySelector("#domain-dialog-close");
const domainCancel = document.querySelector("#domain-cancel");
const domainReadinessScore = document.querySelector("#domain-readiness-score");
const domainReadinessBar = document.querySelector("#domain-readiness-bar");
const domainReadinessStages = document.querySelector("#domain-readiness-stages");
const domainNextActionText = document.querySelector("#domain-next-action-text");
const domainNextActionButton = document.querySelector("#domain-next-action-button");
const domainBlockerList = document.querySelector("#domain-blocker-list");
const domainAssetsDialog = document.querySelector("#domain-assets-dialog");
const domainAssetsForm = document.querySelector("#domain-assets-form");
const domainAssetsTitle = document.querySelector("#domain-assets-title");
const domainAssetsClose = document.querySelector("#domain-assets-close");
const domainAssetsCancel = document.querySelector("#domain-assets-cancel");
const domainAssetsSearch = document.querySelector("#domain-assets-search");
const domainAssetsCount = document.querySelector("#domain-assets-count");
const domainAssetsList = document.querySelector("#domain-assets-list");
const domainAssetsMessage = document.querySelector("#domain-assets-message");
const domainAssetsSave = document.querySelector("#domain-assets-save");
const domainModelDialog = document.querySelector("#domain-model-dialog");
const domainModelForm = document.querySelector("#domain-model-form");
const domainModelPhysicalTable = document.querySelector("#domain-model-physical-table");
const domainModelAssetSummary = document.querySelector("#domain-model-asset-summary");
const domainModelVersion = document.querySelector("#domain-model-version");
const domainModelName = document.querySelector("#domain-model-name");
const domainModelDescription = document.querySelector("#domain-model-description");
const domainModelEntityType = document.querySelector("#domain-model-entity-type");
const domainModelGrain = document.querySelector("#domain-model-grain");
const domainModelPrimaryKeys = document.querySelector("#domain-model-primary-keys");
const domainModelTimeField = document.querySelector("#domain-model-time-field");
const domainModelFields = document.querySelector("#domain-model-fields");
const domainModelMessage = document.querySelector("#domain-model-message");
const domainModelClose = document.querySelector("#domain-model-close");
const domainModelCancel = document.querySelector("#domain-model-cancel");
const domainModelPublish = document.querySelector("#domain-model-publish");
const metricDomainContext = document.querySelector("#metric-domain-context");
const domainTabButtons = document.querySelectorAll("[data-domain-tab]");
const domainTabPanels = document.querySelectorAll("[data-domain-tab-panel]");

let currentResult = null;
let activeConversationId = "";
let conversations = [];
let metricManagementOptions = null;
let metricCatalogData = null;
let activeMetricCatalogId = "";
let activeMetricDetailData = null;
let activeMetricDetailTab = "definition";
let metricDrafts = [];
let activeMetricDraft = null;
let badcaseItems = [];
let activeMetricClosure = null;
let activePreheatProposal = null;
let activeWarehouseSource = null;
let activeSourceTableName = "";
let activeSourceStep = 1;
let availableSourceStep = 1;
let joinGraph = null;
let activeJoinRelationId = "";
let businessDomains = [];
let activeBusinessDomainId = "";
let activeBusinessDomainTab = "overview";
let physicalTableAssets = [];
let activeDomainTableBindings = [];
let activeDomainModelBindingId = "";

async function fetchWithStartupRetry(url, options = {}, attempts = 3) {
  let lastError = null;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      const response = await fetch(url, options);
      if (response.ok || response.status < 500 || attempt === attempts) return response;
      lastError = new Error(`服务暂时不可用（HTTP ${response.status}）`);
    } catch (error) {
      lastError = error;
      if (attempt === attempts) break;
    }
    await new Promise((resolve) => window.setTimeout(resolve, attempt * 450));
  }
  throw new Error(`本地服务暂时不可用，请确认 127.0.0.1:8000 已启动后重试。${lastError?.message ? ` ${lastError.message}` : ""}`);
}

function joinItem(title, subtitle, status) {
  return `<article class="join-item"><header><strong>${escapeHtml(title)}</strong><span class="pill">${escapeHtml(status)}</span></header><small>${escapeHtml(subtitle)}</small></article>`;
}

function renderJoinGraph(data) {
  joinGraph = data;
  if (!data.relations.some((item) => item.id === activeJoinRelationId)) {
    activeJoinRelationId = data.relations[0]?.id || "";
  }
  joinSummary.innerHTML = [
    [data.models.length, "语义模型"], [data.entities.length, "业务实体"],
    [data.relations.filter((x) => x.status === "PUBLISHED").length, "已发布关系"], [data.drafts.length, "待治理草稿"],
  ].map(([value, label]) => `<div class="rich-item"><strong>${value}</strong><small>${label}</small></div>`).join("");
  renderBusinessDomainDetail();
  const facts = data.entities.filter((item) => item.entity_type === "fact").slice(0, 5);
  const dimensions = data.entities.filter((item) => item.entity_type !== "fact").slice(0, 4);
  const nodes = [...facts, ...dimensions];
  const positions = new Map();
  facts.forEach((item, index) => positions.set(item.id, { x: 24, y: 42 + index * 96 }));
  dimensions.forEach((item, index) => positions.set(item.id, { x: 474, y: 64 + index * 112 }));
  const lines = data.relations
    .filter((item) => positions.has(item.left_entity_id) && positions.has(item.right_entity_id))
    .slice(0, 12)
    .map((item) => {
      const left = positions.get(item.left_entity_id);
      const right = positions.get(item.right_entity_id);
      return `<line class="${item.id === activeJoinRelationId ? "selected" : "published"}" data-join-graph-relation-id="${escapeHtml(item.id)}" x1="${left.x + 176}" y1="${left.y + 31}" x2="${right.x}" y2="${right.y + 31}"><title>${escapeHtml(item.id)} · ${escapeHtml(item.relationship_type)}</title></line>`;
    })
    .join("");
  const draftLines = (data.drafts || [])
    .filter((item) => positions.has(item.definition?.left_entity_id) && positions.has(item.definition?.right_entity_id))
    .slice(0, 4)
    .map((item) => {
      const left = positions.get(item.definition.left_entity_id);
      const right = positions.get(item.definition.right_entity_id);
      return `<line class="draft" x1="${left.x + 176}" y1="${left.y + 31}" x2="${right.x}" y2="${right.y + 31}"></line>`;
    })
    .join("");
  joinGraphCanvas.innerHTML = `
    <svg viewBox="0 0 680 560" aria-label="Join 关系图">
      <defs><marker id="join-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z"></path></marker></defs>
      ${lines}${draftLines}
    </svg>
    ${nodes.map((item) => {
      const position = positions.get(item.id);
      return `<button type="button" class="join-node ${item.entity_type === "fact" ? "fact" : "dimension"}" data-join-entity-id="${escapeHtml(item.id)}" style="left:${position.x / 6.8}%;top:${position.y / 5.6}%">
        <span>${item.entity_type === "fact" ? "▦" : "◇"}</span><strong>${escapeHtml(item.name)}</strong>
      </button>`;
    }).join("")}
  `;
  joinModels.innerHTML = data.models.map((m) => joinItem(m.name, `${m.id} · ${m.table}`, m.status)).join("");
  joinRelations.innerHTML = data.relations.map((r) => `
    <article class="join-item">
      <header><strong>${escapeHtml(r.id)}</strong><button type="button" data-join-relation-id="${escapeHtml(r.id)}">查看详情</button></header>
      <small>${escapeHtml(r.left_entity_id)} → ${escapeHtml(r.right_entity_id)} · ${escapeHtml(r.relationship_type)} · v${escapeHtml(r.version)} · ${escapeHtml(r.status)}</small>
    </article>
  `).join("") || '<div class="rich-item">暂无关系。</div>';
  const options = data.entities.map((e) => `<option value="${escapeHtml(e.id)}">${escapeHtml(e.name)} · ${escapeHtml(e.entity_type)}</option>`).join("");
  joinLeft.innerHTML = options; joinRight.innerHTML = options;
  const activeRelation = data.relations.find((item) => item.id === activeJoinRelationId);
  if (activeRelation) fillJoinRelation(activeRelation);
  else if (data.drafts[0]) fillJoinDraft(data.drafts[0]);
  updateJoinNodeSelection();
}

function updateJoinNodeSelection() {
  joinGraphCanvas?.querySelectorAll("[data-join-entity-id]").forEach((node) => {
    node.classList.toggle("selected", node.dataset.joinEntityId === joinLeft.value || node.dataset.joinEntityId === joinRight.value);
  });
}

function selectJoinEntity(entityId) {
  const relations = (joinGraph?.relations || []).filter(
    (item) => item.left_entity_id === entityId || item.right_entity_id === entityId,
  );
  if (!relations.length) return;
  const relation = relations.find((item) => item.id !== activeJoinRelationId) || relations[0];
  selectJoinRelation(relation.id);
}

function selectJoinRelation(relationId) {
  const relation = joinGraph?.relations.find((item) => item.id === relationId);
  if (!relation) return;
  activeJoinRelationId = relation.id;
  joinGraphCanvas?.querySelectorAll("[data-join-graph-relation-id]").forEach((line) => {
    const isSelected = line.dataset.joinGraphRelationId === relation.id;
    line.classList.toggle("selected", isSelected);
    line.classList.toggle("published", !isSelected);
  });
  fillJoinRelation(relation);
}

function fillJoinRelation(item) {
  joinId.value = item.id;
  joinLeft.value = item.left_entity_id;
  joinRight.value = item.right_entity_id;
  joinLeftKey.value = (item.left_keys || []).join(",");
  joinRightKey.value = (item.right_keys || []).join(",");
  joinCardinality.value = item.relationship_type;
  joinStrategy.value = item.fanout_strategy;
  joinValidate.disabled = true;
  joinPublish.disabled = true;
  joinValidation.textContent = `${item.id} v${item.version} · ${item.status}。已发布关系为只读，不可在此修改。`;
  updateJoinNodeSelection();
}

function fillJoinDraft(item) {
  const d = item.definition; joinId.value = item.relation_id; joinLeft.value = d.left_entity_id;
  joinRight.value = d.right_entity_id; joinLeftKey.value = (d.left_keys || []).join(",");
  joinRightKey.value = (d.right_keys || []).join(","); joinCardinality.value = d.relationship_type;
  joinStrategy.value = d.fanout_strategy; joinValidate.disabled = true;
  joinPublish.disabled = true;
  joinValidation.textContent = item.validation?.validated_at ? `草稿只读 · 覆盖率 ${(item.validation.join_coverage * 100).toFixed(2)}% · 唯一率 ${(item.validation.right_key_unique_rate * 100).toFixed(2)}% · Fanout ${item.validation.fanout_multiplier}x · ${item.validation.risk_level}` : "关系草稿只读 · 尚未执行数据检测";
}

async function loadJoinGraph() { const r = await fetch("/api/chatbi/join-graph?workspace_id=demo"); const d = await r.json(); if (!r.ok) throw new Error(d.message || "Join Graph加载失败"); renderJoinGraph(d); }
async function saveJoinDraft() {
  const id = joinId.value.trim().toUpperCase(); const body = {workspace_id:"demo", left_entity_id:joinLeft.value, right_entity_id:joinRight.value, left_keys:joinLeftKey.value.split(",").map(x=>x.trim()).filter(Boolean), right_keys:joinRightKey.value.split(",").map(x=>x.trim()).filter(Boolean), relationship_type:joinCardinality.value, join_type:"left", fanout_strategy:joinStrategy.value, priority:100};
  const r = await fetch(`/api/chatbi/join-graph/drafts/${encodeURIComponent(id)}`, {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)}); const d=await r.json(); if(!r.ok) throw new Error(d.message||"草稿保存失败"); joinValidation.textContent="草稿已保存，请执行数据检测。"; joinValidate.disabled=false; joinPublish.disabled=true; await loadJoinGraph();
}
async function validateJoinDraft() { const r=await fetch(`/api/chatbi/join-graph/drafts/${encodeURIComponent(joinId.value)}/validate`,{method:"POST"}); const d=await r.json(); if(!r.ok) throw new Error(d.message||"检测失败"); const v=d.validation; joinValidation.textContent=`覆盖率 ${(v.join_coverage*100).toFixed(2)}% · 唯一率 ${(v.right_key_unique_rate*100).toFixed(2)}% · Fanout ${v.fanout_multiplier}x · ${v.risk_level}`; joinPublish.disabled=!v.safe_to_publish; await loadJoinGraph(); }
async function publishJoinDraft() { const r=await fetch(`/api/chatbi/join-graph/drafts/${encodeURIComponent(joinId.value)}/publish`,{method:"POST"}); const d=await r.json(); if(!r.ok) throw new Error(d.message||"发布失败"); joinValidation.textContent=`${d.relation_id} v${d.version} 已发布给 Planner。`; joinPublish.disabled=true; await loadJoinGraph(); }
async function scanJoinCandidates() { const domain=activeBusinessDomainId||"production_benchmark"; const r=await fetch(`/api/chatbi/join-graph/scan?domain=${encodeURIComponent(domain)}`,{method:"POST"}); const d=await r.json(); if(!r.ok) throw new Error(d.message||"扫描失败"); joinCandidates.innerHTML=d.candidates.map((c,i)=>`<article class="join-item"><header><strong>${escapeHtml(c.left_entity_id)} → ${escapeHtml(c.right_entity_id)}</strong><button type="button" data-join-candidate="${i}">查看候选</button></header><small>${escapeHtml(c.left_keys.join(", "))} · 置信度 ${Math.round(c.confidence*100)}% · ${escapeHtml(c.reason)}</small></article>`).join("")||'<div class="rich-item">没有发现新候选。</div>'; joinCandidates.dataset.items=JSON.stringify(d.candidates); }

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
  document.querySelectorAll("[data-view-tabs]").forEach((tabs) => {
    tabs.classList.toggle("view-hidden", tabs.dataset.viewTabs !== viewName);
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

function switchSubpanel(targetName) {
  const groupName = targetName.split("-")[0];
  document.querySelectorAll(`[data-subpanel^="${groupName}-"]`).forEach((panel) => {
    panel.classList.toggle("subpanel-hidden", panel.dataset.subpanel !== targetName);
  });
  document.querySelectorAll(`[data-subtab^="${groupName}-"]`).forEach((button) => {
    const isActive = button.dataset.subtab === targetName;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
}

function switchJoinTab(targetName) {
  const panel = document.querySelector('[data-view-panel="join-graph"]');
  if (!panel) return;
  panel.classList.toggle("join-view-relations", targetName === "relations");
  panel.classList.toggle("join-view-candidates", targetName === "candidates");
  panel.querySelectorAll("[data-join-tab]").forEach((button) => {
    const isActive = button.dataset.joinTab === targetName;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
  const sourceDetails = panel.querySelector(".join-source-details");
  if (sourceDetails && targetName === "relations") sourceDetails.open = true;
  if (targetName === "candidates") {
    panel.querySelector("#join-candidates")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function switchEvaluationTab(targetName) {
  evaluationTabs.forEach((button) => {
    const isActive = button.dataset.evaluationTab === targetName;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
  document.querySelectorAll("[data-evaluation-section]").forEach((section) => {
    const sectionName = section.dataset.evaluationSection;
    const visible = targetName === "overview"
      || (targetName === "cases" && sectionName === "cases")
      || (targetName === "gates" && sectionName === "gates");
    section.classList.toggle("interaction-hidden", !visible);
  });
  evaluationDashboardGrid?.classList.toggle("focused", targetName !== "overview");
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

function renderOperationsSummary(data) {
  const funnel = data.funnel || {};
  const cards = [
    [funnel.submitted, "提交问题"],
    [funnel.clarified, "进入澄清"],
    [funnel.executed, "成功执行"],
    [funnel.reflection_passed, "Reflection 通过"],
    [funnel.feedback_received, "收到反馈"],
    [funnel.adopted ?? "未测量", "结果采用"],
  ];
  opsFunnel.innerHTML = cards
    .map(([value, label]) => `<div class="ops-metric"><strong>${escapeHtml(value)}</strong><small>${escapeHtml(label)}</small></div>`)
    .join("");
  const traffic = Object.entries(data.traffic_counts || {})
    .map(([name, count]) => `${name} ${count}`)
    .join(" · ");
  opsDataNote.textContent = `${data.data_note} 流量切片：${traffic || "暂无"}。保留期 ${data.retention_days} 天。`;
  const statuses = Object.entries(data.quality?.status_counts || {})
    .map(([name, count]) => `${name} ${count}`)
    .join(" · ");
  const governance = data.governance || {};
  opsQuality.innerHTML = [
    `状态分布：${statuses || "暂无数据"}`,
    `执行成功率：${((data.quality?.execution_success_rate || 0) * 100).toFixed(1)}%`,
    `Reflection 通过率：${((data.quality?.reflection_pass_rate || 0) * 100).toFixed(1)}%`,
    `显式采用 ${funnel.adopted || 0} 次 · 人工修正 ${funnel.manually_corrected || 0} 次`,
    `治理闭环：验证 ${governance.closure_validated || 0} 次 · 通过 ${governance.closure_passed || 0} 次 · 发布 ${governance.metric_versions_published || 0} 个指标版本`,
    funnel.adoption_note,
  ].map((item) => `<div class="rich-item">${escapeHtml(item)}</div>`).join("");
  const totalLatency = data.latency_ms?.end_to_end || {};
  const executionLatency = data.latency_ms?.execution || {};
  const usage = data.model_usage || {};
  opsPerformance.innerHTML = [
    `端到端：平均 ${totalLatency.average || 0}ms · P50 ${totalLatency.p50 || 0}ms · P95 ${totalLatency.p95 || 0}ms`,
    `数仓执行：平均 ${executionLatency.average || 0}ms · P95 ${executionLatency.p95 || 0}ms`,
    `模型信号：Embedding ${usage.embedding_used || 0} 次 · Reranker ${usage.reranker_used || 0} 次`,
    `估算扫描行：${formatNumber(usage.estimated_rows_scanned || 0)}；${usage.cost_note}`,
  ].map((item) => `<div class="rich-item">${escapeHtml(item)}</div>`).join("");
}

async function loadOperationsSummary() {
  const response = await fetch("/api/chatbi/operations/summary?workspace_id=demo&window_days=30");
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || "运营指标加载失败");
  renderOperationsSummary(data);
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
      <div class="result-actions"><button type="button" data-result-view="table">查看明细</button><button type="button" data-open-feedback>提交 Bad Case</button><button type="button">导出</button></div>
    </section>
    <p class="assistant-meta">${escapeHtml(data.selected_metric?.metric_id || "")} · ${escapeHtml(data.compiled?.query_id || data.trace_id || "")} · Reflection ${escapeHtml(data.reflection?.status || "-")}</p>
  </div></article>`;
}

function clarificationMessageMarkup(data) {
  const candidates = data.retrieval?.mentions?.flatMap((mention) => mention.candidates || []) || [];
  const originalQuery = data.retrieval?.mentions?.[0]?.text || "";
  const title = data.status === "BLOCKED"
    ? "请求已安全阻断"
    : data.status === "REJECT"
      ? "当前问题超出支持范围"
      : "请选择指标口径";
  const badgeClass = data.status === "CLARIFY" ? "step-clarify" : "step-error";
  const candidateMarkup = data.status === "CLARIFY" && candidates.length
    ? `<div class="suggested-followups">${candidates.slice(0, 3).map((candidate) => `<button type="button" data-followup-query="${escapeHtml(originalQuery)}，指标口径选择${escapeHtml(candidate.display_name)}"><strong>${escapeHtml(candidate.display_name)}</strong> · ${escapeHtml(candidate.unit)} · ${escapeHtml(candidate.business_definition || candidate.metric_id)}<small>候选置信度 ${escapeHtml(Math.round(Number(candidate.probability || 0) * 100))}% · 选择后继续原问题</small></button>`).join("")}</div>`
    : "";
  return `<article class="chat-message assistant"><span class="chat-avatar">AI</span><div class="message-content"><p class="assistant-copy">${escapeHtml(data.message || "当前请求无法继续执行。")}</p><section class="interactive-result"><header class="interactive-result-head"><h3>${escapeHtml(title)}</h3><span class="pill ${badgeClass}">${escapeHtml(data.status)}</span></header>${candidateMarkup}</section><p class="assistant-meta">${escapeHtml(data.trace_id || "")} · 未编译 · 未执行</p></div></article>`;
}

function renderActiveConversation() {
  const conversation = activeConversation();
  conversationTitle.textContent = conversation.title;
  const turns = conversation.messages.filter((item) => item.role === "user").length;
  conversationTurnCount.textContent = `${turns} 轮对话`;
  if (!conversation.messages.length) {
    chatThread.innerHTML = `<section id="empty-state" class="chat-empty"><span class="empty-icon">AI</span><h3>从一个业务问题开始</h3><p>我会记住本次会话中的指标、时间、维度和筛选条件。</p><div class="empty-examples"><button type="button" data-example="2024年每月订单量趋势">订单量趋势</button><button type="button" data-example="2024年各区域支付实收金额排名">区域实收排名</button><button type="button" data-example="2024年退款后净收入">跨事实净收入</button></div></section>`;
    contextChips.innerHTML = "<span>新会话 · 暂无继承条件</span>";
    return;
  }
  chatThread.innerHTML = conversation.messages.map((item) => item.role === "user" ? userMessageMarkup(item.text) : sanitizeStoredResultMarkup(item.html)).join("");
  const lastAssistant = [...conversation.messages].reverse().find((item) => item.role === "assistant" && item.data);
  if (lastAssistant) {
    renderResult(lastAssistant.data);
    updateContextPanels(lastAssistant.data);
  }
  chatThread.scrollTop = chatThread.scrollHeight;
}

function sanitizeStoredResultMarkup(markup = "") {
  const template = document.createElement("template");
  template.innerHTML = markup;
  template.content.querySelectorAll("[data-followup-query]").forEach((button) => {
    const label = button.textContent.trim();
    if (["地区", "渠道", "最近 3 个月"].includes(label)) button.remove();
  });
  template.content.querySelectorAll(".result-actions button").forEach((button) => {
    if (button.textContent.trim() === "固定到看板") button.remove();
  });
  return template.innerHTML;
}

function renderClarification(data) {
  const candidates = data.retrieval?.mentions?.flatMap((mention) => mention.candidates || []) || [];
  const isClarify = data.status === "CLARIFY";
  answerTitle.textContent = data.status === "BLOCKED"
    ? "请求已安全阻断"
    : data.status === "REJECT"
      ? "当前问题超出支持范围"
      : "需要先确认指标口径";
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
  caveats.innerHTML = `<div class="rich-item">${isClarify ? "当前版本先安全停止，不在口径不清时执行查询。" : "该请求没有进入 SQL 编译和数据执行。"}</div>`;
  nextActions.innerHTML = `<div class="rich-item">${isClarify ? "请选择候选指标，或把问题改成包含明确指标的表达。" : "请调整为当前数据域支持的只读分析问题。"}</div>`;
  chart.innerHTML = `<div class="empty-state"><p>${isClarify ? "澄清后才会生成图表。" : "请求已停止，不生成图表。"}</p></div>`;
  chartTitle.textContent = isClarify ? "指标候选" : "未执行";
  chartType.textContent = data.status;
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
  metricCatalogData = data;
  renderBusinessDomainDetail();
  const counts = data.domain_counts || {};
  metricCounts.innerHTML = Object.entries(counts)
    .map(([domain, count]) => `<span class="pill">${escapeHtml(domain)}: ${escapeHtml(count)}</span>`)
    .join("");

  const keyword = metricSearch?.value.trim().toLowerCase() || "";
  const type = metricTypeFilter?.value || "ALL";
  const status = metricStatusFilter?.value || "ALL";
  const items = (data.items || []).filter((item) => {
    const searchable = [item.name, item.metric_id, item.description, ...(item.aliases || [])].join(" ").toLowerCase();
    return (!keyword || searchable.includes(keyword))
      && (type === "ALL" || item.metric_type === type)
      && (status === "ALL" || (item.status || "PUBLISHED") === status);
  });

  if (!items.length) {
    metricList.innerHTML = `<div class="rich-item">当前筛选下暂无指标。</div>`;
    return;
  }

  metricList.innerHTML = `
    <div class="metric-table-head" aria-hidden="true">
      <span>指标名称</span><span>类型 / 单位</span><span>状态</span><span>版本</span><span>Owner</span>
    </div>
    ${items
    .map(
      (item) => `
        <article class="metric-table-row ${item.metric_id === activeMetricCatalogId ? "selected" : ""} ${item.read_only ? "governance-impacted" : ""}" data-metric-id="${escapeHtml(item.metric_id)}">
          <button class="metric-name-cell" type="button" data-metric-detail="${escapeHtml(item.metric_id)}">
            <strong>${escapeHtml(item.name)}</strong>
            <small>${escapeHtml(item.metric_id)}</small>
          </button>
          <span>${escapeHtml(item.metric_type)} / ${escapeHtml(item.unit)}</span>
          <span class="metric-published ${governanceStatusClass(item.status)}"><i></i>${escapeHtml(item.status || "PUBLISHED")}</span>
          <span>v${escapeHtml(item.latest_version)}</span>
          <span>${escapeHtml(item.owner)}</span>
        </article>
      `,
    )
    .join("")}
  `;
}

function renderMetricDetail(data) {
  const item = data.metric;
  activeMetricDetailData = data;
  activeMetricCatalogId = item.metric_id;
  if (metricCatalogData) renderMetricCatalog(metricCatalogData);
  const tabButton = (name, label) => `<button type="button" role="tab" aria-selected="${activeMetricDetailTab === name}" class="${activeMetricDetailTab === name ? "active" : ""}" data-metric-detail-tab="${name}">${label}</button>`;
  const panelClass = (name) => `metric-detail-panel ${activeMetricDetailTab === name ? "" : "interaction-hidden"}`;
  const dimensions = (item.dimensions || []).map((dimension) => `
    <article class="metric-asset-row">
      <div><strong>${escapeHtml(dimension.name)}</strong><small>${escapeHtml(dimension.dimension_id)}</small></div>
      <span class="pill">${escapeHtml(dimension.dimension_type)}</span>
      <small>${escapeHtml((dimension.allowed_operators || []).join(" · "))}</small>
    </article>
  `).join("") || '<div class="rich-item">该指标暂无可用维度。</div>';
  const aliases = (item.aliases || []).map((alias) => `<span class="semantic-chip">${escapeHtml(alias)}</span>`).join("") || "<small>暂无别名</small>";
  const examples = (item.example_questions || item.positive_examples || []).map((question) => `<button type="button" data-metric-example="${escapeHtml(question)}">${escapeHtml(question)}</button>`).join("") || "<small>暂无示例问法</small>";
  const versions = (data.versions || []).map((version) => `
    <article class="metric-version-row">
      <strong>v${escapeHtml(version.version)}</strong>
      <span class="pill step-pass">${escapeHtml(version.status)}</span>
      <span>${escapeHtml(version.formula_text)}</span>
      <small>${escapeHtml(new Date(version.published_at).toLocaleString("zh-CN"))}</small>
    </article>
  `).join("") || '<div class="rich-item">暂无发布记录。</div>';
  const blockers = (item.governance_blockers || []).map(
    (blocker) => `<li>${escapeHtml(blocker)}</li>`,
  ).join("");
  const governanceWarning = item.read_only
    ? `<div class="metric-governance-warning">
        <strong>该指标当前只读，禁止创建版本或发布</strong>
        <p>业务域：${escapeHtml(item.business_domain_status)} · 语义模型：${escapeHtml(item.semantic_model_status)} · 指标：${escapeHtml(item.status)}</p>
        ${blockers ? `<ul>${blockers}</ul>` : ""}
      </div>`
    : "";
  metricDetail.innerHTML = `
    <article class="metric-detail-card">
      <header class="metric-detail-header">
        <div>
          <div class="metric-title-line"><strong>${escapeHtml(item.name)}</strong><span class="pill ${governanceStatusClass(item.status)}">${escapeHtml(item.status)}</span><span class="pill">v${escapeHtml(item.latest_version)}</span></div>
          <small>${escapeHtml(item.metric_id)}</small>
          <small>Owner：${escapeHtml(item.owner)}</small>
        </div>
        ${item.read_only ? '<button type="button" disabled>异常治理中</button>' : `<button type="button" data-metric-edit="${escapeHtml(item.metric_id)}">创建下一版本</button>`}
      </header>
      ${governanceWarning}
      <div class="metric-detail-tabs" role="tablist" aria-label="指标详情视图">
        ${tabButton("definition", "业务定义")}
        ${tabButton("calculation", "计算口径")}
        ${tabButton("dimensions", "可用维度")}
        ${tabButton("semantics", "语义与别名")}
        ${tabButton("versions", "版本记录")}
      </div>
      <section class="${panelClass("definition")}" data-metric-detail-panel="definition">
        <h4>业务定义</h4>
        <p>${escapeHtml(item.description)}</p>
        <div class="metric-warning">指标口径需在聚合后参与关联计算，不在明细层级直接相除或相减。</div>
        <h4>业务口径</h4>
        <p>${escapeHtml(item.description)}</p>
        <h4>血缘关系</h4>
        <div class="metric-lineage">
          <span>原始数据</span><b>›</b><span>${escapeHtml(item.semantic_model.name)}</span><b>›</b><span>指标</span><b>›</b><strong>${escapeHtml(item.name)}</strong>
        </div>
      </section>
      <section class="${panelClass("calculation")}" data-metric-detail-panel="calculation">
        <h4>计算公式</h4>
        <div class="formula metric-formula">${escapeHtml(item.formula_text)}</div>
        <h4>聚合与关联策略</h4>
        <div class="metric-calculation-grid">
          <div><small>语义模型</small><strong>${escapeHtml(item.semantic_model.name)}</strong></div>
          <div><small>默认时间字段</small><strong>${escapeHtml(item.semantic_model.default_time_field)}</strong></div>
          <div><small>Fanout 策略</small><strong>${escapeHtml(item.lineage?.fanout_strategy || "single_model")}</strong></div>
          <div><small>版本状态</small><strong>${escapeHtml(data.version_status)}</strong></div>
        </div>
        <details class="metric-expression"><summary>查看表达式 JSON</summary><pre>${escapeHtml(JSON.stringify(data.expression || {}, null, 2))}</pre></details>
      </section>
      <section class="${panelClass("dimensions")}" data-metric-detail-panel="dimensions">
        <h4>可用分析维度</h4>
        <p>以下维度已经通过语义模型映射，可用于筛选、分组或时间聚合。</p>
        <div class="metric-asset-list">${dimensions}</div>
      </section>
      <section class="${panelClass("semantics")}" data-metric-detail-panel="semantics">
        <h4>业务别名</h4>
        <div class="semantic-chip-list">${aliases}</div>
        <h4>示例问法</h4>
        <div class="metric-example-list">${examples}</div>
        <h4>语义完整度</h4>
        <div class="admin-message">${escapeHtml(item.semantic_readiness?.score ?? "-")} / 100 · ${(item.alias_conflicts || []).length ? `${escapeHtml(item.alias_conflicts.length)} 个别名冲突待处理` : "未发现别名冲突"}</div>
      </section>
      <section class="${panelClass("versions")}" data-metric-detail-panel="versions">
        <h4>发布版本</h4>
        <div class="metric-version-list">${versions}</div>
      </section>
      <footer class="metric-detail-meta">
        <div><small>业务域</small><strong>${escapeHtml(item.business_domain_name)}</strong></div>
        <div><small>类型 / 单位</small><strong>${escapeHtml(item.metric_type)} / ${escapeHtml(item.unit)}</strong></div>
        <div><small>创建人</small><strong>${escapeHtml(item.owner)}</strong></div>
        <div><small>物理表</small><strong>${escapeHtml(item.semantic_model.physical_table)}</strong></div>
      </footer>
    </article>
  `;
}

async function loadMetricCatalog() {
  const domain = metricDomainFilter.value;
  const response = await fetchWithStartupRetry(`/api/chatbi/metrics/catalog?workspace_id=demo&domain=${encodeURIComponent(domain)}&limit=50&visibility=governance`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.detail?.message || "指标目录加载失败");
  renderMetricCatalog(data);
  if (data.items?.length) {
    await loadMetricDetail(data.items[0].metric_id);
  }
}

async function loadMetricDetail(metricId) {
  if (metricId !== activeMetricCatalogId) activeMetricDetailTab = "definition";
  const response = await fetch(`/api/chatbi/metrics/catalog/${encodeURIComponent(metricId)}?workspace_id=demo&visibility=governance`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.detail?.message || "指标详情加载失败");
  renderMetricDetail(data);
  return data;
}

function expressionFromForm() {
  const operation = metricAdminOperation.value;
  const term = (modelId, field) => ({
    op: "sum",
    field,
    ...(modelId && modelId !== metricAdminModel.value ? { source_model_id: modelId } : {}),
  });
  if (operation === "ratio") {
    return {
      op: "ratio",
      numerator: term(metricAdminLeftModel.value, metricAdminField.value),
      denominator: term(metricAdminRightModel.value, metricAdminDenominator.value),
      scale: Number(metricAdminScale.value),
      zero_policy: "null",
    };
  }
  if (operation === "subtract") {
    return {
      op: "subtract",
      left: term(metricAdminLeftModel.value, metricAdminField.value),
      right: term(metricAdminRightModel.value, metricAdminDenominator.value),
    };
  }
  return {
    op: operation,
    field: metricAdminField.value,
    ...(metricAdminLeftModel.value !== metricAdminModel.value ? { source_model_id: metricAdminLeftModel.value } : {}),
  };
}

function updateFormulaPreview() {
  const operation = metricAdminOperation.value;
  const isRatio = operation === "ratio";
  const isBinary = isRatio || operation === "subtract";
  metricAdminDenominatorWrap.classList.toggle("hidden", !isBinary);
  metricAdminRightModelWrap.classList.toggle("hidden", !isBinary);
  metricAdminScaleWrap.classList.toggle("hidden", !isRatio);
  if (!metricAdminField.value) {
    metricFormulaPreview.textContent = "选择模型和字段后生成公式预览";
    return;
  }
  const left = `${metricAdminLeftModel.value}.${metricAdminField.value}`;
  const right = `${metricAdminRightModel.value}.${metricAdminDenominator.value || "?"}`;
  metricFormulaPreview.textContent = isRatio
    ? `SUM(${left}) / NULLIF(SUM(${right}), 0) × ${metricAdminScale.value} · aggregate_before_join`
    : operation === "subtract"
      ? `SUM(${left}) - SUM(${right}) · aggregate_before_join`
    : operation === "count_distinct"
      ? `COUNT(DISTINCT ${left})`
      : `SUM(${left})`;
}

function selectedDimensionIds() {
  return [...metricAdminDimensions.querySelectorAll("input:checked")].map((item) => item.value);
}

function localSemanticReadiness() {
  const aliases = metricAdminAliases.value.split(/[,，]/).map((item) => item.trim()).filter(Boolean);
  const positives = metricAdminPositiveExamples.value.split(/\n/).map((item) => item.trim()).filter(Boolean);
  const negatives = metricAdminNegativeExamples.value.split(/\n/).map((item) => item.trim()).filter(Boolean);
  const definitionScore = Math.min(20, Math.round(metricAdminDescription.value.trim().length / 40 * 20));
  const score = definitionScore
    + Math.min(25, Math.round(new Set(aliases).size / 5 * 25))
    + Math.min(25, Math.round(new Set(positives).size / 5 * 25))
    + Math.min(20, Math.round(new Set(negatives).size / 3 * 20))
    + (metricAdminOwner.value.trim() ? 10 : 0);
  const gaps = [];
  if (definitionScore < 20) gaps.push("完善至少 40 字的业务定义");
  if (new Set(aliases).size < 5) gaps.push("补足 5 个业务别名");
  if (new Set(positives).size < 5) gaps.push("补足 5 条正向问法");
  if (new Set(negatives).size < 3) gaps.push("补足 3 条相邻指标负例");
  return { score, gaps };
}

function renderSemanticReadiness(serverReadiness = null, conflicts = null) {
  const readiness = serverReadiness || localSemanticReadiness();
  const score = Number(readiness.score || 0);
  metricSemanticReadinessScore.textContent = `${score} / 100`;
  metricSemanticReadinessScore.className = `pill ${score >= 80 ? "step-pass" : score < 50 ? "step-error" : ""}`;
  metricSemanticReadinessBar.style.width = `${Math.max(0, Math.min(100, score))}%`;
  metricSemanticReadinessDetail.textContent = (readiness.gaps || []).length
    ? `待完善：${readiness.gaps.join("；")}`
    : "语义包达到发布建议标准。";
  if (conflicts !== null) {
    metricAliasConflicts.textContent = conflicts.length
      ? `冲突：${conflicts.map((item) => item.message).join("；")}`
      : "未发现与其他已发布指标重复的名称或别名。";
    metricAliasConflicts.className = `admin-message ${conflicts.length ? "step-error" : "step-pass"}`;
  }
}

function appendUniqueLines(control, values) {
  const current = control.value.split(/\n/).map((item) => item.trim()).filter(Boolean);
  control.value = [...new Set([...current, ...values])].join("\n");
}

function applySemanticFamilyInput() {
  const aliases = new Set(metricAdminAliases.value.split(/[,，]/).map((item) => item.trim()).filter(Boolean));
  const positives = [];
  const negatives = [];
  const unrecognized = [];
  metricSemanticFamilyInput.value.split(/\n/).map((item) => item.trim()).filter(Boolean).forEach((line) => {
    const match = line.match(/^(别名|alias|正例|positive|负例|negative)\s*[:：]\s*(.+)$/i);
    if (!match) {
      unrecognized.push(line);
      return;
    }
    const kind = match[1].toLowerCase();
    const values = match[2].split(/[,，；;]/).map((item) => item.trim()).filter(Boolean);
    if (["别名", "alias"].includes(kind)) values.forEach((item) => aliases.add(item));
    if (["正例", "positive"].includes(kind)) positives.push(...values);
    if (["负例", "negative"].includes(kind)) negatives.push(...values);
  });
  metricAdminAliases.value = [...aliases].join(", ");
  appendUniqueLines(metricAdminPositiveExamples, positives);
  appendUniqueLines(metricAdminNegativeExamples, negatives);
  renderSemanticReadiness();
  metricSemanticFamilyResult.textContent = unrecognized.length
    ? `已应用；${unrecognized.length} 行无法识别，请按前缀格式修改。`
    : `已应用 ${aliases.size} 个别名、${positives.length} 条正例、${negatives.length} 条负例。`;
}

function activeBusinessDomain() {
  return businessDomains.find((item) => item.id === activeBusinessDomainId) || null;
}

function governanceStatusClass(status) {
  if (["ACTIVE", "PUBLISHED", "SCANNED", "RESOLVED"].includes(status)) return "step-pass";
  if (["DEGRADED", "IMPACTED", "BLOCKED", "MISSING", "CHANGED", "OPEN"].includes(status)) return "step-error";
  if (["DRAFT", "CONFIRMED", "PENDING"].includes(status)) return "step-clarify";
  return "";
}

function renderSourceDomainOptions(preferredId = sourceDomainId?.value || "") {
  if (!sourceDomainId) return;
  const selectedId = businessDomains.some((item) => item.id === preferredId)
    ? preferredId
    : "";
  sourceDomainId.innerHTML = `
    <option value="">请先选择已创建的业务域</option>
    ${businessDomains.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} · ${escapeHtml(item.id)}</option>`).join("")}
  `;
  sourceDomainId.value = selectedId;
  const domain = businessDomains.find((item) => item.id === selectedId) || null;
  sourceDomainName.value = domain?.name || "";
  if (sourceDomainContext) {
    sourceDomainContext.querySelector("strong").textContent = domain?.name || "尚未选择业务域";
    sourceDomainContext.querySelector("small").textContent = domain
      ? `${domain.business_goal} · Owner：${domain.owner} · 当前已有 ${domain.model_count} 个语义模型`
      : "请先在“业务域”页面创建业务域，再返回这里选择。";
  }
}

function renderBusinessDomainList() {
  if (!domainList) return;
  const keyword = domainSearch?.value.trim().toLowerCase() || "";
  const status = domainStatusFilter?.value || "ALL";
  const items = businessDomains.filter((item) => {
    const searchable = `${item.name} ${item.id} ${item.owner} ${item.business_goal}`.toLowerCase();
    return (!keyword || searchable.includes(keyword))
      && (status === "ALL" || item.status === status);
  });
  domainList.innerHTML = items.length
    ? items.map((item) => `
        <button type="button" class="domain-list-item ${item.id === activeBusinessDomainId ? "active" : ""} ${governanceStatusClass(item.status) === "step-error" ? "governance-impacted" : ""}" data-domain-id="${escapeHtml(item.id)}">
          <span><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.id)}</small></span>
          <span class="pill ${governanceStatusClass(item.status)}">${escapeHtml(item.status)}</span>
          <small>${escapeHtml(item.readiness_score ?? 0)}% · ${escapeHtml(item.model_count)} 个模型 · ${escapeHtml(item.metric_count)} 个指标 · ${escapeHtml(item.owner)}</small>
        </button>`).join("")
    : `<div class="quality-empty"><strong>${businessDomains.length ? "没有匹配的业务域" : "还没有业务域"}</strong><small>${businessDomains.length ? "请调整搜索或状态筛选。" : "先创建业务域，再选择已扫描的数据表。"}</small></div>`;
}

function renderMetricDomainOptions() {
  if (!metricDomainFilter) return;
  const selected = metricDomainFilter.value || "ALL";
  metricDomainFilter.innerHTML = `
    <option value="ALL">全部业务域</option>
    ${businessDomains.map((item) => `
      <option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}${item.status === "ACTIVE" ? "" : ` · ${escapeHtml(item.status)}`}</option>
    `).join("")}
  `;
  metricDomainFilter.value = [...metricDomainFilter.options].some(
    (option) => option.value === selected,
  ) ? selected : "ALL";
}

function switchBusinessDomainTab(tabName) {
  activeBusinessDomainTab = tabName;
  domainTabButtons.forEach((button) => {
    const active = button.dataset.domainTab === tabName;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  domainTabPanels.forEach((panel) => {
    panel.classList.toggle("interaction-hidden", panel.dataset.domainTabPanel !== tabName);
  });
}

function renderBusinessDomainDetail() {
  if (!domainDetail || !domainEmpty) return;
  const domain = activeBusinessDomain();
  domainEmpty.classList.toggle("hidden", Boolean(domain));
  domainDetail.classList.toggle("hidden", !domain);
  if (!domain) return;
  domainDetailStatus.textContent = domain.status;
  domainDetailStatus.className = `pill ${governanceStatusClass(domain.status)}`;
  domainDetailName.textContent = domain.name;
  domainDetailDescription.textContent = `${domain.business_goal} · Owner：${domain.owner}`;
  domainCreateMetric.disabled = !domain.can_create_metric;
  domainCreateMetric.title = domain.can_create_metric
    ? "在当前业务域创建指标"
    : `尚不能创建指标：${(domain.blockers || []).join("；") || "请先发布语义模型"}`;
  domainSummary.innerHTML = [
    [domain.binding_count ?? domain.source_count, "业务表"],
    [domain.model_count, "语义模型"],
    [domain.dimension_count, "共享维度"],
    [domain.join_count, "安全 Join"],
    [domain.metric_count, "已发布指标"],
  ].map(([value, label]) => `<div><strong>${escapeHtml(value)}</strong><small>${escapeHtml(label)}</small></div>`).join("");

  const models = activeDomainTableBindings;
  domainModelList.innerHTML = models.length
    ? models.map((item) => {
        const referencedMetrics = (metricCatalogData?.items || []).filter(
          (metric) => metric.semantic_model?.semantic_model_id === item.semantic_model_id
            || metric.lineage?.models?.includes(item.semantic_model_id),
        ).length;
        const statusClass = governanceStatusClass(item.status);
        return `
        <article class="${statusClass === "step-error" ? "governance-impacted" : ""}">
          <div><strong>${escapeHtml(item.model_name)}</strong><small>${escapeHtml(item.semantic_model_id)} · ${escapeHtml(item.entity_type)}</small></div>
          <span>${escapeHtml(item.physical_table || "")}<small> · ${escapeHtml((item.exposed_fields || []).length)} 个开放字段 · ${referencedMetrics} 个指标引用</small></span>
          <span class="domain-model-actions">
            <span class="pill ${statusClass}">${escapeHtml(item.status)} · V${escapeHtml(item.version ?? 0)}</span>
            <button class="compact-action" type="button" data-domain-model-id="${escapeHtml(item.id)}">治理模型</button>
          </span>
        </article>`;
      }).join("")
    : '<div class="quality-empty"><strong>尚未选择业务表</strong><small>点击“配置业务表”建立引用，再逐个治理并发布语义模型。</small></div>';

  const relations = (joinGraph?.relations || []).filter((item) => {
    const left = (joinGraph?.entities || []).find((entity) => entity.id === item.left_entity_id);
    return left?.business_domain_id === domain.id || domain.id === "production_benchmark";
  });
  domainRelationSummary.innerHTML = `
    <article><div><strong>${escapeHtml(domain.dimension_count)} 个共享维度</strong><small>用于筛选、分组和时间粒度</small></div><span>已发布</span></article>
    <article><div><strong>${escapeHtml(relations.filter((item) => item.status === "PUBLISHED").length)} 条安全关系</strong><small>跨模型和跨事实查询依赖这些关系</small></div><span>${relations.length ? "可用" : "待治理"}</span></article>`;

  const metrics = (metricCatalogData?.items || []).filter(
    (item) => item.business_domain_id === domain.id,
  );
  domainMetricList.innerHTML = metrics.length
    ? metrics.map((item) => `
        <article>
          <div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.metric_id)}</small></div>
          <span>${escapeHtml(item.metric_type)} / ${escapeHtml(item.unit)}</span>
          <button class="compact-action" type="button" data-domain-metric-id="${escapeHtml(item.metric_id)}">查看指标</button>
        </article>`).join("")
    : '<div class="quality-empty"><strong>尚未发布指标</strong><small>完成模型和关系治理后，在当前业务域创建第一个指标。</small></div>';

  const stageLabels = {
    boundary: "业务边界",
    data: "引用物理表",
    models: "语义模型",
    relations: "维度与关系",
    metrics: "指标发布",
  };
  domainReadinessScore.textContent = `${domain.readiness_score ?? 0}%`;
  domainReadinessBar.style.width = `${domain.readiness_score ?? 0}%`;
  domainReadinessStages.innerHTML = Object.entries(stageLabels).map(([key, label], index) => {
    const stage = domain.stage_status?.[key] || "PENDING";
    return `<div class="${stage.toLowerCase()}"><b>${index + 1}</b><span><strong>${label}</strong><small>${stage}</small></span></div>`;
  }).join("");
  domainNextActionText.textContent = domain.recommended_next_action || "继续完善业务域";
  domainBlockerList.innerHTML = (domain.blockers || []).length
    ? domain.blockers.map((item) => `<div class="domain-blocker"><span>!</span><strong>${escapeHtml(item)}</strong></div>`).join("")
    : '<div class="domain-blocker clear"><span>✓</span><strong>当前没有阻塞创建指标的模型问题</strong></div>';

  if (scopeExampleDomain && [...scopeExampleDomain.options].some((option) => option.value === domain.id)) {
    scopeExampleDomain.value = domain.id;
  }
  switchBusinessDomainTab(activeBusinessDomainTab);
}

async function loadBusinessDomains() {
  if (domainList) domainList.innerHTML = '<div class="rich-item">正在加载业务域...</div>';
  const response = await fetch("/api/chatbi/governance/domains?workspace_id=demo");
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail?.message || data.message || "业务域加载失败");
  businessDomains = data.items || [];
  renderMetricDomainOptions();
  if (!businessDomains.some((item) => item.id === activeBusinessDomainId)) {
    activeBusinessDomainId = businessDomains[0]?.id || "";
  }
  if (activeBusinessDomainId) {
    await loadActiveDomainTableBindings();
  } else {
    activeDomainTableBindings = [];
  }
  renderSourceDomainOptions(sourceDomainId?.value || "");
  renderBusinessDomainList();
  renderBusinessDomainDetail();
}

async function loadActiveDomainTableBindings() {
  if (!activeBusinessDomainId) {
    activeDomainTableBindings = [];
    return;
  }
  const response = await fetch(
    `/api/chatbi/governance/domains/${encodeURIComponent(activeBusinessDomainId)}/table-bindings?workspace_id=demo`,
  );
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail?.message || "业务域模型加载失败");
  activeDomainTableBindings = data.items || [];
}

function openBusinessDomainDialog(domain = null) {
  domainForm.reset();
  domainFormMessage.textContent = "保存业务域后，可在业务域页面继续配置业务表。";
  domainFormTitle.textContent = domain ? "编辑业务域" : "新建业务域";
  domainId.disabled = Boolean(domain);
  domainId.value = domain?.id || "";
  domainName.value = domain?.name || "";
  domainOwner.value = domain?.owner || "data-platform";
  domainGoal.value = domain?.business_goal || "";
  domainDescription.value = domain?.description || "";
  domainDialog.showModal();
}

async function saveBusinessDomain() {
  if (!domainForm.reportValidity()) return;
  const id = domainId.value.trim().toLowerCase();
  domainFormMessage.textContent = "正在保存业务域...";
  const response = await fetch(`/api/chatbi/governance/domains/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_id: "demo",
      name: domainName.value.trim(),
      description: domainDescription.value.trim(),
      owner: domainOwner.value.trim(),
      business_goal: domainGoal.value.trim(),
      operator_id: "metric_admin",
    }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail?.message || data.message || "业务域保存失败");
  activeBusinessDomainId = data.domain.id;
  domainDialog.close();
  await loadBusinessDomains();
}

function domainAssetSuggestion(asset, domain, binding = null) {
  const domainToken = domain.id.toUpperCase().replace(/[^A-Z0-9]+/g, "_");
  const tableToken = asset.table_name
    .replace(/^(fct|dim|bridge|agg)_/i, "")
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "_");
  const fields = (asset.columns || []).map((item) => item.name).filter(Boolean);
  const primaryKeys = fields.filter((name) => name === "id" || name.endsWith("_id")).slice(0, 2);
  const timeField = fields.find((name) => /(^|_)(date|time|timestamp|at|ts)$/i.test(name)) || fields[0] || "";
  const type = asset.table_name.startsWith("dim_")
    ? "dimension"
    : asset.table_name.startsWith("bridge_")
      ? "bridge"
      : asset.table_name.startsWith("agg_")
        ? "aggregate"
        : "fact";
  const modelName = asset.table_name
    .replace(/^(fct|dim|bridge|agg)_/i, "")
    .split("_")
    .filter(Boolean)
    .join(" ");
  return {
    semantic_model_id: binding?.semantic_model_id || `SM_${domainToken}_${tableToken}`.slice(0, 99),
    model_name: binding?.model_name || modelName || asset.table_name,
    description: binding?.description || "",
    entity_id: binding?.entity_id || `E_${domainToken}_${tableToken}`.slice(0, 99),
    entity_name: binding?.entity_name || modelName || asset.table_name,
    entity_type: binding?.entity_type || type,
    grain: binding?.grain || `每行一个 ${modelName || asset.table_name} 业务记录`,
    primary_keys: binding?.primary_keys || (primaryKeys.length ? primaryKeys : fields.slice(0, 1)),
    default_time_field: binding?.default_time_field || timeField,
    exposed_fields: binding?.exposed_fields || fields,
  };
}

function renderDomainPhysicalAssets() {
  const domain = activeBusinessDomain();
  if (!domain) return;
  const query = domainAssetsSearch.value.trim().toLowerCase();
  const bindings = new Map(activeDomainTableBindings.map((item) => [item.physical_asset_id, item]));
  const visibleAssets = physicalTableAssets.filter((asset) => (
    !query
    || `${asset.source_name} ${asset.database_name} ${asset.table_name}`.toLowerCase().includes(query)
  ));
  domainAssetsCount.textContent = `${physicalTableAssets.length} 张物理表 · ${activeDomainTableBindings.length} 个域内模型`;
  domainAssetsList.innerHTML = visibleAssets.length
    ? visibleAssets.map((asset) => {
        const binding = bindings.get(asset.id);
        const definition = domainAssetSuggestion(asset, domain, binding);
        const selected = Boolean(binding);
        const reusedBy = (asset.assigned_domain_ids || []).filter((id) => id !== domain.id);
        const fields = (asset.columns || []).map((item) => item.name).filter(Boolean);
        return `
          <article class="domain-binding-card ${selected ? "selected" : ""}" data-physical-asset-id="${escapeHtml(asset.id)}">
            <header>
              <input type="checkbox" data-binding-enabled ${selected ? "checked" : ""} ${binding?.status === "PUBLISHED" ? "disabled" : ""} aria-label="选择 ${escapeHtml(asset.table_name)}" />
              <span>
                <strong>${escapeHtml(asset.physical_table)}</strong>
                <small>${escapeHtml(definition.model_name)} · ${escapeHtml(definition.entity_type)} · ${fields.length} 个字段</small>
              </span>
              <span class="domain-binding-summary">
                <small>${binding ? `已${binding.status === "PUBLISHED" ? "发布" : "选择"}` : "未选择"}</small>
                <small class="domain-binding-reuse">${reusedBy.length ? `另有 ${reusedBy.length} 个业务域复用` : "尚未被其他域复用"}</small>
              </span>
            </header>
          </article>`;
      }).join("")
    : `<div class="quality-empty"><strong>${physicalTableAssets.length ? "没有匹配的物理表" : "还没有可用的物理资产"}</strong><small>${physicalTableAssets.length ? "请调整搜索条件。" : "请先到“数据资产”连接数据库并执行扫描。"}</small></div>`;
}

async function configureActiveDomainTables() {
  const domain = activeBusinessDomain();
  if (!domain) return;
  domainAssetsTitle.textContent = `为“${domain.name}”配置业务表`;
  domainAssetsMessage.textContent = "正在加载物理资产和当前业务域绑定...";
  domainAssetsSearch.value = "";
  domainAssetsDialog.showModal();
  const [assetsResponse, bindingsResponse] = await Promise.all([
    fetch("/api/chatbi/governance/assets?workspace_id=demo"),
    fetch(`/api/chatbi/governance/domains/${encodeURIComponent(domain.id)}/table-bindings?workspace_id=demo`),
  ]);
  const assetsData = await assetsResponse.json();
  const bindingsData = await bindingsResponse.json();
  if (!assetsResponse.ok) throw new Error(assetsData.detail?.message || "物理资产加载失败");
  if (!bindingsResponse.ok) throw new Error(bindingsData.detail?.message || "业务域绑定加载失败");
  physicalTableAssets = assetsData.items || [];
  activeDomainTableBindings = bindingsData.items || [];
  renderDomainPhysicalAssets();
  domainAssetsMessage.textContent = physicalTableAssets.length
    ? "请选择当前业务域要引用的物理表。保存后在本域“数据模型”中逐表定义业务语义。"
    : "当前没有可选物理表。请先到“数据资产”完成数据库连接和扫描。";
}

async function saveActiveDomainTableBindings() {
  const domain = activeBusinessDomain();
  if (!domain) return;
  const physicalAssetIds = [...domainAssetsList.querySelectorAll(".domain-binding-card")]
    .filter((card) => card.querySelector("[data-binding-enabled]").checked)
    .map((card) => card.dataset.physicalAssetId);
  if (!physicalAssetIds.length) throw new Error("请至少选择一张物理表");
  domainAssetsMessage.textContent = "正在保存业务域与物理表的引用关系...";
  const response = await fetch(`/api/chatbi/governance/domains/${encodeURIComponent(domain.id)}/table-selections`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_id: "demo",
      physical_asset_ids: physicalAssetIds,
      operator_id: "metric_admin",
    }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail?.message || data.message || "业务表选择保存失败");
  activeDomainTableBindings = data.items || [];
  await loadBusinessDomains();
  domainAssetsDialog.close();
  activeBusinessDomainTab = "assets";
  renderBusinessDomainDetail();
}

async function openDomainModelEditor(bindingId) {
  const binding = activeDomainTableBindings.find((item) => item.id === bindingId);
  if (!binding || !domainModelDialog) return;
  activeDomainModelBindingId = binding.id;
  if (!physicalTableAssets.length) {
    const response = await fetch("/api/chatbi/governance/assets?workspace_id=demo");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail?.message || "物理资产加载失败");
    physicalTableAssets = data.items || [];
  }
  const asset = physicalTableAssets.find((item) => item.id === binding.physical_asset_id);
  domainModelPhysicalTable.textContent = `${binding.physical_table} · ${binding.semantic_model_id}`;
  domainModelAssetSummary.innerHTML = `
    <div><small>物理表</small><strong>${escapeHtml(binding.physical_table)}</strong></div>
    <div><small>数据源</small><strong>${escapeHtml(asset?.source_name || binding.source_id)}</strong></div>
    <div><small>扫描字段</small><strong>${escapeHtml((binding.available_fields || []).length)} 个</strong></div>
    <div><small>结构状态</small><strong>${escapeHtml(asset?.status || "ACTIVE")}</strong></div>`;
  domainModelVersion.textContent = `${binding.status} · V${binding.version ?? 0}`;
  domainModelName.value = binding.model_name;
  domainModelDescription.value = binding.description || "";
  domainModelEntityType.value = binding.entity_type;
  domainModelGrain.value = binding.grain;
  domainModelPrimaryKeys.value = (binding.primary_keys || []).join(", ");
  domainModelTimeField.innerHTML = [
    '<option value="">不设置默认分析时间</option>',
    ...(binding.available_fields || []).map(
      (field) => `<option value="${escapeHtml(field)}">${escapeHtml(field)}</option>`,
    ),
  ].join("");
  domainModelTimeField.value = binding.default_time_field || "";
  const selectedFields = new Set(binding.exposed_fields || []);
  domainModelFields.innerHTML = (binding.available_fields || []).map((field) => `
    <label>
      <input type="checkbox" value="${escapeHtml(field)}" ${selectedFields.has(field) ? "checked" : ""} />
      <span>${escapeHtml(field)}</span>
    </label>`).join("");
  domainModelMessage.textContent = "保存草稿不会进入查询链路；发布后生成一个新版本并立即生效。";
  domainModelDialog.showModal();
}

async function saveActiveDomainModel(publish = false) {
  const domain = activeBusinessDomain();
  const binding = activeDomainTableBindings.find(
    (item) => item.id === activeDomainModelBindingId,
  );
  if (!domain || !binding || !domainModelForm.reportValidity()) return;
  const exposedFields = [...domainModelFields.querySelectorAll("input:checked")]
    .map((item) => item.value);
  const primaryKeys = domainModelPrimaryKeys.value
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
  if (!exposedFields.length) throw new Error("请至少开放一个字段");
  if (!primaryKeys.length) throw new Error("请至少填写一个业务唯一键");
  domainModelMessage.textContent = publish ? "正在保存草稿并发布模型..." : "正在保存模型草稿...";
  const response = await fetch(
    `/api/chatbi/governance/domains/${encodeURIComponent(domain.id)}/models/${encodeURIComponent(binding.id)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workspace_id: "demo",
        operator_id: "metric_admin",
        model_name: domainModelName.value.trim(),
        description: domainModelDescription.value.trim(),
        entity_type: domainModelEntityType.value,
        grain: domainModelGrain.value.trim(),
        primary_keys: primaryKeys,
        default_time_field: domainModelTimeField.value,
        exposed_fields: exposedFields,
      }),
    },
  );
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail?.message || "模型草稿保存失败");
  activeDomainTableBindings = data.items || [];
  if (publish) {
    const publishResponse = await fetch(
      `/api/chatbi/governance/domains/${encodeURIComponent(domain.id)}/models/${encodeURIComponent(binding.id)}/publish`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_id: "demo", operator_id: "metric_admin" }),
      },
    );
    const publishData = await publishResponse.json();
    if (!publishResponse.ok) throw new Error(publishData.detail?.message || "语义模型发布失败");
    activeDomainTableBindings = publishData.items || [];
    await Promise.all([loadBusinessDomains(), loadMetricManagementOptions(), loadJoinGraph()]);
  } else {
    await loadBusinessDomains();
  }
  domainModelDialog.close();
  activeBusinessDomainTab = "assets";
  renderBusinessDomainDetail();
}

function createMetricInActiveDomain() {
  const domain = activeBusinessDomain();
  if (!domain) return;
  if (!domain.can_create_metric) {
    activeBusinessDomainTab = "overview";
    renderBusinessDomainDetail();
    return;
  }
  switchView("metric-admin");
  switchSubpanel("metric-governance");
  resetMetricAdminForm();
  metricAdminDomain.value = domain.id;
  renderManagementOptions([]);
}

function renderManagementOptions(selectedDimensions = []) {
  if (!metricManagementOptions) return;
  const requestedDomain = metricAdminDomain.value;
  metricAdminDomain.innerHTML = metricManagementOptions.domains
    .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`)
    .join("");
  if (scopeExampleDomain) {
    const selectedScopeDomain = scopeExampleDomain.value;
    scopeExampleDomain.innerHTML = metricManagementOptions.domains
      .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`)
      .join("");
    if (metricManagementOptions.domains.some((item) => item.id === selectedScopeDomain)) {
      scopeExampleDomain.value = selectedScopeDomain;
    }
  }
  if (metricManagementOptions.domains.some((item) => item.id === requestedDomain)) {
    metricAdminDomain.value = requestedDomain;
  }
  const domain = metricAdminDomain.value || metricManagementOptions.domains[0]?.id;
  const matchingModels = metricManagementOptions.semantic_models.filter((item) => item.business_domain_id === domain);
  metricAdminModel.innerHTML = '<option value="">请选择事实模型</option>' + matchingModels
    .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} · ${escapeHtml(item.physical_table)}</option>`)
    .join("");
  const model = matchingModels.find((item) => item.id === metricAdminModel.dataset.preferred) || null;
  if (model) metricAdminModel.value = model.id;
  const modelOptions = '<option value="">请选择模型</option>' + matchingModels
    .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`)
    .join("");
  metricAdminLeftModel.innerHTML = modelOptions;
  metricAdminRightModel.innerHTML = modelOptions;
  metricAdminLeftModel.value = model?.id || "";
  metricAdminRightModel.value = model?.id || "";
  updateMetricExpressionFields();
  const compatible = metricManagementOptions.dimensions.filter((item) => (item.fields || []).includes(model?.id));
  metricAdminDimensions.innerHTML = compatible
    .map((item) => {
      const checked = selectedDimensions.includes(item.id) || (!selectedDimensions.length && ["D_DATE", "D_MONTH"].includes(item.id));
      return `<label><input type="checkbox" value="${escapeHtml(item.id)}" ${checked ? "checked" : ""} /> <span>${escapeHtml(item.name)}</span><small>${escapeHtml(item.id)}</small></label>`;
    })
    .join("") || '<div class="admin-message">选择语义模型后显示该模型已经治理的可用维度。</div>';
  const domainItem = metricManagementOptions.domains.find((item) => item.id === domain);
  if (metricDomainContext) {
    metricDomainContext.querySelector("strong").textContent = domainItem?.name || "请先选择业务域";
    metricDomainContext.querySelector("small").textContent = model
      ? `当前模型：${model.name}；只能使用该域已发布的维度和安全关系。`
      : "请先选择事实模型，再定义公式和可用维度。";
  }
  updateFormulaPreview();
}

function updateMetricExpressionFields(preferredLeft = "", preferredRight = "") {
  if (!metricManagementOptions) return;
  const modelById = new Map(metricManagementOptions.semantic_models.map((item) => [item.id, item]));
  const leftFields = modelById.get(metricAdminLeftModel.value)?.fields || [];
  const rightFields = modelById.get(metricAdminRightModel.value)?.fields || [];
  metricAdminField.innerHTML = '<option value="">请选择度量字段</option>' + leftFields.map((field) => `<option value="${escapeHtml(field)}">${escapeHtml(field)}</option>`).join("");
  metricAdminDenominator.innerHTML = '<option value="">请选择度量字段</option>' + rightFields.map((field) => `<option value="${escapeHtml(field)}">${escapeHtml(field)}</option>`).join("");
  const safeLeft = leftFields.includes(preferredLeft) ? preferredLeft : "";
  const safeRight = rightFields.includes(preferredRight) ? preferredRight : "";
  metricAdminField.value = safeLeft;
  metricAdminDenominator.value = safeRight;
  updateFormulaPreview();
}

async function loadMetricManagementOptions() {
  const response = await fetch("/api/chatbi/metrics/manage/options?workspace_id=demo");
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || "指标配置加载失败");
  metricManagementOptions = data;
  renderManagementOptions(selectedDimensionIds());
  renderBusinessDomainDetail();
}

function semanticScopeError(data, fallback) {
  return data.detail?.message || data.message || fallback;
}

async function loadSemanticScopeExamples() {
  if (!scopeExampleDomain?.value) return;
  scopeExampleStatus.textContent = "正在加载业务域边界...";
  const response = await fetch(`/api/chatbi/metrics/manage/scope-examples/${encodeURIComponent(scopeExampleDomain.value)}?workspace_id=demo`);
  const data = await response.json();
  if (!response.ok) throw new Error(semanticScopeError(data, "业务域边界加载失败"));
  scopeExampleInput.value = (data.items || [])
    .map((item) => `${item.text}${item.reason ? ` | ${item.reason}` : ""}`)
    .join("\n");
  scopeExampleCount.textContent = `${data.total || 0} 条`;
  scopeNegativeThreshold.value = String(data.negative_threshold);
  scopeMargin.value = String(data.margin);
  scopeExampleStatus.textContent = data.total
    ? `已发布到 ${data.embedding_model}；查询端会将相似域外请求优先 REJECT。`
    : "当前业务域尚未维护边界样本。";
}

function scopeExamplesFromInput() {
  return scopeExampleInput.value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [text, ...reasonParts] = line.split("|");
      return { text: text.trim(), reason: reasonParts.join("|").trim() };
    });
}

function governedExamplesFromText(value) {
  return value.split("\n").map((line) => line.trim()).filter(Boolean).map((line) => {
    const [text, ...reasonParts] = line.split("|");
    return { text: text.trim(), reason: reasonParts.join("|").trim() };
  });
}

async function loadAmbiguityPolicy() {
  if (!scopeExampleDomain?.value) return;
  const response = await fetch(`/api/chatbi/metrics/manage/ambiguity-policy/${encodeURIComponent(scopeExampleDomain.value)}?workspace_id=demo`);
  const data = await response.json();
  if (!response.ok) throw new Error(semanticScopeError(data, "歧义策略加载失败"));
  ambiguityExampleInput.value = (data.items || []).map((item) => `${item.text}${item.reason ? ` | ${item.reason}` : ""}`).join("\n");
  specificityExampleInput.value = (data.specificity_items || []).map((item) => `${item.text}${item.reason ? ` | ${item.reason}` : ""}`).join("\n");
  ambiguityExampleCount.textContent = `${data.total || 0} 条`;
  selectionMargin.value = String(data.selection_margin);
  ambiguityThreshold.value = String(data.ambiguity_threshold);
  ambiguityMargin.value = String(data.ambiguity_margin);
  specificityThreshold.value = String(data.specificity_threshold);
  specificityMargin.value = String(data.specificity_margin);
  ambiguityExampleStatus.textContent = data.total ? "歧义策略已发布。" : "尚未维护必须澄清的语义边界。";
}

async function saveAmbiguityPolicy() {
  const examples = governedExamplesFromText(ambiguityExampleInput.value);
  const specificityExamples = governedExamplesFromText(specificityExampleInput.value);
  if (examples.length < 3) throw new Error("至少填写 3 条歧义示例");
  if (specificityExamples.length < 3) throw new Error("至少填写 3 条明确口径示例");
  ambiguityExampleSave.disabled = true;
  ambiguityExampleStatus.textContent = "正在生成歧义向量并发布决策策略...";
  const response = await fetch(`/api/chatbi/metrics/manage/ambiguity-policy/${encodeURIComponent(scopeExampleDomain.value)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_id: "demo",
      examples,
      specificity_examples: specificityExamples,
      selection_margin: Number(selectionMargin.value),
      ambiguity_threshold: Number(ambiguityThreshold.value),
      ambiguity_margin: Number(ambiguityMargin.value),
      specificity_threshold: Number(specificityThreshold.value),
      specificity_margin: Number(specificityMargin.value),
    }),
  });
  const data = await response.json();
  ambiguityExampleSave.disabled = false;
  if (!response.ok) throw new Error(semanticScopeError(data, "歧义策略发布失败"));
  ambiguityExampleCount.textContent = `${data.total} 条`;
  ambiguityExampleStatus.textContent = `发布成功：歧义 ${data.total} 条、明确证据 ${data.specificity_total} 条；歧义门槛 ${data.ambiguity_threshold}/${data.ambiguity_margin}，明确门槛 ${data.specificity_threshold}/${data.specificity_margin}。`;
}

function scopeGovernancePayload() {
  return {
    workspace_id: "demo",
    examples: scopeExamplesFromInput(),
    negative_threshold: Number(scopeNegativeThreshold.value),
    margin: Number(scopeMargin.value),
  };
}

async function saveSemanticScopeExamples() {
  const examples = scopeExamplesFromInput();
  if (examples.length < 3) throw new Error("至少填写 3 条不同的域外示例");
  scopeExampleSave.disabled = true;
  scopeExampleStatus.textContent = "正在生成本地语义向量并原子发布...";
  const response = await fetch(`/api/chatbi/metrics/manage/scope-examples/${encodeURIComponent(scopeExampleDomain.value)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...scopeGovernancePayload(), examples }),
  });
  const data = await response.json();
  scopeExampleSave.disabled = false;
  if (!response.ok) throw new Error(semanticScopeError(data, "业务域边界发布失败"));
  scopeExampleCount.textContent = `${data.total} 条`;
  scopeExampleStatus.textContent = `发布成功：${data.total} 条边界样本，模型 ${data.embedding_model}，本次处理 ${data.total_tokens} 个文本单位。`;
}

async function previewSemanticScopeExamples() {
  const queries = scopePreviewInput.value.split("\n").map((item) => item.trim()).filter(Boolean);
  if (scopeExamplesFromInput().length < 3) throw new Error("至少填写 3 条不同的域外示例");
  if (!queries.length) throw new Error("至少填写 1 条预览问法");
  scopePreviewRun.disabled = true;
  scopePreviewResult.textContent = "正在计算指标与边界相似度...";
  const response = await fetch(`/api/chatbi/metrics/manage/scope-examples/${encodeURIComponent(scopeExampleDomain.value)}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...scopeGovernancePayload(), queries }),
  });
  const data = await response.json();
  scopePreviewRun.disabled = false;
  if (!response.ok) throw new Error(semanticScopeError(data, "影响预览失败"));
  const rows = (data.items || []).map((item) => `
    <li class="${item.predicted_status === "REJECT" ? "step-error" : "step-pass"}">
      <strong>${escapeHtml(item.predicted_status)}</strong> · ${escapeHtml(item.query)}
      <small>指标 ${escapeHtml(item.top_metric_similarity)} / 边界 ${escapeHtml(item.scope_similarity)} · 最近样本：${escapeHtml(item.nearest_scope_example)}</small>
    </li>`).join("");
  scopePreviewResult.innerHTML = `<strong>预计 REJECT ${data.reject_count}，KEEP ${data.keep_count}</strong><ul>${rows}</ul>`;
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
  activeMetricClosure = null;
  metricClosurePanel.classList.add("hidden");
  metricAdminModel.dataset.preferred = "";
  renderManagementOptions([]);
  renderSemanticReadiness();
  metricAliasConflicts.textContent = "保存草稿后检查跨指标名称与别名冲突。";
  metricAliasConflicts.className = "admin-message";
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
  const leftTerm = expression.op === "ratio" ? expression.numerator : expression.op === "subtract" ? expression.left : expression;
  const rightTerm = expression.op === "ratio" ? expression.denominator : expression.op === "subtract" ? expression.right : null;
  metricAdminLeftModel.value = leftTerm?.source_model_id || item.semantic_model_id;
  metricAdminRightModel.value = rightTerm?.source_model_id || item.semantic_model_id;
  updateMetricExpressionFields(leftTerm?.field || "", rightTerm?.field || "");
  if (expression.op === "ratio") {
    metricAdminField.value = expression.numerator?.field || "";
    metricAdminDenominator.value = expression.denominator?.field || "";
    metricAdminScale.value = String(expression.scale || 1);
  } else if (expression.op === "subtract") {
    metricAdminField.value = expression.left?.field || "";
    metricAdminDenominator.value = expression.right?.field || "";
  } else {
    metricAdminField.value = expression.field || "";
  }
  metricAdminTitle.textContent = item.metric_status === "PUBLISHED" ? `编辑 ${item.name}` : `完善 ${item.name}`;
  metricAdminSubtitle.textContent = `保存后可发布 v${item.next_version}`;
  metricAdminStatus.textContent = `草稿 · 待发布 v${item.next_version}`;
  const isPublishedEdit = item.metric_status === "PUBLISHED";
  const closurePassed = item.validation?.closure_gate?.status === "PASS";
  metricAdminPublish.disabled = isPublishedEdit && !closurePassed;
  if (closurePassed) {
    metricClosureStatus.textContent = "PASS";
    metricClosureStatus.className = "pill step-pass";
  }
  renderSemanticReadiness(item.validation?.semantic_readiness, item.validation?.alias_conflicts || []);
  const proposal = item.validation?.ai_preheat_proposal;
  activePreheatProposal = proposal?.status === "PROPOSED" ? proposal : null;
  metricPreheatStatus.textContent = proposal?.status || "未生成";
  metricPreheatApply.disabled = !activePreheatProposal;
  metricPreheatPreview.textContent = proposal
    ? `来源：${proposal.source}；别名 ${(proposal.aliases || []).length} 条，正例 ${(proposal.positive_examples || []).length} 条，负例 ${(proposal.negative_examples || []).length} 条。请在上方字段审阅后应用。`
    : "先保存指标草稿，再让 AI 生成别名和正反向问法。人工审阅后才可应用。";
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
  const conflicts = data.draft.validation?.alias_conflicts || [];
  renderSemanticReadiness(data.draft.validation?.semantic_readiness, conflicts);
  metricAdminMessage.textContent = conflicts.length
    ? `结构校验通过，但存在 ${conflicts.length} 个语义冲突，闭环发布会被阻止。`
    : `校验通过：${data.draft.formula_text}`;
  await loadMetricDrafts();
  return data.draft;
}

async function generateMetricPreheat() {
  const draft = await saveMetricDraft();
  metricPreheatGenerate.disabled = true;
  metricPreheatStatus.textContent = "生成中";
  metricPreheatPreview.textContent = "AI 正在读取已确认的业务元数据；公式、维度和血缘不会交给 AI 修改。";
  const response = await fetch(`/api/chatbi/metrics/manage/drafts/${encodeURIComponent(draft.metric_id)}/preheat/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ workspace_id: "demo", operator_id: "metric_admin" }),
  });
  const data = await response.json();
  metricPreheatGenerate.disabled = false;
  if (!response.ok) throw new Error(data.detail?.message || data.message || "AI 预热生成失败");
  activePreheatProposal = data.proposal;
  metricAdminAliases.value = (data.proposal.aliases || []).join(", ");
  metricAdminPositiveExamples.value = (data.proposal.positive_examples || []).join("\n");
  metricAdminNegativeExamples.value = (data.proposal.negative_examples || []).join("\n");
  metricPreheatStatus.textContent = "待人工审阅";
  metricPreheatPreview.textContent = `已生成别名 ${(data.proposal.aliases || []).length} 条、正例 ${(data.proposal.positive_examples || []).length} 条、负例 ${(data.proposal.negative_examples || []).length} 条。可直接编辑上方内容，确认后应用。`;
  metricPreheatApply.disabled = false;
  renderSemanticReadiness();
}

async function applyMetricPreheat() {
  if (!activeMetricDraft || !activePreheatProposal) return;
  metricPreheatApply.disabled = true;
  const response = await fetch(`/api/chatbi/metrics/manage/drafts/${encodeURIComponent(activeMetricDraft.metric_id)}/preheat/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_id: "demo",
      operator_id: "metric_admin",
      aliases: metricAdminAliases.value.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
      positive_examples: metricAdminPositiveExamples.value.split("\n").map((item) => item.trim()).filter(Boolean),
      negative_examples: metricAdminNegativeExamples.value.split("\n").map((item) => item.trim()).filter(Boolean),
    }),
  });
  const data = await response.json();
  if (!response.ok) {
    metricPreheatApply.disabled = false;
    throw new Error(data.detail?.message || data.message || "预热草稿应用失败");
  }
  activePreheatProposal = null;
  metricPreheatStatus.textContent = "已人工应用";
  metricPreheatPreview.textContent = "人工审阅结果已写回指标草稿；仍需通过正常发布门禁才会生效。";
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
  let indexMessage = "";
  try {
    const indexResponse = await fetch(`/api/chatbi/metrics/manage/semantic-index/${encodeURIComponent(data.metric_id)}/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: "demo" }),
    });
    const indexData = await indexResponse.json();
    indexMessage = indexResponse.ok
      ? `语义索引已同步 ${indexData.documents} 个文档。`
      : `语义索引同步失败：${indexData.detail?.message || indexData.message || "请重试"}`;
  } catch (error) {
    indexMessage = `语义索引同步失败：${error.message}`;
  }
  metricAdminMessage.textContent = `${data.metric_id} v${data.version} 已发布。${indexMessage}`;
  metricAdminStatus.textContent = `已发布 v${data.version}`;
  activeMetricDraft = null;
  await Promise.all([loadMetricDrafts(), loadMetricCatalog()]);
}

function sourceCompletedStep(status) {
  return {
    DRAFT: 1,
    SCANNED: 2,
    CONFIRMED: 3,
    PUBLISHED: 3,
    DEGRADED: 3,
  }[status] || 0;
}

function setSourceStep(step) {
  const target = Math.max(1, Math.min(Number(step) || 1, availableSourceStep));
  activeSourceStep = target;
  sourceStepPanels.forEach((panel) => {
    panel.classList.toggle("interaction-hidden", Number(panel.dataset.sourceStepPanel) !== target);
  });
  sourceStepButtons.forEach((button) => {
    const stepNumber = Number(button.dataset.sourceStep);
    const isActive = stepNumber === target;
    button.classList.toggle("active", isActive);
    button.classList.toggle("done", stepNumber <= sourceCompletedStep(activeWarehouseSource?.status));
    button.disabled = stepNumber > availableSourceStep;
    button.setAttribute("aria-selected", String(isActive));
    const connector = button.nextElementSibling;
    if (connector?.tagName === "I") {
      connector.classList.toggle("done", stepNumber < sourceCompletedStep(activeWarehouseSource?.status));
    }
  });
}

function updateSourceWizard(source) {
  const completed = sourceCompletedStep(source?.status);
  availableSourceStep = Math.min(3, Math.max(1, completed + 1));
  const target = source?.status === "PUBLISHED" ? 3 : availableSourceStep;
  setSourceStep(target);
}

function renderSchemaImpacts(items) {
  if (!schemaImpactList || !schemaImpactSummary || !schemaImpactCount) return;
  const sourceItems = items.filter(
    (item) => !activeWarehouseSource || item.source_id === activeWarehouseSource.id,
  );
  const openItems = sourceItems.filter((item) => item.status === "OPEN");
  const affectedModels = new Set(
    openItems.flatMap((item) => item.impact?.model_ids || []),
  );
  const affectedRelations = new Set(
    openItems.flatMap((item) => item.impact?.relation_ids || []),
  );
  const affectedMetrics = new Set(
    openItems.flatMap((item) => item.impact?.metric_ids || []),
  );
  schemaImpactCount.textContent = `${openItems.length} 个待处理`;
  schemaImpactCount.className = `pill ${openItems.length ? "step-error" : "step-pass"}`;
  schemaImpactSummary.innerHTML = [
    [openItems.length, "待处理事件"],
    [affectedModels.size, "受影响模型"],
    [affectedRelations.size, "受影响关系"],
    [affectedMetrics.size, "受影响指标"],
  ].map(([value, label]) => `<div class="rich-item"><strong>${escapeHtml(value)}</strong><small>${escapeHtml(label)}</small></div>`).join("");
  const labels = {
    TABLE_REMOVED: "物理表已删除",
    BREAKING_COLUMNS: "字段发生破坏性变化",
    ADDITIVE_COLUMNS: "新增字段",
    TABLE_ADDED: "新增物理表",
    TABLE_RESTORED: "物理表已恢复",
  };
  schemaImpactList.innerHTML = sourceItems.length
    ? sourceItems.map((item) => {
        const removed = item.diff?.removed_columns || [];
        const changed = item.diff?.type_changes || [];
        const added = item.diff?.added_columns || [];
        const domains = item.impact?.domain_ids || [];
        const detail = [
          removed.length ? `删除字段：${removed.join("、")}` : "",
          changed.length ? `类型变化：${changed.map((field) => `${field.field}（${field.old_type} → ${field.new_type}）`).join("、")}` : "",
          added.length ? `新增字段：${added.join("、")}` : "",
        ].filter(Boolean).join("；") || "表级结构状态发生变化";
        return `
          <article class="${item.status === "OPEN" ? "open" : ""}">
            <header>
              <div>
                <strong>${escapeHtml(labels[item.change_type] || item.change_type)}</strong>
                <small>${escapeHtml(item.physical_table)} · ${escapeHtml(item.detected_at)}</small>
              </div>
              <span class="pill ${item.severity === "CRITICAL" || item.severity === "HIGH" ? "step-error" : ""}">${escapeHtml(item.severity)} · ${escapeHtml(item.status)}</span>
            </header>
            <p>${escapeHtml(detail)}</p>
            <div class="schema-impact-resources">
              <span>${escapeHtml((item.impact?.model_ids || []).length)} 模型</span>
              <span>${escapeHtml((item.impact?.relation_ids || []).length)} 关系</span>
              <span>${escapeHtml((item.impact?.dimension_ids || []).length)} 维度</span>
              <span>${escapeHtml((item.impact?.metric_ids || []).length)} 指标</span>
            </div>
            ${item.status === "OPEN" ? `
              <footer>
                <small>${item.change_type === "TABLE_REMOVED"
                  ? "请先恢复物理表或改绑模型；系统已阻断所有受影响查询。"
                  : "请进入业务域修订模型字段并重新发布；仍引用失效字段的指标会继续保持阻断。"}</small>
                ${domains[0] ? `<button type="button" data-impact-domain="${escapeHtml(domains[0])}">前往受影响业务域</button>` : ""}
              </footer>` : ""}
          </article>`;
      }).join("")
    : '<div class="quality-empty"><strong>暂无结构变更</strong><small>后续扫描发现破坏性变化时会显示在这里。</small></div>';
}

async function loadPhysicalAssetInventory() {
  if (!sourceAssetInventory || !sourceAssetSummary) return;
  const [response, impactResponse] = await Promise.all([
    fetchWithStartupRetry("/api/chatbi/governance/assets?workspace_id=demo"),
    fetchWithStartupRetry("/api/chatbi/governance/schema-impacts?workspace_id=demo&event_status=ALL"),
  ]);
  const data = await response.json();
  const impactData = await impactResponse.json();
  if (!response.ok) throw new Error(data.detail?.message || "物理资产加载失败");
  if (!impactResponse.ok) throw new Error(impactData.detail?.message || "结构影响加载失败");
  physicalTableAssets = data.items || [];
  renderSchemaImpacts(impactData.items || []);
  const sourceAssets = physicalTableAssets.filter(
    (item) => !activeWarehouseSource || item.source_id === activeWarehouseSource.id,
  );
  const activeCount = sourceAssets.filter((item) => item.status === "ACTIVE").length;
  const missingCount = sourceAssets.filter((item) => item.status === "MISSING").length;
  const changedCount = sourceAssets.filter((item) => item.status === "CHANGED").length;
  const reusedCount = sourceAssets.filter((item) => (item.assigned_domain_ids || []).length > 0).length;
  sourceAssetSummary.innerHTML = [
    [sourceAssets.length, "物理表"],
    [activeCount, "结构正常"],
    [changedCount, "结构已变化"],
    [missingCount, "扫描缺失"],
    [reusedCount, "已被业务域引用"],
  ].map(([value, label]) => `<div class="rich-item"><strong>${escapeHtml(value)}</strong><small>${escapeHtml(label)}</small></div>`).join("");
  sourceAssetInventory.innerHTML = sourceAssets.length
    ? sourceAssets.map((item) => `
        <article>
          <div>
            <strong>${escapeHtml(item.physical_table)}</strong>
            <small>${escapeHtml(item.source_name)} · ${(item.columns || []).length} 个字段</small>
          </div>
          <span>${(item.assigned_domain_ids || []).length
            ? `已被 ${(item.assigned_domain_ids || []).length} 个业务域引用`
            : "尚未被业务域引用"}</span>
          <span class="asset-card-actions">
            <span class="pill ${item.status === "ACTIVE" ? "step-pass" : "step-error"}">${escapeHtml(item.status)}</span>
            <span class="pill">READ ONLY</span>
          </span>
        </article>`).join("")
    : '<div class="quality-empty"><strong>还没有物理资产</strong><small>返回第 2 步扫描数据库结构。</small></div>';
}

function renderSourceTableDetail(card) {
  if (!card || !sourceTableDetail) return;
  activeSourceTableName = card.dataset.sourceTable;
  sourceTables.querySelectorAll("[data-source-table]").forEach((item) => {
    item.classList.toggle("selected", item === card);
  });
  const valueOf = (className) => card.querySelector(`.${className}`)?.value || "";
  const selectOptions = (className) => [...(card.querySelector(`.${className}`)?.options || [])]
    .map((option) => `<option value="${escapeHtml(option.value)}" ${option.selected ? "selected" : ""}>${escapeHtml(option.textContent)}</option>`)
    .join("");
  const enabled = card.querySelector(".source-enabled")?.checked;
  sourceTableDetail.innerHTML = `
    <div class="source-table-detail-editor" data-source-detail-table="${escapeHtml(activeSourceTableName)}">
      <header>
        <div><h5>${escapeHtml(activeSourceTableName)}</h5><small>人工确认后才会进入发布模型</small></div>
        <label class="source-detail-switch"><input type="checkbox" data-source-detail-enabled ${enabled ? "checked" : ""}/> 启用此表</label>
      </header>
      <div class="metric-form-grid">
        <label>模型 ID<input data-source-field="source-model-id" value="${escapeHtml(valueOf("source-model-id"))}" /></label>
        <label>模型名称<input data-source-field="source-model-name" value="${escapeHtml(valueOf("source-model-name"))}" /></label>
        <label>实体 ID<input data-source-field="source-entity-id" value="${escapeHtml(valueOf("source-entity-id"))}" /></label>
        <label>实体名称<input data-source-field="source-entity-name" value="${escapeHtml(valueOf("source-entity-name"))}" /></label>
        <label>实体类型<select data-source-field="source-entity-type">${selectOptions("source-entity-type")}</select></label>
        <label>粒度<input data-source-field="source-grain" value="${escapeHtml(valueOf("source-grain"))}" /></label>
        <label>业务唯一键（人工确认）<input data-source-field="source-primary-keys" value="${escapeHtml(valueOf("source-primary-keys"))}" /></label>
        <label>默认时间字段<select data-source-field="source-time-field">${selectOptions("source-time-field")}</select></label>
      </div>
    </div>
  `;
}

function parsedSourceDimensions() {
  try {
    const value = JSON.parse(sourceDimensionsJson.value || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

function sourceModelTableCards() {
  return [...sourceTables.querySelectorAll("[data-source-table]")];
}

function updateSourceDimensionFields() {
  const selectedModel = sourceDimensionModel.value;
  const card = sourceModelTableCards().find(
    (item) => item.querySelector(".source-model-id")?.value.trim().toUpperCase() === selectedModel,
  );
  const table = (activeWarehouseSource?.scan_snapshot?.tables || []).find(
    (item) => item.name === card?.dataset.sourceTable,
  );
  sourceDimensionField.innerHTML = (table?.columns || [])
    .map((column) => `<option value="${escapeHtml(column.name)}">${escapeHtml(column.name)} · ${escapeHtml(column.type)}</option>`)
    .join("");
}

function renderSourceDimensionBuilder() {
  if (!sourceDimensionList || !sourceDimensionModel) return;
  const cards = sourceModelTableCards();
  const selectedModel = sourceDimensionModel.value;
  sourceDimensionModel.innerHTML = cards
    .map((card) => {
      const modelId = card.querySelector(".source-model-id")?.value.trim().toUpperCase() || "";
      const modelName = card.querySelector(".source-model-name")?.value.trim() || card.dataset.sourceTable;
      return `<option value="${escapeHtml(modelId)}">${escapeHtml(modelName)} · ${escapeHtml(modelId)}</option>`;
    })
    .join("");
  if ([...sourceDimensionModel.options].some((option) => option.value === selectedModel)) {
    sourceDimensionModel.value = selectedModel;
  }
  updateSourceDimensionFields();
  const dimensions = parsedSourceDimensions();
  sourceDimensionList.innerHTML = dimensions.length
    ? dimensions.map((item) => {
        const mapping = item.mappings?.[0] || {};
        return `<article>
          <div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.dimension_id)} · ${escapeHtml(item.dimension_type)}</small></div>
          <span>${escapeHtml(mapping.semantic_model_id || "")}.${escapeHtml(mapping.field || "")}${mapping.grain ? ` · ${escapeHtml(mapping.grain)}` : ""}</span>
          <button type="button" data-source-dimension-remove="${escapeHtml(item.dimension_id)}">移除</button>
        </article>`;
      }).join("")
    : '<div class="rich-item">尚未配置维度。</div>';
}

function addSourceDimension() {
  const dimensionId = sourceDimensionId.value.trim().toUpperCase();
  const name = sourceDimensionName.value.trim();
  const modelId = sourceDimensionModel.value;
  const field = sourceDimensionField.value;
  if (!/^D_[A-Z0-9_]{2,96}$/.test(dimensionId)) {
    throw new Error("维度 ID 必须以 D_ 开头");
  }
  if (!name || !modelId || !field) throw new Error("请补全维度名称、模型和字段");
  const type = sourceDimensionType.value;
  const timeBased = ["date", "time_grain"].includes(type);
  const mapping = {
    semantic_model_id: modelId,
    field,
    kind: timeBased ? "time_grain" : "field",
    ...(timeBased ? { grain: sourceDimensionGrain.value } : {}),
  };
  const dimensions = parsedSourceDimensions().filter((item) => item.dimension_id !== dimensionId);
  dimensions.push({
    dimension_id: dimensionId,
    name,
    dimension_type: type,
    allowed_operators: timeBased ? ["eq", "between", "gte", "lte"] : ["eq", "neq", "in", "not_in"],
    mappings: [mapping],
  });
  sourceDimensionsJson.value = JSON.stringify(dimensions, null, 2);
  sourceDimensionId.value = "";
  sourceDimensionName.value = "";
  renderSourceDimensionBuilder();
}

function renderWarehouseSource(source) {
  activeWarehouseSource = source;
  sourceStatus.textContent = source.status;
  if (sourceConnectionTitle) sourceConnectionTitle.textContent = source.name;
  if (sourceScanDatabase) sourceScanDatabase.textContent = source.connection?.database || sourceDatabase.value;
  sourcePublish.disabled = source.status !== "CONFIRMED";
  sourcePublish.textContent = source.status === "PUBLISHED" ? "模型已发布" : "确认并发布模型";
  const snapshot = source.scan_snapshot || {};
  sourceScanSummary.textContent = snapshot.table_count
    ? `扫描到 ${snapshot.table_count} 张表、${snapshot.column_count} 个字段；结构指纹 ${snapshot.schema_sha256?.slice(0, 16)}…`
    : "请先扫描数据仓库。";
  const confirmed = new Map((source.governance?.tables || []).map((item) => [item.table, item]));
  sourceDimensionsJson.value = JSON.stringify(source.governance?.dimensions || [], null, 2);
  sourceTables.innerHTML = (snapshot.tables || []).map((item) => {
    const suggestion = item.suggestion || {};
    const saved = confirmed.get(item.name) || {};
    const enabled = saved.enabled ?? false;
    const keys = saved.primary_keys || suggestion.primary_key_suggestions || [];
    const timeField = saved.default_time_field || suggestion.default_time_field_suggestion || "";
    return `<article class="rich-item source-table" data-source-table="${escapeHtml(item.name)}">
      <header><input class="source-enabled" type="checkbox" aria-label="启用 ${escapeHtml(item.name)}" ${enabled ? "checked" : ""}/><button class="source-table-select" type="button" data-source-table-select="${escapeHtml(item.name)}"><strong>${escapeHtml(item.name)}</strong></button><span class="pill">建议：${escapeHtml(suggestion.classification_suggestion || "unknown")}</span></header>
      <small>${item.columns.length} 字段：${escapeHtml(item.columns.slice(0, 10).map((column) => column.name).join(", "))}${item.columns.length > 10 ? "…" : ""}</small>
      <div class="metric-form-grid">
        <label>模型 ID<input class="source-model-id" value="${escapeHtml(saved.semantic_model_id || suggestion.semantic_model_id_suggestion || "")}" /></label>
        <label>模型名称<input class="source-model-name" value="${escapeHtml(saved.model_name || item.name)}" /></label>
        <label>实体 ID<input class="source-entity-id" value="${escapeHtml(saved.entity_id || suggestion.entity_id_suggestion || "")}" /></label>
        <label>实体名称<input class="source-entity-name" value="${escapeHtml(saved.entity_name || item.name)}" /></label>
        <label>实体类型<select class="source-entity-type">${["fact","dimension","bridge","aggregate"].map((type) => `<option value="${type}" ${(saved.entity_type || suggestion.classification_suggestion) === type ? "selected" : ""}>${type}</option>`).join("")}</select></label>
        <label>粒度<input class="source-grain" value="${escapeHtml(saved.grain || `每行代表一条 ${item.name} 记录`)}" /></label>
        <label>业务唯一键（人工确认，逗号分隔）<input class="source-primary-keys" value="${escapeHtml(keys.join(","))}" /></label>
        <label>默认时间字段<select class="source-time-field">${item.columns.map((column) => `<option value="${escapeHtml(column.name)}" ${column.name === timeField ? "selected" : ""}>${escapeHtml(column.name)}</option>`).join("")}</select></label>
      </div>
      <small>系统建议仅供参考；勾选发布即表示人员确认这些业务事实。</small>
    </article>`;
  }).join("") || '<div class="rich-item">尚未扫描。</div>';
  const tableCards = [...sourceTables.querySelectorAll("[data-source-table]")];
  const selectedCard = tableCards.find((card) => card.dataset.sourceTable === activeSourceTableName) || tableCards[0];
  if (selectedCard) {
    renderSourceTableDetail(selectedCard);
  } else if (sourceTableDetail) {
    sourceTableDetail.innerHTML = '<div class="quality-empty"><strong>尚无扫描结果</strong><small>保存连接并扫描结构后，可在这里确认表语义。</small></div>';
  }
  renderSourceDimensionBuilder();
  if (sourcePublishSummary) {
    const governedTables = (source.governance?.tables || []).filter((item) => item.enabled !== false);
    const dimensions = source.governance?.dimensions || [];
    const publishedDomain = businessDomains.find((item) => item.id === source.business_domain_id);
    const modelCount = governedTables.length || (source.status === "PUBLISHED" ? publishedDomain?.model_count || 0 : 0);
    const dimensionCount = dimensions.length || (source.status === "PUBLISHED" ? publishedDomain?.dimension_count || 0 : 0);
    sourcePublishSummary.innerHTML = `
      <div class="rich-item"><small>业务域</small><strong>${escapeHtml(source.governance?.business_domain_name || publishedDomain?.name || source.business_domain_id || "待确认")}</strong></div>
      <div class="rich-item"><small>语义模型</small><strong>${escapeHtml(modelCount)}</strong><span>个已发布模型</span></div>
      <div class="rich-item"><small>共享维度</small><strong>${escapeHtml(dimensionCount)}</strong><span>个已发布维度</span></div>
    `;
  }
  updateSourceWizard(source);
}

async function saveWarehouseSource() {
  const response = await fetch(`/api/chatbi/governance/sources/${encodeURIComponent(sourceId.value.trim())}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_id: "demo",
      name: sourceName.value.trim(),
      kind: "clickhouse",
      operator_id: "metric_admin",
      connection: {
        host: sourceHost.value.trim(),
        port: Number(sourcePort.value),
        database: sourceDatabase.value.trim(),
        username: sourceUsername.value.trim(),
        credential_env: sourceCredentialEnv.value.trim(),
      },
    }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail?.message || "数据源保存失败");
  renderWarehouseSource(data.source);
  sourceMessage.textContent = "连接配置已保存；密码未进入页面请求或治理数据库。";
  return data.source;
}

async function loadWarehouseSources() {
  const response = await fetchWithStartupRetry("/api/chatbi/governance/sources?workspace_id=demo");
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail?.message || "数据源加载失败");
  const source = (data.items || []).find((item) => item.id === sourceId.value.trim()) || data.items?.[0];
  if (source) {
    sourceId.value = source.id;
    sourceName.value = source.name;
    sourceHost.value = source.connection.host || "127.0.0.1";
    sourcePort.value = source.connection.port || 8123;
    sourceDatabase.value = source.connection.database || "";
    sourceUsername.value = source.connection.username || sourceUsername.value || "chatbi_reader";
    sourceCredentialEnv.value = source.connection.credential_env || "CLICKHOUSE_READER_PASSWORD";
    renderSourceDomainOptions(source.business_domain_id || sourceDomainId.value);
    const sourceDomain = businessDomains.find((item) => item.id === source.business_domain_id);
    sourceDomainName.value = source.governance?.business_domain_name || sourceDomain?.name || sourceDomainName.value;
    renderWarehouseSource(source);
    await loadPhysicalAssetInventory();
    sourceMessage.textContent = {
      DRAFT: "连接配置已保存，请继续扫描数据库结构。",
      SCANNED: "结构扫描已完成，请逐表完成人工语义确认。",
      CONFIRMED: "人工语义确认已保存，请核对摘要并发布模型。",
      PUBLISHED: "语义模型已发布；如需修改，可返回已完成步骤重新配置。",
    }[source.status] || "请先保存数据源连接配置。";
  } else {
    activeWarehouseSource = null;
    availableSourceStep = 1;
    setSourceStep(1);
  }
}

async function scanWarehouseSource() {
  if (!sourceForm.reportValidity()) {
    sourceMessage.textContent = "请先补全连接配置中的必填项。";
    return;
  }
  await saveWarehouseSource();
  sourceScan.disabled = true;
  sourceMessage.textContent = "正在只读扫描 system.columns…";
  const response = await fetch(`/api/chatbi/governance/sources/${encodeURIComponent(sourceId.value.trim())}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ workspace_id: "demo", operator_id: "metric_admin" }),
  });
  const data = await response.json();
  sourceScan.disabled = false;
  if (!response.ok) throw new Error(data.detail?.message || "结构扫描失败");
  renderWarehouseSource(data.source);
  sourceMessage.textContent = "扫描完成。请逐表确认，不建议直接接受所有自动建议。";
}

function warehouseGovernanceTables() {
  return [...sourceTables.querySelectorAll("[data-source-table]")].filter((card) => card.querySelector(".source-enabled").checked).map((card) => ({
    table: card.dataset.sourceTable,
    enabled: true,
    semantic_model_id: card.querySelector(".source-model-id").value.trim().toUpperCase(),
    model_name: card.querySelector(".source-model-name").value.trim(),
    entity_id: card.querySelector(".source-entity-id").value.trim().toUpperCase(),
    entity_name: card.querySelector(".source-entity-name").value.trim(),
    entity_type: card.querySelector(".source-entity-type").value,
    grain: card.querySelector(".source-grain").value.trim(),
    primary_keys: card.querySelector(".source-primary-keys").value.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
    default_time_field: card.querySelector(".source-time-field").value,
  }));
}

async function confirmWarehouseGovernance() {
  if (!sourceDomainId.value) throw new Error("请先选择当前物理表要归入的业务域");
  const tables = warehouseGovernanceTables();
  if (!tables.length) throw new Error("至少启用并确认一张表");
  let dimensions;
  try {
    dimensions = JSON.parse(sourceDimensionsJson.value || "[]");
  } catch {
    throw new Error("维度映射不是合法 JSON");
  }
  const response = await fetch(`/api/chatbi/governance/sources/${encodeURIComponent(sourceId.value.trim())}/confirmation`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_id: "demo",
      business_domain_id: sourceDomainId.value.trim(),
      business_domain_name: sourceDomainName.value.trim(),
      business_domain_description: "由指标管理员在数据接入页面确认",
      tables,
      dimensions,
      operator_id: "metric_admin",
    }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail?.message || "人工确认保存失败");
  renderWarehouseSource(data.source);
  sourceMessage.textContent = `已保存 ${tables.length} 张表的人工确认；尚未发布。`;
}

async function publishWarehouseGovernance() {
  const response = await fetch(`/api/chatbi/governance/sources/${encodeURIComponent(sourceId.value.trim())}/publish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ workspace_id: "demo", operator_id: "metric_admin" }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail?.message || "语义模型发布失败");
  renderWarehouseSource(data.source);
  sourceMessage.textContent = "已发布。新模型现在可以在指标与跨事实公式页面中选择。";
  await Promise.all([loadMetricManagementOptions(), loadBusinessDomains()]);
}

async function editPublishedMetric(metricId, badcase = null) {
  if (!metricManagementOptions) await loadMetricManagementOptions();
  const data = activeMetricDetailData?.metric?.metric_id === metricId
    ? activeMetricDetailData
    : await loadMetricDetail(metricId);
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
  if (badcase) {
    activeMetricClosure = { feedback: badcase, metricId };
    const examples = new Set(metricAdminPositiveExamples.value.split(/\n/).map((item) => item.trim()).filter(Boolean));
    examples.add(badcase.user_query);
    metricAdminPositiveExamples.value = [...examples].join("\n");
    metricClosurePanel.classList.remove("hidden");
    metricClosureStatus.textContent = "待验证";
    metricClosureStatus.className = "pill";
    metricClosureContext.innerHTML = `<strong>${escapeHtml(badcase.feedback_id)}</strong><div>问题：${escapeHtml(badcase.user_query)}</div><div>反馈：${escapeHtml(badcase.message)}</div><div>原命中：${escapeHtml(affectedMetricId(badcase) || "未命中指标")}</div>`;
    const catalog = await fetch("/api/chatbi/metrics/catalog?workspace_id=demo&domain=ALL&limit=200").then((response) => response.json());
    metricClosureExpectedMetric.innerHTML = (catalog.items || []).map((metric) => `<option value="${escapeHtml(metric.metric_id)}">${escapeHtml(metric.name)} · ${escapeHtml(metric.metric_id)}</option>`).join("");
    metricClosureExpectedMetric.value = metricId;
    metricClosureExpectedStatus.value = "SUCCESS";
    metricClosureExpectedIntent.value = badcase.snapshot?.dsl?.intent || "";
    metricClosureExpectedDimension.value = badcase.snapshot?.dsl?.dimensions?.[0]?.dimension_id || "";
    metricClosureExpectedChart.value = badcase.page_context?.profile?.chart_spec?.type || "";
    metricClosureExpectedRows.value = "";
    metricClosureNotes.value = badcase.expected_behavior || badcase.message;
    metricClosureResult.textContent = "已把 Bad Case 问法加入正向样本。请检查指标口径并运行闭环验证。";
  }
  switchSubpanel("metric-governance");
  switchView("metric-admin");
  requestAnimationFrame(() => {
    metricAdminForm.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function affectedMetricId(item) {
  const dslMetric = item.snapshot?.dsl?.metrics?.[0]?.metric_id;
  if (dslMetric) return dslMetric;
  const versionIds = Object.keys(item.snapshot?.metric_versions || {});
  if (versionIds.length) return versionIds[0];
  return item.page_context?.selected_metric?.metric_id
    || item.page_context?.retrieval?.mentions?.[0]?.candidates?.[0]?.metric_id
    || null;
}

async function runMetricClosureValidation() {
  if (!activeMetricClosure) throw new Error("请先从 Bad Case 看板进入指标修复");
  metricClosureRun.disabled = true;
  metricClosureResult.textContent = "正在保存草稿并验证当前 Bad Case 与受影响 Golden...";
  const draft = await saveMetricDraft();
  const expectedStatus = metricClosureExpectedStatus.value;
  const payload = {
    workspace_id: "demo",
    feedback_id: activeMetricClosure.feedback.feedback_id,
    biz_domain: draft.business_domain_id,
    expected_status: expectedStatus,
    expected_metric_id: expectedStatus === "SUCCESS" ? metricClosureExpectedMetric.value : null,
    expected_intent: metricClosureExpectedIntent.value.trim() || null,
    expected_dimension_id: metricClosureExpectedDimension.value.trim() || null,
    expected_chart_type: metricClosureExpectedChart.value.trim() || null,
    expected_row_count: metricClosureExpectedRows.value === "" ? null : Number(metricClosureExpectedRows.value),
    expected_reflection_status: expectedStatus === "SUCCESS" ? "PASS" : null,
    expected_notes: metricClosureNotes.value.trim(),
  };
  const response = await fetch(`/api/chatbi/metrics/manage/drafts/${encodeURIComponent(draft.metric_id)}/closure-validation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  metricClosureRun.disabled = false;
  if (!response.ok) throw new Error(data.message || data.detail?.message || "闭环验证失败");
  const checkRows = (data.checks || []).map((check) => `<li class="${check.passed ? "step-pass" : "step-error"}">${check.passed ? "PASS" : "FAIL"} · ${escapeHtml(check.detail)}</li>`).join("");
  metricClosureResult.innerHTML = `<strong>修改后：${escapeHtml(data.candidate.selected_metric_id || "未选择")} · ${escapeHtml(data.candidate.gate_status)}</strong><div>同域 Golden：${escapeHtml(data.regression.passed)}/${escapeHtml(data.regression.total)}</div><ul>${checkRows}</ul>`;
  metricClosureStatus.textContent = data.status;
  metricClosureStatus.className = `pill ${data.status === "PASS" ? "step-pass" : "step-error"}`;
  activeMetricDraft.validation = { ...(activeMetricDraft.validation || {}), closure_gate: { status: data.status } };
  metricAdminPublish.disabled = !data.publish_ready;
  metricAdminMessage.textContent = data.message;
  await Promise.all([loadMetricDrafts(), loadGoldenQuestions()]);
}

function renderEvaluationReport(data) {
  const summary = data.summary || {};
  const passRate = Math.round((summary.pass_rate || 0) * 10000) / 100;
  const failedGateCount = (data.gates || []).filter((item) => !item.passed).length;
  const releasePassed = failedGateCount === 0;
  evaluationSummary.innerHTML = `
    <div class="release-gate ${releasePassed ? "pass" : "fail"}"><span>${releasePassed ? "✓" : "!"}</span><div><strong>${releasePassed ? "发布门禁通过" : "发布门禁未通过"}</strong><small>${escapeHtml(failedGateCount)} 个安全 / 可信门禁失败</small></div></div>
    <div class="summary-stat"><small>总体通过率</small><strong>${escapeHtml(passRate)}%</strong></div>
    <div class="summary-stat"><strong>${escapeHtml(summary.passed ?? "-")} / ${escapeHtml(summary.total ?? "-")}</strong><small>通过</small></div>
  `;

  const visibleCases = (data.cases || []).filter(
    (item) => item.name !== "数据质量审计上下文",
  );
  evaluationCases.innerHTML = visibleCases
    .map((item) => {
      const match = String(item.status || "").match(/(\d+)\s*\/\s*(\d+)/);
      const completed = match ? Number(match[1]) : item.passed ? 1 : 0;
      const total = match ? Number(match[2]) : 1;
      const progress = total ? Math.max(0, Math.min(100, completed / total * 100)) : 0;
      return `
        <article class="evaluation-result-row">
          <strong>${escapeHtml(item.name)}</strong>
          <div class="evaluation-progress"><i style="width:${progress}%"></i></div>
          <span class="pill ${item.passed ? "step-pass" : "step-error"}">${item.passed ? "PASS" : "FAIL"}</span>
          <b>${escapeHtml(item.status || `${completed}/${total}`)}</b>
        </article>
      `;
    })
    .join("") || `<div class="rich-item">暂无用例结果。</div>`;

  evaluationGates.innerHTML = (data.gates || [])
    .map(
      (item) => `
        <article class="evaluation-card">
          <header>
            <span class="gate-check ${item.passed ? "pass" : "fail"}">${item.passed ? "✓" : "!"}</span>
            <strong>${escapeHtml(item.name)}</strong>
          </header>
          <p>${escapeHtml(item.detail || "")}</p>
        </article>
      `,
    )
    .join("") || `<div class="rich-item">暂无门禁结果。</div>`;
}

async function loadEvaluationReport() {
  const response = await fetch("/api/chatbi/evaluations/latest");
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.detail?.message || "测评报告加载失败");
  renderEvaluationReport(data);
}

function renderBadcaseBoard(data) {
  badcaseItems = data.items || [];
  const counts = data.status_counts || {};
  const statuses = ["OPEN", "CONFIRMED", "FIXED", "WONT_FIX"];
  badcaseCounts.innerHTML = statuses
    .map((status) => `<span class="pill">${status}: ${counts[status] || 0}</span>`)
    .join("");

  if (!data.items?.length) {
    badcaseList.innerHTML = `<div class="rich-item">当前筛选下暂无反馈。</div>`;
    badcaseDetail.innerHTML = `<div class="quality-empty"><strong>暂无待处理问题</strong><small>新反馈会在这里显示关联证据和处理记录。</small></div>`;
    return;
  }

  badcaseList.innerHTML = data.items
    .map((item, index) => `
      <article class="badcase-queue-row ${index === 0 ? "selected" : ""}" data-feedback-id="${escapeHtml(item.feedback_id)}">
        <button type="button" data-badcase-select="${escapeHtml(item.feedback_id)}">
          <strong>${escapeHtml(item.message || item.user_query)}</strong>
          <small>${escapeHtml(typeLabel(item.feedback_type))}</small>
          <span class="severity ${escapeHtml((item.severity || "").toLowerCase())}">${escapeHtml(item.severity)}</span>
          <span class="issue-status">${escapeHtml(item.status)}</span>
          <time>${escapeHtml(item.created_at)}</time>
        </button>
      </article>
    `)
    .join("");
  renderBadcaseDetail(data.items[0]);
}

function renderBadcaseDetail(item) {
  const canConfirm = item.status === "OPEN";
  const canFix = item.status === "OPEN" || item.status === "CONFIRMED";
  const canRemediate = item.regression_candidate && (item.status === "CONFIRMED" || item.status === "FIXED") && affectedMetricId(item);
  badcaseDetail.innerHTML = `
    <article class="badcase-detail-card" data-feedback-id="${escapeHtml(item.feedback_id)}">
      <header>
        <div><h4>${escapeHtml(item.message || typeLabel(item.feedback_type))}</h4><small>${escapeHtml(item.feedback_id)}</small></div>
        <span class="pill ${item.status === "FIXED" ? "step-pass" : ""}">${escapeHtml(item.status)}</span>
      </header>
      <div class="issue-facts"><span>来源：用户反馈</span><span>严重程度：${escapeHtml(item.severity)}</span><span>类型：${escapeHtml(typeLabel(item.feedback_type))}</span></div>
      <section><h4>用户问题</h4><p>${escapeHtml(item.user_query)}</p></section>
      <section><h4>问题判断</h4><div class="issue-diagnosis">${escapeHtml(item.message)}</div></section>
      <section><h4>关联证据</h4><dl><dt>反馈 ID</dt><dd>${escapeHtml(item.feedback_id)}</dd><dt>Query Run</dt><dd>${escapeHtml(item.query_id || "-")}</dd><dt>预期表现</dt><dd>${escapeHtml(item.expected_behavior || "待运营确认")}</dd></dl></section>
      <section><h4>处理记录</h4><ol class="issue-timeline"><li>已提交用户反馈 <small>${escapeHtml(item.created_at)}</small></li><li class="active">${item.status === "OPEN" ? "等待运营确认" : `当前状态：${escapeHtml(item.status)}`}</li></ol></section>
      <footer>
        <button type="button" data-feedback-action="WONT_FIX">不处理</button>
        <button type="button" data-feedback-action="CONFIRMED" ${canConfirm ? "" : "disabled"}>确认问题</button>
        <button type="button" data-remediation-action="METRIC" ${canRemediate ? "" : "disabled"}>修正指标并验证</button>
        <button type="button" data-feedback-action="FIXED" ${canFix ? "" : "disabled"}>创建修复任务</button>
      </footer>
    </article>
  `;
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

  if (["CLARIFY", "REJECT", "BLOCKED"].includes(data.status)) {
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
        retrieval: currentResult.retrieval,
        execution: currentResult.execution,
        profile: currentResult.profile,
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

async function recordProductInteraction(eventName) {
  const queryId = currentResult?.compiled?.query_id;
  if (!queryId) {
    resultAdoptionStatus.textContent = "当前结果没有可关联的查询 ID。";
    return;
  }
  const response = await fetch("/api/chatbi/operations/interactions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_id: currentResult.workspace_id || "demo",
      conversation_id: currentResult.conversation_id,
      query_id: queryId,
      event_name: eventName,
    }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || "结果反馈记录失败");
  resultAdoptionStatus.textContent = eventName === "result_adopted" ? "已记录：结果可直接使用。" : "已记录：结果经过人工修正。";
}

async function runAsk() {
  const query = queryInput.value.trim();
  if (!query) return;

  chatFeedbackPanel?.classList.add("hidden");
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
    const identityResponse = await fetch(
      `/api/chatbi/demo/identity-token?role_id=${encodeURIComponent(demoRoleInput.value)}`,
    );
    const identity = await identityResponse.json();
    if (!identityResponse.ok) throw new Error(identity.message || "演示身份加载失败");
    if (sidebarOperatorId) sidebarOperatorId.textContent = identity.operator_id || identity.role_id;
    const response = await fetch("/api/chatbi/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        biz_domain: domainInput.value,
        workspace_id: "demo",
        conversation_id: activeConversationId,
        timezone: "Asia/Shanghai",
        identity_token: identity.identity_token,
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
    const html = ["CLARIFY", "REJECT", "BLOCKED"].includes(data.status) ? clarificationMessageMarkup(data) : interactiveResultMarkup(data);
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
  button.addEventListener("click", () => {
    switchView(button.dataset.view);
    if (button.dataset.view === "ops") {
      loadOperationsSummary().catch((error) => {
        opsDataNote.textContent = `运营指标加载失败：${error.message}`;
      });
    }
    if (button.dataset.view === "source-governance") {
      loadWarehouseSources().catch((error) => { sourceMessage.textContent = `加载失败：${error.message}`; });
    }
    if (button.dataset.view === "business-domains") {
      loadBusinessDomains().catch((error) => {
        domainList.innerHTML = `<div class="rich-item">业务域加载失败：${escapeHtml(error.message)}</div>`;
      });
    }
  });
});

subtabButtons.forEach((button) => {
  button.addEventListener("click", () => switchSubpanel(button.dataset.subtab));
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

demoRoleInput?.addEventListener("change", () => {
  if (sidebarOperatorId) sidebarOperatorId.textContent = demoRoleInput.value;
});

function startNewConversation() {
  const conversation = createConversation();
  conversations.unshift(conversation);
  activeConversationId = conversation.id;
  currentResult = null;
  setOverall("IDLE");
  pipeline.innerHTML = "<li>提交问题后展示完整链路。</li>";
  contextMemory.innerHTML = "<p>完成第一轮分析后显示继承条件。</p>";
  queryInput.value = "";
  persistConversations();
  renderConversationList();
  renderActiveConversation();
  queryInput.focus();
}

async function copyConversationSummary() {
  const conversation = activeConversation();
  const lines = [conversation.title];
  conversation.messages.forEach((item) => {
    if (item.role === "user") {
      lines.push(`问题：${item.text || ""}`);
      return;
    }
    const summary = item.data?.interpretation?.findings?.[0]?.text
      || item.data?.interpretation?.findings?.[0]
      || item.data?.message;
    if (summary) lines.push(`结论：${summary}`);
  });
  await navigator.clipboard.writeText(lines.join("\n"));
  if (conversationActionStatus) {
    conversationActionStatus.textContent = "已复制";
    window.setTimeout(() => { conversationActionStatus.textContent = ""; }, 1800);
  }
}

newConversationButton.addEventListener("click", startNewConversation);
conversationShare?.addEventListener("click", () => {
  copyConversationSummary().catch(() => {
    if (conversationActionStatus) conversationActionStatus.textContent = "复制失败";
  });
});
conversationMore?.addEventListener("click", () => {
  const opening = conversationMenu?.classList.contains("hidden");
  conversationMenu?.classList.toggle("hidden", !opening);
  conversationMore.setAttribute("aria-expanded", String(opening));
});
conversationMenu?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-conversation-command]");
  if (!button) return;
  conversationMenu.classList.add("hidden");
  conversationMore?.setAttribute("aria-expanded", "false");
  if (button.dataset.conversationCommand === "new") startNewConversation();
  if (button.dataset.conversationCommand === "copy") {
    copyConversationSummary().catch(() => {
      if (conversationActionStatus) conversationActionStatus.textContent = "复制失败";
    });
  }
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
  const feedbackButton = event.target.closest("[data-open-feedback]");
  if (feedbackButton) {
    feedbackStatus.textContent = "待提交";
    feedbackStatus.className = "pill";
    feedbackMessage.value = "";
    feedbackExpected.value = "";
    chatFeedbackPanel?.classList.remove("hidden");
    feedbackMessage.focus();
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
}

chatThread.addEventListener("click", handleConversationAction);

feedbackForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitFeedback();
});

chatFeedbackClose?.addEventListener("click", () => {
  chatFeedbackPanel.classList.add("hidden");
});

document.querySelectorAll("[data-product-interaction]").forEach((button) => {
  button.addEventListener("click", () => {
    recordProductInteraction(button.dataset.productInteraction).catch((error) => {
      resultAdoptionStatus.textContent = `记录失败：${error.message}`;
    });
  });
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

metricSearch?.addEventListener("input", () => {
  if (metricCatalogData) renderMetricCatalog(metricCatalogData);
});
metricTypeFilter?.addEventListener("change", () => {
  if (metricCatalogData) renderMetricCatalog(metricCatalogData);
});
metricStatusFilter?.addEventListener("change", () => {
  if (metricCatalogData) renderMetricCatalog(metricCatalogData);
});
metricCatalogNew?.addEventListener("click", () => {
  switchSubpanel("metric-governance");
  resetMetricAdminForm();
});

metricList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-metric-detail]");
  if (!button) return;
  loadMetricDetail(button.dataset.metricDetail).catch((error) => {
    metricDetail.innerHTML = `<div class="rich-item">指标详情加载失败：${escapeHtml(error.message)}</div>`;
  });
});

metricDetail.addEventListener("click", (event) => {
  const detailTab = event.target.closest("button[data-metric-detail-tab]");
  if (detailTab && activeMetricDetailData) {
    activeMetricDetailTab = detailTab.dataset.metricDetailTab;
    renderMetricDetail(activeMetricDetailData);
    return;
  }
  const editButton = event.target.closest("button[data-metric-edit]");
  if (editButton) {
    editButton.disabled = true;
    editButton.textContent = "正在创建...";
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
scopeExampleDomain?.addEventListener("change", () => {
  loadSemanticScopeExamples().catch((error) => {
    scopeExampleStatus.textContent = `业务域边界加载失败：${error.message}`;
  });
  loadAmbiguityPolicy().catch((error) => {
    ambiguityExampleStatus.textContent = `歧义策略加载失败：${error.message}`;
  });
});
scopeExampleSave?.addEventListener("click", () => {
  saveSemanticScopeExamples().catch((error) => {
    scopeExampleSave.disabled = false;
    scopeExampleStatus.textContent = `发布失败：${error.message}`;
  });
});
scopePreviewRun?.addEventListener("click", () => {
  previewSemanticScopeExamples().catch((error) => {
    scopePreviewRun.disabled = false;
    scopePreviewResult.textContent = `预览失败：${error.message}`;
  });
});
ambiguityExampleSave?.addEventListener("click", () => {
  saveAmbiguityPolicy().catch((error) => {
    ambiguityExampleSave.disabled = false;
    ambiguityExampleStatus.textContent = `发布失败：${error.message}`;
  });
});
metricAdminDomain.addEventListener("change", () => {
  activeBusinessDomainId = metricAdminDomain.value;
  metricAdminModel.dataset.preferred = "";
  renderManagementOptions([]);
});
metricAdminModel.addEventListener("change", () => {
  metricAdminModel.dataset.preferred = metricAdminModel.value;
  renderManagementOptions([]);
});
[metricAdminOperation, metricAdminField, metricAdminDenominator, metricAdminScale, metricAdminLeftModel, metricAdminRightModel].forEach((control) => {
  control.addEventListener("change", updateFormulaPreview);
});
metricAdminLeftModel.addEventListener("change", () => updateMetricExpressionFields("", metricAdminDenominator.value));
metricAdminRightModel.addEventListener("change", () => updateMetricExpressionFields(metricAdminField.value, ""));
[metricAdminDescription, metricAdminOwner, metricAdminAliases, metricAdminPositiveExamples, metricAdminNegativeExamples].forEach((control) => {
  control.addEventListener("input", () => renderSemanticReadiness());
});
metricAdminOperation.addEventListener("change", () => {
  if (metricAdminOperation.value === "ratio") metricAdminType.value = "ratio";
  if (metricAdminOperation.value === "subtract") metricAdminType.value = "amount";
  if (metricAdminOperation.value === "count_distinct") metricAdminType.value = "count";
});
metricPreheatGenerate?.addEventListener("click", () => {
  generateMetricPreheat().catch((error) => {
    metricPreheatGenerate.disabled = false;
    metricPreheatStatus.textContent = "失败";
    metricPreheatPreview.textContent = `生成失败：${error.message}`;
  });
});
metricPreheatApply?.addEventListener("click", () => {
  applyMetricPreheat().catch((error) => {
    metricPreheatApply.disabled = false;
    metricPreheatPreview.textContent = `应用失败：${error.message}`;
  });
});
sourceForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  saveWarehouseSource().catch((error) => { sourceMessage.textContent = `保存失败：${error.message}`; });
});
sourceStepButtons.forEach((button) => {
  button.addEventListener("click", () => setSourceStep(Number(button.dataset.sourceStep)));
});
sourceScan?.addEventListener("click", () => scanWarehouseSource().catch((error) => {
  sourceScan.disabled = false;
  sourceMessage.textContent = `扫描失败：${error.message}`;
}));
sourceTables?.addEventListener("click", (event) => {
  const card = event.target.closest("[data-source-table]");
  if (card) renderSourceTableDetail(card);
});
function syncSourceTableDetail(event) {
  const editor = event.target.closest("[data-source-detail-table]");
  if (!editor) return;
  const card = [...sourceTables.querySelectorAll("[data-source-table]")]
    .find((item) => item.dataset.sourceTable === editor.dataset.sourceDetailTable);
  if (!card) return;
  if (event.target.matches("[data-source-detail-enabled]")) {
    card.querySelector(".source-enabled").checked = event.target.checked;
    return;
  }
  const fieldName = event.target.dataset.sourceField;
  if (!fieldName) return;
  const original = card.querySelector(`.${fieldName}`);
  if (original) original.value = event.target.value;
  if (["source-model-id", "source-model-name"].includes(fieldName)) {
    renderSourceDimensionBuilder();
  }
}
sourceTableDetail?.addEventListener("input", syncSourceTableDetail);
sourceTableDetail?.addEventListener("change", syncSourceTableDetail);
sourceDimensionModel?.addEventListener("change", updateSourceDimensionFields);
sourceDimensionType?.addEventListener("change", () => {
  sourceDimensionGrain.disabled = !["date", "time_grain"].includes(sourceDimensionType.value);
});
sourceDimensionAdd?.addEventListener("click", () => {
  try {
    addSourceDimension();
    sourceMessage.textContent = "维度映射已加入当前人工确认草稿。";
  } catch (error) {
    sourceMessage.textContent = `维度添加失败：${error.message}`;
  }
});
sourceAssetsRefresh?.addEventListener("click", () => {
  loadPhysicalAssetInventory().catch((error) => {
    sourceAssetInventory.innerHTML = `<div class="rich-item">物理资产加载失败：${escapeHtml(error.message)}</div>`;
  });
});
schemaImpactList?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-impact-domain]");
  if (!button) return;
  activeBusinessDomainId = button.dataset.impactDomain;
  activeBusinessDomainTab = "assets";
  switchView("business-domains");
  loadBusinessDomains().catch((error) => {
    domainList.innerHTML = `<div class="rich-item">业务域加载失败：${escapeHtml(error.message)}</div>`;
  });
});
sourceOpenDomains?.addEventListener("click", () => switchView("business-domains"));
sourceDomainId?.addEventListener("change", () => {
  renderSourceDomainOptions(sourceDomainId.value);
  sourceMessage.textContent = sourceDomainId.value
    ? `已选择业务域“${sourceDomainName.value}”；请选择该域需要引用的物理表。`
    : "请先选择一个已创建的业务域。";
});
sourceDimensionList?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-source-dimension-remove]");
  if (!button) return;
  const dimensions = parsedSourceDimensions().filter(
    (item) => item.dimension_id !== button.dataset.sourceDimensionRemove,
  );
  sourceDimensionsJson.value = JSON.stringify(dimensions, null, 2);
  renderSourceDimensionBuilder();
});
sourceDimensionsJson?.addEventListener("input", renderSourceDimensionBuilder);
sourceConfirm?.addEventListener("click", () => confirmWarehouseGovernance().catch((error) => {
  sourceMessage.textContent = `确认失败：${error.message}`;
}));
sourcePublish?.addEventListener("click", () => publishWarehouseGovernance().catch((error) => {
  sourceMessage.textContent = `发布失败：${error.message}`;
}));
domainNew?.addEventListener("click", () => openBusinessDomainDialog());
domainRefresh?.addEventListener("click", () => loadBusinessDomains().catch((error) => {
  domainList.innerHTML = `<div class="rich-item">业务域加载失败：${escapeHtml(error.message)}</div>`;
}));
domainSearch?.addEventListener("input", renderBusinessDomainList);
domainStatusFilter?.addEventListener("change", renderBusinessDomainList);
domainList?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-domain-id]");
  if (!button) return;
  activeBusinessDomainId = button.dataset.domainId;
  activeBusinessDomainTab = "assets";
  renderBusinessDomainList();
  await loadActiveDomainTableBindings();
  renderBusinessDomainDetail();
  if (scopeExampleDomain) {
    scopeExampleDomain.value = activeBusinessDomainId;
    Promise.all([loadSemanticScopeExamples(), loadAmbiguityPolicy()]).catch((error) => {
      scopeExampleStatus.textContent = `语义策略加载失败：${error.message}`;
    });
  }
});
domainTabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    switchBusinessDomainTab(button.dataset.domainTab);
    if (button.dataset.domainTab === "semantics") {
      Promise.all([loadSemanticScopeExamples(), loadAmbiguityPolicy()]).catch((error) => {
        scopeExampleStatus.textContent = `语义策略加载失败：${error.message}`;
      });
    }
  });
});
domainAddModel?.addEventListener("click", () => configureActiveDomainTables().catch((error) => {
  domainAssetsMessage.textContent = `业务表配置加载失败：${error.message}`;
}));
domainCreateMetric?.addEventListener("click", createMetricInActiveDomain);
domainNextActionButton?.addEventListener("click", () => {
  const domain = activeBusinessDomain();
  if (!domain) return;
  if (!(domain.binding_count || domain.model_count)) {
    configureActiveDomainTables().catch((error) => {
      domainBlockerList.innerHTML = `<div class="domain-blocker"><span>!</span><strong>${escapeHtml(error.message)}</strong></div>`;
    });
    return;
  }
  if ((domain.blockers || []).length) {
    switchBusinessDomainTab("assets");
    return;
  }
  if (domain.dimension_count === 0 || (domain.model_count > 1 && domain.join_count === 0)) {
    switchBusinessDomainTab("relations");
    return;
  }
  if (domain.metric_count === 0) {
    createMetricInActiveDomain();
    return;
  }
  switchBusinessDomainTab("semantics");
});
domainOpenJoin?.addEventListener("click", () => {
  switchView("join-graph");
  loadJoinGraph().catch((error) => { joinValidation.textContent = error.message; });
});
domainEdit?.addEventListener("click", () => openBusinessDomainDialog(activeBusinessDomain()));
domainDialogClose?.addEventListener("click", () => domainDialog.close());
domainCancel?.addEventListener("click", () => domainDialog.close());
domainAssetsClose?.addEventListener("click", () => domainAssetsDialog.close());
domainAssetsCancel?.addEventListener("click", () => domainAssetsDialog.close());
domainAssetsSearch?.addEventListener("input", renderDomainPhysicalAssets);
domainAssetsList?.addEventListener("change", (event) => {
  if (!event.target.matches("[data-binding-enabled]")) return;
  event.target.closest(".domain-binding-card")?.classList.toggle("selected", event.target.checked);
});
domainAssetsSave?.addEventListener("click", () => {
  saveActiveDomainTableBindings().catch((error) => {
    domainAssetsMessage.textContent = `保存失败：${error.message}`;
  });
});
domainModelList?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-domain-model-id]");
  if (!button) return;
  openDomainModelEditor(button.dataset.domainModelId).catch((error) => {
    domainModelList.innerHTML = `<div class="rich-item">模型详情加载失败：${escapeHtml(error.message)}</div>`;
  });
});
domainModelClose?.addEventListener("click", () => domainModelDialog.close());
domainModelCancel?.addEventListener("click", () => domainModelDialog.close());
domainModelForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  saveActiveDomainModel(false).catch((error) => {
    domainModelMessage.textContent = `保存失败：${error.message}`;
  });
});
domainModelPublish?.addEventListener("click", () => {
  saveActiveDomainModel(true).catch((error) => {
    domainModelMessage.textContent = `发布失败：${error.message}`;
  });
});
domainForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  saveBusinessDomain().catch((error) => {
    domainFormMessage.textContent = `保存失败：${error.message}`;
  });
});
domainMetricList?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-domain-metric-id]");
  if (!button) return;
  switchView("metric-admin");
  switchSubpanel("metric-catalog");
  loadMetricDetail(button.dataset.domainMetricId).catch((error) => {
    metricDetail.innerHTML = `<div class="rich-item">指标详情加载失败：${escapeHtml(error.message)}</div>`;
  });
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
evaluationTabs.forEach((button) => {
  button.addEventListener("click", () => switchEvaluationTab(button.dataset.evaluationTab));
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

function handleBadcaseAction(event) {
  const remediationButton = event.target.closest("button[data-remediation-action]");
  if (remediationButton && !remediationButton.disabled) {
    const card = remediationButton.closest("[data-feedback-id]");
    const item = badcaseItems.find((candidate) => candidate.feedback_id === card?.dataset.feedbackId);
    const metricId = item ? affectedMetricId(item) : null;
    if (!item || !metricId) return;
    editPublishedMetric(metricId, item).catch((error) => {
      badcaseDetail.insertAdjacentHTML("afterbegin", `<div class="rich-item">进入修复失败：${escapeHtml(error.message)}</div>`);
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
    badcaseDetail.insertAdjacentHTML("afterbegin", `<div class="rich-item">状态更新失败：${escapeHtml(error.message)}</div>`);
  });
}

badcaseList.addEventListener("click", (event) => {
  const selectButton = event.target.closest("button[data-badcase-select]");
  if (selectButton) {
    const item = badcaseItems.find((candidate) => candidate.feedback_id === selectButton.dataset.badcaseSelect);
    if (!item) return;
    badcaseList.querySelectorAll(".badcase-queue-row").forEach((row) => {
      row.classList.toggle("selected", row.dataset.feedbackId === item.feedback_id);
    });
    renderBadcaseDetail(item);
    return;
  }
  handleBadcaseAction(event);
});
badcaseDetail?.addEventListener("click", handleBadcaseAction);

metricClosureRun?.addEventListener("click", () => {
  runMetricClosureValidation().catch((error) => {
    metricClosureRun.disabled = false;
    metricClosureStatus.textContent = "FAIL";
    metricClosureStatus.className = "pill step-error";
    metricClosureResult.textContent = `闭环验证失败：${error.message}`;
  });
});

metricClosureExpectedStatus?.addEventListener("change", () => {
  metricClosureExpectedMetric.disabled = metricClosureExpectedStatus.value !== "SUCCESS";
});

metricClosureExpectedMetric?.addEventListener("change", () => {
  if (!activeMetricClosure || metricClosureExpectedStatus.value !== "SUCCESS") return;
  const metricId = metricClosureExpectedMetric.value;
  if (!metricId || metricId === activeMetricDraft?.metric_id) return;
  editPublishedMetric(metricId, activeMetricClosure.feedback).catch((error) => {
    metricClosureResult.textContent = `切换正确指标失败：${error.message}`;
  });
});

metricSemanticFamilyApply?.addEventListener("click", applySemanticFamilyInput);

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

opsRefresh?.addEventListener("click", () => {
  loadOperationsSummary().catch((error) => {
    opsDataNote.textContent = `运营指标加载失败：${error.message}`;
  });
});

joinRefresh?.addEventListener("click", () => loadJoinGraph().catch((e) => { joinValidation.textContent=e.message; }));
joinScan?.addEventListener("click", () => scanJoinCandidates().catch((e) => { joinValidation.textContent=e.message; }));
document.querySelectorAll("[data-join-tab]").forEach((button) => {
  button.addEventListener("click", () => switchJoinTab(button.dataset.joinTab));
});
joinGraphCanvas?.addEventListener("click", (event) => {
  const line = event.target.closest("[data-join-graph-relation-id]");
  if (line) {
    selectJoinRelation(line.dataset.joinGraphRelationId);
    return;
  }
  const node = event.target.closest("[data-join-entity-id]");
  if (node) selectJoinEntity(node.dataset.joinEntityId);
});
joinRelations?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-join-relation-id]");
  if (!button || !joinGraph) return;
  selectJoinRelation(button.dataset.joinRelationId);
});
joinLeft?.addEventListener("change", updateJoinNodeSelection);
joinRight?.addEventListener("change", updateJoinNodeSelection);
joinForm?.addEventListener("submit", (event) => { event.preventDefault(); saveJoinDraft().catch((e) => { joinValidation.textContent=e.message; }); });
joinValidate?.addEventListener("click", () => validateJoinDraft().catch((e) => { joinValidation.textContent=e.message; }));
joinPublish?.addEventListener("click", () => publishJoinDraft().catch((e) => { joinValidation.textContent=e.message; }));
joinCandidates?.addEventListener("click", (event) => {
  const button=event.target.closest("[data-join-candidate]"); if(!button) return;
  const item=JSON.parse(joinCandidates.dataset.items||"[]")[Number(button.dataset.joinCandidate)]; if(!item) return;
  joinId.value=`J_CANDIDATE_${Number(button.dataset.joinCandidate) + 1}`; joinLeft.value=item.left_entity_id; joinRight.value=item.right_entity_id;
  joinLeftKey.value=item.left_keys.join(","); joinRightKey.value=item.right_keys.join(","); joinValidation.textContent="候选关系预览 · 当前页面仅供查看，不会创建或修改治理数据。";
  updateJoinNodeSelection();
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
    return Promise.all([loadMetricDrafts(), loadSemanticScopeExamples(), loadAmbiguityPolicy()]);
  })
  .catch((error) => {
    metricDraftList.innerHTML = `<div class="rich-item">指标管理加载失败：${escapeHtml(error.message)}</div>`;
  });

loadBusinessDomains().catch((error) => {
  if (domainList) domainList.innerHTML = `<div class="rich-item">业务域加载失败：${escapeHtml(error.message)}</div>`;
});

loadJoinGraph().catch((error) => { if (joinValidation) joinValidation.textContent = `Join Graph加载失败：${error.message}`; });

loadEvaluationReport().catch((error) => {
  evaluationSummary.innerHTML = `<div class="rich-item">测评报告加载失败：${escapeHtml(error.message)}</div>`;
});

loadBadcases().catch((error) => {
  badcaseList.innerHTML = `<div class="rich-item">加载失败：${escapeHtml(error.message)}</div>`;
});
loadGoldenQuestions().catch((error) => {
  goldenList.innerHTML = `<div class="rich-item">黄金集加载失败：${escapeHtml(error.message)}</div>`;
});
loadOperationsSummary().catch((error) => {
  if (opsDataNote) opsDataNote.textContent = `运营指标加载失败：${error.message}`;
});
