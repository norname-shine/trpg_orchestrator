const state = {
  campaigns: [],
  activeCampaign: "",
  selectedCampaign: "",
  polling: null,
  sideTab: "quests",
  activePanel: "story",
  autoScroll: true,
  lastJobRunning: false,
  lastCampaignState: {},
  assetCache: {},
  collapsedPanels: {
    map: false,
    task: false,
    memory: false,
  },
};

const $ = (id) => document.getElementById(id);
const ASSET_GENERATOR_VERSION = 2;

function init() {
  drawBackground();
  drawPixelAvatar("TRPG", { cache: false });
  drawPixelMap("TRPG", { cache: false });
  bindControls();
  applyCollapseState();
  refresh();
  state.polling = setInterval(refresh, 2500);
}

function bindControls() {
  $("runTurnBtn").addEventListener("click", runTurn);
  $("prepareBtn").addEventListener("click", prepareOnly);
  $("refreshBtn").addEventListener("click", refresh);
  $("exportBtn").addEventListener("click", () => window.open("/api/export", "_blank"));
  $("clearInputBtn").addEventListener("click", () => {
    $("actionInput").value = "";
    $("actionInput").focus();
  });
  $("mapZoomBtn").addEventListener("click", () => {
    const label = $("mapLabel").textContent || state.activeCampaign || "map";
    drawPixelMap(`${label}:${Date.now()}`, { cache: false });
  });
  $("viewAllBtn").addEventListener("click", () => setGalleryFilter("all"));
  $("viewAllCampaignsBtn").addEventListener("click", () => {
    closeStoryPicker();
    showPanel("logs");
    setLog("全部跑团列表已经在顶部卡片和下拉面板中联动展示。后续会接入完整管理页。");
  });

  $("actionInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      runTurn();
    }
  });

  $("storySelectBtn").addEventListener("click", openStoryPicker);
  $("closeStoryPicker").addEventListener("click", closeStoryPicker);
  $("storyOverlay").addEventListener("click", (event) => {
    if (event.target.id === "storyOverlay") closeStoryPicker();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeStoryPicker();
  });

  document.querySelectorAll("[data-command]").forEach((button) => {
    button.addEventListener("click", () => runCommand(button.dataset.command));
  });
  document.querySelectorAll("[data-panel-tab]").forEach((button) => {
    button.addEventListener("click", () => showPanel(button.dataset.panelTab));
  });
  document.querySelectorAll("[data-side-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      state.sideTab = button.dataset.sideTab;
      document.querySelectorAll("[data-side-tab]").forEach((x) => x.classList.toggle("active", x === button));
      renderSidePanel(state.lastCampaignState);
    });
  });
  document.querySelectorAll("[data-collapse-panel]").forEach((button) => {
    button.addEventListener("click", () => toggleCollapsePanel(button.dataset.collapsePanel));
  });
  $("autoScrollBtn").addEventListener("click", () => {
    state.autoScroll = !state.autoScroll;
    $("autoScrollBtn").classList.toggle("active", state.autoScroll);
  });
  document.querySelectorAll("#galleryFilters button").forEach((button) => {
    button.addEventListener("click", () => setGalleryFilter(button.dataset.filter));
  });
}

function toggleCollapsePanel(name) {
  if (!Object.prototype.hasOwnProperty.call(state.collapsedPanels, name)) return;
  state.collapsedPanels[name] = !state.collapsedPanels[name];
  applyCollapseState();
}

function applyCollapseState() {
  const leftColumn = document.querySelector(".leftColumn");
  Object.entries(state.collapsedPanels).forEach(([name, collapsed]) => {
    leftColumn?.classList.toggle(`${name}-collapsed`, collapsed);
    const panel = document.querySelector(`.${name}Panel`);
    panel?.classList.toggle("collapsed", collapsed);
    const button = document.querySelector(`[data-collapse-panel="${name}"]`);
    if (button) {
      button.textContent = collapsed ? "+" : "−";
      button.setAttribute("aria-expanded", String(!collapsed));
      button.setAttribute("aria-label", `${collapsed ? "展开" : "收起"}${collapsePanelLabel(name)}`);
    }
  });
}

