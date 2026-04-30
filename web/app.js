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
  galleryFilter: "all",
  renderedMapKey: "",
};

const $ = (id) => document.getElementById(id);
const ASSET_GENERATOR_VERSION = 6;

function init() {
  drawBackground();
  drawPixelAvatar("TRPG", { cache: false });
  drawPixelMap("TRPG", { cache: false, force: true });
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
  renderCachedMap(scene);

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

function renderCachedMap(scene) {
  const seed = scene.location || state.activeCampaign || "map";
  const objectId = slugify(scene.location || "current_map");
  const mapKey = `${state.activeCampaign}:${objectId}:v${ASSET_GENERATOR_VERSION}`;
  if (state.renderedMapKey === mapKey) return;
  state.renderedMapKey = mapKey;
  drawPixelMap(seed, {
    cache: true,
    objectId,
    scene,
    force: true,
  });
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
  renderGallery(campaignState);
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
  const rows = state.sideTab === "items" ? itemRows(campaignState) : questRows(campaignState);
  const fallback = state.sideTab === "items" ? ["暂无物品记录"] : ["暂无任务记录"];
  list.innerHTML = "";
  (rows.length ? rows.slice(-5) : fallback.map((title) => ({ title, tag: "记录" }))).forEach((row, index) => {
    const li = document.createElement("li");
    const b = document.createElement("b");
    b.textContent = row.title || row;
    if (row.detail) {
      const small = document.createElement("small");
      small.textContent = row.detail;
      b.appendChild(small);
    }
    const span = document.createElement("span");
    span.textContent = row.tag || (index === rows.length - 1 ? "当前" : "记录");
    li.append(b, span);
    list.appendChild(li);
  });
}

function questRows(campaignState) {
  const quests = campaignState.quests || {};
  return dedupeRows([...normalizeFactRows(quests.quest_updates), ...normalizeFactRows(quests.facts)])
    .map((row) => ({ ...row, tag: row.tag || "任务" }));
}

function itemRows(campaignState) {
  const player = campaignState.player || {};
  const recent = campaignState.recent || {};
  const source = [
    ...normalizeFactRows(campaignState.equipment?.facts),
    ...normalizeFactRows(player.facts),
    ...clauseRows(recent.short_term_state?.resources, "物品"),
    ...clauseRows(recent.short_term_state?.injury_or_damage, "损耗"),
  ];
  const keywords = /斩斧|碎羽|素材|装备|物件|药瓶|货车|泥|痕|油灯|拖布|登记册|任务板|缰绳|行囊|鳞|补给|样本|碎片/;
  return dedupeRows(source.filter((row) => keywords.test(row.title + row.detail))).map((row) => ({ ...row, tag: row.tag || "物品" }));
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
  return normalizeFactRows(rows).map((row) => row.title);
}

function normalizeFactRows(rows) {
  const list = Array.isArray(rows) ? rows : rows ? [rows] : [];
  return list.map((row) => {
    if (typeof row === "string") return splitFactText(row);
    if (!row || typeof row !== "object") return null;
    const text = row.value || row.summary || row.title || row.name || row.text || row.description || "";
    const parsed = splitFactText(text || row.id || "");
    parsed.tag = row.field ? fieldLabel(row.field) : (row.kind || row.type || parsed.tag || "记录");
    return parsed;
  }).filter((row) => row && row.title);
}

function clauseRows(value, tag = "记录") {
  const text = typeof value === "string" ? value : Array.isArray(value) ? value.join("；") : "";
  return text.split(/[；;。]/)
    .map((part) => splitFactText(part))
    .filter((row) => row.title)
    .map((row) => ({ ...row, tag }));
}

function splitFactText(text) {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  if (!clean) return { title: "", detail: "", tag: "记录" };
  const parts = clean.split(/[；;。]/).map((x) => x.trim()).filter(Boolean);
  const title = parts[0]?.slice(0, 42) || clean.slice(0, 42);
  const detail = parts.slice(1).join("；").slice(0, 96);
  return { title, detail, tag: "记录" };
}

function fieldLabel(field) {
  return {
    quest_history_updates: "任务",
    equipment_history_updates: "装备",
    location_history_updates: "地点",
    enemy_or_mystery_updates: "生态",
    world_state_updates: "世界",
    player_growth: "成长",
  }[field] || "记录";
}

function dedupeRows(rows) {
  const seen = new Set();
  return rows.filter((row) => {
    const key = `${row.title}:${row.detail}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function renderOutput(output) {
  const parsed = output.parsed || {};
  const blocks = Array.isArray(parsed.blocks) ? parsed.blocks : [];
  renderStoryBlocks(blocks, parsed.body || "暂无正文。");
  renderChoicePanel(blocks, parsed.choices || "暂无选择点。");
  renderSummary(parsed.summary || "暂无回合摘要。");
  const director = {
    pressure_pack: output.pressure_pack || {},
    ai_flavor_report: output.ai_flavor_report || {},
    audit_result: output.audit_result || {},
  };
  setText("directorText", JSON.stringify(director, null, 2));
}

function renderStoryBlocks(blocks, fallbackText) {
  const container = $("storyText");
  container.innerHTML = "";
  const visibleBlocks = blocks.filter((block) => !["choice_prompt", "summary"].includes(block.type));
  const rows = visibleBlocks.length ? visibleBlocks : legacyTextBlocks(fallbackText);
  if (!rows.length) container.textContent = "暂无正文。";
  rows.forEach((block) => container.appendChild(renderMessageBlock(block)));
  scrollActiveFeed();
}

function renderMessageBlock(block) {
  const role = blockRole(block);
  const card = document.createElement("article");
  card.className = `msg ${role}`;
  card.dataset.blockType = block.type || "gm_narration";

  const avatar = document.createElement("div");
  avatar.className = "msgAvatar";
  if (role === "player" || role === "npc") {
    const canvas = document.createElement("canvas");
    canvas.width = 48;
    canvas.height = 48;
    avatar.appendChild(canvas);
    drawBlockAvatar(canvas, block, role);
  } else {
    avatar.textContent = role === "system" ? "检" : "叙";
  }

  const body = document.createElement("div");
  body.className = "msgBody";
  const title = document.createElement("strong");
  title.textContent = block.speaker || defaultSpeaker(block.type);
  const content = document.createElement("div");
  content.className = "msgText";
  content.textContent = block.body || "";
  body.append(title, content);
  const check = checkMeta(block);
  if (check) body.appendChild(check);

  const time = document.createElement("time");
  time.textContent = block.time || "现在";
  card.append(avatar, body, time);
  return card;
}

function renderChoicePanel(blocks, fallbackText) {
  const choiceBlock = blocks.find((block) => block.type === "choice_prompt");
  const holder = $("choicesText");
  if (!holder) return;
  holder.innerHTML = "";
  if (choiceBlock?.body) {
    const intro = document.createElement("div");
    intro.className = "choiceIntro";
    intro.textContent = choiceBlock.body;
    holder.appendChild(intro);
  }
  const choices = Array.isArray(choiceBlock?.choices) ? choiceBlock.choices : [];
  if (choices.length) {
    const grid = document.createElement("div");
    grid.className = "choiceGrid";
    choices.slice(0, 4).forEach((choice, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "choiceOption";
      const label = choice.label || choice.text || `选择 ${index + 1}`;
      button.innerHTML = `<b>${escapeHtml(label)}</b>${choice.risk ? `<small>${escapeHtml(choice.risk)}</small>` : ""}`;
      button.addEventListener("click", () => {
        const input = $("actionInput");
        if (input) {
          input.value = label;
          input.focus();
        }
      });
      grid.appendChild(button);
    });
    holder.appendChild(grid);
    return;
  }
  holder.textContent = choiceBlock?.body || fallbackText || "暂无选择点。";
}

function blockRole(block) {
  if (block.type === "player_action") return "player";
  if (block.type === "npc_dialogue") return "npc";
  if (block.type === "system_check") return "system";
  return "gm";
}

function defaultSpeaker(type) {
  if (type === "player_action") return "玩家";
  if (type === "npc_dialogue") return "NPC";
  if (type === "system_check") return "系统检定";
  return "GM 叙述";
}

function checkMeta(block) {
  const check = block.check || block.meta?.check;
  if (!check || typeof check !== "object") return null;
  const row = document.createElement("div");
  row.className = "checkMeta";
  const parts = [
    check.skill || check.name || check.type,
    check.roll ? `掷骰 ${check.roll}` : "",
    check.target ? `难度 ${check.target}` : "",
    check.result || check.outcome || "",
  ].filter(Boolean);
  row.textContent = parts.join(" · ");
  return parts.length ? row : null;
}

function legacyTextBlocks(text) {
  return String(text || "")
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part, index) => ({
      type: index % 6 === 3 ? "system_check" : "gm_narration",
      speaker: index % 6 === 3 ? "系统记录" : "GM 叙述",
      body: part,
      time: "现在",
    }));
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
  state.renderedMapKey = "";
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
  state.galleryFilter = filter || "all";
  document.querySelectorAll("#galleryFilters button").forEach((button) => {
    button.classList.toggle("active", button.dataset.filter === state.galleryFilter);
  });
  document.querySelectorAll("#galleryGrid article").forEach((card) => {
    card.classList.toggle("hidden", state.galleryFilter !== "all" && card.dataset.kind !== state.galleryFilter);
  });
}

function renderGallery(campaignState) {
  const grid = $("galleryGrid");
  if (!grid) return;
  const assets = buildVisualAssets(campaignState);
  grid.innerHTML = "";
  assets.forEach((asset) => {
    const card = document.createElement("article");
    card.dataset.kind = asset.kind;
    const canvas = document.createElement("canvas");
    canvas.width = asset.kind === "scene" ? 260 : 128;
    canvas.height = asset.kind === "scene" ? 120 : 128;
    canvas.className = "galleryCanvas";
    const title = document.createElement("b");
    title.textContent = asset.title;
    const meta = document.createElement("small");
    meta.textContent = asset.meta || galleryKindLabel(asset.kind);
    card.append(canvas, title, meta);
    grid.appendChild(card);
    drawGalleryAsset(canvas, asset);
  });
  setGalleryFilter(state.galleryFilter);
}

function buildVisualAssets(campaignState) {
  const recent = campaignState.recent || {};
  const scene = recent.current_scene || {};
  const rows = [];
  rows.push({
    kind: "scene",
    key: `map:${scene.location || state.activeCampaign || "current"}`,
    title: conciseTitle(scene.location || "当前区域地图", 18),
    meta: "地图",
    seed: scene.location || state.activeCampaign || "map",
    scene,
  });
  (scene.active_npcs || []).slice(0, 4).forEach((name) => {
    rows.push({
      kind: "npc",
      key: `npc:${name}`,
      title: name,
      meta: "NPC",
      seed: name,
    });
  });
  itemRows(campaignState).slice(-6).forEach((item, index) => {
    rows.push({
      kind: "item",
      key: `item:${item.title}:${index}`,
      title: conciseTitle(item.title, 20),
      meta: item.tag || "物品",
      seed: `${item.title}:${item.detail}`,
      detail: item.detail,
    });
  });
  monsterRows(campaignState).slice(-3).forEach((monster, index) => {
    rows.push({
      kind: "monster",
      key: `monster:${monster.title}:${index}`,
      title: conciseTitle(monster.title, 20),
      meta: monster.tag || "生态",
      seed: `${monster.title}:${monster.detail}`,
      detail: monster.detail,
    });
  });
  return dedupeAssets(rows).slice(0, 12);
}

function monsterRows(campaignState) {
  const rows = [
    ...normalizeFactRows(campaignState.ecology?.facts),
    ...normalizeFactRows(campaignState.world?.facts),
    ...clauseRows(campaignState.recent?.short_term_state?.resources, "生态"),
    ...clauseRows(campaignState.recent?.short_term_state?.injury_or_damage, "生态"),
  ];
  return rows.filter((row) => /怪物|土砂龙|迁徙|生态|痕迹|泥痕|驮兽|未知/.test(row.title + row.detail));
}

function dedupeAssets(rows) {
  const seen = new Set();
  return rows.filter((row) => {
    const key = slugify(row.key || row.title);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function conciseTitle(text, maxLen) {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  return clean.length > maxLen ? `${clean.slice(0, maxLen - 1)}…` : clean;
}

function galleryKindLabel(kind) {
  return { npc: "NPC", scene: "场景", item: "物品", monster: "生态" }[kind] || "资料";
}

function drawGalleryAsset(canvas, asset) {
  const kind = asset.kind === "scene" ? "gallery_map" : `gallery_${asset.kind}`;
  const subdir = asset.kind === "scene" ? "maps" : asset.kind === "npc" ? "portraits" : "items";
  const draw = () => {
    if (asset.kind === "scene") drawPixelMap(asset.seed, { cache: false, canvas, scene: asset.scene, compact: true });
    else if (asset.kind === "npc") drawPixelPortraitToCanvas(canvas, asset.seed, "npc");
    else if (asset.kind === "monster") drawCanvasMonster(canvas, asset);
    else drawCanvasItem(canvas, asset);
  };
  if (state.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      kind,
      subdir,
      objectId: slugify(asset.key || asset.title),
      seedText: asset.seed || asset.title,
      draw,
    });
    return;
  }
  draw();
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

function drawBlockAvatar(canvas, block, role) {
  const actorKey = block.avatar_key || block.actor_id || block.speaker || role;
  const kind = role === "npc" ? "npc_portrait" : "player_portrait";
  const draw = () => drawPixelPortraitToCanvas(canvas, actorKey, role);
  if (state.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      kind,
      subdir: "portraits",
      objectId: slugify(actorKey),
      seedText: actorKey,
      draw,
    });
    return;
  }
  draw();
}

function drawPixelPortraitToCanvas(canvas, seedText, role) {
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(`${role}:${seedText}`);
  const size = canvas.width;
  const cell = size / 24;
  const npc = role === "npc";
  const skin = ["#d9a36e", "#c58b5c", "#e0b17d", "#b9794f", "#9f6748"][seed % 5];
  const hair = ["#2b241c", "#463423", "#6b4a2e", "#1d2528", "#7a6a48"][(seed >>> 3) % 5];
  const cloth = role === "npc"
    ? ["#465a63", "#7a5c36", "#5c6642", "#6d4b55", "#66594a", "#31515a"][(seed >>> 6) % 6]
    : ["#31556b", "#704b2e", "#365747", "#533f65"][(seed >>> 6) % 4];
  const accent = ["#d6bc75", "#9eb0a2", "#b46d45", "#486d88", "#8d7650"][(seed >>> 11) % 5];
  const hairStyle = npc ? (seed >>> 14) % 5 : (seed >>> 14) % 3;
  const faceStyle = npc ? (seed >>> 18) % 5 : (seed >>> 18) % 3;
  const px = (x, y, w, h, color) => {
    ctx.fillStyle = color;
    ctx.fillRect(Math.round(x * cell), Math.round(y * cell), Math.ceil(w * cell), Math.ceil(h * cell));
  };
  const mirror = (x, y, w, h, color) => {
    px(x, y, w, h, color);
    px(24 - x - w, y, w, h, color);
  };
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, size, size);
  px(0, 0, 24, 24, npc ? ["#d8c4a4", "#c8b79b", "#d4c0aa"][(seed >>> 22) % 3] : "#d3c7b0");
  if (hairStyle === 0) {
    px(5, 3, 14, 4, hair);
    mirror(4, 5, 3, 3, hair);
  } else if (hairStyle === 1) {
    px(4, 2, 16, 3, hair);
    px(5, 5, 6, 3, hair);
    px(14, 5, 5, 2, hair);
  } else if (hairStyle === 2) {
    px(6, 2, 12, 2, hair);
    mirror(3, 4, 4, 7, hair);
  } else if (hairStyle === 3) {
    px(4, 4, 16, 3, hair);
    px(3, 2, 18, 2, "#24211b");
    px(5, 1, 14, 1, accent);
  } else {
    px(5, 2, 14, 5, hair);
    px(17, 5, 3, 5, hair);
  }
  px(6, 6, 12, 10, skin);
  mirror(5, 8, 2, 5, shadeColor(skin, -18));
  px(8, 8, 8, 5, "#e7bd89");
  if (faceStyle === 2) {
    mirror(8, 9, 3, 1, "#111816");
  } else {
    mirror(8, 9, 2, 1, "#111816");
  }
  px(11, 11, 2, 1, "#805338");
  px(9, 14, 6, faceStyle === 1 ? 2 : 1, (seed >>> 9) & 1 ? "#6b2e2e" : "#4e2c24");
  if (faceStyle === 3) px(7, 12, 2, 1, "#d9c08f");
  if (faceStyle === 4) px(10, 15, 5, 2, "#59412d");
  px(6, 16, 12, 5, cloth);
  mirror(3, 17, 4, 5, npc ? shadeColor(cloth, -18) : "#6a4a30");
  px(8, 16, 8, 1, accent);
  if (npc) {
    if ((seed >>> 24) & 1) {
      px(17, 5, 2, 6, "#7b6c50");
      px(18, 4, 1, 1, accent);
    } else {
      px(4, 6, 2, 6, "#6f5f45");
      px(18, 6, 2, 6, "#6f5f45");
    }
    if ((seed >>> 25) & 1) px(12, 4, 7, 2, "#1f2426");
    if ((seed >>> 26) & 1) px(7, 13, 10, 1, "#51321f");
  } else {
    px(17, 15, 4, 2, "#8f6530");
    px(18, 14, 2, 1, "#d6bc75");
  }
  px(4, 22, 16, 2, "#8f846f");
}

function shadeColor(hex, amount) {
  const raw = hex.replace("#", "");
  const num = parseInt(raw, 16);
  const r = Math.max(0, Math.min(255, (num >> 16) + amount));
  const g = Math.max(0, Math.min(255, ((num >> 8) & 255) + amount));
  const b = Math.max(0, Math.min(255, (num & 255) + amount));
  return `#${[r, g, b].map((x) => x.toString(16).padStart(2, "0")).join("")}`;
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
  const canvas = options.canvas || $("mapCanvas");
  if (!canvas) return;
  if (options.cache && state.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      kind: "map",
      subdir: "maps",
      objectId: options.objectId || slugify(seedText),
      seedText,
      draw: () => drawPixelMap(seedText, { cache: false, canvas, scene: options.scene, compact: options.compact }),
    });
    return;
  }
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  const seed = hashSeed(seedText);
  const scene = options.scene || {};
  ctx.imageSmoothingEnabled = true;
  drawMapPaper(ctx, w, h, seed);
  drawMapTerrain(ctx, w, h, seed);
  drawMapRoute(ctx, w, h, seed);
  drawMapNodes(ctx, w, h, seed, scene, Boolean(options.compact || h < 180));
}

function drawMapPaper(ctx, w, h, seed) {
  const g = ctx.createLinearGradient(0, 0, w, h);
  g.addColorStop(0, "#eadfca");
  g.addColorStop(.55, "#f6eedb");
  g.addColorStop(1, "#d6c3a1");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
  for (let i = 0; i < 360; i += 1) {
    const x = (i * 73 + seed) % w;
    const y = (i * 41 + (seed >>> 4)) % h;
    ctx.fillStyle = i % 2 ? "rgba(99,76,45,.055)" : "rgba(255,255,255,.11)";
    ctx.fillRect(x, y, 1.5, 1.5);
  }
}

function drawMapTerrain(ctx, w, h, seed) {
  const blob = (x, y, rw, rh, color, alpha) => {
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.ellipse(x, y, rw, rh, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  };
  blob(w * .78, h * .28, w * .23, h * .23, "#d5ad68", .34);
  blob(w * .86, h * .65, w * .2, h * .26, "#c69a5d", .22);
  blob(w * .26, h * .72, w * .22, h * .18, "#aebc8d", .24);
  ctx.save();
  ctx.strokeStyle = "rgba(127, 93, 55, .32)";
  ctx.lineWidth = Math.max(2, w / 260);
  for (let i = 0; i < 10; i += 1) {
    const x = w * .62 + i * w * .035;
    const y = h * .34 + Math.sin(i + seed) * h * .05;
    ctx.beginPath();
    ctx.moveTo(x - 22, y + 20);
    ctx.lineTo(x, y - 18);
    ctx.lineTo(x + 24, y + 20);
    ctx.stroke();
  }
  ctx.restore();
}

function drawMapRoute(ctx, w, h, seed) {
  const route = [[w * .12, h * .67], [w * .34, h * .58], [w * .55, h * .48], [w * .82, h * .36]];
  const creek = [[w * .06, h * .32], [w * .2, h * .42], [w * .36, h * .4], [w * .51, h * .52]];
  strokeCurve(ctx, creek, "rgba(78,135,157,.48)", Math.max(9, w / 38));
  strokeCurve(ctx, creek, "rgba(242,250,247,.42)", Math.max(2, w / 120));
  strokeCurve(ctx, route, "rgba(74,53,31,.22)", Math.max(16, w / 26));
  strokeCurve(ctx, route, "#8b6a3d", Math.max(8, w / 60));
  ctx.save();
  ctx.setLineDash([12, 12]);
  strokeCurve(ctx, route, "rgba(255,244,214,.48)", Math.max(2, w / 180));
  ctx.restore();
  const migration = [[w * .16, h * .82], [w * .34, h * .78], [w * .55, h * .69], [w * .72, h * .61]];
  ctx.save();
  ctx.setLineDash([10, 8]);
  strokeCurve(ctx, migration, "rgba(83,118,68,.78)", Math.max(6, w / 76));
  ctx.restore();
}

function drawMapNodes(ctx, w, h, seed, scene, compact) {
  const labels = mapLabels(scene);
  const nodes = [
    { label: labels[0], x: w * .17, y: h * .66, tone: "#b98634" },
    { label: labels[1], x: w * .44, y: h * .52, tone: "#4b7da8" },
    { label: labels[2], x: w * .67, y: h * .38, tone: "#b98634" },
  ];
  if (/泥|痕|药|货车|驮兽/.test(JSON.stringify(scene))) {
    nodes.push({ label: "可疑痕迹", x: w * .58, y: h * .28, tone: "#a74732" });
  }
  nodes.forEach((node) => drawMapNode(ctx, node, compact));
  ctx.save();
  ctx.font = `800 ${compact ? 22 : 42}px Microsoft YaHei`;
  ctx.fillStyle = "#536f45";
  ctx.strokeStyle = "rgba(255,250,239,.8)";
  ctx.lineWidth = compact ? 6 : 9;
  ctx.strokeText("异常迁徙 / 现场压力", w * .18, h * .9);
  ctx.fillText("异常迁徙 / 现场压力", w * .18, h * .9);
  ctx.restore();
}

function mapLabels(scene) {
  const text = String(scene.location || "");
  if (text.includes("长夜据点")) return ["前厅", "廊道", "货车"];
  if (text.includes("石溪") || text.includes("黄土")) return ["公会", "石溪道", "黄土峡口"];
  return ["起点", "现场", "远端"];
}

function drawMapNode(ctx, node, compact) {
  const cardW = compact ? 106 : 190;
  const cardH = compact ? 40 : 66;
  const x = Math.max(cardW / 2 + 8, Math.min(node.x, ctx.canvas.width - cardW / 2 - 8));
  const y = Math.max(cardH / 2 + 8, Math.min(node.y, ctx.canvas.height - cardH / 2 - 8));
  ctx.save();
  ctx.fillStyle = "rgba(255,250,239,.9)";
  ctx.strokeStyle = "rgba(73,48,25,.28)";
  roundRectPath(ctx, x - cardW / 2, y - cardH / 2, cardW, cardH, 10);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = node.tone;
  ctx.beginPath();
  ctx.arc(x - cardW / 2 + (compact ? 19 : 30), y, compact ? 8 : 15, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#3e3020";
  ctx.font = `800 ${compact ? 18 : 34}px Microsoft YaHei`;
  ctx.fillText(conciseTitle(node.label, compact ? 5 : 8), x - cardW / 2 + (compact ? 34 : 58), y + (compact ? 6 : 12));
  ctx.restore();
}

function strokeCurve(ctx, points, color, width) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(points[0][0], points[0][1]);
  for (let i = 1; i < points.length - 1; i += 1) {
    const midX = (points[i][0] + points[i + 1][0]) / 2;
    const midY = (points[i][1] + points[i + 1][1]) / 2;
    ctx.quadraticCurveTo(points[i][0], points[i][1], midX, midY);
  }
  const last = points[points.length - 1];
  ctx.lineTo(last[0], last[1]);
  ctx.stroke();
  ctx.restore();
}

function drawCanvasItem(canvas, asset) {
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(asset.seed || asset.title);
  drawIconBase(ctx, canvas.width, canvas.height, "#cfb88d", "#7f603d");
  const text = `${asset.title}${asset.detail || ""}`;
  if (/泥|痕/.test(text)) return drawMudIcon(ctx, canvas.width, canvas.height, seed);
  if (/药|瓶/.test(text)) return drawBottleIcon(ctx, canvas.width, canvas.height, seed);
  if (/斧|装备|武器/.test(text)) return drawAxeIcon(ctx, canvas.width, canvas.height, seed);
  if (/登记|任务板|木牌|记录/.test(text)) return drawSignIcon(ctx, canvas.width, canvas.height, seed);
  if (/羽|鳞|素材|碎片/.test(text)) return drawScaleIcon(ctx, canvas.width, canvas.height, seed);
  return drawSatchelIcon(ctx, canvas.width, canvas.height, seed);
}

function drawCanvasMonster(canvas, asset) {
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(asset.seed || asset.title);
  drawIconBase(ctx, canvas.width, canvas.height, "#9ea889", "#4f6348");
  ctx.fillStyle = "#715332";
  for (let i = 0; i < 5; i += 1) {
    ctx.beginPath();
    ctx.ellipse(40 + i * 12, 74 - i * 5, 18, 8, -.35, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.strokeStyle = "#3f3022";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(32, 38);
  ctx.quadraticCurveTo(65, 12, 96, 42);
  ctx.stroke();
  ctx.fillStyle = (seed & 1) ? "#d5b86a" : "#b08a4e";
  ctx.beginPath();
  ctx.arc(66, 45, 14, 0, Math.PI * 2);
  ctx.fill();
}

function drawIconBase(ctx, w, h, bg1, bg2) {
  const g = ctx.createLinearGradient(0, 0, w, h);
  g.addColorStop(0, bg1);
  g.addColorStop(1, bg2);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = "rgba(72,48,26,.28)";
  ctx.lineWidth = 4;
  roundRectPath(ctx, 9, 9, w - 18, h - 18, 16);
  ctx.stroke();
}

function drawMudIcon(ctx, w, h) {
  ctx.fillStyle = "#69482d";
  for (let i = 0; i < 14; i += 1) {
    ctx.beginPath();
    ctx.ellipse(32 + (i * 17) % 56, 34 + (i * 11) % 48, 10, 5, i, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.strokeStyle = "#2f241a";
  ctx.lineWidth = 5;
  [34, 56].forEach((x) => {
    ctx.beginPath();
    ctx.moveTo(x, 82);
    ctx.quadraticCurveTo(x + 10, 56, x + 28, 70);
    ctx.stroke();
  });
}

function drawBottleIcon(ctx, w, h) {
  ctx.fillStyle = "#dbe9c9";
  roundRectPath(ctx, w * .42, h * .26, w * .22, h * .48, 8);
  ctx.fill();
  ctx.fillStyle = "#6f8f65";
  ctx.fillRect(w * .47, h * .18, w * .12, h * .13);
  ctx.fillStyle = "rgba(167,71,50,.72)";
  ctx.fillRect(w * .44, h * .54, w * .18, h * .17);
  ctx.strokeStyle = "#6b4c32";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(w * .24, h * .76);
  ctx.lineTo(w * .72, h * .83);
  ctx.stroke();
}

function drawAxeIcon(ctx, w, h) {
  ctx.strokeStyle = "#4c3824";
  ctx.lineWidth = 9;
  ctx.beginPath();
  ctx.moveTo(w * .28, h * .78);
  ctx.lineTo(w * .7, h * .25);
  ctx.stroke();
  ctx.fillStyle = "#d1bc84";
  ctx.beginPath();
  ctx.moveTo(w * .63, h * .18);
  ctx.lineTo(w * .88, h * .32);
  ctx.lineTo(w * .62, h * .45);
  ctx.closePath();
  ctx.fill();
}

function drawSignIcon(ctx, w, h) {
  ctx.fillStyle = "#704820";
  roundRectPath(ctx, w * .22, h * .36, w * .56, h * .25, 5);
  ctx.fill();
  ctx.fillStyle = "#ead2a0";
  ctx.fillRect(w * .3, h * .45, w * .36, h * .04);
  ctx.fillRect(w * .3, h * .53, w * .46, h * .04);
  ctx.fillStyle = "#5b3b20";
  ctx.fillRect(w * .47, h * .62, w * .08, h * .24);
}

function drawScaleIcon(ctx, w, h) {
  for (let i = 0; i < 4; i += 1) {
    ctx.fillStyle = ["#d4c37c", "#a7904f", "#6d744f", "#e2d08a"][i];
    ctx.beginPath();
    ctx.moveTo(w * (.28 + i * .08), h * (.68 - i * .05));
    ctx.quadraticCurveTo(w * (.43 + i * .07), h * .22, w * (.73 + i * .02), h * (.55 - i * .03));
    ctx.quadraticCurveTo(w * (.52 + i * .04), h * .78, w * (.28 + i * .08), h * (.68 - i * .05));
    ctx.fill();
  }
}

function drawSatchelIcon(ctx, w, h) {
  ctx.fillStyle = "#8b6036";
  roundRectPath(ctx, w * .24, h * .38, w * .54, h * .36, 10);
  ctx.fill();
  ctx.fillStyle = "#b98a53";
  roundRectPath(ctx, w * .31, h * .29, w * .4, h * .18, 8);
  ctx.fill();
  ctx.strokeStyle = "#4f3620";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(w * .36, h * .5);
  ctx.lineTo(w * .72, h * .63);
  ctx.stroke();
  ctx.fillStyle = "#d9bd73";
  ctx.fillRect(w * .46, h * .53, w * .1, h * .1);
}

function roundRectPath(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
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
    if (saved.url) updateMapImageIfNeeded(canvas, saved.url);
  } catch (err) {
    console.warn("asset cache failed", err);
    state.assetCache[key] = null;
    draw();
    updateMapImageIfNeeded(canvas, canvas.toDataURL("image/png"));
  }
}

function drawImageToCanvas(canvas, url, fallback) {
  const image = new Image();
  image.onload = () => {
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    updateMapImageIfNeeded(canvas, image.src);
  };
  image.onerror = () => {
    if (fallback) fallback();
  };
  image.src = `${url}?v=${ASSET_GENERATOR_VERSION}`;
}

function updateMapImageIfNeeded(canvas, url) {
  if (canvas.id !== "mapCanvas") return;
  const image = $("mapImage");
  if (image && url) image.src = url;
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