function collapsePanelLabel(name) {
  return {
    map: "区域地图",
    task: "任务物品",
    memory: "近期记忆",
  }[name] || "窗口";
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  const data = await res.json();
  if (!res.ok || data.ok === false) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

async function runTurn() {
  const action = $("actionInput").value.trim();
  if (!action) {
    showPanel("logs");
    return setLog("玩家行动不能为空。");
  }
  await startJob("/api/run-turn", { action, campaign_id: state.activeCampaign });
}

async function prepareOnly() {
  const action = $("actionInput").value.trim();
  if (!action) {
    showPanel("logs");
    return setLog("玩家行动不能为空。");
  }
  await startJob("/api/prepare", { action, campaign_id: state.activeCampaign });
}

async function runCommand(name) {
  await startJob("/api/command", { name, campaign_id: state.activeCampaign });
}

async function startJob(path, payload) {
  try {
    setBusy(true);
    showPanel("logs");
    setLog("命令已提交，后台开始执行。");
    await api(path, { method: "POST", body: JSON.stringify(payload) });
    await refresh();
  } catch (err) {
    setBusy(false, true);
    showPanel("logs");
    setLog(err.message);
  }
}

async function refresh() {
  try {
    const data = await api("/api/status");
    renderStatus(data);
    renderCampaignState(data.campaign_state || {});
    renderOutput(data.output || {});
  } catch (err) {
    setBusy(false, true);
    showPanel("logs");
    setLog(err.message);
  }
}

function renderStatus(data) {
  state.campaigns = data.campaign_list || [];
  state.activeCampaign = data.active_campaign || "";
  state.selectedCampaign = state.selectedCampaign || state.activeCampaign;
  setText("campaignName", campaignTitle(state.activeCampaign) || "-");

  const scene = data.campaign_state?.recent?.current_scene || {};
  const chapterName = currentCampaignMeta()?.chapter || "";
  const chapterBtn = $("chapterBtn");
  if (chapterBtn) {
    const hasChapter = Boolean(chapterName && chapterName !== "current");
    chapterBtn.classList.toggle("hidden", !hasChapter);
    if (hasChapter) setText("chapterName", chapterName);
  }
  setText("mapLabel", scene.location || "当前路线");
  const characterName = extractPlayerName(data.campaign_state?.player || {}, data.campaign_state?.character_prompt || {}) || "player";
  drawPixelAvatar(characterName || state.activeCampaign || "TRPG", {
    cache: true,
    objectId: slugify(characterName || "player"),
    variant: "hunter",
  });
  drawPixelMap(scene.location || state.activeCampaign || "map", {
    cache: true,
    objectId: slugify(scene.location || "current_map"),
  });

  const job = data.job || {};
  const failed = job.returncode !== null && job.returncode !== 0;
  setBusy(Boolean(job.running), failed);
  setText("jobText", job.running ? "运行中" : failed ? "已停止" : "待机");

  const cmd = job.command && job.command.length ? `\n\n$ ${job.command.join(" ")}` : "";
  const output = [job.output, job.error, cmd].filter(Boolean).join("\n");
  if (output) setLog(output);

  if (state.lastJobRunning && !job.running && !failed) showPanel("story");
  state.lastJobRunning = Boolean(job.running);
}

function renderCampaignState(campaignState) {
  state.lastCampaignState = campaignState;
  const title = campaignState.title || campaignTitle(state.activeCampaign) || "未命名跑团";
  const recent = campaignState.recent || {};
  const scene = recent.current_scene || {};
  const card = buildCharacterCard(campaignState, title, scene);
  renderCharacterCard(card);
  renderCompanionCard(card.companion);
  renderSidePanel(campaignState);
  renderMemoryPanel(campaignState);
}

function extractPlayerName(player, characterPrompt = {}) {
  const facts = Array.isArray(player.facts) ? player.facts.join(" ") : "";
  const identity = player.confirmed_identity || characterPrompt.confirmed_identity || {};
  if (identity.name) return identity.name;
  if (facts.includes("Lee")) return "Lee";
  if (facts.includes("玩家")) return "玩家角色";
  return "";
}

function buildCharacterCard(campaignState, fallbackTitle, scene) {
  const player = campaignState.player || {};
  const prompt = campaignState.character_prompt || {};
  const provided = player.character_card || prompt.character_card || {};
  const identity = provided.identity || player.confirmed_identity || prompt.confirmed_identity || {};
  const mechanics = campaignState.mechanics || {};
  const strictReady = hasStrictVitals(provided.vitals) || hasStrictAttributes(provided.attributes);
  const requestedMode = provided.mode || (strictReady ? "strict_stats" : "narrative_status");
  const mode = requestedMode === "auto" ? (strictReady ? "strict_stats" : "narrative_status") : requestedMode;
  const name = identity.name || extractPlayerName(player, prompt) || fallbackTitle;
  const roleParts = [
    identity.ancestry,
    identity.class_or_role || identity.role,
    identity.level_or_stage,
  ].filter(Boolean);
  const fallbackRole = name === "Lee" ? "新晋猎人 / 斩斧 / 正式猎人" : (campaignState.genre || "身份待确认");
  const progression = normalizeProgression(provided.progression, mode);
  return {
    mode,
    name,
    meta: roleParts.length ? roleParts.join(" / ") : fallbackRole,
    progression,
    vitals: normalizeVitals(provided.vitals, mode),
    conditions: normalizeConditions(provided.conditions, campaignState, scene),
    attributes: normalizeAttributes(provided.attributes, mode),
    companion: normalizeCompanion(provided.companion || prompt.companion_card || identity.companion || {}),
  };
}

function normalizeCompanion(companion) {
  return {
    name: companion.name || "浩文",
    meta: companion.personality || companion.meta || "老练但嘴硬",
    seed: companion.visual_seed || `palico:${state.activeCampaign}:haowen`,
  };
}

function hasStrictVitals(vitals) {
  return Array.isArray(vitals) && vitals.some((item) => Number.isFinite(item?.current) && Number.isFinite(item?.max));
}

function hasStrictAttributes(attributes) {
  return Array.isArray(attributes) && attributes.some((item) => Number.isFinite(item?.value));
}

function normalizeProgression(progress, mode) {
  const source = progress || {};
  const current = Number(source.current);
  const max = Number(source.max);
  if (Number.isFinite(current) && Number.isFinite(max) && max > 0) {
    return {
      label: source.label || "经验值",
      value: `${current} / ${max}`,
      percent: Math.max(0, Math.min(100, (current / max) * 100)),
    };
  }
  return {
    label: source.label || (mode === "strict_stats" ? "经验值" : "成长"),
    value: source.text || "新人阶段，稳步成长",
    percent: Number.isFinite(Number(source.percent)) ? Number(source.percent) : 42,
  };
}

function normalizeVitals(vitals, mode) {
  if (Array.isArray(vitals) && vitals.length) {
    return vitals.map((item, index) => normalizeVital(item, index, mode));
  }
  return [
    { key: "health", label: "生命值", state: "状态良好", percent: 82, tone: "red" },
    { key: "focus", label: "专注值", state: "稳定", percent: 78, tone: "blue" },
    { key: "stamina", label: "体力值", state: "有消耗", percent: 72, tone: "green" },
  ];
}

function normalizeVital(item, index, mode) {
  const current = Number(item.current);
  const max = Number(item.max);
  const hasNumbers = Number.isFinite(current) && Number.isFinite(max) && max > 0;
  const labels = ["生命值", "专注值", "体力值"];
  const tones = ["red", "blue", "green"];
  return {
    key: item.key || `vital_${index}`,
    label: item.label || labels[index] || "状态",
    state: mode === "strict_stats" && hasNumbers ? `${current} / ${max}` : (item.state || item.text || "叙事状态"),
    percent: hasNumbers ? Math.max(0, Math.min(100, (current / max) * 100)) : Number(item.percent || 66),
    tone: item.tone || tones[index % tones.length],
  };
}

function normalizeConditions(conditions, campaignState, scene) {
  const rows = Array.isArray(conditions) ? conditions : [];
  const labels = rows.map((item) => typeof item === "string" ? item : item.label || item.name).filter(Boolean);
  if (labels.length) return labels.slice(0, 6);
  const mechanics = campaignState.mechanics || {};
  return [
    "谨慎",
    mechanics.use_dice ? "严格数值" : "叙事判定",
    "斩斧",
    scene?.immediate_pressure ? "任务压力" : "整备中",
  ];
}

function normalizeAttributes(attributes, mode) {
  if (Array.isArray(attributes) && attributes.length) {
    return attributes.map((item) => {
      if (typeof item === "string") return { label: item.slice(0, 1), text: item };
      const value = Number.isFinite(Number(item.value)) ? String(item.value) : (item.rank || item.text || "");
      const modifier = item.modifier ? ` (${item.modifier})` : "";
      return {
        label: item.short || item.label || item.key || "项",
        text: mode === "strict_stats" && value ? `${value}${modifier}` : (item.state || item.text || value || "记录"),
      };
    }).slice(0, 6);
  }
  return [
    { label: "斧", text: "牵制" },
    { label: "剑", text: "爆发" },
    { label: "迹", text: "追踪" },
    { label: "营", text: "补给" },
    { label: "捕", text: "陷阱" },
    { label: "退", text: "保命" },
  ];
}

function renderCharacterCard(card) {
  setText("characterName", card.name);
  setText("characterMeta", card.meta);
  setText("characterCardMode", card.mode === "strict_stats" ? "数值卡" : "叙事卡");
  setText("progressLabel", card.progression.label);
  setText("progressValue", card.progression.value);
  const progressBar = $("progressBar");
  if (progressBar) progressBar.style.width = `${Math.max(4, Math.min(100, card.progression.percent))}%`;
  renderVitals(card.vitals);
  renderConditionBadges(card.conditions);
  renderAttributes(card.attributes);
}

function renderCompanionCard(companion) {
  setText("palicoName", companion.name);
  setText("palicoMeta", companion.meta);
  drawPixelPalico(companion.seed || companion.name, {
    cache: true,
    objectId: slugify(companion.name || "palico"),
  });
}

function renderVitals(vitals) {
  const holder = $("vitalList");
  if (!holder) return;
  holder.innerHTML = "";
  vitals.slice(0, 4).forEach((vital) => {
    const row = document.createElement("div");
    row.className = `vitalRow ${vital.tone || ""}`;
    const label = document.createElement("span");
    label.textContent = vital.label;
    const value = document.createElement("b");
    value.textContent = vital.state;
    const bar = document.createElement("i");
    bar.style.width = `${Math.max(4, Math.min(100, vital.percent || 0))}%`;
    row.append(label, value, bar);
    holder.appendChild(row);
  });
}

function renderConditionBadges(labels) {
  const holder = $("characterBadges");
  if (!holder) return;
  holder.innerHTML = "";
  labels.slice(0, 6).forEach((label) => {
    const span = document.createElement("span");
    span.textContent = label;
    holder.appendChild(span);
  });
}

function renderAttributes(attributes) {
  const holder = $("attributeGrid");
  if (!holder) return;
  holder.innerHTML = "";
  attributes.slice(0, 6).forEach((item) => {
    const cell = document.createElement("div");
    const b = document.createElement("b");
    b.textContent = item.label;
    const span = document.createElement("span");
    span.textContent = item.text;
    cell.append(b, span);
    holder.appendChild(cell);
  });
}

function currentCampaignMeta() {
  return state.campaigns.find((campaign) => campaign.campaign_id === state.activeCampaign) || null;
}

function renderSidePanel(campaignState) {
  const list = $("sideList");
  if (!list) return;
  const quests = campaignState.quests || {};
  const player = campaignState.player || {};
  const rows = state.sideTab === "items"
    ? normalizeRows(player.facts || []).filter((x) => /斩斧|碎羽|记录|素材|装备|泥甲|物件/.test(x))
    : normalizeRows(quests.quest_updates || quests.facts || []);
  const fallback = state.sideTab === "items" ? ["暂无物品记录"] : ["暂无任务记录"];
  list.innerHTML = "";
  (rows.length ? rows.slice(-5) : fallback).forEach((row, index) => {
    const li = document.createElement("li");
    const b = document.createElement("b");
    b.textContent = row;
    const span = document.createElement("span");
    span.textContent = index === rows.length - 1 ? "当前" : "记录";
    li.append(b, span);
    list.appendChild(li);
  });
}

function renderMemoryPanel(campaignState) {
  const list = $("memoryList");
  if (!list) return;
  const recent = normalizeRows(campaignState.recent?.recent_summary || []);
  const threads = normalizeRows(campaignState.threads?.main_threads || []);
  const rows = [...recent.slice(-3), ...threads.slice(-2)].filter(Boolean).slice(-5);
  list.innerHTML = "";
  (rows.length ? rows : ["暂无近期记忆"]).forEach((row, index) => {
    const li = document.createElement("li");
    li.textContent = row;
    const span = document.createElement("span");
    span.textContent = `${index + 1}条`;
    li.appendChild(span);
    list.appendChild(li);
  });
}

function normalizeRows(rows) {
  return rows.map((row) => {
    if (typeof row === "string") return row;
    return row.summary || row.title || row.id || JSON.stringify(row);
  }).filter(Boolean);
}

function renderOutput(output) {
  const parsed = output.parsed || {};
  renderStory(parsed.body || "暂无正文。");
  setText("choicesText", parsed.choices || "暂无选择点。");
  renderSummary(parsed.summary || "暂无回合摘要。");
  const director = {
    pressure_pack: output.pressure_pack || {},
    ai_flavor_report: output.ai_flavor_report || {},
    audit_result: output.audit_result || {},
  };
  setText("directorText", JSON.stringify(director, null, 2));
}

function renderStory(text) {
  const container = $("storyText");
  container.innerHTML = "";
  const parts = String(text).split(/\n{2,}/).map((part) => part.trim()).filter(Boolean);
  if (!parts.length) {
    container.textContent = "暂无正文。";
    return;
  }
  parts.forEach((part, index) => {
    const card = document.createElement("article");
    const role = index === 0 ? "gm" : index % 6 === 3 ? "system" : "gm";
    card.className = `msg ${role}`;
    const badge = document.createElement("div");
    badge.className = "badge";
    badge.textContent = role === "system" ? "检" : "叙";
    const body = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = role === "system" ? "系统记录" : "GM 叙述";
    const content = document.createElement("div");
    content.textContent = part;
    body.append(title, content);
    const time = document.createElement("time");
    time.textContent = "现在";
    card.append(badge, body, time);
    container.appendChild(card);
  });
  scrollActiveFeed();
}

function renderSummary(text) {
  const container = $("summaryText");
  container.innerHTML = "";
  String(text).split(/\n{2,}/).map((x) => x.trim()).filter(Boolean).forEach((part) => {
    const card = document.createElement("article");
    card.className = "msg system";
    const badge = document.createElement("div");
    badge.className = "badge";
    badge.textContent = "摘";
    const body = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = "回合摘要";
    const content = document.createElement("div");
    content.textContent = part;
    body.append(title, content);
    card.append(badge, body);
    container.appendChild(card);
  });
}

function openStoryPicker() {
  renderStoryPicker();
  $("storyOverlay").classList.remove("hidden");
  $("storyOverlay").setAttribute("aria-hidden", "false");
}

function closeStoryPicker() {
  $("storyOverlay").classList.add("hidden");
  $("storyOverlay").setAttribute("aria-hidden", "true");
}

function renderStoryPicker() {
  const campaigns = $("campaignList");
  const stories = $("storyList");
  campaigns.innerHTML = "";
  stories.innerHTML = "";
  const availableCampaigns = state.campaigns.length ? state.campaigns : demoCampaigns();
  if (!state.selectedCampaign && availableCampaigns[0]) {
    state.selectedCampaign = availableCampaigns[0].campaign_id;
  }
  availableCampaigns.forEach((campaign) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `campaignRailItem${campaign.campaign_id === state.selectedCampaign ? " active" : ""}`;
    button.innerHTML = `<b>${escapeHtml(campaign.title || campaign.name || campaign.campaign_id)}</b><small>${escapeHtml(campaign.status || "进行中")}</small>`;
    button.addEventListener("click", () => {
      state.selectedCampaign = campaign.campaign_id;
      renderStoryPicker();
    });
    campaigns.appendChild(button);
  });
  const selected = availableCampaigns.find((x) => x.campaign_id === state.selectedCampaign) || availableCampaigns[0];
  if (!selected) return;
  const isActive = selected.campaign_id === state.activeCampaign;
  const detail = document.createElement("div");
  detail.className = "pickerCampaignDetail";
  detail.innerHTML = `
    <b>${escapeHtml(selected.title || selected.name || selected.campaign_id)}</b>
    <small>${escapeHtml(selected.genre || selected.status || "未记录题材")}</small>
    <p>${escapeHtml(selected.conversation ? `固定对话：${selected.conversation}` : "固定对话未绑定")}</p>
  `;
  const switchBtn = document.createElement("button");
  switchBtn.type = "button";
  switchBtn.className = "pickerAction";
  switchBtn.textContent = isActive ? "当前跑团" : "切换到此跑团";
  switchBtn.disabled = isActive;
  switchBtn.addEventListener("click", () => selectCampaign(selected.campaign_id));
  const newBtn = document.createElement("button");
  newBtn.type = "button";
  newBtn.className = "pickerAction secondary";
  newBtn.textContent = "新建跑团 Demo";
  newBtn.addEventListener("click", () => {
    window.location.href = "/new-campaign-demo.html";
  });
  stories.append(detail, switchBtn, newBtn);
}

function demoCampaigns() {
  return [
    {
      campaign_id: "demo_fog_harbor",
      title: "雾港迷航",
      status: "进行中 · 第三章",
      conversation: "雾港固定对话",
      genre: "海雾、港口、失踪货物",
      tone: "潮湿、悬疑、低声交涉",
      chapter: "第三章",
    },
    {
      campaign_id: "demo_spark_wilds",
      title: "星火荒原",
      status: "进行中 · 第一章",
      conversation: "荒原固定对话",
      genre: "荒原、遗迹、商队",
      tone: "干热、开阔、危险路线",
      chapter: "第一章",
    },
  ];
}

async function selectCampaign(campaignId) {
  await api("/api/select-campaign", {
    method: "POST",
    body: JSON.stringify({ campaign_id: campaignId }),
  });
  state.activeCampaign = campaignId;
  state.selectedCampaign = campaignId;
  closeStoryPicker();
  await refresh();
}

function showPanel(name) {
  state.activePanel = name;
  ["story", "choices", "director", "logs", "summary"].forEach((item) => {
    const el = $(`${item}Tab`);
    if (el) el.classList.toggle("hidden", item !== name);
  });
  document.querySelectorAll("[data-panel-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.panelTab === name);
  });
  scrollActiveFeed();
}

function setGalleryFilter(filter) {
  document.querySelectorAll("#galleryFilters button").forEach((button) => {
    button.classList.toggle("active", button.dataset.filter === filter);
  });
  document.querySelectorAll("#galleryGrid article").forEach((card) => {
    card.classList.toggle("hidden", filter !== "all" && card.dataset.kind !== filter);
  });
}

function setBusy(running, error = false) {
  const pill = $("jobPill");
  pill.classList.toggle("running", running);
  pill.classList.toggle("error", !running && error);
  document.querySelectorAll("button").forEach((button) => {
    if (button.closest(".storyOverlay")) return;
    if (button.dataset.collapsePanel) return;
    button.disabled = running;
  });
  $("actionInput").disabled = running;
}

function setLog(text) {
  setText("logText", text || "");
  scrollActiveFeed();
}

function setText(id, text) {
  const el = $(id);
  if (el) el.textContent = text;
}

function campaignTitle(campaignId) {
  const row = state.campaigns.find((campaign) => campaign.campaign_id === campaignId);
  return row?.title || row?.name || campaignId;
}

function scrollActiveFeed() {
  if (!state.autoScroll) return;
  const feed = $(`${state.activePanel}Tab`);
  if (feed) feed.scrollTop = feed.scrollHeight;
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

function hashSeed(text) {
  let h = 2166136261;
  for (const ch of String(text)) {
    h ^= ch.charCodeAt(0);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function drawPixelAvatar(seedText, options = {}) {
  const canvas = $("avatarCanvas");
  if (!canvas) return;
  if (options.cache && state.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      kind: "portrait",
      subdir: "portraits",
      objectId: options.objectId || slugify(seedText),
      seedText,
      draw: () => drawPixelAvatar(seedText, { cache: false, variant: options.variant }),
    });
    return;
  }
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(seedText);
  const size = canvas.width;
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, size, size);
  ctx.fillStyle = "#d7c7aa";
  ctx.fillRect(0, 0, size, size);
  const cell = 4;
  const px = (x, y, w, h, color) => {
    ctx.fillStyle = color;
    ctx.fillRect(x * cell, y * cell, w * cell, h * cell);
  };
  const mirror = (x, y, w, h, color) => {
    px(x, y, w, h, color);
    px(24 - x - w, y, w, h, color);
  };
  px(0, 0, 24, 24, "#d7c7aa");
  px(5, 2, 14, 3, "#2b241c");
  mirror(4, 4, 3, 2, "#2b241c");
  px(6, 5, 12, 10, "#c79665");
  mirror(5, 7, 2, 6, "#b77f4f");
  px(8, 7, 8, 6, "#dfb27a");
  mirror(8, 8, 2, 1, "#151817");
  px(11, 9, 2, 1, "#8c5c3c");
  px(10, 12, 4, 1, "#5a2e25");
  px(7, 14, 10, 2, "#5c3f2a");
  px(6, 16, 12, 4, "#384548");
  mirror(3, 17, 4, 5, "#6a4a30");
  px(9, 17, 6, 5, "#2f3b3e");
  px(8, 16, 8, 1, "#b8945d");
  mirror(4, 21, 5, 2, "#81765c");
  px(14, 14, 5, 2, "#b8945d");
  px(16, 13, 2, 1, "#d6c38c");
  if ((seed >>> 3) & 1) px(7, 6, 3, 1, "#6f4b2f");
  if (options.variant === "hunter") {
    px(3, 15, 5, 2, "#7f5b36");
    px(16, 15, 5, 2, "#7f5b36");
    px(18, 18, 3, 1, "#c8b07c");
    px(19, 19, 2, 1, "#5d5543");
    px(2, 20, 3, 1, "#5d5543");
  }
}

function drawPixelPalico(seedText, options = {}) {
  const canvas = $("palicoCanvas");
  if (!canvas) return;
  if (options.cache && state.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      kind: "palico",
      subdir: "portraits",
      objectId: options.objectId || slugify(seedText),
      seedText,
      draw: () => drawPixelPalico(seedText, { cache: false }),
    });
    return;
  }
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(seedText);
  const size = canvas.width;
  const cell = 2;
  const px = (x, y, w, h, color) => {
    ctx.fillStyle = color;
    ctx.fillRect(x * cell, y * cell, w * cell, h * cell);
  };
  const mirror = (x, y, w, h, color) => {
    px(x, y, w, h, color);
    px(32 - x - w, y, w, h, color);
  };
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, size, size);
  px(0, 0, 32, 32, "#ead7b8");
  mirror(7, 3, 5, 8, "#69513a");
  mirror(9, 5, 2, 4, "#f2d7a8");
  px(9, 8, 14, 13, "#8a6b48");
  px(10, 10, 12, 9, "#d7b784");
  mirror(11, 14, 2, 2, "#141716");
  px(15, 15, 2, 2, "#6c4931");
  px(13, 18, 6, 1, "#4e2c24");
  px(8, 21, 16, 3, "#9f3030");
  px(21, 19, 5, 5, "#d6a23e");
  px(22, 20, 3, 3, "#f2dfad");
  px(10, 24, 12, 4, (seed & 1) ? "#3b4e53" : "#5f432b");
  mirror(5, 24, 5, 5, "#6d5a43");
  mirror(4, 16, 4, 3, "#8a6b48");
  px(14, 11, 4, 1, "#f0cf99");
}

function drawPixelMap(seedText, options = {}) {
  const canvas = $("mapCanvas");
  if (!canvas) return;
  if (options.cache && state.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      kind: "map",
      subdir: "maps",
      objectId: options.objectId || slugify(seedText),
      seedText,
      draw: () => drawPixelMap(seedText, { cache: false }),
    });
    return;
  }
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  const seed = hashSeed(seedText);
  const cell = 12;
  ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = "#cfc7b0";
  ctx.fillRect(0, 0, w, h);
  for (let y = 0; y < h; y += cell) {
    for (let x = 0; x < w; x += cell) {
      const n = (x * 31 + y * 17 + seed) % 97;
      ctx.fillStyle = n < 24 ? "#8ab0b7" : n < 34 ? "#d8c99f" : n < 42 ? "#b7c2a6" : "#d5ceb9";
      ctx.fillRect(x, y, cell, cell);
    }
  }
  ctx.fillStyle = "#746a55";
  for (let i = 0; i < 38; i += 1) {
    const x = i * 20;
    const y = 190 - Math.sin(i / 3) * 44;
    ctx.fillRect(x, y, 28, 14);
  }
  ctx.fillStyle = "#f2dfad";
  [[120, 130], [330, 96], [510, 168]].forEach(([x, y]) => {
    ctx.fillRect(x, y, 70, 50);
    ctx.fillStyle = "#8a6b43";
    ctx.fillRect(x + 10, y + 10, 50, 8);
    ctx.fillStyle = "#f2dfad";
  });
  ctx.fillStyle = "#4d82bd";
  ctx.fillRect(590, 40, 24, 24);
  ctx.fillStyle = "#d6a23e";
  ctx.fillRect(145, 112, 22, 22);
}

async function cacheCanvasAsset({ canvas, kind, subdir, objectId, seedText, draw }) {
  const campaignId = state.activeCampaign;
  const safeId = slugify(objectId || seedText || kind);
  const key = `${kind}:${campaignId}:${safeId}:v${ASSET_GENERATOR_VERSION}`;
  const memory = state.assetCache[key];
  if (memory === "pending") return;
  if (memory?.url) {
    drawImageToCanvas(canvas, memory.url, draw);
    return;
  }
  state.assetCache[key] = "pending";
  try {
    const lookup = await api(`/api/asset?campaign_id=${encodeURIComponent(campaignId)}&key=${encodeURIComponent(key)}`);
    if (lookup.exists && lookup.url) {
      state.assetCache[key] = { url: lookup.url };
      drawImageToCanvas(canvas, lookup.url, draw);
      return;
    }
    draw();
    const saved = await api("/api/asset", {
      method: "POST",
      body: JSON.stringify({
        campaign_id: campaignId,
        key,
        kind,
        subdir,
        filename: `${kind}_${safeId}`,
        seed: String(seedText || key),
        style: "local_canvas_pixel",
        generator_version: ASSET_GENERATOR_VERSION,
        data_url: canvas.toDataURL("image/png"),
      }),
    });
    state.assetCache[key] = saved.url ? { url: saved.url } : null;
  } catch (err) {
    console.warn("asset cache failed", err);
    state.assetCache[key] = null;
    draw();
  }
}

function drawImageToCanvas(canvas, url, fallback) {
  const image = new Image();
  image.onload = () => {
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  };
  image.onerror = () => {
    if (fallback) fallback();
  };
  image.src = `${url}?v=${ASSET_GENERATOR_VERSION}`;
}

function slugify(value) {
  return String(value || "asset")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fff]+/gi, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 64) || "asset";
}

function drawBackground() {
  const canvas = $("rainCanvas");
  const ctx = canvas.getContext("2d");
  let marks = [];
  function resize() {
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(window.innerWidth * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    marks = Array.from({ length: 48 }, () => ({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      r: 30 + Math.random() * 120,
      a: 0.035 + Math.random() * 0.06,
      s: 0.06 + Math.random() * 0.12,
    }));
  }
  function frame() {
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
    ctx.lineWidth = 1;
    for (const mark of marks) {
      ctx.strokeStyle = `rgba(120, 92, 55, ${mark.a})`;
      ctx.beginPath();
      ctx.arc(mark.x, mark.y, mark.r, 0, Math.PI * 1.35);
      ctx.stroke();
      mark.x += mark.s;
      if (mark.x - mark.r > window.innerWidth + 80) mark.x = -mark.r;
    }
    requestAnimationFrame(frame);
  }
  window.addEventListener("resize", resize);
  resize();
  frame();
}

init();
