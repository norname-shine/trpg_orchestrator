const state = {
  campaigns: [],
  activeCampaign: "",
  selectedCampaign: "",
  polling: null,
  sideTab: "quests",
  activePanel: "story",
  autoScroll: false,
  lastJobRunning: false,
  lastCampaignState: {},
  assetCache: {},
  collapsedPanels: {
    map: false,
    task: false,
    memory: false,
  },
  galleryFilter: "all",
  galleryFilterIds: ["all", "cg", "monster", "npc", "scene", "item"],
  renderedMapKey: "",
  canvasRules: "",
  galleryAssets: [],
  cachedAssets: [],
  storyTurnsByCampaign: {},
  storyTurnSignatures: {},
  selectedGalleryKey: "",
  transientGalleryAsset: null,
  currentMapAsset: null,
  writebackReview: {},
  currentPressurePack: {},
  ruleFiles: [],
  selectedRule: "",
  frontendState: {},
  assetSeed: "",
  runProgress: {
    active: false,
    percent: 0,
    target: 0,
    timer: null,
    hideTimer: null,
  },
};

const $ = (id) => document.getElementById(id);
const ASSET_GENERATOR_VERSION = 16;

function init() {
  drawBackground();
  drawPixelAvatar("TRPG", { cache: false });
  drawPixelMap("TRPG", { cache: false, force: true });
  bindControls();
  hidePlayerHiddenAdminPanels();
  applyCollapseState();
  loadCanvasRules();
  refresh();
  state.polling = setInterval(refresh, 2500);
}

function bindControls() {
  $("runTurnBtn").addEventListener("click", runTurn);
  $("refreshBtn").addEventListener("click", refresh);
  $("exportBtn").addEventListener("click", exportCampaign);
  $("memoryReportBtn").addEventListener("click", loadMemoryReport);
  document.querySelectorAll("[data-quick]").forEach((button) => {
    button.addEventListener("click", () => applyQuickAction(button.dataset.quick));
  });
  document.getElementById("companionAvatarWrap")?.addEventListener("click", () => {
    insertCompanionMention();
  });
  document.getElementById("viewCompanionDataBtn")?.addEventListener("click", () => {
    openCompanionOverlay();
  });
  $("closeCompanionOverlay")?.addEventListener("click", closeCompanionOverlay);
  $("companionOverlay")?.addEventListener("click", (event) => {
    if (event.target.id === "companionOverlay") closeCompanionOverlay();
  });
  $("viewAllBtn").addEventListener("click", openGalleryOverlay);
  document.querySelector(".mapCanvas")?.addEventListener("click", () => openCurrentMapOverlay());
  document.querySelector(".mapCanvas")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openCurrentMapOverlay();
    }
  });
  $("closeGalleryOverlay").addEventListener("click", closeGalleryOverlay);
  $("galleryOverlay").addEventListener("click", (event) => {
    if (event.target.id === "galleryOverlay") closeGalleryOverlay();
  });
  $("closeCgOverlay")?.addEventListener("click", closeCgOverlay);
  $("cgOverlay")?.addEventListener("click", (event) => {
    if (event.target.id === "cgOverlay") closeCgOverlay();
  });
  $("useGalleryAssetBtn").addEventListener("click", useSelectedGalleryAsset);
  $("rulesBtn").addEventListener("click", openRulesBrowser);
  $("closeRulesOverlay").addEventListener("click", closeRulesOverlay);
  $("rulesOverlay").addEventListener("click", (event) => {
    if (event.target.id === "rulesOverlay") closeRulesOverlay();
  });
  $("rulesSearchBtn").addEventListener("click", () => loadRulesDirectory($("rulesSearch").value.trim()));
  $("rulesClearBtn").addEventListener("click", () => {
    $("rulesSearch").value = "";
    loadRulesDirectory("");
  });
  $("rulesSearch").addEventListener("keydown", (event) => {
    if (event.key === "Enter") loadRulesDirectory($("rulesSearch").value.trim());
  });
  $("refreshWritebackBtn").addEventListener("click", loadWritebackReview);
  $("auditWritebackBtn").addEventListener("click", auditWriteback);
  $("applyWritebackBtn").addEventListener("click", applyWriteback);
  $("newCampaignPageBtn").addEventListener("click", () => {
    window.location.href = "/new-campaign-demo.html";
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
    if (event.key === "Escape") closeGalleryOverlay();
    if (event.key === "Escape") closeCgOverlay();
    if (event.key === "Escape") closeRulesOverlay();
    if (event.key === "Escape") closeCompanionOverlay();
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
  await startJob("/api/run-turn", { action, campaign_id: state.activeCampaign }, { storyProgress: true, clearInputOnSuccess: true });
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

function exportCampaign() {
  const params = state.activeCampaign ? `?campaign_id=${encodeURIComponent(state.activeCampaign)}` : "";
  window.open(`/api/export-campaign${params}`, "_blank");
}

async function startJob(path, payload, options = {}) {
  try {
    setBusy(true);
    if (options.storyProgress) {
      showPanel("story");
      beginRunProgress();
      scrollStoryToBottom(true);
      setLog("命令已提交，后台开始执行。");
    } else {
      showPanel("logs");
      setLog("命令已提交，后台开始执行。");
    }
    await api(path, { method: "POST", body: JSON.stringify(payload) });
    if (options.clearInputOnSuccess) {
      const input = $("actionInput");
      if (input) input.value = "";
    }
    await refresh();
  } catch (err) {
    setBusy(false, true);
    showPanel("logs");
    setLog(err.message);
  }
}

async function refresh() {
  try {
    const data = await api("/api/frontend-state");
    state.frontendState = data.frontend_state || {};
    state.assetSeed = state.frontendState.asset_seed || state.frontendState.campaign?.asset_seed || state.activeCampaign || "";
    state.currentPressurePack = data.output?.pressure_pack || {};
    state.cachedAssets = Array.isArray(data.assets) ? data.assets : [];
    renderStatus(data);
    updateRunProgressFromPipeline(data.pipeline || {}, data.job || {}, data.output || {});
    renderFrontendState(state.frontendState, data.campaign_state || {});
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
  renderCachedAvatar(data.campaign_state || {});
  renderModule("map_panel", state.frontendState?.modules?.map_panel || state.frontendState?.map_panel || {}, state.frontendState || {}, data.campaign_state || {});

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

async function loadCanvasRules() {
  try {
    const data = await api("/api/canvas-rules");
    state.canvasRules = data.rules || "";
  } catch (err) {
    console.warn("canvas rules unavailable", err);
    state.canvasRules = "";
  }
}

async function loadCachedAssets() {
  if (!state.activeCampaign) {
    state.cachedAssets = [];
    return;
  }
  try {
    const data = await api(`/api/assets?campaign_id=${encodeURIComponent(state.activeCampaign)}`);
    state.cachedAssets = Array.isArray(data.assets) ? data.assets : [];
  } catch (err) {
    console.warn("asset list unavailable", err);
    state.cachedAssets = [];
  }
}

function renderCachedMap(scene, mapPanel = {}) {
  const modulePayload = mapPanel.payload || mapPanel.latest_map || {};
  const mode = mapPanel.mode || (mapPanel.keep_previous ? "keep_previous" : "none");
  const updateRequested = mapPanel.update_requested === true;
  const seed = scene.location || state.activeCampaign || "map";
  const route = modulePayload.map_route || {};
  const mapCanvas = modulePayload.map_canvas || {};
  const routeKey = mapCanvas.title || route.title || (route.nodes || []).map((node) => node.label || node.id).join("_");
  setText("mapLabel", route.title || modulePayload.title || scene.location || "当前路线");
  if (!updateRequested || mode === "keep_previous" || mode === "none") {
    state.currentMapAsset = {
      kind: "scene",
      key: modulePayload.asset_key || "",
      title: modulePayload.title || scene.location || "当前区域地图",
      meta: "当前地图",
      detail: routeKey || scene.immediate_pressure || "当前展示的区域地图。",
      seed: scopedSeed(seed),
      scene: { ...scene, map_route: route, map_canvas: mapCanvas },
      cachedUrl: modulePayload.url || "",
      status: "cached",
    };
    if (modulePayload.url) setAssetImage($("mapImage"), modulePayload.url);
    return;
  }
  if (!Array.isArray(route.nodes) || !route.nodes.length) {
    console.warn("skip map redraw: empty route payload", mapPanel);
    return;
  }
  const objectId = slugify(`${scene.location || "current_map"}:${routeKey || "base"}`);
  const mapKey = `${state.activeCampaign}:${objectId}:v${ASSET_GENERATOR_VERSION}`;
  const mapScene = { ...scene, map_route: route, map_canvas: mapCanvas };
  state.currentMapAsset = {
    kind: "scene",
    key: `current_map:${mapKey}`,
    title: route.title || scene.location || "当前区域地图",
    meta: "当前地图",
    detail: routeKey || scene.immediate_pressure || "当前展示的区域地图。",
    seed: scopedSeed(seed),
    scene: mapScene,
    cachedUrl: modulePayload.url || "",
    status: "current",
  };
  if (state.renderedMapKey === mapKey) return;
  state.renderedMapKey = mapKey;
  const mapWrap = document.querySelector(".mapCanvas");
  if (mapWrap) {
    mapWrap.tabIndex = 0;
    mapWrap.setAttribute("role", "button");
    mapWrap.setAttribute("aria-label", "打开完整区域地图");
  }
  drawPixelMap(seed, {
    cache: true,
    objectId,
    scene: mapScene,
    metadata: {
      title: route.title || scene.location || "当前区域地图",
      detail: routeKey || scene.immediate_pressure || "",
      meta: "地图 / 结构化路线",
      source: "map_route",
      object_id: objectId,
      map_route: route,
      map_canvas: mapCanvas,
      visual_assets: modulePayload.visual_assets || [],
      status: "current",
    },
    force: true,
  });
}

function renderCachedAvatar(campaignState = {}) {
  const characterName = extractPlayerName(campaignState.player || {}, campaignState.character_prompt || {}) || "player";
  const playerFeedback = formalPortraitFeedbackAsset(characterName, characterName, "player");
  if (playerFeedback?.url && $("avatarImage")) setAssetImage($("avatarImage"), playerFeedback.url);
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
  const fallback = characterFallback(campaignState, name, scene);
  const fallbackRole = fallback.meta || campaignState.genre || "身份待确认";
  const progression = normalizeProgression(provided.progression, mode, fallback);
  const companionSource = provided.companion || prompt.companion_card || identity.companion || null;
  return {
    mode,
    name,
    meta: roleParts.length ? roleParts.join(" / ") : fallbackRole,
    progression,
    vitals: normalizeVitals(provided.vitals, mode, fallback),
    conditions: normalizeConditions(provided.conditions, campaignState, scene),
    attributes: normalizeAttributes(provided.attributes, mode, fallback),
    companion: normalizeCompanion(companionSource),
  };
}

function hidePlayerHiddenAdminPanels() {
  document.querySelectorAll('[data-panel-tab="director"], [data-panel-tab="writeback"]').forEach((button) => {
    button.hidden = true;
    button.classList.add("hidden");
  });
}

function renderFrontendState(frontendState, campaignState) {
  const fs = frontendState || {};
  const modules = fs.modules || {};
  state.lastCampaignState = campaignState;
  renderCharacterCard(protocolCharacterCard(fs.character_card, campaignState));
  renderCompanionCard(protocolCompanionCard(fs.companion_card, campaignState));
  ["story_progress", "map_panel", "gallery", "inventory", "dossier", "character_card", "canvas_jobs"].forEach((name) => {
    renderModule(name, modules[name], fs, campaignState);
  });
  renderSidePanel(campaignState, fs);
  renderMemoryPanel(campaignState);
  if (!modules.gallery || modules.gallery.mode !== "no_update") {
    renderGalleryFilters(fs.gallery?.filters || []);
    renderGallery(campaignState, fs.gallery || {}, modules.gallery);
  }
  renderQuickActions(fs.quick_actions || []);
}

function renderModule(name, moduleState = {}, frontendState = {}, campaignState = {}) {
  if (!moduleState) return;
  if (moduleState.mode === "hidden" || moduleState.mode === "admin_only") return;
  if (moduleState.mode === "no_update") return;
  if (moduleState.mode === "keep_previous") return keepPreviousModule(name, moduleState);
  if (name === "story_progress") return renderStoryProgressModule(moduleState);
  if (name === "map_panel") return updateMapModule(moduleState, campaignState);
  if (name === "gallery") return updateGalleryModule(moduleState, campaignState);
  if (name === "inventory") return updateInventoryModule(moduleState);
  if (name === "dossier") return updateDossierModule(moduleState);
  if (name === "character_card") return updateCharacterCardModule(moduleState, campaignState);
  if (name === "canvas_jobs") return processCanvasJobs(moduleState, frontendState, campaignState);
}

function keepPreviousModule(name, moduleState = {}) {
  if (name !== "map_panel") return;
  const ref = moduleState.payload_ref || moduleState.payload?.url || "";
  if (ref && !ref.startsWith("asset://") && $("mapImage")) setAssetImage($("mapImage"), ref);
}

function updateMapModule(moduleState = {}, campaignState = {}) {
  if (moduleState.mode !== "update" || moduleState.update_requested !== true) return;
  renderCachedMap(campaignState?.recent?.current_scene || {}, moduleState);
}

function updateGalleryModule(moduleState = {}, campaignState = {}) {
  if (moduleState.mode !== "update" || moduleState.update_requested !== true) return;
  renderGallery(campaignState, { module_payload: moduleState.payload || {} }, moduleState);
}

function updateInventoryModule(moduleState = {}) {
  if (moduleState.mode !== "update" || moduleState.update_requested !== true) return;
  state.latestInventoryPayload = moduleState.payload || [];
}

function updateDossierModule(moduleState = {}) {
  if (moduleState.mode !== "update" || moduleState.update_requested !== true) return;
  state.latestDossierPayload = moduleState.payload || [];
}

function updateCharacterCardModule(moduleState = {}, campaignState = {}) {
  if (moduleState.mode !== "update" || moduleState.update_requested !== true || !moduleState.payload) return;
  renderCharacterCard(protocolCharacterCard(moduleState.payload, campaignState));
}

function processCanvasJobs(moduleState = {}, frontendState = {}, campaignState = {}) {
  if (moduleState.mode !== "update" || moduleState.update_requested !== true) return;
  const jobs = Array.isArray(moduleState.payload) ? moduleState.payload : [];
  if (!jobs.length) return;
  jobs.forEach((job) => {
    if (!isValidCanvasJob(job)) {
      console.warn("skip invalid canvas job", job);
      return;
    }
    if (job.kind === "map") {
      const mapModule = frontendState.modules?.map_panel || {};
      const payload = mapModule.payload || {};
      const route = payload.map_route || {};
      if (!Array.isArray(route.nodes) || !route.nodes.length) {
        console.warn("skip map canvas job without route nodes", job);
        return;
      }
      renderCachedMap(campaignState?.recent?.current_scene || {}, { mode: "update", update_requested: true, payload });
      return;
    }
    if (job.kind === "portrait") {
      const card = frontendState.modules?.character_card?.payload || frontendState.character_card || {};
      const seed = card.name || job.asset_key || state.activeCampaign || "portrait";
      drawPixelAvatar(seed, {
        cache: true,
        objectId: slugify(job.asset_key),
        seedText: scopedSeed(`${state.activeCampaign}:${job.asset_key}`),
        variant: "npc",
      });
      return;
    }
    console.warn("canvas job kind deferred", job.kind);
  });
}

function isValidCanvasJob(job) {
  if (!job || typeof job !== "object") return false;
  const required = ["job_id", "kind", "renderer", "trigger", "input_ref", "asset_key", "cache_policy"];
  if (required.some((key) => !String(job[key] || "").trim())) return false;
  const text = required.map((key) => String(job[key] || "").toLowerCase()).join(" ");
  if (text.includes("placeholder") || text.includes("todo") || text.includes("tbd")) return false;
  if (!state.activeCampaign || !state.assetSeed) return false;
  return true;
}

function renderStoryProgressModule(moduleState = {}) {
  const payload = moduleState.payload || state.frontendState?.story_progress || {};
  const panel = $("storyProgressPanel");
  if (!panel) return;
  if (payload.enabled === false) {
    panel.classList.remove("hidden");
    setText("storyPace", "idle");
    setText("storyOverallProgress", "0%");
    setText("storyChapterName", "当前章节");
    setText("storyChapterProgress", "0%");
    setText("storyNodeName", "当前节点");
    setText("storyNodeProgress", "0%");
    setText("storyProgressStatus", payload.status_text || "未启用结构化故事进度");
    const bar = $("storyOverallBar");
    if (bar) bar.style.width = "0%";
    return;
  }
  const overall = clampPercent(payload.overall_progress);
  const chapter = payload.current_chapter || {};
  const node = payload.current_node || {};
  panel.classList.remove("hidden");
  setText("storyPace", payload.pace_command || "normal");
  setText("storyOverallProgress", `${overall}%`);
  setText("storyChapterName", chapter.name || "当前章节");
  setText("storyChapterProgress", `${clampPercent(payload.chapter_progress ?? chapter.progress)}%`);
  setText("storyNodeName", node.name || "当前节点");
  setText("storyNodeProgress", `${clampPercent(payload.node_progress ?? node.progress)}%`);
  setText("storyProgressStatus", payload.status_text || payload.progress_label || "故事进度正常。");
  const bar = $("storyOverallBar");
  if (bar) bar.style.width = `${overall}%`;
}

function clampPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(0, Math.min(100, Math.round(number)));
}

function protocolCharacterCard(card = {}, campaignState = {}) {
  if (!card || !card.name) {
    const title = campaignState.title || campaignTitle(state.activeCampaign) || "未命名跑团";
    const scene = campaignState.recent?.current_scene || {};
    return buildCharacterCard(campaignState, title, scene);
  }
  return {
    mode: "narrative_status",
    name: card.name,
    meta: card.identity || "身份待确认",
    progression: {
      label: card.progress?.label || "进展",
      value: card.progress?.text || "",
      percent: Number(card.progress?.percent || 0),
    },
    vitals: (card.core_stats || []).map((stat, index) => {
      const current = Number(stat.current);
      const max = Number(stat.max) || 100;
      return {
        key: stat.key || `core_${index}`,
        label: stat.label || "状态",
        state: stat.text || (Number.isFinite(current) ? `${current} / ${max}` : ""),
        percent: Number.isFinite(current) ? Math.max(0, Math.min(100, (current / max) * 100)) : 0,
        tone: stat.tone || ["red", "blue", "green"][index % 3],
        current,
        max,
      };
    }),
    conditions: Array.isArray(card.tags) ? card.tags : [],
    attributes: Array.isArray(card.attributes) ? card.attributes : [],
    companion: protocolCompanionCard(state.frontendState?.companion_card, campaignState),
  };
}

function protocolCompanionCard(companion = {}, campaignState = {}) {
  if (companion && companion.name) {
    const raw = companion.meta || companion;
    return {
      name: companion.name,
      meta: companion.identity || companion.archetype || "伙伴",
      seed: raw.visual_seed || companion.visual_seed || companion.portrait?.asset_key || companion.name,
      archetype: companion.archetype || "companion",
      raw,
    };
  }
  const title = campaignState.title || campaignTitle(state.activeCampaign) || "未命名跑团";
  const scene = campaignState.recent?.current_scene || {};
  return buildCharacterCard(campaignState, title, scene).companion;
}

function renderQuickActions(actions) {
  const composer = document.querySelector(".composer");
  if (!composer || !Array.isArray(actions) || !actions.length) return;
  let bar = composer.querySelector(".globalActionBar");
  if (!bar) {
    bar = document.createElement("div");
    bar.className = "globalActionBar";
    const input = composer.querySelector(".inputWrap");
    composer.insertBefore(bar, input || composer.firstChild);
  }
  bar.innerHTML = "";
  actions.forEach((action) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = action.label || action.action;
    button.addEventListener("click", () => applyQuickAction(action.action || action.label || ""));
    bar.appendChild(button);
  });
  // 在末尾添加"清空输入"按钮
  const clearBtn = document.createElement("button");
  clearBtn.type = "button";
  clearBtn.textContent = "清空输入";
  clearBtn.addEventListener("click", () => {
    const input = $("actionInput");
    if (input) { input.value = ""; input.focus(); }
  });
  bar.appendChild(clearBtn);
}

function applyQuickAction(action) {
  const input = $("actionInput");
  if (!input || !action) return;
  input.value = action;
  input.focus();
  if (action === "继续" || action === "复盘") runTurn();
}

function characterFallback(campaignState, name, scene = {}) {
  const text = normalizeActorName(`${state.activeCampaign} ${campaignState.title || ""} ${campaignState.genre || ""} ${campaignState.tone || ""} ${name}`);
  const pressured = Boolean(scene?.immediate_pressure);
  if (text.includes("coc") || text.includes("克苏鲁") || text.includes("调查")) {
    return {
      kind: "coc",
      meta: "COC 调查员",
      progression: { label: "调查进展", value: pressured ? "线索初开，风险升高" : "案件导入，保持观察", percent: pressured ? 38 : 24 },
      vitals: [
        { key: "health", label: "生命值", state: "未受伤", percent: 84, tone: "red" },
        { key: "sanity", label: "理智值", state: pressured ? "轻微动摇" : "稳定", percent: pressured ? 68 : 78, tone: "blue" },
        { key: "stamina", label: "体力值", state: "潮湿疲惫", percent: 70, tone: "green" },
      ],
      attributes: [
        { label: "侦", text: "观察" },
        { label: "图", text: "资料" },
        { label: "说", text: "话术" },
        { label: "潜", text: "隐蔽" },
        { label: "医", text: "急救" },
        { label: "稳", text: "理智" },
      ],
    };
  }
  if (text.includes("dnd") || text.includes("奇幻") || text.includes("冒险者")) {
    return {
      kind: "dnd",
      meta: "DND 队伍代表",
      progression: { label: "冒险进展", value: pressured ? "任务展开，局势紧张" : "第一章，接受委托", percent: pressured ? 34 : 22 },
      vitals: [
        { key: "health", label: "生命值", state: "可战斗", percent: 86, tone: "red" },
        { key: "focus", label: "专注值", state: "警戒", percent: 74, tone: "blue" },
        { key: "stamina", label: "体力值", state: "整备中", percent: 80, tone: "green" },
      ],
      attributes: [
        { label: "力", text: "近战" },
        { label: "敏", text: "闪避" },
        { label: "体", text: "耐久" },
        { label: "智", text: "知识" },
        { label: "感", text: "察觉" },
        { label: "魅", text: "交涉" },
      ],
    };
  }
  if (text.includes("fate") || text.includes("圣杯") || text.includes("御主") || text.includes("从者")) {
    return {
      kind: "fate",
      meta: "普通高中生 / 新任御主",
      progression: { label: "同步状态", value: pressured ? "令咒完整，黑痕扩散" : "契约未稳，异常同步", percent: pressured ? 45 : 32 },
      vitals: [
        { key: "health", label: "生命值", state: pressured ? "惊惧疲惫" : "可行动", percent: 72, tone: "red" },
        { key: "focus", label: "专注值", state: "受干扰", percent: 54, tone: "blue" },
        { key: "stamina", label: "体力值", state: "奔逃后消耗", percent: 58, tone: "green" },
      ],
      attributes: [
        { label: "令", text: "令咒" },
        { label: "脉", text: "灵脉" },
        { label: "逃", text: "撤退" },
        { label: "察", text: "观察" },
        { label: "匣", text: "井匣" },
        { label: "契", text: "从者" },
      ],
    };
  }
  return {
    kind: "monster_hunter",
    meta: name === "Lee" ? "新晋猎人 / 斩斧 / 正式猎人" : "猎人 / 生态调查",
    progression: { label: "成长", value: "新人阶段，稳步成长", percent: 42 },
    vitals: [
      { key: "health", label: "生命值", state: "状态良好", percent: 82, tone: "red" },
      { key: "focus", label: "专注值", state: "稳定", percent: 78, tone: "blue" },
      { key: "stamina", label: "体力值", state: "有消耗", percent: 72, tone: "green" },
    ],
    attributes: [
      { label: "斧", text: "牵制" },
      { label: "剑", text: "爆发" },
      { label: "迹", text: "追踪" },
      { label: "营", text: "补给" },
      { label: "捕", text: "陷阱" },
      { label: "退", text: "保命" },
    ],
  };
}

function normalizeCompanion(companion) {
  if (!companion || typeof companion !== "object") return null;
  const name = String(companion.name || "").trim();
  if (!name) return null;
  const archetype = companion.archetype || companion.species || companion.kind || companion.type || inferCompanionArchetype(name, companion.meta || companion.personality || "");
  const rawMeta = companion.personality || companion.meta || defaultCompanionMeta(archetype);
  return {
    name,
    meta: companionDisplayMeta(rawMeta, archetype),
    seed: companion.visual_seed || `companion:${state.activeCampaign}:${name}`,
    archetype,
    raw: companion,
  };
}

function defaultCompanionMeta(archetype) {
  if (normalizeActorName(archetype).includes("palico")) return "老练但嘴硬";
  if (normalizeActorName(archetype).includes("servant")) return "从者 / 契约伙伴";
  return "同行伙伴";
}

function companionDisplayMeta(meta, archetype) {
  const type = normalizeActorName(archetype);
  const text = String(meta || "").trim();
  if (type.includes("palico") && !/艾露猫|艾鲁猫|palico/i.test(text)) return `艾露猫 / ${text || "同行伙伴"}`;
  if (type.includes("servant") && !/从者|英灵|servant/i.test(text)) return `从者 / ${text || "契约伙伴"}`;
  return text || "同行伙伴";
}

function inferCompanionArchetype(name, meta = "") {
  const text = normalizeActorName(`${state.activeCampaign} ${name} ${meta}`);
  if (text.includes("fate") || text.includes("servant") || text.includes("从者") || text.includes("英灵")) return "servant";
  if (text.includes("monsterhunter") || text.includes("怪猎") || text.includes("艾露") || text.includes("艾鲁") || text.includes("palico") || text.includes("浩文")) return "palico";
  return "companion";
}

function hasStrictVitals(vitals) {
  return Array.isArray(vitals) && vitals.some((item) => Number.isFinite(item?.current) && Number.isFinite(item?.max));
}

function hasStrictAttributes(attributes) {
  return Array.isArray(attributes) && attributes.some((item) => Number.isFinite(item?.value));
}

function normalizeProgression(progress, mode, fallback = {}) {
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
    label: source.label || fallback.progression?.label || (mode === "strict_stats" ? "经验值" : "成长"),
    value: source.text || fallback.progression?.value || "新人阶段，稳步成长",
    percent: Number.isFinite(Number(source.percent)) ? Number(source.percent) : (fallback.progression?.percent || 42),
  };
}

function normalizeVitals(vitals, mode, fallback = {}) {
  if (Array.isArray(vitals) && vitals.length) {
    return vitals.map((item, index) => normalizeVital(item, index, mode));
  }
  return fallback.vitals || [
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
  const kind = characterFallback(campaignState, extractPlayerName(campaignState.player || {}, campaignState.character_prompt || {}), scene).kind;
  if (kind === "coc") {
    return ["谨慎", mechanics.use_dice ? "COC检定" : "叙事调查", "潮湿", scene?.immediate_pressure ? "线索压力" : "案件导入"];
  }
  if (kind === "dnd") {
    return ["警戒", mechanics.use_dice ? "D20检定" : "叙事冒险", "整备", scene?.immediate_pressure ? "任务压力" : "酒馆待命"];
  }
  if (kind === "fate") {
    return ["怕死", "令咒完整", "异常同步", scene?.immediate_pressure ? "黑痕压力" : "契约未稳"];
  }
  return [
    "谨慎",
    mechanics.use_dice ? "严格数值" : "叙事判定",
    "斩斧",
    scene?.immediate_pressure ? "任务压力" : "整备中",
  ];
}

function normalizeAttributes(attributes, mode, fallback = {}) {
  if (Array.isArray(attributes) && attributes.length) {
    return attributes.map((item) => {
      if (typeof item === "string") return { label: item.slice(0, 1), text: item };
      const value = Number.isFinite(Number(item.value)) ? String(item.value) : (item.rank || item.text || "");
      const modifier = item.modifier ? ` (${item.modifier})` : "";
      return {
        label: item.short || item.label || item.key || "项",
        text: mode === "strict_stats" && value ? `${value}${modifier}` : (item.state || item.text || value || "记录"),
        value: Number.isFinite(Number(item.value)) ? Number(item.value) : undefined,
        max: Number.isFinite(Number(item.max)) ? Number(item.max) : undefined,
        percent: Number.isFinite(Number(item.percent)) ? Number(item.percent) : undefined,
      };
    }).slice(0, 6);
  }
  return fallback.attributes || [
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
  renderAttributes(card.attributes, card.name);
  const avatar = $("avatarImage");
  const feedback = formalPortraitFeedbackAsset(card.name, card.name, "player");
  if (avatar && feedback?.url) {
    setAssetImage(avatar, feedback.url);
  }
}

function renderCompanionCard(companion) {
  const card = document.querySelector(".companionCard");
  if (card) card.hidden = !companion;
  if (!companion) return;
  setText("palicoName", companion.name);
  setText("palicoMeta", companion.meta);
  drawCompanionAvatar(companion.seed || companion.name, {
    cache: true,
    objectId: slugify(companion.name || "companion"),
    seedText: scopedSeed(companion.seed || companion.name || "companion"),
    archetype: companion.archetype,
    kind: "companion_portrait",
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
    const track = document.createElement("em");
    track.className = "statTrack";
    const bar = document.createElement("i");
    bar.style.width = `${Math.max(4, Math.min(100, vital.percent || 0))}%`;
    track.appendChild(bar);
    row.append(label, value, track);
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

function renderAttributes(attributes, characterName = "player") {
  renderAttributeStar(attributes, characterName);
}

function renderAttributeStar(attributes = [], characterName = "player") {
  const canvas = $("attributeStarCanvas");
  const image = $("attributeStarImage");
  if (!canvas) return;
  const rows = normalizeStarAttributes(attributes);
  const signature = rows.map((item) => `${item.label}:${item.text}:${Math.round(item.ratio * 1000)}`).join("|");
  const objectId = slugify(`${characterName || "player"}_attribute_star_${hashSeed(signature).toString(16)}`);
  const seedText = scopedSeed(`${characterName || "player"}:${signature}`);
  const draw = () => drawAttributeStarToCanvas(canvas, rows);
  if (state.activeCampaign && image) {
    cacheCanvasAsset({
      canvas,
      targetImage: image,
      kind: "attribute_star",
      subdir: "portraits",
      objectId,
      seedText,
      metadata: {
        title: `${characterName || "角色"}六维星图`,
        kind: "attribute_star",
        detail: rows.map((item) => `${shortStarLabel(item)}:${Math.round(item.ratio * 100)}`).join(" / "),
      },
      draw,
    });
    return;
  }
  draw();
  if (image) setAssetImage(image, canvas.toDataURL("image/png"));
}

function drawAttributeStarToCanvas(canvas, rows) {
  const ctx = canvas.getContext("2d");
  const logicalSize = 320;
  const scale = Math.max(1, canvas.width / logicalSize);
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  const w = logicalSize;
  const h = logicalSize;
  const cx = w / 2;
  const cy = h / 2;
  const outer = w * .34;
  ctx.clearRect(0, 0, w, h);
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  const point = (radius, index) => {
    const angle = -Math.PI / 2 + index * Math.PI * 2 / 6;
    return [cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius];
  };
  const poly = (points) => {
    ctx.beginPath();
    points.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
    ctx.closePath();
  };
  for (let ring = 4; ring >= 1; ring -= 1) {
    poly(Array.from({ length: 6 }, (_, index) => point(outer * ring / 4, index)));
    ctx.fillStyle = ring % 2 ? "rgba(255,250,239,.55)" : "rgba(185,130,46,.08)";
    ctx.fill();
    ctx.strokeStyle = "rgba(91,62,30,.22)";
    ctx.lineWidth = 2;
    ctx.stroke();
  }
  ctx.strokeStyle = "rgba(91,62,30,.2)";
  ctx.lineWidth = 2;
  for (let index = 0; index < 6; index += 1) {
    const [x, y] = point(outer, index);
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(x, y);
    ctx.stroke();
  }
  const values = rows.map((item, index) => point(outer * item.ratio, index));
  poly(values);
  ctx.fillStyle = "rgba(77,127,168,.34)";
  ctx.fill();
  ctx.strokeStyle = "#4d7fa8";
  ctx.lineWidth = 5;
  ctx.stroke();
  rows.forEach((item, index) => {
    const [x, y] = point(outer + 22, index);
    ctx.fillStyle = "#fff8e8";
    ctx.strokeStyle = "rgba(126,95,58,.28)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y, 17, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#7c5526";
    const label = shortStarLabel(item);
    ctx.font = "800 24px Microsoft YaHei";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(label, x, y + 1);
  });
  ctx.setTransform(1, 0, 0, 1, 0, 0);
}

function shortStarLabel(item) {
  const raw = String(item.text || item.label || item.key || "?").trim();
  const compact = raw.replace(/\s+/g, "");
  if (/^[a-z0-9_ -]+$/i.test(compact)) return compact.slice(0, 3).toUpperCase();
  return compact.slice(0, 3);
}

function normalizeStarAttributes(attributes = []) {
  const fallback = [
    { label: "一", text: "属性", ratio: .58 },
    { label: "二", text: "属性", ratio: .58 },
    { label: "三", text: "属性", ratio: .58 },
    { label: "四", text: "属性", ratio: .58 },
    { label: "五", text: "属性", ratio: .58 },
    { label: "六", text: "属性", ratio: .58 },
  ];
  const rows = Array.isArray(attributes) ? attributes.slice(0, 6) : [];
  const normalized = rows.map((item, index) => {
    const value = Number(item.value);
    const max = Number(item.max);
    const percent = Number(item.percent);
    const ratio = Number.isFinite(value) && Number.isFinite(max) && max > 0
      ? value / max
      : Number.isFinite(percent) ? percent / 100 : (.5 + (index % 3) * .1);
    return {
      label: item.label || item.short || item.key || fallback[index].label,
      text: item.text || item.state || item.rank || "",
      ratio: Math.max(.08, Math.min(1, ratio)),
    };
  });
  while (normalized.length < 6) normalized.push(fallback[normalized.length]);
  return normalized;
}

function currentCampaignMeta() {
  return state.campaigns.find((campaign) => campaign.campaign_id === state.activeCampaign) || null;
}

function renderSidePanel(campaignState, frontendState = state.frontendState || {}) {
  const list = $("sideList");
  if (!list) return;
  const rows = state.sideTab === "items" ? protocolInventoryRows(frontendState, campaignState) : protocolQuestRows(frontendState, campaignState);
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

async function renderOutput(output) {
  if (output.campaign_id && state.activeCampaign && output.campaign_id !== state.activeCampaign) {
    clearStoryTurnHistory(state.activeCampaign);
    renderStoryBlocks([], "当前跑团暂无正文记录。");
    setText("summaryText", `已拦截其他跑团的正文记录：${output.campaign_id}`);
    setText("directorText", JSON.stringify({
      warning: "output campaign mismatch",
      active_campaign: state.activeCampaign,
      output_campaign: output.campaign_id,
    }, null, 2));
    return;
  }
  let blocks = Array.isArray(output.parsed?.blocks) ? output.parsed.blocks : [];
  let body = output.parsed?.body || "";
  let choices = output.parsed?.choices || "";
  let summary = output.parsed?.summary || "";

  // If backend returned no blocks, try parsing public_text as JSON
  if (!blocks.length && output.public_text) {
    try {
      const trimmed = output.public_text.trim();
      // Check if it starts with { (JSON) or ``` (JSON in code fence)
      if (trimmed.startsWith("{") || trimmed.startsWith("```")) {
        let jsonStr = trimmed;
        if (jsonStr.startsWith("```")) {
          const lines = jsonStr.split("\n");
          if (lines[0].startsWith("```")) lines.shift();
          if (lines.length && lines[lines.length - 1].startsWith("```")) lines.pop();
          jsonStr = lines.join("\n");
        }
        const jsonData = JSON.parse(jsonStr);
        const rawBlocks = jsonData.blocks || jsonData.narrative_blocks || [];
        if (Array.isArray(rawBlocks) && rawBlocks.length) {
          blocks = rawBlocks;
          body = jsonData.body || joinBlocksText(rawBlocks) || body;
          choices = jsonData.choices || choicesText(rawBlocks) || choices;
          summary = jsonData.summary || jsonData.turn_summary || summary;
        }
      }
    } catch (err) {
      console.warn("inline JSON parse failed", err);
    }
  }

  // Preprocess blocks: split NPC dialogue out of gm_narration blocks
  blocks = splitNpcDialogueBlocks(blocks);

  const storyBlocks = appendStoryTurnHistory(blocks, body || "暂无正文。", output);
  renderStoryBlocks(storyBlocks, body || "暂无正文。");
  renderSummary(summary || "暂无回合摘要。");
  const director = {
    pressure_pack: output.pressure_pack || {},
    ai_flavor_report: output.ai_flavor_report || {},
    audit_result: output.audit_result || {},
  };
  setText("directorText", JSON.stringify(director, null, 2));
}

async function loadWritebackReview(options = {}) {
  if (!state.activeCampaign) return;
  try {
    const data = await api(`/api/writeback-review?campaign_id=${encodeURIComponent(state.activeCampaign)}`);
    state.writebackReview = data;
    renderWritebackReview(data);
  } catch (err) {
    if (!options.silent) {
      showPanel("writeback");
      setText("writebackDecision", "无法读取写回");
      setText("writebackHint", err.message);
      setText("writebackText", "");
      $("writebackFiles").innerHTML = "";
    }
  }
}

function appendStoryTurnHistory(blocks, fallbackText, output = {}) {
  const campaignId = state.activeCampaign || output.campaign_id || "default";
  const rows = visibleStoryBlocks(blocks);
  const turnBlocks = rows.length ? rows : legacyTextBlocks(fallbackText);
  if (!turnBlocks.length) return [];
  const signature = storyTurnSignature(turnBlocks, output);
  const turns = state.storyTurnsByCampaign[campaignId] || [];
  const signatures = state.storyTurnSignatures[campaignId] || [];
  if (!signatures.includes(signature)) {
    turns.push({ signature, blocks: turnBlocks });
    signatures.push(signature);
    while (turns.length > 10) turns.shift();
    while (signatures.length > 10) signatures.shift();
    state.storyTurnsByCampaign[campaignId] = turns;
    state.storyTurnSignatures[campaignId] = signatures;
  }
  return (state.storyTurnsByCampaign[campaignId] || []).flatMap((turn) => turn.blocks);
}

function clearStoryTurnHistory(campaignId = state.activeCampaign || "default") {
  delete state.storyTurnsByCampaign[campaignId];
  delete state.storyTurnSignatures[campaignId];
}

function storyTurnSignature(blocks, output = {}) {
  const simplified = blocks.map((block) => ({
    type: block.type || "",
    speaker: block.speaker || "",
    body: block.body || "",
    asset_key: block.asset_key || "",
    cached_url: block.cached_url || "",
    choices: Array.isArray(block.choices) ? block.choices.map((choice) => choice.label || choice.text || "") : [],
  }));
  return stableJson({
    campaign_id: output.campaign_id || state.activeCampaign || "",
    blocks: simplified,
  });
}

function visibleStoryBlocks(blocks) {
  return (Array.isArray(blocks) ? blocks : []).filter((block) => !["summary", "backend_note"].includes(block.type));
}

function renderWritebackReview(data) {
  const decision = data.decision || "not_audited";
  const labels = { accept: "V4 接受", revise: "V4 修订", reject: "V4 拒绝", not_audited: "未审核" };
  setText("writebackDecision", labels[decision] || decision);
  const reason = data.audit_result?.reason || (data.warnings || []).join("；") || "解析 ChatGPT 回复后，可在这里审核并应用状态回写。";
  setText("writebackHint", reason);
  const files = $("writebackFiles");
  files.innerHTML = "";
  (data.memory_files_to_update || []).forEach((name) => {
    const pill = document.createElement("span");
    pill.textContent = name;
    files.appendChild(pill);
  });
  const payload = {
    decision,
    warnings: data.warnings || [],
    audit_result: data.audit_result || {},
    approved_writeback: data.approved_writeback || {},
    raw_writeback: data.writeback || {},
    pending_updates: data.pending_updates || {},
  };
  setText("writebackText", JSON.stringify(payload, null, 2));
  const apply = $("applyWritebackBtn");
  if (apply) apply.disabled = !["accept", "revise"].includes(decision);
}

async function auditWriteback() {
  try {
    showPanel("writeback");
    setText("writebackDecision", "V4 审核中");
    const data = await api("/api/audit-writeback", {
      method: "POST",
      body: JSON.stringify({ campaign_id: state.activeCampaign }),
    });
    renderWritebackReview(data);
  } catch (err) {
    setText("writebackDecision", "审核失败");
    setText("writebackHint", err.message);
  }
}

async function applyWriteback() {
  const decision = state.writebackReview?.decision;
  if (!["accept", "revise"].includes(decision)) return;
  if (!window.confirm("写入长期记忆？系统会先备份将被修改的记忆文件。")) return;
  try {
    const data = await api("/api/apply-writeback", {
      method: "POST",
      body: JSON.stringify({ campaign_id: state.activeCampaign }),
    });
    setText("writebackDecision", "已写入");
    setText("writebackHint", `更新文件：${(data.updated_files || []).join(", ") || "无"}`);
    await refresh();
  } catch (err) {
    setText("writebackDecision", "写入失败");
    setText("writebackHint", err.message);
  }
}

function renderStoryBlocks(blocks, fallbackText) {
  const container = $("storyText");
  container.innerHTML = "";
  const visibleBlocks = visibleStoryBlocks(blocks);
  const rows = visibleBlocks.length ? visibleBlocks : legacyTextBlocks(fallbackText);
  if (!rows.length) container.textContent = "暂无正文。";
  rows.forEach((block) => {
    try {
      container.appendChild(renderMessageBlock(block));
    } catch (err) {
      console.warn("story block render failed", block, err);
    }
  });
  scrollActiveFeed();
  if (state.runProgress.active && blocks.length) scrollStoryToBottom(true);
}

function protocolQuestRows(frontendState = {}, campaignState = {}) {
  const rows = Array.isArray(frontendState.quests) ? frontendState.quests : [];
  if (rows.length) {
    return rows.map((row) => ({
      title: row.short_name || row.title || row.id,
      detail: row.detail || "",
      tag: row.priority || row.status || "任务",
    }));
  }
  return questRows(campaignState);
}

function protocolInventoryRows(frontendState = {}, campaignState = {}) {
  const rows = Array.isArray(frontendState.inventory) ? frontendState.inventory : [];
  if (rows.length) {
    return rows.map((row) => ({
      title: row.short_name || row.raw_name || row.id,
      detail: row.detail || "",
      tag: row.category || row.role || "物品",
    }));
  }
  return itemRows(campaignState);
}

function renderMessageBlock(block) {
  if (block.type === "cg_image") return renderCgImageBlock(block);
  if (block.type === "choice_prompt") return renderChoiceBlock(block);
  const role = blockRole(block);
  const card = document.createElement("article");
  card.className = `msg ${role}`;
  card.dataset.blockType = block.type || "gm_narration";

  const avatar = document.createElement("div");
  avatar.className = "msgAvatar";
  if (role === "player" || role === "npc" || role === "companion") {
    const image = document.createElement("img");
    image.alt = `${block.speaker || defaultSpeaker(block.type)} 头像 PNG`;
    avatar.appendChild(image);
    drawBlockAvatar(image, block, role);
  } else {
    avatar.textContent = role === "system" ? "检" : "叙";
  }

  const body = document.createElement("div");
  body.className = "msgBody";
  const title = document.createElement("strong");
  title.textContent = displaySpeaker(block) || defaultSpeaker(block.type);
  const content = document.createElement("div");
  content.className = "msgText";
  content.textContent = block.body || "";
  body.append(title, content);
  const storyImage = renderStoryImage(block);
  if (storyImage) body.appendChild(storyImage);
  const check = block.type === "system_check" ? checkMeta(block) : null;
  if (check) body.appendChild(check);

  const time = document.createElement("time");
  time.textContent = block.time || "现在";
  card.append(avatar, body, time);
  return card;
}

function renderCgImageBlock(block) {
  const card = document.createElement("article");
  card.className = "msg cg";
  card.dataset.blockType = "cg_image";
  const spacer = document.createElement("div");
  spacer.className = "msgAvatar cgAvatar";
  spacer.textContent = "CG";
  const body = document.createElement("div");
  body.className = "msgBody";
  const title = document.createElement("strong");
  title.textContent = "CG";
  body.appendChild(title);
  const storyImage = renderStoryImage(block);
  if (storyImage) body.appendChild(storyImage);
  const time = document.createElement("time");
  time.textContent = block.time || "现在";
  card.append(spacer, body, time);
  return card;
}

function renderStoryImage(block) {
  const url = block.cached_url || block.image_url || block.url || "";
  if (!url) return null;
  const figure = document.createElement("figure");
  figure.className = "storyImage";
  const image = document.createElement("img");
  image.src = cacheBustAssetUrl(url);
  image.alt = "CG";
  image.loading = "lazy";
  if (block.type === "cg_image") {
    image.tabIndex = 0;
    image.setAttribute("role", "button");
    image.setAttribute("aria-label", "查看 CG 大图");
    image.addEventListener("click", () => openCgOverlay(url, publicCgDetail(block)));
    image.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openCgOverlay(url, publicCgDetail(block));
      }
    });
  }
  figure.appendChild(image);
  const captionText = block.type === "cg_image" ? publicCgDetail(block) : (block.image_detail || block.image_title || "");
  if (captionText) {
    const caption = document.createElement("figcaption");
    caption.textContent = captionText;
    figure.appendChild(caption);
  }
  return figure;
}

function openCgOverlay(url, caption = "") {
  if (!url) return;
  const overlay = $("cgOverlay");
  const image = $("cgDialogImage");
  if (!overlay || !image) return;
  setText("cgDialogTitle", "CG");
  setText("cgDialogCaption", conciseCgSceneText(caption));
  image.src = cacheBustAssetUrl(url);
  overlay.classList.remove("hidden");
  overlay.setAttribute("aria-hidden", "false");
}

function closeCgOverlay() {
  const overlay = $("cgOverlay");
  if (!overlay) return;
  overlay.classList.add("hidden");
  overlay.setAttribute("aria-hidden", "true");
  const image = $("cgDialogImage");
  if (image) image.removeAttribute("src");
}

function publicCgDetail(block) {
  const candidates = [
    block.public_detail,
    block.scene_detail,
    block.image_caption,
    block.image_detail,
    block.body,
  ];
  const technical = /(16\s*:\s*9|9\s*:\s*16|PC|手机|构图|预览|正式图标|正式深度图片|头像反哺|反哺|画幅|aspect|ratio|mobile|variant|crop|safe area|缓存|技术|参数)/i;
  const loaded = /(CG\s*)?已载入|载入正文|本回合\s*CG|剧情\s*CG/i;
  for (const value of candidates) {
    const text = conciseCgSceneText(value);
    if (!text || technical.test(text) || loaded.test(text)) continue;
    return text;
  }
  return "雨夜小卖部门口，Lee 抱紧金属盒，黑水倒影逼近。";
}

function conciseCgSceneText(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .replace(/[。；;，,]\s*(16\s*:\s*9|9\s*:\s*16|PC|手机|构图|预览|头像反哺|反哺|缓存|技术|参数).*$/i, "")
    .trim()
    .slice(0, 72);
}

function cacheBustAssetUrl(url) {
  if (!url || url.startsWith("data:") || url.startsWith("blob:")) return url;
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}v=${ASSET_GENERATOR_VERSION}`;
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

function renderChoiceBlock(block) {
  const card = document.createElement("article");
  card.className = "choiceCard inlineChoice";
  card.dataset.blockType = "choice_prompt";
  const header = document.createElement("div");
  header.className = "choiceTitle";
  const mark = document.createElement("span");
  mark.className = "choiceMark";
  mark.textContent = "抉";
  const title = document.createElement("strong");
  title.textContent = block.speaker || "关键抉择";
  header.append(mark, title);
  const time = document.createElement("time");
  time.textContent = block.time || "现在";
  header.appendChild(time);
  card.appendChild(header);
  if (block.body) {
    const intro = document.createElement("div");
    intro.className = "choiceIntro";
    intro.textContent = block.body;
    card.appendChild(intro);
  }
  const choices = Array.isArray(block.choices) ? block.choices : [];
  if (choices.length) {
    const grid = document.createElement("div");
    grid.className = "choiceGrid";
    choices.slice(0, 4).forEach((choice, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "choiceOption";
      const displayId = String.fromCharCode(65 + index);
      const label = choice.label || choice.text || `选择 ${index + 1}`;
      button.innerHTML = `<b>${escapeHtml(displayId)}. ${escapeHtml(label)}</b>${choice.risk ? `<small>${escapeHtml(choice.risk)}</small>` : ""}`;
      button.addEventListener("click", () => {
        const input = $("actionInput");
        if (input) {
          input.value = label;
          input.focus();
        }
      });
      grid.appendChild(button);
    });
    card.appendChild(grid);
  }
  return card;
}

function blockRole(block) {
  if (block.type === "player_action") return "player";
  if (block.type === "npc_dialogue") {
    const key = block.avatar_key || block.actor_id || block.speaker || "";
    if (isCompanionActorName(key)) return "companion";
    return "npc";
  }
  if (block.type === "cg_image") return "system";
  if (block.type === "system_check") return "system";
  return "gm";
}

function defaultSpeaker(type) {
  if (type === "player_action") return "玩家";
  if (type === "npc_dialogue") return "NPC";
  if (type === "cg_image") return "剧情 CG";
  if (type === "system_check") return "系统检定";
  return "GM 叙述";
}

function checkMeta(block) {
  const check = block.check || block.meta?.check;
  if (!check || typeof check !== "object") return null;
  const row = document.createElement("div");
  row.className = "checkMeta";
  const result = String(check.result || check.outcome || "").toLowerCase();
  const success = result.includes("success") || result.includes("成功") || check.success === true;
  const failure = result.includes("fail") || result.includes("失败") || check.success === false;
  row.classList.toggle("success", success);
  row.classList.toggle("failure", failure);
  const total = check.total ?? check.value ?? "";
  const target = check.dc ?? check.target ?? check.difficulty ?? "";
  const parts = [
    `${check.skill || check.name || check.type || "检定"} 检定`,
    check.roll ? `${check.roll}${check.modifier ? ` + ${check.modifier}` : ""}` : "",
    total !== "" ? `= ${total}` : "",
    target !== "" ? `难度 ${target}` : "",
  ].filter(Boolean);
  const status = document.createElement("b");
  status.textContent = failure ? "失败" : success ? "成功" : (check.result || check.outcome || "结果待定");
  row.innerHTML = `<span>${escapeHtml(parts.join("  >  "))}</span>`;
  row.appendChild(status);
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

/**
 * Split NPC dialogue segments out of gm_narration blocks.
 * Detects patterns like "掌车人终于憋不住，从牙缝里挤出一句："..." or "某某某说："
 * and creates separate npc_dialogue blocks with proper avatar_key.
 */
function splitNpcDialogueBlocks(blocks) {
  const result = [];
  for (const block of blocks) {
    if (block.type !== "gm_narration" || !block.body) {
      result.push(block);
      continue;
    }
    // Try to extract NPC dialogue segments using quote patterns
    const parts = splitGmBlock(block);
    for (const part of parts) {
      result.push(part);
    }
  }
  return result;
}

/**
 * Known NPC names extracted from the block content via heuristic.
 * We match Chinese names (2-3 chars) followed by dialogue verbs.
 */
const NPC_VERBS = /(?:终于憋不住|挤出一句|说道|低声开口|喊道|叫道|说|问|答|喊|嚷|嘟囔|咕哝|骂|吼|抱怨|提醒|打断|插嘴|接口|补充|解释|回答|命令|指示| whispered|said|shouted|asked|replied)/;

/**
 * Try to split a gm_narration block into sub-blocks.
 * Returns array of blocks (may be just the original if no split needed).
 */
function splitGmBlock(block) {
  const body = block.body;
  // Match patterns like: "NPC名终于憋不住，从牙缝里挤出一句："...""
  // or "NPC名说道："..."
  // This regex captures: leading narration text, then NPC name + verb + dialogue
  const dialogueRegex = /([\u4e00-\u9fff]{2,3}(?:终于憋不住[^"]*?(?:挤出一句|说道)|低声开口|说道|喊道|叫道|说[^"]*?[：:]|问[^"]*?[：:]|答[^"]*?[：:]|喊[^"]*?[：:]|嚷[^"]*?[：:]|骂[^"]*?[：:]|抱怨[^"]*?[：:]|提醒[^"]*?[：:]|打断[^"]*?[：:]))[：:]\s*"([^"]*)"/g;

  const segments = [];
  let lastIndex = 0;
  let match;

  while ((match = dialogueRegex.exec(body)) !== null) {
    // Text before this dialogue segment
    const before = body.substring(lastIndex, match.index);
    if (before.trim()) {
      segments.push(createSubBlock(block, "gm_narration", "GM", "", before.trim()));
    }

    // The NPC dialogue segment
    const npcName = extractNpcName(match[1]);
    const dialogueText = match[2];
    // Include the action context (e.g., "掌车人终于憋不住，从牙缝里")
    const actionBeforeQuote = match[1].substring(npcName.length);
    const fullDialogueBody = `${npcName}${actionBeforeQuote}："${dialogueText}"`;
    segments.push(createSubBlock(block, "npc_dialogue", npcName, npcName, fullDialogueBody));

    lastIndex = match.index + match[0].length;
  }

  // Remaining text after last dialogue
  const remaining = body.substring(lastIndex);
  if (remaining.trim()) {
    segments.push(createSubBlock(block, "gm_narration", "GM", "", remaining.trim()));
  }

  return segments.length > 1 ? segments : [block];
}

function extractNpcName(actionText) {
  // Extract NPC name (first 2-3 Chinese chars) from action context
  const nameMatch = actionText.match(/([\u4e00-\u9fff]{2,3})/);
  return nameMatch ? nameMatch[1] : "NPC";
}

function createSubBlock(original, type, speaker, avatarKey, body) {
  return {
    type: type,
    speaker: speaker,
    actor_id: avatarKey || "",
    actor_kind: type === "npc_dialogue" ? "npc" : "gm",
    avatar_key: avatarKey || "",
    body: body,
    time: original.time || "现在",
    check: {},
    choices: [],
    tags: [],
  };
}

function joinBlocksText(blocks) {
  return blocks
    .filter((b) => b.body && !["choice_prompt", "summary"].includes(b.type))
    .map((b) => b.body)
    .join("\n\n");
}

function choicesText(blocks) {
  const choice = blocks.find((b) => b.type === "choice_prompt");
  if (!choice) return "";
  const lines = [choice.body || ""];
  (choice.choices || []).forEach((c) => {
    const label = c.label || c.text || "";
    const risk = c.risk ? `（风险：${c.risk}）` : "";
    if (label) lines.push(`${label}${risk}`);
  });
  return lines.filter(Boolean).join("\n");
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
    button.innerHTML = `<b>${escapeHtml(campaign.title || campaign.name || campaign.campaign_id)}</b>`;
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
    <small>${escapeHtml(selected.genre || "未记录题材")}</small>
    <p>${escapeHtml(bindingSafetyText(selected))}</p>
  `;
  const switchBtn = document.createElement("button");
  switchBtn.type = "button";
  switchBtn.className = "pickerAction";
  switchBtn.textContent = isActive ? "当前跑团" : "切换到此跑团";
  switchBtn.disabled = isActive;
  switchBtn.addEventListener("click", () => selectCampaign(selected.campaign_id));
  stories.append(detail, switchBtn);
}

function populateCampaignProfileFields(campaign) {
  if (!campaign) return;
  setInputValue("profileTitle", campaign.title || campaign.name || "");
  setInputValue("profileGenre", campaign.genre || "");
  setInputValue("profileTone", campaign.tone || "");
  setInputValue("profileDiceSystem", "");
  setInputValue("profileStatsStyle", "");
  setChecked("profileUseDice", false);
  setChecked("profileUseCombatRules", false);
  renderBindingSafety(campaign);
}

async function loadCampaignProfile(campaignId) {
  if (!campaignId) return;
  try {
    const data = await api(`/api/campaign-profile?campaign_id=${encodeURIComponent(campaignId)}`);
    if (state.selectedCampaign !== campaignId) return;
    const profile = data.profile || {};
    const mechanics = profile.mechanics || {};
    setInputValue("profileTitle", profile.title || "");
    setInputValue("profileGenre", profile.genre || "");
    setInputValue("profileTone", profile.tone || "");
    setInputValue("profileDiceSystem", mechanics.dice_system || "");
    setInputValue("profileStatsStyle", mechanics.stats_style || "");
    setChecked("profileUseDice", Boolean(mechanics.use_dice));
    setChecked("profileUseCombatRules", Boolean(mechanics.use_combat_rules));
    renderBindingSafety({ ...campaignById(campaignId), ...(data.registry_meta || {}) });
  } catch (err) {
    setPickerNotice(err.message);
  }
}

function bindingSafetyText(campaign) {
  const project = campaign.project || campaign.chatgpt_project_name || "";
  const conversation = campaign.conversation || campaign.chatgpt_conversation_name || "";
  if (!project || !conversation) return "固定对话未绑定。发送/抓取会由后端安全检查阻止。";
  return `绑定 Project：${project}；固定对话：${conversation}。只操作此固定对话，不创建、不删除、不切换到其他对话。`;
}

function renderBindingSafety(campaign) {
  setText("bindingSafetyHint", bindingSafetyText(campaign || {}));
  const archived = (campaign?.status || "").toLowerCase() === "archived";
  const archiveBtn = $("archiveCampaignBtn");
  const restoreBtn = $("restoreCampaignBtn");
  if (archiveBtn) archiveBtn.disabled = archived;
  if (restoreBtn) restoreBtn.disabled = !archived;
  setText("campaignArchiveHint", archived ? "当前跑团已归档；记忆、日志和素材仍保留，可随时恢复。" : "当前跑团未归档。归档只改变状态，不删除任何文件。");
}

function campaignById(campaignId) {
  return state.campaigns.find((campaign) => campaign.campaign_id === campaignId) || {};
}

function setInputValue(id, value) {
  const el = $(id);
  if (el) el.value = value || "";
}

function setChecked(id, value) {
  const el = $(id);
  if (el) el.checked = Boolean(value);
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

async function createCampaign() {
  const campaignId = $("newCampaignId").value.trim();
  const name = $("newCampaignName").value.trim();
  const template = $("newCampaignTemplate")?.value || "custom";
  if (!campaignId || !name) {
    setPickerNotice("请填写 campaign_id 和跑团名称。");
    return;
  }
  try {
    await api("/api/init-campaign", {
      method: "POST",
      body: JSON.stringify({ campaign_id: campaignId, name, template }),
    });
    state.selectedCampaign = campaignId;
    await refresh();
    renderStoryPicker();
    setPickerNotice("跑团已创建。请继续绑定固定对话。");
  } catch (err) {
    setPickerNotice(err.message);
  }
}

async function saveChatGPTBinding() {
  const projectName = $("bindingProject").value.trim();
  const conversationName = $("bindingConversation").value.trim();
  const campaignId = state.selectedCampaign || state.activeCampaign;
  if (!campaignId) return setPickerNotice("请先选择跑团。");
  if (!projectName || !conversationName) return setPickerNotice("请填写 Project 和固定对话名称。");
  try {
    await api("/api/set-chatgpt-binding", {
      method: "POST",
      body: JSON.stringify({ campaign_id: campaignId, project_name: projectName, conversation_name: conversationName }),
    });
    await refresh();
    renderStoryPicker();
    setPickerNotice("固定对话绑定已保存。");
  } catch (err) {
    setPickerNotice(err.message);
  }
}

async function saveCampaignProfile() {
  const campaignId = state.selectedCampaign || state.activeCampaign;
  if (!campaignId) return setPickerNotice("请先选择跑团。");
  try {
    await api("/api/campaign-profile", {
      method: "POST",
      body: JSON.stringify({
        campaign_id: campaignId,
        title: $("profileTitle").value.trim(),
        genre: $("profileGenre").value.trim(),
        tone: $("profileTone").value.trim(),
        mechanics: {
          use_dice: $("profileUseDice").checked,
          use_combat_rules: $("profileUseCombatRules").checked,
          dice_system: $("profileDiceSystem").value.trim(),
          stats_style: $("profileStatsStyle").value.trim(),
        },
      }),
    });
    await refresh();
    renderStoryPicker();
    setPickerNotice("跑团基础字段已保存。");
  } catch (err) {
    setPickerNotice(err.message);
  }
}

async function setCampaignArchiveStatus(status) {
  const campaignId = state.selectedCampaign || state.activeCampaign;
  if (!campaignId) return setPickerNotice("请先选择跑团。");
  try {
    await api("/api/campaign-status", {
      method: "POST",
      body: JSON.stringify({ campaign_id: campaignId, status }),
    });
    await refresh();
    state.selectedCampaign = campaignId;
    renderStoryPicker();
    setPickerNotice(status === "archived" ? "跑团已归档，未删除任何文件。" : "跑团已恢复。");
  } catch (err) {
    setPickerNotice(err.message);
  }
}

function setPickerNotice(text) {
  const footer = $("newCampaignPageBtn");
  if (footer) footer.querySelector("span").textContent = text || "新建跑团";
}

function showPanel(name) {
  state.activePanel = name;
  ["story", "director", "writeback", "memory", "logs", "summary"].forEach((item) => {
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
  let visibleCount = 0;
  document.querySelectorAll("#galleryGrid article").forEach((card) => {
    const visible = galleryAssetMatchesFilter({ kind: card.dataset.kind }, state.galleryFilter);
    card.classList.toggle("hidden", !visible);
    card.hidden = !visible;
    if (visible) visibleCount += 1;
  });
  const button = $("viewAllBtn");
  if (button) button.textContent = `显示全部资料（${visibleCount}）`;
  if (!$("galleryOverlay")?.classList.contains("hidden")) renderGalleryDialog();
}

function renderGallery(campaignState, galleryState = {}, moduleState = null) {
  const grid = $("galleryGrid");
  if (!grid) return;
  const modulePayload = moduleState?.payload || galleryState.module_payload || {};
  const moduleAssets = [
    ...(Array.isArray(modulePayload.visual_assets) ? modulePayload.visual_assets : []),
    ...(Array.isArray(modulePayload.gallery_updates) ? modulePayload.gallery_updates : []),
  ].map(protocolGalleryAsset).filter(Boolean);
  const protocolAssets = moduleAssets.length ? moduleAssets : Array.isArray(galleryState.assets) ? galleryState.assets.map(protocolGalleryAsset).filter(Boolean) : [];
  const fallbackAssets = buildVisualAssets(campaignState).map((asset) => normalizeGalleryAssetForFixedFilters(asset)).filter(Boolean);
  const cachedAssets = cachedGalleryAssets().map((asset) => normalizeGalleryAssetForFixedFilters(asset)).filter(Boolean);
  const assets = markGalleryArchiveState(protocolAssets.length ? mergeGalleryAssets(protocolAssets, cachedAssets) : mergeGalleryAssets(fallbackAssets, cachedAssets));
  state.galleryAssets = assets;
  grid.innerHTML = "";
  assets.forEach((asset) => {
    const card = document.createElement("article");
    card.dataset.kind = asset.kind;
    card.dataset.key = asset.key;
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    card.setAttribute("aria-label", `查看资料：${asset.title}`);
    const image = document.createElement("img");
    image.className = "galleryThumb";
    image.alt = `${asset.title} PNG`;
    const text = document.createElement("div");
    text.className = "galleryText";
    const title = document.createElement("b");
    title.textContent = asset.title;
    const detail = document.createElement("p");
    detail.textContent = galleryDetail(asset);
    const meta = document.createElement("small");
    meta.textContent = assetStatusLabel(asset);
    text.append(title, detail, meta);
    card.append(image, text);
    grid.appendChild(card);
    card.addEventListener("click", () => openAssetFromGallery(asset));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openAssetFromGallery(asset);
      }
    });
    drawGalleryAsset(image, asset);
  });
  setGalleryFilter(state.galleryFilter);
}

function renderGalleryFilters(filters) {
  const holder = $("galleryFilters");
  if (!holder || !Array.isArray(filters) || !filters.length) return;
  state.galleryFilterIds = filters.map((filter) => filter.key).filter(Boolean);
  const current = filters.some((filter) => filter.key === state.galleryFilter) ? state.galleryFilter : "all";
  state.galleryFilter = current;
  holder.innerHTML = "";
  filters.forEach((filter) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.filter = filter.key;
    button.textContent = filter.label || filter.key;
    button.classList.toggle("active", filter.key === state.galleryFilter);
    button.addEventListener("click", () => setGalleryFilter(filter.key));
    holder.appendChild(button);
  });
}

function protocolGalleryAsset(asset) {
  const kind = fixedGalleryKind(asset.kind);
  if (!kind) return null;
  const detail = asset.detail || "";
  return {
    kind,
    key: asset.key || `${kind}:${asset.title}`,
    title: conciseTitle(asset.title || asset.key || "资料", 22),
    meta: asset.meta || galleryKindLabel(kind),
    seed: scopedSeed(asset.seed || asset.title || asset.key),
    detail,
    cachedUrl: asset.cached_url || asset.url || "",
    sourceObjectId: asset.source_object_id || "",
    status: asset.status || "",
    archived: Boolean(asset.archived),
    createdAt: asset.created_at || "",
    visualPrompt: asset.visual_prompt || asset.visualPrompt || inferItemVisualPrompt(asset.title || asset.key || "", detail, kind),
    imagePrompt: asset.image_prompt || asset.imagePrompt || {},
  };
}

function openAssetFromGallery(asset) {
  if (asset?.kind === "cg") {
    openCgOverlay(asset.cachedUrl, asset.detail || galleryDetail(asset));
    return;
  }
  openGalleryOverlay(asset.key);
}

function markGalleryArchiveState(assets) {
  let currentSceneMarked = false;
  return assets.map((asset) => {
    if (asset.kind !== "scene" || !asset.cachedUrl) return asset;
    if (!currentSceneMarked) {
      currentSceneMarked = true;
      return { ...asset, status: "current", archived: false };
    }
    return { ...asset, status: asset.status || "archived", archived: true };
  });
}

function openCurrentMapOverlay() {
  if (!state.currentMapAsset) return;
  openGalleryOverlay(state.currentMapAsset.key, state.currentMapAsset);
}

function openGalleryOverlay(assetKey = "", transientAsset = null) {
  state.transientGalleryAsset = transientAsset;
  const requested = state.galleryAssets.find((asset) => asset.key === assetKey);
  if (requested && !galleryAssetMatchesFilter(requested, state.galleryFilter)) {
    state.galleryFilter = requested.kind === "monster" || requested.kind === "ecology" ? "monster" : requested.kind;
    setGalleryFilter(state.galleryFilter);
  }
  const assets = filteredGalleryAssets();
  state.selectedGalleryKey = assetKey || state.selectedGalleryKey || assets[0]?.key || state.galleryAssets[0]?.key || "";
  renderGalleryDialog();
  const overlay = $("galleryOverlay");
  overlay.classList.remove("hidden");
  overlay.setAttribute("aria-hidden", "false");
}

function closeGalleryOverlay() {
  const overlay = $("galleryOverlay");
  if (!overlay) return;
  overlay.classList.add("hidden");
  overlay.setAttribute("aria-hidden", "true");
  state.transientGalleryAsset = null;
}

function filteredGalleryAssets() {
  const rows = state.galleryAssets.filter((asset) => galleryAssetMatchesFilter(asset, state.galleryFilter));
  if (state.transientGalleryAsset) {
    return [state.transientGalleryAsset, ...rows.filter((asset) => asset.key !== state.transientGalleryAsset.key)];
  }
  return rows;
}

function galleryAssetMatchesFilter(asset, filter) {
  const value = filter || "all";
  if (value === "all") return true;
  if (value === "cg") return asset.kind === "cg";
  if (value === "monster") return asset.kind === "monster" || asset.kind === "ecology";
  if (value === "scene") return asset.kind === "scene" || asset.kind === "location";
  if (value === "item") return ["item", "weapon", "supply", "material", "ritual_tool"].includes(asset.kind);
  if (value === "clue") return ["clue", "document", "ritual_tool"].includes(asset.kind);
  if (value === "character") return ["character", "npc", "companion"].includes(asset.kind);
  return asset.kind === value;
}

function renderGalleryDialog() {
  const list = $("galleryDialogList");
  if (!list) return;
  const assets = filteredGalleryAssets();
  list.innerHTML = "";
  if (!assets.length) {
    const empty = document.createElement("div");
    empty.className = "galleryEmpty";
    empty.textContent = "当前筛选下暂无资料。";
    list.appendChild(empty);
    renderGalleryInspector(null);
    return;
  }
  if (!assets.some((asset) => asset.key === state.selectedGalleryKey)) {
    state.selectedGalleryKey = assets[0].key;
  }
  assets.forEach((asset) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = `galleryDialogItem${asset.key === state.selectedGalleryKey ? " active" : ""}`;
    row.innerHTML = `<b>${escapeHtml(asset.title)}</b><small>${escapeHtml(galleryDetail(asset))}</small><span>${escapeHtml(assetStatusLabel(asset))}</span>`;
    row.addEventListener("click", () => {
      state.selectedGalleryKey = asset.key;
      renderGalleryDialog();
    });
    list.appendChild(row);
  });
  renderGalleryInspector(assets.find((asset) => asset.key === state.selectedGalleryKey) || assets[0]);
}

function renderGalleryInspector(asset) {
  const image = $("galleryInspectorImage");
  const title = $("galleryInspectorTitle");
  const detail = $("galleryInspectorDetail");
  const meta = $("galleryInspectorMeta");
  const useButton = $("useGalleryAssetBtn");
  const inspector = $("galleryInspector");
  if (inspector) inspector.dataset.kind = asset?.kind || "";
  if (!asset) {
    if (image) image.removeAttribute("src");
    setText("galleryInspectorTitle", "暂无资料");
    setText("galleryInspectorDetail", "当前筛选下没有可查看的资料。");
    setText("galleryInspectorMeta", "资料");
    if (useButton) useButton.disabled = true;
    return;
  }
  if (image) drawGalleryAsset(image, asset);
  if (title) title.textContent = asset.title;
  if (detail) detail.textContent = galleryDetail(asset);
  if (meta) meta.textContent = assetStatusLabel(asset);
  if (useButton) {
    useButton.disabled = !canUseGalleryAsset(asset);
    useButton.textContent = canUseGalleryAsset(asset) ? "引用到行动输入" : "仅供查看";
  }
}

function useSelectedGalleryAsset() {
  const asset = state.galleryAssets.find((item) => item.key === state.selectedGalleryKey);
  if (!asset || !canUseGalleryAsset(asset)) return;
  const input = $("actionInput");
  if (!input) return;
  const text = asset.kind === "npc" ? `@${asset.title}：` : `查看物品「${asset.title}」：`;
  input.value = input.value.trim() ? `${input.value.trim()}\n${text}` : text;
  input.focus();
  closeGalleryOverlay();
}

function canUseGalleryAsset(asset) {
  return asset && (asset.kind === "npc" || asset.kind === "item");
}

function assetStatusLabel(asset) {
  const status = String(asset?.status || "").toLowerCase();
  const base = asset?.meta || galleryKindLabel(asset?.kind);
  if (asset?.archived) return `${base} / 已归档`;
  if (status.includes("dead") || status.includes("死亡") || status.includes("阵亡")) return `${base} / 已死亡`;
  if (status.includes("lost") || status.includes("失联")) return `${base} / 失联`;
  if (status.includes("consumed") || status.includes("消耗")) return `${base} / 已消耗`;
  if (status.includes("current")) return `${base} / 当前`;
  if (asset?.kind === "scene" && asset?.createdAt) return `${base} / 历史`;
  return base;
}

async function loadMemoryReport() {
  try {
    const params = state.activeCampaign ? `?campaign_id=${encodeURIComponent(state.activeCampaign)}` : "";
    const data = await api(`/api/memory-report${params}`);
    renderMemoryReport(data);
    showPanel("memory");
  } catch (err) {
    showPanel("logs");
    setLog(err.message);
  }
}

function renderMemoryReport(data) {
  const stats = $("memoryStats");
  const recent = $("memoryRecent");
  const unconfirmed = $("memoryUnconfirmed");
  const compact = $("memoryCompact");
  if (stats) {
    stats.innerHTML = "";
    (data.files || []).forEach((file) => {
      const card = document.createElement("div");
      card.className = "reportMetric";
      card.innerHTML = `<b>${escapeHtml(file.entries ?? 0)}</b><span>${escapeHtml(file.file)}</span><small>${escapeHtml(file.main_bucket || "条目")}</small>`;
      stats.appendChild(card);
    });
  }
  renderReportRows(recent, data.recent_writes || [], (row) => `<b>${escapeHtml(row.type || "摘要")}</b><p>${escapeHtml(row.text || "")}</p>`, "暂无最近写入摘要。");
  renderReportRows(unconfirmed, data.unconfirmed || [], (row) => {
    const items = (row.items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    return `<b>${escapeHtml(row.file)} · ${escapeHtml(row.count || 0)} 条</b><ul>${items}</ul>`;
  }, "暂无未确认内容。");
  const compaction = data.compaction || {};
  const rows = [
    ...(compaction.files || []).filter((row) => row.needs_compaction),
    ...(compaction.npcs || []).filter((row) => row.needs_compaction),
  ];
  renderReportRows(compact, rows, (row) => {
    if (row.file) return `<b>${escapeHtml(row.file)}</b><p>${escapeHtml(row.bucket)} 当前 ${escapeHtml(row.count)} 条，建议保留最近 ${escapeHtml(row.suggested_keep_recent)} 条。</p>`;
    return `<b>NPC：${escapeHtml(row.npc)}</b><p>事实 ${escapeHtml(row.facts)} 条，建议整理成稳定人物摘要。</p>`;
  }, compaction.needs_any_compaction ? "暂无可展示压缩项。" : "当前没有达到压缩阈值的记忆。");
}

function renderReportRows(container, rows, render, emptyText) {
  if (!container) return;
  container.innerHTML = "";
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "reportEmpty";
    empty.textContent = emptyText;
    container.appendChild(empty);
    return;
  }
  rows.forEach((row) => {
    const card = document.createElement("article");
    card.className = "reportRow";
    card.innerHTML = render(row);
    container.appendChild(card);
  });
}

async function openRulesBrowser() {
  closeGalleryOverlay();
  const overlay = $("rulesOverlay");
  overlay.classList.remove("hidden");
  overlay.setAttribute("aria-hidden", "false");
  await loadRulesDirectory($("rulesSearch")?.value.trim() || "");
}

function closeRulesOverlay() {
  const overlay = $("rulesOverlay");
  if (!overlay) return;
  overlay.classList.add("hidden");
  overlay.setAttribute("aria-hidden", "true");
}

async function loadRulesDirectory(query = "") {
  try {
    const suffix = query ? `?q=${encodeURIComponent(query)}` : "";
    const data = await api(`/api/rules${suffix}`);
    state.ruleFiles = data.rules || [];
    renderRulesList(data);
    const first = (data.matches && data.matches[0]) || state.ruleFiles.find((item) => item.name === state.selectedRule) || state.ruleFiles[0];
    if (first) await openRuleFile(first.name);
  } catch (err) {
    setText("rulesViewerTitle", "规则读取失败");
    setText("rulesContent", err.message);
  }
}

function renderRulesList(data) {
  const list = $("rulesList");
  if (!list) return;
  const query = (data.query || "").trim();
  const rows = query ? (data.matches || []) : (data.rules || []);
  list.innerHTML = "";
  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "rulesEmpty";
    empty.textContent = "没有匹配的规则文件。";
    list.appendChild(empty);
    return;
  }
  rows.forEach((rule) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `ruleItem${rule.name === state.selectedRule ? " active" : ""}`;
    const snippets = (rule.snippets || []).map((item) => `<small>${escapeHtml(item)}</small>`).join("");
    button.innerHTML = `<b>${escapeHtml(rule.title || rule.name)}</b><span>${escapeHtml(rule.name)}</span>${snippets}`;
    button.addEventListener("click", () => openRuleFile(rule.name));
    list.appendChild(button);
  });
}

async function openRuleFile(name) {
  if (!name) return;
  state.selectedRule = name;
  document.querySelectorAll(".ruleItem").forEach((item) => item.classList.toggle("active", item.querySelector("span")?.textContent === name));
  const data = await api(`/api/rules?name=${encodeURIComponent(name)}`);
  setText("rulesViewerTitle", data.name || name);
  setText("rulesContent", data.content || "文件为空。");
}

function galleryDetail(asset) {
  const status = assetStatusLabel(asset);
  const suffix = status ? `（${status}）` : "";
  if (asset.detail) return conciseTitle(`${asset.detail}${suffix}`, 96);
  if (asset.kind === "npc") return "当前场景中的可互动角色，头像以稳定名称本地生成。";
  if (asset.kind === "scene") return "当前区域路线图，已缓存为本地 PNG。";
  if (asset.kind === "monster") return "生态或痕迹记录，未确认部分不会写成事实。";
  return "本地记忆中的物品、装备或现场线索。";
}

function buildVisualAssets(campaignState) {
  const recent = campaignState.recent || {};
  const scene = recent.current_scene || {};
  const protectedActors = protectedActorNames(campaignState);
  const pressureAssets = pressureVisualAssets(protectedActors);
  const rows = [];
  rows.push({
    kind: "scene",
    key: `map:${scene.location || state.activeCampaign || "current"}`,
    title: conciseTitle(scene.location || "当前区域地图", 18),
    meta: "地图",
    seed: scene.location || state.activeCampaign || "map",
    scene,
  });
  (scene.active_npcs || [])
    .filter((name) => !isProtectedActorName(name, protectedActors))
    .slice(0, 4)
    .forEach((name) => {
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
  return dedupeAssets([...rows, ...pressureAssets]).slice(0, 16);
}

function pressureVisualAssets(protectedActors = protectedActorNames(state.lastCampaignState || {})) {
  const assets = Array.isArray(state.currentPressurePack?.visual_assets) ? state.currentPressurePack.visual_assets : [];
  return assets.map((asset, index) => {
    const rawKind = String(asset.kind || "").toLowerCase();
    const displayZone = String(asset.display_zone || "").toLowerCase();
    let kind = normalizePressureKind(asset.kind);
    if (kind === "scene" && rawKind === "scene" && displayZone !== "map") {
      kind = "item";
    }
    const title = asset.title || asset.id || `${galleryKindLabel(kind)} ${index + 1}`;
    const detail = asset.detail || asset.source_memory || "";
    const visualPrompt = kind === "item" && rawKind === "scene"
      ? inferSceneVisualPrompt(title, detail)
      : asset.visual_prompt || asset.visualPrompt || inferItemVisualPrompt(title, detail, kind);
    return {
      kind,
      key: `v4:${kind}:${asset.id || title}:${index}`,
      title: conciseTitle(title, 22),
      meta: kind === "item" && rawKind === "scene"
        ? "视觉记录"
        : asset.certainty === "confirmed" ? galleryKindLabel(kind) : `${galleryKindLabel(kind)} / ${asset.certainty || "clue"}`,
      seed: `${asset.id || title}:${detail}`,
      detail,
      certainty: asset.certainty || "clue",
      displayZone: asset.display_zone || "gallery",
      cachePolicy: asset.cache_policy || "stable",
      sourceMemory: asset.source_memory || "",
      visualPrompt,
      imagePrompt: asset.image_prompt || asset.imagePrompt || buildImagePrompt(title, detail, kind),
    };
  }).filter((asset) => asset.kind !== "scene" || asset.displayZone === "map")
    .filter((asset) => !(asset.kind === "npc" && isProtectedActorName(asset.title, protectedActors)));
}

function normalizePressureKind(kind) {
  const value = String(kind || "").toLowerCase();
  if (value === "map" || value === "scene") return "scene";
  if (value === "npc") return "npc";
  if (value === "monster" || value === "ecology") return "monster";
  return "item";
}

function cachedGalleryAssets() {
  return (state.cachedAssets || []).filter((entry) => {
    const kind = String(entry.kind || "");
    const metadata = entry.metadata || {};
    const reusableNpcPortrait = kind === "npc_portrait";
    if (!entry.exists || !entry.metadata || !(kind === "map" || kind.startsWith("gallery_") || reusableNpcPortrait)) return false;
    const normalizedKind = normalizeGalleryKind(kind);
    if (normalizedKind === "scene" && !(kind === "map" || entry.metadata?.source === "map_route")) return false;
    if (normalizedKind !== "npc") return true;
    const title = metadata.title || readableAssetTitle(entry.key, normalizedKind);
    return !isProtectedActorName(title) && !isProtectedActorName(metadata.object_id);
  }).map((entry) => {
    const metadata = entry.metadata || {};
    const normalizedKind = normalizeGalleryKind(entry.kind);
    const title = metadata.title || readableAssetTitle(entry.key, normalizedKind);
    return {
      kind: normalizedKind,
      key: entry.key,
      title: conciseTitle(title, 22),
      meta: metadata.meta || galleryKindLabel(normalizedKind),
      seed: entry.seed || title,
      detail: metadata.detail || "",
      cachedUrl: entry.url,
      sourceObjectId: metadata.object_id || "",
      generatorVersion: entry.generator_version,
      imagePrompt: metadata.image_prompt || {},
    };
  });
}

function protectedActorNames(campaignState = state.lastCampaignState || {}) {
  const card = buildCharacterCard(campaignState, campaignTitle(state.activeCampaign) || state.activeCampaign || "玩家角色", campaignState.recent?.current_scene || {});
  return new Set([
    card.name,
    card.companion?.name,
  ].map(normalizeActorName).filter(Boolean));
}

function currentCompanion() {
  return buildCharacterCard(
    state.lastCampaignState || {},
    campaignTitle(state.activeCampaign) || state.activeCampaign || "玩家角色",
    state.lastCampaignState?.recent?.current_scene || {},
  ).companion;
}

function displaySpeaker(block) {
  const raw = String(block?.speaker || "").trim();
  if (block?.type === "player_action") {
    const normalized = raw.replace(/^player\s*[?？:：-]\s*/i, "").trim();
    return normalized || block.actor_id || "玩家";
  }
  return raw;
}

function visibleCompanion() {
  return protocolCompanionCard(state.frontendState?.companion_card, state.lastCampaignState || {}) || currentCompanion();
}

function insertCompanionMention() {
  const companion = visibleCompanion();
  const input = $("actionInput");
  if (!input || !companion?.name) return;
  const text = `@${companion.name}：`;
  input.value = input.value.trim() ? `${input.value.trim()}\n${text}` : text;
  input.focus();
}

function openCompanionOverlay() {
  const companion = visibleCompanion();
  if (!companion?.name) return;
  setText("companionDialogName", companion.name);
  setText("companionDialogMeta", companion.meta || companion.archetype || "同行伙伴");
  renderCompanionData(companion);
  const image = $("companionDialogImage");
  if (image) {
    drawCompanionAvatar(companion.seed || companion.name, {
      cache: true,
      objectId: slugify(companion.name || "companion"),
      targetImage: image,
      seedText: scopedSeed(companion.seed || companion.name || "companion"),
      archetype: companion.archetype,
      kind: "companion_portrait",
    });
  }
  const overlay = $("companionOverlay");
  if (!overlay) return;
  overlay.classList.remove("hidden");
  overlay.setAttribute("aria-hidden", "false");
}

function renderCompanionData(companion) {
  const holder = $("companionDialogData");
  if (!holder) return;
  const raw = companion.raw && typeof companion.raw === "object" ? companion.raw : {};
  const rows = [
    ["名称", companion.name],
    ["类型", companion.archetype || raw.archetype || raw.species || raw.kind || "companion"],
    ["身份", companion.meta || raw.identity || raw.species || raw.kind || ""],
    ["性格", raw.personality || raw.temperament || ""],
    ["定位", raw.role || raw.class || raw.job || ""],
    ["备注", raw.note || raw.description || raw.summary || ""],
  ].filter((row) => row[1]);
  holder.innerHTML = "";
  rows.forEach(([label, value]) => {
    const item = document.createElement("div");
    item.className = "companionDataItem";
    const b = document.createElement("b");
    b.textContent = label;
    const span = document.createElement("span");
    span.textContent = String(value);
    item.append(b, span);
    holder.appendChild(item);
  });
}

function closeCompanionOverlay() {
  const overlay = $("companionOverlay");
  if (!overlay) return;
  overlay.classList.add("hidden");
  overlay.setAttribute("aria-hidden", "true");
}

function isCompanionActorName(value) {
  const companion = visibleCompanion();
  return Boolean(companion?.name && normalizeActorName(value) === normalizeActorName(companion.name));
}

function isProtectedActorName(value, protectedActors = protectedActorNames()) {
  const raw = String(value || "");
  const normalized = normalizeActorName(raw.replace(/^[^:]+:/, ""));
  if (protectedActors.has(normalized)) return true;
  return Array.from(protectedActors).some((name) => normalized === name || normalized.includes(name));
}

function normalizeActorName(value) {
  return String(value || "").toLowerCase().replace(/[\s_：:「」'"]/g, "").trim();
}

function mergeGalleryAssets(primary, cached) {
  const rows = [...primary];
  const existing = new Set(primary.map((asset) => slugify(asset.key || asset.title)));
  cached.forEach((asset) => {
    const key = slugify(asset.kind === "scene" ? (asset.key || asset.title) : (asset.sourceObjectId || asset.key || asset.title));
    if (!existing.has(key)) {
      rows.push(asset);
      existing.add(key);
    }
  });
  return rows.slice(0, 120);
}

function normalizeGalleryKind(kind) {
  const value = String(kind || "").toLowerCase();
  if (["cg", "generated_cg", "gallery_image", "formal_cg", "剧情图", "生图"].some((token) => value.includes(token))) return "cg";
  if (value.includes("servant") || value.includes("从者")) return "servant";
  if (value.includes("master") || value.includes("御主")) return "master";
  if (value.includes("document") || value.includes("文献")) return "document";
  if (value.includes("clue") || value.includes("线索")) return "clue";
  if (value.includes("anomaly") || value.includes("异常")) return "anomaly";
  if (value.includes("quest") || value.includes("任务")) return "quest";
  if (value.includes("character") || value.includes("角色")) return "character";
  if (value.includes("map")) return "scene";
  if (value.includes("npc") || value.includes("portrait")) return "npc";
  if (value.includes("monster") || value.includes("ecology")) return "monster";
  if (["item", "weapon", "supply", "material", "ritual_tool", "equipment", "物品", "装备", "补给", "材料", "仪式"].some((token) => value.includes(token))) return "item";
  return "";
}

function fixedGalleryKind(kind) {
  const raw = String(kind || "").toLowerCase();
  if (raw.includes("gallery_npc")) return "";
  if (["generated_cg", "gallery_image", "formal_cg", "cg_image"].some((token) => raw.includes(token))) {
    return (state.galleryFilterIds || []).includes("cg") ? "cg" : "";
  }
  const allowed = new Set((state.galleryFilterIds || []).filter((key) => key && key !== "all"));
  if (!allowed.size) return normalizeGalleryKind(kind);
  let value = normalizeGalleryKind(kind);
  const aliases = {
    location: "scene",
    map: "scene",
    ecology: "monster",
    weapon: "item",
    supply: "item",
    material: "item",
    ritual_tool: "item",
  };
  value = aliases[value] || value;
  if (allowed.has(value)) return value;
  if (value === "character" && allowed.has("npc")) return "npc";
  return "";
}

function normalizeGalleryAssetForFixedFilters(asset) {
  const kind = fixedGalleryKind(asset?.kind);
  if (!kind) return null;
  return { ...asset, kind };
}

function readableAssetTitle(key, kind) {
  const text = String(key || kind || "asset")
    .replace(/^gallery_[^:]+:/, "")
    .replace(/^[^:]+:/, "")
    .replace(/:v\d+$/, "")
    .replace(new RegExp(`^${escapeRegExp(state.activeCampaign)}:`), "")
    .replace(/[_-]+/g, " ")
    .trim();
  return text || galleryKindLabel(kind);
}

function escapeRegExp(text) {
  return String(text || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
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
  return { cg: "CG", master: "御主", servant: "从者", npc: "NPC", scene: "场景", item: "物品", monster: "生态", clue: "线索", document: "文献", anomaly: "异常", character: "角色", quest: "任务" }[kind] || "资料";
}

function drawGalleryAsset(targetImage, asset) {
  if (asset.kind === "npc") {
    const feedback = formalPortraitFeedbackAsset(asset.title, asset.title, "npc");
    if (feedback?.url) {
      setAssetImage(targetImage, feedback.url);
      return;
    }
  }
  if (asset.cachedUrl) {
    setAssetImage(targetImage, asset.cachedUrl);
    return;
  }
  const canvas = createAssetCanvas(128, 128);
  const kind = asset.kind === "scene" ? "gallery_map" : asset.kind === "npc" ? "npc_portrait" : `gallery_${asset.kind}`;
  const subdir = asset.kind === "scene" ? "maps" : asset.kind === "npc" || asset.kind === "servant" || asset.kind === "master" ? "portraits" : asset.kind === "cg" ? "generated" : "items";
  const draw = () => {
    if (asset.kind === "scene") drawPixelMap(asset.seed, { cache: false, canvas, scene: asset.scene, compact: true });
    else if (asset.kind === "npc" || asset.kind === "servant" || asset.kind === "master") drawPixelPortraitToCanvas(canvas, asset.seed, "npc");
    else if (asset.kind === "monster") drawCanvasMonster(canvas, asset);
    else drawCanvasItem(canvas, asset);
  };
  if (state.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      targetImage,
      kind,
      subdir,
      objectId: slugify(asset.key || asset.title),
      seedText: scopedSeed(asset.seed || asset.title),
      metadata: {
        title: asset.title,
        detail: galleryDetail(asset),
        meta: asset.meta || galleryKindLabel(asset.kind),
        source: "gallery",
        object_id: asset.key || asset.title,
        certainty: asset.certainty || undefined,
        display_zone: asset.displayZone || undefined,
        cache_policy: asset.cachePolicy || undefined,
        source_memory: asset.sourceMemory || undefined,
        kind: asset.kind,
        visual_prompt: asset.visualPrompt || undefined,
        image_prompt: asset.imagePrompt || buildImagePrompt(asset.title, galleryDetail(asset), asset.kind),
      },
      draw,
    });
    return;
  }
  draw();
  setAssetImage(targetImage, canvas.toDataURL("image/png"));
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

function beginRunProgress() {
  clearTimeout(state.runProgress.hideTimer);
  state.runProgress.active = true;
  state.runProgress.percent = 0;
  state.runProgress.target = 12;
  const panel = $("runProgress");
  if (panel) panel.classList.remove("hidden", "complete");
  setRunProgress(8, "发送行动中");
  startRunProgressTween();
}

function startRunProgressTween() {
  if (state.runProgress.timer) return;
  state.runProgress.timer = setInterval(() => {
    if (!state.runProgress.active) return;
    const diff = state.runProgress.target - state.runProgress.percent;
    if (Math.abs(diff) < 0.35) {
      state.runProgress.percent = state.runProgress.target;
    } else {
      state.runProgress.percent += diff * 0.14;
    }
    paintRunProgress(state.runProgress.percent);
  }, 80);
}

function setRunProgress(target, label) {
  state.runProgress.target = Math.max(state.runProgress.target, Math.min(100, Number(target) || 0));
  setText("runProgressLabel", label || "处理中");
  startRunProgressTween();
}

function updateRunProgressFromPipeline(pipeline, job, output) {
  if (!state.runProgress.active && !job.running) return;
  const stage = pipeline.stage || output.stage || "";
  const labels = {
    director_ready: "V4 层完成",
    actor_parsed: "GPT 层完成",
    audited: "审核层完成",
    synced: "已同步到页面",
    pending_parse: "等待解析层",
  };
  if (pipeline.percent) {
    setRunProgress(pipeline.percent, labels[stage] || pipeline.label || "处理中");
  } else if (stage === "pending_parse") {
    setRunProgress(30, labels.pending_parse);
  } else if (job.running) {
    setRunProgress(Math.max(state.runProgress.target, 18), "后台执行中");
  }
  const succeeded = job.returncode === 0 || job.returncode === undefined || job.returncode === null;
  const failed = job.returncode !== undefined && job.returncode !== null && job.returncode !== 0;
  if (!job.running && failed) {
    failRunProgress();
    return;
  }
  if (!job.running && succeeded && (pipeline.percent >= 100 || output.stage === "parsed")) {
    completeRunProgress();
  }
}

function completeRunProgress() {
  if (!state.runProgress.active) return;
  setRunProgress(100, "已同步到页面");
  const panel = $("runProgress");
  if (panel) panel.classList.add("complete");
  scrollStoryToBottom(true);
  clearTimeout(state.runProgress.hideTimer);
  state.runProgress.hideTimer = setTimeout(() => {
    state.runProgress.active = false;
    const progress = $("runProgress");
    if (progress) progress.classList.add("hidden");
  }, 1500);
}

function failRunProgress() {
  if (!state.runProgress.active) return;
  setText("runProgressLabel", "执行失败");
  const panel = $("runProgress");
  if (panel) panel.classList.add("complete");
  clearTimeout(state.runProgress.hideTimer);
  state.runProgress.hideTimer = setTimeout(() => {
    state.runProgress.active = false;
    const progress = $("runProgress");
    if (progress) progress.classList.add("hidden");
  }, 2200);
}

function paintRunProgress(percent) {
  const value = Math.round(Math.max(0, Math.min(100, percent)));
  const bar = $("runProgressBar");
  if (bar) bar.style.width = `${value}%`;
  setText("runProgressPercent", `${value}%`);
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

function scrollStoryToBottom(force = false) {
  const feed = $("storyTab");
  if (!feed) return;
  if (force || state.activePanel === "story" || state.autoScroll) {
    feed.scrollTo({ top: feed.scrollHeight, behavior: "smooth" });
  }
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

function drawBlockAvatar(targetImage, block, role) {
  const actorKey = block.avatar_key || block.actor_id || block.speaker || role;
  const feedback = formalPortraitFeedbackAsset(actorKey, block.speaker, role);
  if (feedback?.url) {
    setAssetImage(targetImage, feedback.url);
    return;
  }
  const actorSeed = scopedSeed(actorKey);
  const canvas = createAssetCanvas(role === "companion" ? 160 : 96, role === "companion" ? 160 : 96);

  let kind, draw;
  if (role === "companion") {
    const companion = visibleCompanion();
    const companionSeed = scopedSeed(companion?.seed || companion?.name || actorKey);
    kind = "companion_portrait";
    draw = () => drawCompanionToCanvas(canvas, companionSeed, companion?.archetype);
    if (state.activeCampaign) {
      cacheCanvasAsset({
        canvas,
        targetImage,
        kind,
        subdir: "portraits",
        objectId: slugify(companion?.name || actorKey),
        seedText: companionSeed,
        draw,
      });
      return;
    }
  } else if (role === "npc") {
    kind = "npc_portrait";
    draw = () => drawPixelPortraitToCanvas(canvas, actorSeed, "npc");
  } else {
    // Player log avatars reuse the main character portrait cache.
    kind = "portrait";
    draw = () => drawPixelAvatar(actorSeed, { cache: false, variant: "hunter", canvas, targetImage: null });
  }

  if (state.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      targetImage,
      kind,
      subdir: "portraits",
      objectId: slugify(actorKey),
      seedText: actorSeed,
      draw,
    });
    return;
  }
  draw();
  setAssetImage(targetImage, canvas.toDataURL("image/png"));
}

function formalPortraitFeedbackAsset(actorKey = "", speaker = "", role = "") {
  const names = new Set([actorKey, speaker].map(normalizeActorName).filter(Boolean));
  if (!names.size) return null;
  const roleKinds = role === "player"
    ? new Set(["portrait", "player_portrait"])
    : role === "companion"
      ? new Set(["companion", "companion_portrait"])
      : new Set(["npc_portrait"]);
  const candidates = (state.cachedAssets || []).filter((asset) => {
    if (!asset?.exists || !asset.url || !roleKinds.has(String(asset.kind || ""))) return false;
    const metadata = asset.metadata || {};
    const title = normalizeActorName(metadata.title || asset.key || "");
    const objectId = normalizeActorName(metadata.object_id || "");
    return names.has(title) || names.has(objectId);
  });
  return candidates.find((asset) => assetVersionTag(asset) === "VCG")
    || candidates.find((asset) => (asset.metadata || {}).source === "manual_cg_portrait_feedback")
    || null;
}

function assetVersionTag(asset) {
  const metadata = asset?.metadata || {};
  const raw = String(metadata.version_tag || metadata.version || asset?.version_tag || asset?.key || "").toUpperCase();
  return raw.includes("VCG") ? "VCG" : "";
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
  const canvas = options.canvas || createAssetCanvas(96, 96);
  const targetImage = options.targetImage === undefined ? $("avatarImage") : options.targetImage;
  const effectiveSeed = options.seedText || seedText;
  if (options.cache && state.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      targetImage,
      kind: "portrait",
      subdir: "portraits",
      objectId: options.objectId || slugify(seedText),
      seedText: effectiveSeed,
      draw: () => drawPixelAvatar(effectiveSeed, { cache: false, variant: options.variant, canvas, targetImage: null }),
    });
    return;
  }
  if (options.variant === "player_full_body") {
    drawPlayerFullBodyToCanvas(canvas, effectiveSeed);
    if (targetImage) setAssetImage(targetImage, canvas.toDataURL("image/png"));
    return;
  }
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(effectiveSeed);
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
  if (targetImage) setAssetImage(targetImage, canvas.toDataURL("image/png"));
}

function drawPlayerFullBodyToCanvas(canvas, seedText) {
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(`full:${seedText}`);
  const size = canvas.width;
  const cell = size / 32;
  const px = (x, y, w, h, color) => {
    ctx.fillStyle = color;
    ctx.fillRect(Math.round(x * cell), Math.round(y * cell), Math.ceil(w * cell), Math.ceil(h * cell));
  };
  const mirror = (x, y, w, h, color) => {
    px(x, y, w, h, color);
    px(32 - x - w, y, w, h, color);
  };
  const bg = ["#d8c7a8", "#d3ccb7", "#d6c2a5"][(seed >>> 2) % 3];
  const skin = ["#d7a06c", "#c48a5c", "#e0b17d", "#b9794f"][seed % 4];
  const hair = ["#241d17", "#463423", "#1d2528", "#6b4a2e"][(seed >>> 4) % 4];
  const coat = ["#384548", "#314c5d", "#4a3e58", "#3d513e"][(seed >>> 7) % 4];
  const leather = ["#7b5734", "#65452b", "#8a623b"][(seed >>> 11) % 3];
  const accent = ["#d2b56b", "#9fb7c7", "#b66c45", "#c9c0a0"][(seed >>> 14) % 4];
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, size, size);
  px(0, 0, 32, 32, bg);
  px(5, 28, 22, 2, "rgba(76, 58, 39, .28)");
  px(11, 3, 10, 3, hair);
  px(9, 5, 14, 3, hair);
  mirror(8, 7, 3, 4, hair);
  px(10, 7, 12, 8, skin);
  mirror(9, 9, 2, 4, shadeColor(skin, -18));
  px(12, 9, 8, 3, "#e7bd89");
  mirror(12, 10, 2, 1, "#101615");
  px(15, 12, 2, 1, "#805338");
  px(13, 14, 6, 1, "#4e2c24");
  px(10, 15, 12, 2, "#5a3b24");
  px(9, 17, 14, 8, coat);
  mirror(6, 17, 4, 8, leather);
  px(11, 17, 10, 1, accent);
  px(12, 19, 8, 5, shadeColor(coat, -12));
  px(8, 24, 6, 5, "#3a3329");
  px(18, 24, 6, 5, "#3a3329");
  px(7, 29, 7, 1, "#25221d");
  px(18, 29, 7, 1, "#25221d");
  px(23, 12, 2, 13, accent);
  px(24, 11, 1, 3, "#efe0ad");
  if (normalizeActorName(state.activeCampaign).includes("fate")) {
    px(25, 16, 2, 9, "#1e2531");
    px(24, 15, 4, 1, "#c9b76a");
  } else if (normalizeActorName(state.activeCampaign).includes("coc")) {
    px(6, 20, 5, 4, "#d8d0b6");
    px(7, 21, 3, 1, "#5b4a35");
  } else if (normalizeActorName(state.activeCampaign).includes("dnd")) {
    px(5, 17, 4, 6, "#8b8f93");
    px(4, 16, 2, 8, "#b9c0c8");
  }
}

function drawCompanionAvatar(seedText, options = {}) {
  const canvas = options.canvas || createAssetCanvas(160, 160);
  const targetImage = options.targetImage === undefined ? $("palicoImage") : options.targetImage;
  const effectiveSeed = options.seedText || seedText;
  if (options.cache && state.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      targetImage,
      kind: options.kind || "companion_portrait",
      subdir: "portraits",
      objectId: options.objectId || slugify(seedText),
      seedText: effectiveSeed,
      draw: () => drawCompanionToCanvas(canvas, effectiveSeed, options.archetype),
    });
    return;
  }
  drawCompanionToCanvas(canvas, effectiveSeed, options.archetype);
  if (targetImage) setAssetImage(targetImage, canvas.toDataURL("image/png"));
}

function drawCompanionToCanvas(canvas, seedText, archetype = "") {
  const type = normalizeActorName(archetype || inferCompanionArchetype(seedText));
  if (type.includes("palico") || type.includes("艾露") || type.includes("艾鲁") || normalizeActorName(seedText).includes("浩文")) {
    drawHighSpecPalicoToCanvas(canvas, seedText);
    return;
  }
  if (type.includes("servant")) {
    drawHighSpecServantToCanvas(canvas, seedText);
    return;
  }
  drawHighSpecCompanionToCanvas(canvas, seedText, type);
}

function drawHighSpecServantToCanvas(canvas, seedText) {
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(`servant-high:${seedText}`);
  const cell = canvas.width / 40;
  const px = (x, y, w, h, color) => {
    ctx.fillStyle = color;
    ctx.fillRect(Math.round(x * cell), Math.round(y * cell), Math.ceil(w * cell), Math.ceil(h * cell));
  };
  const mirror = (x, y, w, h, color) => {
    px(x, y, w, h, color);
    px(40 - x - w, y, w, h, color);
  };
  const skin = ["#d1a173", "#c08a63", "#deb383", "#a97860"][seed % 4];
  const hair = ["#1d1e26", "#20242d", "#2b241c", "#423342"][(seed >>> 4) % 4];
  const coat = ["#1d2431", "#2f2538", "#1f3032", "#342637"][(seed >>> 8) % 4];
  const accent = ["#c8b45f", "#9cb4d8", "#d6d0ea", "#b96363"][(seed >>> 12) % 4];
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  px(0, 0, 40, 40, "#d4c8b5");
  for (let i = 0; i < 7; i += 1) {
    px(4 + i * 5, 6 + ((seed >>> i) & 3), 2, 18 - (i % 3), "rgba(64,69,88,.38)");
  }
  px(15, 4, 10, 3, hair);
  px(13, 6, 14, 4, hair);
  mirror(12, 8, 3, 8, hair);
  px(14, 10, 12, 10, skin);
  mirror(13, 13, 2, 5, shadeColor(skin, -18));
  px(16, 12, 8, 3, "#e1b98b");
  mirror(16, 14, 2, 1, "#10151a");
  px(19, 16, 2, 1, "#805338");
  px(17, 19, 6, 1, "#4e2c24");
  px(13, 21, 14, 3, "#2a1d20");
  px(11, 24, 18, 9, coat);
  mirror(7, 23, 5, 10, shadeColor(coat, 10));
  px(15, 24, 10, 1, accent);
  px(17, 26, 6, 5, shadeColor(coat, -14));
  px(12, 33, 6, 4, "#202027");
  px(22, 33, 6, 4, "#202027");
  px(11, 37, 8, 1, "#131418");
  px(21, 37, 8, 1, "#131418");
  mirror(5, 10, 2, 16, "rgba(25,30,40,.64)");
  mirror(4, 9, 1, 5, accent);
  px(27, 19, 2, 12, "#151923");
  px(26, 18, 4, 1, accent);
  px(30, 14, 2, 10, "rgba(245,236,208,.65)");
  px(14, 3, 12, 1, accent);
}

function drawHighSpecCompanionToCanvas(canvas, seedText, archetype = "") {
  drawPlayerFullBodyToCanvas(canvas, seedText);
  const ctx = canvas.getContext("2d");
  const cell = canvas.width / 32;
  const px = (x, y, w, h, color) => {
    ctx.fillStyle = color;
    ctx.fillRect(Math.round(x * cell), Math.round(y * cell), Math.ceil(w * cell), Math.ceil(h * cell));
  };
  const type = normalizeActorName(archetype);
  if (type.includes("drone")) {
    px(6, 8, 20, 10, "#5b6f7d");
    px(8, 10, 16, 6, "#8fb0bf");
    px(13, 12, 6, 2, "#d8edf2");
  } else if (type.includes("familiar")) {
    px(4, 5, 5, 5, "#8b6d45");
    px(23, 5, 5, 5, "#8b6d45");
    px(6, 22, 20, 2, "#c8b45f");
  }
}

function drawHighSpecPalicoToCanvas(canvas, seedText) {
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(`palico-high:${seedText}`);
  const cell = canvas.width / 40;
  const px = (x, y, w, h, color) => {
    ctx.fillStyle = color;
    ctx.fillRect(Math.round(x * cell), Math.round(y * cell), Math.ceil(w * cell), Math.ceil(h * cell));
  };
  const mirror = (x, y, w, h, color) => {
    px(x, y, w, h, color);
    px(40 - x - w, y, w, h, color);
  };
  const fur = ["#8a6b48", "#6f573f", "#9a7650"][(seed >>> 2) % 3];
  const light = ["#d7b784", "#e4c38e", "#cfa878"][(seed >>> 6) % 3];
  const armor = ["#354f53", "#5f432b", "#38465f", "#596342"][(seed >>> 9) % 4];
  const accent = ["#d6a23e", "#c8b07c", "#9fb7c7"][(seed >>> 12) % 3];
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  px(0, 0, 40, 40, "#eadfca");
  px(6, 5, 8, 11, fur);
  px(26, 5, 8, 11, fur);
  px(8, 7, 4, 7, "#f2d7a8");
  px(28, 7, 4, 7, "#f2d7a8");
  px(10, 8, 20, 15, fur);
  px(11, 9, 18, 13, shadeColor(fur, 12));
  px(13, 13, 14, 8, light);
  px(15, 11, 10, 3, "#f0cf99");
  mirror(14, 15, 3, 3, "#141716");
  px(19, 17, 2, 2, "#6c4931");
  px(16, 20, 3, 1, "#6c4931");
  px(21, 20, 3, 1, "#6c4931");
  px(17, 22, 6, 1, "#4e2c24");
  px(8, 18, 6, 1, "#6c4931");
  px(26, 18, 6, 1, "#6c4931");
  px(8, 20, 6, 1, "#6c4931");
  px(26, 20, 6, 1, "#6c4931");
  px(13, 6, 14, 3, "#5c4b37");
  px(14, 5, 12, 1, accent);
  px(26, 8, 6, 5, accent);
  px(27, 9, 4, 2, "#f2dfad");
  px(11, 24, 18, 4, "#9f3030");
  px(12, 28, 16, 7, armor);
  mirror(6, 28, 6, 6, "#6d5a43");
  px(9, 35, 7, 2, "#3a3329");
  px(24, 35, 7, 2, "#3a3329");
  px(30, 22, 4, 10, "#8a6b48");
  px(32, 20, 2, 4, light);
  if ((seed >>> 16) & 1) {
    px(5, 26, 4, 7, "#7f5b36");
    px(4, 25, 2, 9, "#c8b07c");
  }
}

function drawPixelPalico(seedText, options = {}) {
  const canvas = options.canvas || createAssetCanvas(96, 96);
  const targetImage = options.targetImage === undefined ? $("palicoImage") : options.targetImage;
  const effectiveSeed = options.seedText || seedText;
  if (options.cache && state.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      targetImage,
      kind: "companion",
      subdir: "portraits",
      objectId: options.objectId || slugify(seedText),
      seedText: effectiveSeed,
      draw: () => drawPixelPalico(effectiveSeed, { cache: false, canvas, targetImage: null }),
    });
    return;
  }
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(effectiveSeed);
  const size = canvas.width;
  const cell = size / 32;
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
  px(0, 0, 32, 32, "#eadfca");
  px(5, 3, 7, 9, "#69513a");
  px(20, 3, 7, 9, "#69513a");
  px(7, 5, 4, 6, "#f2d7a8");
  px(21, 5, 4, 6, "#f2d7a8");
  px(8, 8, 16, 13, "#8a6b48");
  px(9, 9, 14, 11, "#9b7851");
  px(10, 11, 12, 8, "#d7b784");
  px(12, 10, 8, 2, "#f0cf99");
  mirror(11, 13, 3, 3, "#141716");
  px(15, 15, 2, 2, "#6c4931");
  px(12, 17, 3, 1, "#6c4931");
  px(17, 17, 3, 1, "#6c4931");
  px(13, 19, 6, 1, "#4e2c24");
  px(5, 15, 5, 1, "#6c4931");
  px(22, 15, 5, 1, "#6c4931");
  px(5, 17, 5, 1, "#6c4931");
  px(22, 17, 5, 1, "#6c4931");
  px(11, 5, 10, 3, "#5c4b37");
  px(12, 4, 8, 1, "#d6a23e");
  px(20, 7, 5, 4, "#d6a23e");
  px(21, 8, 3, 2, "#f2dfad");
  px(8, 21, 16, 3, "#9f3030");
  px(10, 24, 12, 4, (seed & 1) ? "#3b4e53" : "#5f432b");
  mirror(5, 24, 5, 5, "#6d5a43");
  px(4, 19, 5, 3, "#8a6b48");
  px(23, 19, 5, 3, "#8a6b48");
  if (targetImage) setAssetImage(targetImage, canvas.toDataURL("image/png"));
}

function drawPixelMap(seedText, options = {}) {
  const canvas = options.canvas || $("mapCanvas");
  if (!canvas) return;
  const effectiveSeed = options.seedText || scopedSeed(seedText);
  if (options.cache && state.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      kind: "map",
      subdir: "maps",
      objectId: options.objectId || slugify(seedText),
      seedText: effectiveSeed,
      metadata: options.metadata || undefined,
      draw: () => drawPixelMap(seedText, { cache: false, canvas, scene: options.scene, compact: options.compact, seedText: effectiveSeed }),
    });
    return;
  }
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  const seed = hashSeed(effectiveSeed);
  const scene = options.scene || {};
  ctx.imageSmoothingEnabled = true;
  if (hasSemanticMapCanvas(scene.map_canvas)) {
    drawSemanticSceneMap(ctx, w, h, seed, scene);
    return;
  }
  drawMapPaper(ctx, w, h, seed);
  drawMapTerrain(ctx, w, h, seed);
  drawMapCanvasAscii(ctx, w, h, scene.map_canvas || {});
  drawMapRoute(ctx, w, h, seed, scene);
  drawMapNodes(ctx, w, h, seed, scene, Boolean(options.compact || h < 180));
}

function hasSemanticMapCanvas(mapCanvas = {}) {
  return Array.isArray(mapCanvas.ascii) && mapCanvas.ascii.length || Array.isArray(mapCanvas.points) && mapCanvas.points.length;
}

function drawSemanticSceneMap(ctx, w, h, seed, scene = {}) {
  const mapCanvas = scene.map_canvas || {};
  const palette = mapWorldPalette(scene);
  const layout = buildSemanticSceneLayout(mapCanvas, w, h);
  drawSceneMapBackground(ctx, w, h, palette, seed);
  drawSceneRoom(ctx, layout.mainRoom, palette.mainFloor, palette.wall, palette.wallEdge, "main");
  drawSceneRoom(ctx, layout.secondaryRoom, palette.secondaryFloor, palette.wall, palette.wallEdge, "secondary");
  drawSceneRoom(ctx, layout.stairRoom, palette.utilityFloor, palette.wall, palette.wallEdge, "utility");
  drawSceneRoom(ctx, layout.threatRoom, palette.threatFloor, palette.wall, palette.danger, "danger");
  drawConnectorPassage(ctx, layout.mainRoom, layout.secondaryRoom, palette);
  drawFurnitureLayer(ctx, layout, palette);
  drawSpecialAreas(ctx, layout, mapCanvas, palette, seed);
  drawSemanticRoutes(ctx, layout, mapCanvas, palette);
  drawSemanticMapMarkers(ctx, layout, mapCanvas, palette);
}

function mapWorldPalette(scene = {}) {
  const text = stableJson(scene).toLowerCase();
  if (/coc|克苏鲁|miskatonic|调查/.test(text)) {
    return { bgA: "#e7e2d4", bgB: "#cfc8b8", wall: "#564b44", wallEdge: "#302b28", mainFloor: "#eee4d2", secondaryFloor: "#dde0dc", utilityFloor: "#e4ddce", threatFloor: "#ead6cf", label: "#fffaf0", text: "#3d3128", water: "#15363d", waterHi: "#4f9ca8", danger: "#b3483f", unknown: "#785aa8", interact: "#6f925d", personA: "#b84f47", personB: "#5f8f67", resource: "#b78a34", route: "#8f7a58" };
  }
  if (/dnd|龙|城堡|border|keep|地下城/.test(text)) {
    return { bgA: "#e8dcc4", bgB: "#cbb78e", wall: "#5e5545", wallEdge: "#342d24", mainFloor: "#ead9ba", secondaryFloor: "#d8d4bd", utilityFloor: "#ded2ad", threatFloor: "#ead0bd", label: "#fff7e8", text: "#3c3021", water: "#1f3d45", waterHi: "#68a3ad", danger: "#aa4936", unknown: "#6e5aa2", interact: "#6e8d56", personA: "#af4a3a", personB: "#5f8b56", resource: "#ba8e37", route: "#927148" };
  }
  return { bgA: "#ebe5d8", bgB: "#cfd4d3", wall: "#55483e", wallEdge: "#2f2924", mainFloor: "#efe1c8", secondaryFloor: "#dce1df", utilityFloor: "#e4dac5", threatFloor: "#ead2ca", label: "#fffaf1", text: "#3b3029", water: "#132f38", waterHi: "#4c99a8", danger: "#b3453e", unknown: "#7653a2", interact: "#6f925d", personA: "#bd4d47", personB: "#609269", resource: "#b98734", route: "#8c7757" };
}

function buildSemanticSceneLayout(mapCanvas = {}, w, h) {
  const margin = Math.max(30, w * .04);
  const mainRoom = rect(w * .06, h * .08, w * .38, h * .55);
  const secondaryRoom = rect(w * .54, h * .08, w * .38, h * .46);
  const waterArea = rect(w * .07, h * .68, w * .33, h * .2);
  const stairRoom = rect(w * .44, h * .66, w * .18, h * .22);
  const threatRoom = rect(w * .66, h * .63, w * .27, h * .25);
  const pointMap = new Map();
  (Array.isArray(mapCanvas.points) ? mapCanvas.points : []).forEach((point, index) => {
    const label = String(point.label || point.id || `点位 ${index + 1}`);
    pointMap.set(String(point.id || label), { ...point, label, area: semanticAreaFor(label, point) });
  });
  return { margin, mainRoom, secondaryRoom, waterArea, stairRoom, threatRoom, pointMap };
}

function rect(x, y, w, h) {
  return { x, y, w, h, cx: x + w / 2, cy: y + h / 2 };
}

function semanticAreaFor(label, point = {}) {
  const text = `${label} ${point.id || ""} ${point.kind || ""}`;
  if (/后门|菜市场|卷帘|旧门|shutter|backdoor/i.test(text)) return "secondary";
  if (/楼梯|stair/i.test(text)) return "stairs";
  if (/楼上|威胁|threat|撞裂/i.test(text)) return "threat";
  if (/黑水|水|污染|water/i.test(text)) return "water";
  return "main";
}

function drawSceneMapBackground(ctx, w, h, palette, seed) {
  const g = ctx.createLinearGradient(0, 0, w, h);
  g.addColorStop(0, palette.bgA);
  g.addColorStop(1, palette.bgB);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
  ctx.save();
  ctx.globalAlpha = .14;
  for (let i = 0; i < 260; i += 1) {
    const x = (i * 97 + seed) % w;
    const y = (i * 53 + (seed >>> 3)) % h;
    ctx.fillStyle = i % 2 ? "#7f715f" : "#fff8e9";
    ctx.fillRect(x, y, 2, 2);
  }
  ctx.restore();
}

function drawSceneRoom(ctx, room, floor, wall, edge, variant = "main") {
  ctx.save();
  ctx.fillStyle = "rgba(64,49,37,.14)";
  roundRectPath(ctx, room.x + 8, room.y + 10, room.w, room.h, 18);
  ctx.fill();
  ctx.fillStyle = wall;
  roundRectPath(ctx, room.x, room.y, room.w, room.h, 18);
  ctx.fill();
  ctx.strokeStyle = edge;
  ctx.lineWidth = 4;
  ctx.stroke();
  const inset = Math.max(18, Math.min(room.w, room.h) * .08);
  ctx.fillStyle = floor;
  roundRectPath(ctx, room.x + inset, room.y + inset, room.w - inset * 2, room.h - inset * 2, 12);
  ctx.fill();
  ctx.strokeStyle = "rgba(70,54,38,.16)";
  ctx.lineWidth = 1.5;
  const tile = variant === "secondary" ? 42 : 52;
  for (let x = room.x + inset + tile; x < room.x + room.w - inset; x += tile) {
    ctx.beginPath(); ctx.moveTo(x, room.y + inset); ctx.lineTo(x, room.y + room.h - inset); ctx.stroke();
  }
  for (let y = room.y + inset + tile; y < room.y + room.h - inset; y += tile) {
    ctx.beginPath(); ctx.moveTo(room.x + inset, y); ctx.lineTo(room.x + room.w - inset, y); ctx.stroke();
  }
  if (variant === "danger") {
    ctx.fillStyle = "rgba(179,69,62,.08)";
    roundRectPath(ctx, room.x + inset, room.y + inset, room.w - inset * 2, room.h - inset * 2, 12);
    ctx.fill();
  }
  ctx.restore();
}

function drawConnectorPassage(ctx, main, secondary, palette) {
  const y = main.y + main.h * .58;
  ctx.save();
  ctx.strokeStyle = "rgba(84,72,58,.24)";
  ctx.lineWidth = 26;
  ctx.lineCap = "round";
  ctx.beginPath(); ctx.moveTo(main.x + main.w - 8, y); ctx.lineTo(secondary.x + 8, y); ctx.stroke();
  ctx.strokeStyle = palette.route;
  ctx.lineWidth = 10;
  ctx.setLineDash([18, 14]);
  ctx.beginPath(); ctx.moveTo(main.x + main.w + 8, y); ctx.lineTo(secondary.x - 8, y); ctx.stroke();
  ctx.restore();
}

function drawFurnitureLayer(ctx, layout, palette) {
  const room = layout.mainRoom;
  drawCounter(ctx, room.x + room.w * .13, room.y + room.h * .18, room.w * .32, room.h * .12, palette);
  drawShelves(ctx, room.x + room.w * .58, room.y + room.h * .18, room.w * .22, room.h * .3, palette);
  drawRelicTable(ctx, room.x + room.w * .2, room.y + room.h * .42, room.w * .18, room.h * .15, palette);
  drawThreshold(ctx, room.x + room.w * .44, room.y + room.h * .82, room.w * .22, room.h * .04, palette);
  drawOldDoor(ctx, layout.secondaryRoom.x + layout.secondaryRoom.w * .26, layout.secondaryRoom.y + layout.secondaryRoom.h * .16, layout.secondaryRoom.w * .34, layout.secondaryRoom.h * .09, palette);
  drawRollingDoorGlow(ctx, layout.secondaryRoom.x + layout.secondaryRoom.w * .5, layout.secondaryRoom.y + layout.secondaryRoom.h * .68, layout.secondaryRoom.w * .32, layout.secondaryRoom.h * .12, palette);
  drawStairs(ctx, layout.stairRoom, palette);
}

function drawCounter(ctx, x, y, w, h, palette) {
  ctx.save();
  ctx.fillStyle = "#8f7453";
  roundRectPath(ctx, x, y, w, h, 8); ctx.fill();
  ctx.fillStyle = "#c5a574";
  roundRectPath(ctx, x + 8, y + 7, w - 16, h - 14, 5); ctx.fill();
  ctx.strokeStyle = "rgba(65,44,25,.38)"; ctx.lineWidth = 3; ctx.stroke();
  ctx.restore();
}

function drawShelves(ctx, x, y, w, h, palette) {
  ctx.save();
  for (let i = 0; i < 3; i += 1) {
    const yy = y + i * h / 3;
    ctx.fillStyle = "#7a6448";
    roundRectPath(ctx, x, yy, w, h / 4, 6); ctx.fill();
    ctx.fillStyle = i % 2 ? "#d4b56e" : "#9f7657";
    for (let j = 0; j < 4; j += 1) ctx.fillRect(x + 10 + j * (w - 24) / 4, yy + 7, 9, h / 4 - 14);
  }
  ctx.restore();
}

function drawRelicTable(ctx, x, y, w, h, palette) {
  ctx.save();
  ctx.fillStyle = "#6f5940";
  roundRectPath(ctx, x, y, w, h, 8); ctx.fill();
  ctx.fillStyle = "#554235";
  roundRectPath(ctx, x + w * .24, y + h * .22, w * .52, h * .5, 6); ctx.fill();
  ctx.strokeStyle = palette.resource; ctx.lineWidth = 3; ctx.stroke();
  ctx.restore();
}

function drawThreshold(ctx, x, y, w, h, palette) {
  ctx.save();
  ctx.fillStyle = "#654b36";
  roundRectPath(ctx, x, y, w, Math.max(10, h), 5); ctx.fill();
  ctx.fillStyle = "#d4bd78";
  for (let i = 0; i < 4; i += 1) {
    ctx.beginPath(); ctx.arc(x + 18 + i * 22, y + h / 2, 5, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

function drawOldDoor(ctx, x, y, w, h, palette) {
  ctx.save();
  ctx.fillStyle = "#6f6257";
  roundRectPath(ctx, x, y, w, h, 6); ctx.fill();
  ctx.strokeStyle = "#423930"; ctx.lineWidth = 3; ctx.stroke();
  ctx.restore();
}

function drawRollingDoorGlow(ctx, x, y, w, h, palette) {
  ctx.save();
  const glow = ctx.createRadialGradient(x + w / 2, y + h / 2, 2, x + w / 2, y + h / 2, w);
  glow.addColorStop(0, "rgba(255,68,52,.82)");
  glow.addColorStop(1, "rgba(255,68,52,0)");
  ctx.fillStyle = glow; ctx.fillRect(x - w, y - h * 3, w * 3, h * 7);
  ctx.fillStyle = "#5d5248";
  roundRectPath(ctx, x, y, w, h, 5); ctx.fill();
  ctx.strokeStyle = "#c74235"; ctx.lineWidth = 4; ctx.stroke();
  ctx.restore();
}

function drawStairs(ctx, room, palette) {
  ctx.save();
  const inset = room.w * .18;
  ctx.strokeStyle = "#6f5d46";
  ctx.lineWidth = 5;
  for (let i = 0; i < 6; i += 1) {
    const y = room.y + room.h * .25 + i * room.h * .085;
    ctx.beginPath(); ctx.moveTo(room.x + inset, y); ctx.lineTo(room.x + room.w - inset, y); ctx.stroke();
  }
  ctx.restore();
}

function drawSpecialAreas(ctx, layout, mapCanvas, palette, seed) {
  drawWaterBlob(ctx, layout.waterArea, palette, seed, "large");
  drawWaterBlob(ctx, rect(layout.mainRoom.x + layout.mainRoom.w * .58, layout.mainRoom.y + layout.mainRoom.h * .56, layout.mainRoom.w * .18, layout.mainRoom.h * .14), palette, seed >>> 4, "small");
  drawThreatPulse(ctx, layout.threatRoom, palette, seed);
}

function drawWaterBlob(ctx, area, palette, seed, scale = "large") {
  ctx.save();
  const g = ctx.createRadialGradient(area.cx, area.cy, 8, area.cx, area.cy, Math.max(area.w, area.h));
  g.addColorStop(0, shadeColor(palette.waterHi, 10));
  g.addColorStop(.5, palette.water);
  g.addColorStop(1, "#0d2028");
  ctx.fillStyle = g;
  ctx.beginPath();
  const steps = 18;
  for (let i = 0; i <= steps; i += 1) {
    const a = i / steps * Math.PI * 2;
    const wobble = 1 + Math.sin(a * 3 + seed) * .08 + Math.cos(a * 5 + seed) * .06;
    const x = area.cx + Math.cos(a) * area.w * .5 * wobble;
    const y = area.cy + Math.sin(a) * area.h * .5 * wobble;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.closePath(); ctx.fill();
  ctx.strokeStyle = "rgba(116,188,198,.48)"; ctx.lineWidth = scale === "large" ? 4 : 2; ctx.stroke();
  ctx.strokeStyle = "rgba(222,249,248,.32)"; ctx.lineWidth = 2;
  for (let i = 0; i < (scale === "large" ? 5 : 2); i += 1) {
    ctx.beginPath(); ctx.ellipse(area.cx - area.w * .18 + i * area.w * .09, area.cy + Math.sin(i + seed) * area.h * .08, area.w * .13, area.h * .08, 0, 0, Math.PI * 2); ctx.stroke();
  }
  ctx.restore();
}

function drawThreatPulse(ctx, room, palette, seed) {
  ctx.save();
  const g = ctx.createRadialGradient(room.cx, room.cy, 4, room.cx, room.cy, room.w * .55);
  g.addColorStop(0, "rgba(255,111,64,.35)");
  g.addColorStop(1, "rgba(179,69,62,0)");
  ctx.fillStyle = g; ctx.fillRect(room.x, room.y, room.w, room.h);
  ctx.restore();
}

function drawSemanticRoutes(ctx, layout, mapCanvas, palette) {
  const position = semanticPointPositionFactory(layout);
  ctx.save();
  ctx.lineCap = "round";
  (Array.isArray(mapCanvas.routes) ? mapCanvas.routes : []).forEach((route) => {
    const from = position(route.from);
    const to = position(route.to);
    if (!from || !to) return;
    const blocked = String(route.kind || "").toLowerCase().includes("blocked");
    ctx.strokeStyle = blocked ? "rgba(179,69,62,.58)" : "rgba(143,122,88,.36)";
    ctx.lineWidth = blocked ? 8 : 6;
    ctx.setLineDash(blocked ? [14, 10] : []);
    ctx.beginPath(); ctx.moveTo(from.x, from.y); ctx.lineTo(to.x, to.y); ctx.stroke();
  });
  ctx.restore();
}

function drawSemanticMapMarkers(ctx, layout, mapCanvas, palette) {
  const position = semanticPointPositionFactory(layout);
  const entries = [
    ...(Array.isArray(mapCanvas.points) ? mapCanvas.points : []).map((item) => ({ ...item, source: "point" })),
    ...(Array.isArray(mapCanvas.hazards) ? mapCanvas.hazards : []).map((item) => ({ ...item, source: "hazard" })),
  ];
  const used = [];
  entries.forEach((entry, index) => {
    const label = String(entry.label || entry.id || `点位 ${index + 1}`);
    const kind = semanticMarkerKind(label, entry);
    const pos = resolveSemanticMarkerPosition(label, entry, layout, position, index);
    const shifted = avoidLabelCollision(pos, used);
    used.push(shifted.labelBox);
    drawSemanticIconLabel(ctx, shifted.x, shifted.y, label, kind, palette, shifted.side);
  });
}

function semanticPointPositionFactory(layout) {
  return (idOrLabel) => {
    const raw = layout.pointMap.get(String(idOrLabel));
    if (!raw) return null;
    return resolveSemanticMarkerPosition(raw.label, raw, layout, null, 0);
  };
}

function resolveSemanticMarkerPosition(label, entry, layout, lookup, index) {
  const text = `${label} ${entry.id || ""}`;
  if (/柜台/.test(text)) return { x: layout.mainRoom.x + layout.mainRoom.w * .29, y: layout.mainRoom.y + layout.mainRoom.h * .24, side: "right" };
  if (/货架/.test(text)) return { x: layout.mainRoom.x + layout.mainRoom.w * .68, y: layout.mainRoom.y + layout.mainRoom.h * .28, side: "left" };
  if (/井匣|盒|relic|box/i.test(text)) return { x: layout.mainRoom.x + layout.mainRoom.w * .29, y: layout.mainRoom.y + layout.mainRoom.h * .49, side: "right" };
  if (/铜钱|coin/.test(text)) return { x: layout.mainRoom.x + layout.mainRoom.w * .43, y: layout.mainRoom.y + layout.mainRoom.h * .61, side: "right" };
  if (/陈航/.test(text)) return { x: layout.mainRoom.x + layout.mainRoom.w * .67, y: layout.mainRoom.y + layout.mainRoom.h * .68, side: "left" };
  if (/许守井/.test(text)) return { x: layout.mainRoom.x + layout.mainRoom.w * .28, y: layout.mainRoom.y + layout.mainRoom.h * .74, side: "right" };
  if (/门槛|threshold/.test(text)) return { x: layout.mainRoom.x + layout.mainRoom.w * .54, y: layout.mainRoom.y + layout.mainRoom.h * .84, side: "right" };
  if (/卷帘|红光|shutter/i.test(text)) return { x: layout.secondaryRoom.x + layout.secondaryRoom.w * .65, y: layout.secondaryRoom.y + layout.secondaryRoom.h * .72, side: "left" };
  if (/后门|旧门|backdoor/i.test(text)) return { x: layout.secondaryRoom.x + layout.secondaryRoom.w * .43, y: layout.secondaryRoom.y + layout.secondaryRoom.h * .22, side: "right" };
  if (/未知|clue|unknown|\?/.test(text)) return { x: layout.secondaryRoom.x + layout.secondaryRoom.w * .82, y: layout.secondaryRoom.y + layout.secondaryRoom.h * .5, side: "left" };
  if (/黑水|water/i.test(text)) return { x: layout.waterArea.cx, y: layout.waterArea.cy, side: "right" };
  if (/楼梯|stair/i.test(text)) return { x: layout.stairRoom.cx, y: layout.stairRoom.cy, side: "right" };
  if (/楼上|威胁|threat/i.test(text)) return { x: layout.threatRoom.cx, y: layout.threatRoom.cy, side: "left" };
  const area = semanticAreaFor(label, entry);
  const room = area === "secondary" ? layout.secondaryRoom : area === "stairs" ? layout.stairRoom : area === "threat" ? layout.threatRoom : area === "water" ? layout.waterArea : layout.mainRoom;
  return { x: room.x + room.w * (.25 + (index % 3) * .22), y: room.y + room.h * (.28 + (Math.floor(index / 3) % 3) * .2), side: index % 2 ? "left" : "right" };
}

function semanticMarkerKind(label, entry = {}) {
  const text = `${label} ${entry.kind || ""} ${entry.symbol || ""}`;
  if (/陈航|person|人物|npc|许守井/i.test(text)) return /陈航/.test(text) ? "personDanger" : "person";
  if (/黑水|water|污染|~/.test(text)) return "water";
  if (/铜钱|coin/.test(text)) return "coin";
  if (/危险|威胁|hazard|danger|!|卷帘|红光|楼上/i.test(text)) return "danger";
  if (/未知|clue|unknown|\?/.test(text)) return "unknown";
  if (/资源|交互|resource|\+|井匣|柜台|threshold|门槛/i.test(text)) return "interact";
  return "object";
}

function avoidLabelCollision(pos, used) {
  const labelW = 150;
  const labelH = 38;
  let y = pos.y;
  for (let guard = 0; guard < 8; guard += 1) {
    const box = { x: pos.side === "left" ? pos.x - labelW - 48 : pos.x + 48, y: y - labelH / 2, w: labelW, h: labelH };
    if (!used.some((other) => rectsOverlap(box, other))) return { ...pos, y, labelBox: box };
    y += labelH + 8;
  }
  return { ...pos, y, labelBox: { x: pos.x + 48, y: y - labelH / 2, w: labelW, h: labelH } };
}

function rectsOverlap(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

function drawSemanticIconLabel(ctx, x, y, label, kind, palette, side = "right") {
  const style = semanticIconStyle(kind, palette);
  drawSemanticIcon(ctx, x, y, kind, style);
  const text = conciseTitle(label, 8);
  ctx.save();
  ctx.font = "800 22px Microsoft YaHei";
  const padX = 18;
  const labelW = Math.max(88, ctx.measureText(text).width + padX * 2);
  const labelH = 38;
  const lx = side === "left" ? x - labelW - 48 : x + 48;
  const ly = y - labelH / 2;
  ctx.fillStyle = style.labelBg;
  ctx.strokeStyle = style.labelStroke;
  ctx.lineWidth = 2;
  roundRectPath(ctx, lx, ly, labelW, labelH, 12); ctx.fill(); ctx.stroke();
  ctx.fillStyle = style.labelText;
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.fillText(text, lx + padX, ly + labelH / 2 + 1);
  ctx.restore();
}

function semanticIconStyle(kind, palette) {
  const styles = {
    interact: { fill: "#fff8e7", stroke: palette.interact, text: palette.interact, labelBg: "#fffaf0", labelStroke: "rgba(105,132,80,.34)", labelText: "#48643b" },
    danger: { fill: "#fff0ee", stroke: palette.danger, text: palette.danger, labelBg: "#fff1ee", labelStroke: "rgba(179,69,62,.36)", labelText: "#a43e37" },
    unknown: { fill: "#f6f0ff", stroke: palette.unknown, text: palette.unknown, labelBg: "#faf4ff", labelStroke: "rgba(118,83,162,.34)", labelText: "#66428f" },
    water: { fill: "#edf9fb", stroke: palette.waterHi, text: palette.water, labelBg: "#f1fbfc", labelStroke: "rgba(76,153,168,.36)", labelText: "#1f5b67" },
    coin: { fill: "#fff7df", stroke: palette.resource, text: palette.resource, labelBg: "#fff8e8", labelStroke: "rgba(183,135,52,.35)", labelText: "#7a5a22" },
    person: { fill: "#f8fff7", stroke: palette.personB, text: palette.personB, labelBg: "#fffdf7", labelStroke: "rgba(96,146,105,.35)", labelText: "#3f7048" },
    personDanger: { fill: "#fff3f1", stroke: palette.personA, text: palette.personA, labelBg: "#fff4f2", labelStroke: "rgba(189,77,71,.35)", labelText: "#9b3834" },
    object: { fill: "#fffaf0", stroke: palette.route, text: palette.text, labelBg: "#fffaf0", labelStroke: "rgba(92,75,54,.28)", labelText: palette.text },
  };
  return styles[kind] || styles.object;
}

function drawSemanticIcon(ctx, x, y, kind, style) {
  ctx.save();
  ctx.fillStyle = style.fill;
  ctx.strokeStyle = style.stroke;
  ctx.lineWidth = 4;
  if (kind === "danger" || kind === "personDanger") {
    ctx.beginPath(); ctx.moveTo(x, y - 22); ctx.lineTo(x + 22, y); ctx.lineTo(x, y + 22); ctx.lineTo(x - 22, y); ctx.closePath(); ctx.fill(); ctx.stroke();
  } else {
    ctx.beginPath(); ctx.arc(x, y, 22, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  }
  ctx.fillStyle = style.text;
  ctx.font = "900 24px Microsoft YaHei";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  let glyph = "•";
  if (kind === "interact") glyph = "✦";
  else if (kind === "danger" || kind === "personDanger") glyph = "!";
  else if (kind === "unknown") glyph = "?";
  else if (kind === "water") glyph = "≋";
  else if (kind === "coin") glyph = "¥";
  else if (kind === "person") glyph = "人";
  ctx.fillText(glyph, x, y + 1);
  ctx.restore();
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

function drawMapCanvasAscii(ctx, w, h, mapCanvas = {}) {
  const rows = Array.isArray(mapCanvas.ascii) ? mapCanvas.ascii : [];
  if (!rows.length) return;
  const gridRows = rows.length;
  const gridCols = Math.max(...rows.map((row) => String(row).length), 1);
  const cellW = w / gridCols;
  const cellH = h / gridRows;
  const colors = {
    "#": "rgba(72,51,34,.2)",
    "~": "rgba(45,95,122,.22)",
    "!": "rgba(167,71,50,.16)",
    "?": "rgba(75,125,168,.13)",
    "+": "rgba(83,111,69,.12)",
  };
  ctx.save();
  rows.forEach((row, y) => {
    String(row).split("").forEach((ch, x) => {
      const color = colors[ch];
      if (!color) return;
      ctx.fillStyle = color;
      ctx.fillRect(x * cellW, y * cellH, Math.ceil(cellW), Math.ceil(cellH));
    });
  });
  ctx.strokeStyle = "rgba(91,68,42,.08)";
  ctx.lineWidth = 1;
  for (let x = 0; x <= gridCols; x += 1) {
    ctx.beginPath();
    ctx.moveTo(x * cellW, 0);
    ctx.lineTo(x * cellW, h);
    ctx.stroke();
  }
  for (let y = 0; y <= gridRows; y += 1) {
    ctx.beginPath();
    ctx.moveTo(0, y * cellH);
    ctx.lineTo(w, y * cellH);
    ctx.stroke();
  }
  ctx.restore();
}

function drawMapRoute(ctx, w, h, seed, scene = {}) {
  const structured = structuredMapLayout(scene, w, h);
  if (structured.nodes.length) {
    if (structured.edges.length) {
      structured.edges.forEach((edge) => drawStructuredMapEdge(ctx, edge, structured.nodeMap, w));
    } else {
      for (let i = 0; i < structured.nodes.length - 1; i += 1) {
        drawStructuredMapEdge(ctx, { from: structured.nodes[i].id, to: structured.nodes[i + 1].id, kind: "route" }, structured.nodeMap, w);
      }
    }
    return;
  }
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
  const structured = structuredMapLayout(scene, w, h);
  if (structured.nodes.length) {
    structured.nodes.forEach((node) => drawMapNode(ctx, node, compact));
    structured.markers.forEach((marker) => drawMapMarker(ctx, marker, compact));
    drawMapTitle(ctx, scene.map_route?.title || "结构化路线", w, h, compact);
    return;
  }
  const labels = mapLabels(scene);
  const routeNodes = Array.isArray(scene.map_route?.nodes) ? scene.map_route.nodes.slice(0, 5) : [];
  const positions = [[.17, .66], [.36, .54], [.56, .42], [.72, .31], [.84, .48]];
  const nodes = routeNodes.length
    ? routeNodes.map((node, index) => ({
        label: conciseTitle(node.label || node.id || `节点 ${index + 1}`, compact ? 8 : 12),
        x: w * positions[index][0],
        y: h * positions[index][1],
        tone: node.certainty === "clue" ? "#a74732" : node.certainty === "inferred" ? "#4b7da8" : "#b98634",
      }))
    : [
        { label: labels[0], x: w * .17, y: h * .66, tone: "#b98634" },
        { label: labels[1], x: w * .44, y: h * .52, tone: "#4b7da8" },
        { label: labels[2], x: w * .67, y: h * .38, tone: "#b98634" },
      ];
  if (/泥|痕|药|货车|驮兽/.test(JSON.stringify(scene))) {
    nodes.push({ label: "可疑痕迹", x: w * .58, y: h * .28, tone: "#a74732" });
  }
  const markers = Array.isArray(scene.map_route?.markers) ? scene.map_route.markers.slice(0, 3) : [];
  markers.forEach((marker, index) => {
    nodes.push({
      label: conciseTitle(marker.label || marker.kind || "线索", compact ? 8 : 12),
      x: w * ([.58, .77, .29][index] || .58),
      y: h * ([.28, .62, .34][index] || .28),
      tone: marker.certainty === "confirmed" ? "#536f45" : "#a74732",
    });
  });
  nodes.forEach((node) => drawMapNode(ctx, node, compact));
  drawMapTitle(ctx, scene.map_route?.title || "异常迁徙 / 现场压力", w, h, compact);
}

function structuredMapLayout(scene, w, h) {
  const canvasMap = scene.map_canvas || {};
  const canvasInfo = canvasMap.canvas || {};
  const cols = Math.max(1, Number(canvasInfo.grid_cols) || 32);
  const rows = Math.max(1, Number(canvasInfo.grid_rows) || 18);
  const toPx = (value, max, size) => (Math.max(0, Math.min(max - 1, Number(value) || 0)) + 0.5) / max * size;
  if (Array.isArray(canvasMap.points) && canvasMap.points.length) {
    const nodes = canvasMap.points.slice(0, 12).map((point, index) => {
      const id = String(point.id || point.label || `point_${index + 1}`);
      return {
        id,
        label: conciseTitle(point.label || id, 12),
        x: toPx(point.x, cols, w),
        y: toPx(point.y, rows, h),
        tone: nodeTone(point),
        kind: "node",
        certainty: point.certainty || "confirmed",
      };
    });
    const nodeMap = new Map(nodes.map((node) => [node.id, node]));
    nodes.forEach((node) => nodeMap.set(node.label, node));
    const edges = Array.isArray(canvasMap.routes) ? canvasMap.routes.slice(0, 16) : [];
    const markers = (Array.isArray(canvasMap.hazards) ? canvasMap.hazards.slice(0, 10) : []).map((marker, index) => ({
      label: conciseTitle(marker.label || marker.kind || `标记 ${index + 1}`, 12),
      kind: marker.kind || "hazard",
      certainty: marker.certainty || "uncertain",
      x: toPx(marker.x, cols, w),
      y: toPx(marker.y, rows, h),
      tone: markerTone(marker),
    }));
    return { nodes, nodeMap, edges, markers };
  }
  const route = scene.map_route || {};
  const sourceNodes = Array.isArray(route.nodes) ? route.nodes.slice(0, 7) : [];
  const positions = [[.13, .66], [.29, .54], [.45, .42], [.62, .34], [.78, .43], [.68, .64], [.42, .72]];
  const nodes = sourceNodes.map((node, index) => {
    const id = String(node.id || node.label || `node_${index + 1}`);
    return {
      id,
      label: conciseTitle(node.label || node.id || `节点 ${index + 1}`, 12),
      x: w * positions[index % positions.length][0],
      y: h * positions[index % positions.length][1],
      tone: nodeTone(node),
      kind: "node",
      certainty: node.certainty || "confirmed",
    };
  });
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));
  nodes.forEach((node) => nodeMap.set(node.label, node));
  const edges = Array.isArray(route.edges) ? route.edges.slice(0, 10) : [];
  const markerPositions = [[.58, .25], [.82, .62], [.25, .34], [.52, .78], [.72, .22]];
  const markers = (Array.isArray(route.markers) ? route.markers.slice(0, 5) : []).map((marker, index) => ({
    label: conciseTitle(marker.label || marker.kind || "线索", 12),
    kind: marker.kind || "clue",
    certainty: marker.certainty || "uncertain",
    x: w * markerPositions[index % markerPositions.length][0],
    y: h * markerPositions[index % markerPositions.length][1],
    tone: markerTone(marker),
  }));
  return { nodes, nodeMap, edges, markers };
}

function nodeTone(node) {
  if (node.certainty === "clue") return "#a74732";
  if (node.certainty === "inferred") return "#4b7da8";
  if (node.certainty === "uncertain") return "#8f7653";
  return "#b98634";
}

function markerTone(marker) {
  const kind = String(marker.kind || "").toLowerCase();
  if (kind.includes("hazard") || kind.includes("danger") || kind.includes("危险")) return "#a74732";
  if (kind.includes("trace") || kind.includes("clue") || kind.includes("线索")) return "#4b7da8";
  if (kind.includes("resource") || kind.includes("资源")) return "#5d956b";
  if (kind.includes("pressure") || kind.includes("压力")) return "#b98634";
  return marker.certainty === "confirmed" ? "#536f45" : "#a74732";
}

function drawStructuredMapEdge(ctx, edge, nodeMap, w) {
  const from = nodeMap.get(edge.from);
  const to = nodeMap.get(edge.to);
  if (!from || !to) return;
  const kind = String(edge.kind || "route").toLowerCase();
  const styles = {
    route: { color: "#8b6a3d", width: Math.max(7, w / 74), dash: [] },
    blocked: { color: "#8e3f32", width: Math.max(8, w / 68), dash: [18, 10] },
    trace: { color: "#4b7da8", width: Math.max(5, w / 96), dash: [6, 10] },
    danger: { color: "#a74732", width: Math.max(9, w / 62), dash: [4, 7] },
  };
  const style = styles[kind] || styles.route;
  ctx.save();
  ctx.strokeStyle = "rgba(74,53,31,.18)";
  ctx.lineWidth = style.width + 8;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(from.x, from.y);
  ctx.lineTo(to.x, to.y);
  ctx.stroke();
  ctx.strokeStyle = style.color;
  ctx.lineWidth = style.width;
  ctx.setLineDash(style.dash);
  ctx.beginPath();
  ctx.moveTo(from.x, from.y);
  ctx.lineTo(to.x, to.y);
  ctx.stroke();
  if (kind === "blocked") drawBlockMark(ctx, (from.x + to.x) / 2, (from.y + to.y) / 2, style.width);
  ctx.restore();
}

function drawBlockMark(ctx, x, y, size) {
  ctx.save();
  ctx.strokeStyle = "#f7ead0";
  ctx.lineWidth = Math.max(3, size / 2);
  ctx.beginPath();
  ctx.moveTo(x - size * 1.4, y - size * 1.4);
  ctx.lineTo(x + size * 1.4, y + size * 1.4);
  ctx.moveTo(x + size * 1.4, y - size * 1.4);
  ctx.lineTo(x - size * 1.4, y + size * 1.4);
  ctx.stroke();
  ctx.restore();
}

function drawMapMarker(ctx, marker, compact) {
  const size = compact ? 24 : 42;
  ctx.save();
  ctx.fillStyle = "rgba(255,250,239,.92)";
  ctx.strokeStyle = marker.tone;
  ctx.lineWidth = compact ? 3 : 5;
  ctx.beginPath();
  ctx.arc(marker.x, marker.y, size, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = marker.tone;
  ctx.font = `900 ${compact ? 18 : 28}px Microsoft YaHei`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(markerGlyph(marker.kind), marker.x, marker.y + 1);
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";
  ctx.font = `800 ${compact ? 14 : 24}px Microsoft YaHei`;
  ctx.fillText(conciseTitle(marker.label, compact ? 6 : 9), marker.x + size + 6, marker.y + (compact ? 5 : 9));
  ctx.restore();
}

function markerGlyph(kind) {
  const value = String(kind || "").toLowerCase();
  if (value.includes("hazard") || value.includes("danger") || value.includes("危险")) return "!";
  if (value.includes("resource") || value.includes("Resources")) return "+";
  if (value.includes("pressure") || value.includes("Pressure")) return "压";
  return "?";
}

function drawMapTitle(ctx, title, w, h, compact) {
  ctx.save();
  ctx.font = `800 ${compact ? 22 : 42}px Microsoft YaHei`;
  ctx.fillStyle = "#536f45";
  ctx.strokeStyle = "rgba(255,250,239,.8)";
  ctx.lineWidth = compact ? 6 : 9;
  ctx.strokeText(conciseTitle(title, compact ? 14 : 18), w * .18, h * .9);
  ctx.fillText(conciseTitle(title, compact ? 14 : 18), w * .18, h * .9);
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
  const prompt = asset.visualPrompt || asset.visual_prompt || inferItemVisualPrompt(asset.title, asset.detail, asset.kind);
  const type = String(prompt.type || "").toLowerCase();
  const silhouette = String(prompt.silhouette || "").toLowerCase();
  const text = `${asset.title}${asset.detail || ""}${asset.meta || ""}${asset.kind || ""}${type}${silhouette}`;
  if (type === "red_gate_signal" || silhouette.includes("door_crack_light")) return drawRedGateSignalIcon(ctx, canvas.width, canvas.height, seed);
  if (type === "broken_door_impact" || silhouette.includes("cracked_door")) return drawBrokenDoorImpactIcon(ctx, canvas.width, canvas.height, seed);
  if (type === "switch_axe" || silhouette.includes("transforming_axe")) return drawSwitchAxeIcon(ctx, canvas.width, canvas.height, seed);
  if (type === "sealed_relic_box" || silhouette.includes("sealed_square_box")) return drawRelicBoxIcon(ctx, canvas.width, canvas.height, seed);
  if (type === "phone" || silhouette.includes("smartphone")) return drawPhoneIcon(ctx, canvas.width, canvas.height, seed);
  if (type === "mud_armor_fragment" || silhouette.includes("armor_fragment")) return drawMudArmorFragmentIcon(ctx, canvas.width, canvas.height, seed);
  if (/楼上|撞击|裂|cracked/.test(text)) return drawBrokenDoorImpactIcon(ctx, canvas.width, canvas.height, seed);
  if (/卷帘|红光|gate/.test(text)) return drawRedGateSignalIcon(ctx, canvas.width, canvas.height, seed);
  if (/门缝|door/.test(text)) return drawRedGateSignalIcon(ctx, canvas.width, canvas.height, seed);
  if (/手机|电话|信号|拨号|屏幕|phone|smartphone/.test(text)) return drawPhoneIcon(ctx, canvas.width, canvas.height, seed);
  if (/ritual|仪式|占卜|骨|匣|盒|钥匙/.test(text)) return drawRitualIcon(ctx, canvas.width, canvas.height, seed);
  if (/泥|痕/.test(text)) return drawMudIcon(ctx, canvas.width, canvas.height, seed);
  if (/药|瓶|supply/.test(text)) return drawBottleIcon(ctx, canvas.width, canvas.height, seed);
  if (/斧|装备|武器|weapon/.test(text)) return drawAxeIcon(ctx, canvas.width, canvas.height, seed);
  if (/登记|任务板|木牌|记录|document|文献|信|照片|书/.test(text)) return drawSignIcon(ctx, canvas.width, canvas.height, seed);
  if (/羽|鳞|素材|碎片|material/.test(text)) return drawScaleIcon(ctx, canvas.width, canvas.height, seed);
  return drawSatchelIcon(ctx, canvas.width, canvas.height, seed);
}

function inferItemVisualPrompt(title = "", detail = "", kind = "") {
  const text = `${title} ${detail} ${kind}`;
  let type = "satchel";
  let category = "misc";
  let role = "record";
  let material = "";
  let silhouette = "";
  if (/手机|电话|信号|拨号|屏幕|phone|smartphone/i.test(text)) {
    type = "phone"; category = "device"; role = "communication_or_clue"; material = "glass_and_plastic"; silhouette = "smartphone";
  } else if (/斩斧|switch\s*axe/i.test(text)) {
    type = "switch_axe"; category = "weapon"; role = "equipment"; material = "bone_and_metal"; silhouette = "long_transforming_axe_sword";
  } else if (/井匣|金属盒|盒|匣/.test(text)) {
    type = "sealed_relic_box"; category = "ritual_tool"; role = "clue"; material = "dark_metal"; silhouette = "sealed_square_box";
  } else if (/泥甲|泥壳|甲片/.test(text)) {
    type = "mud_armor_fragment"; category = "material"; role = "loot_or_trace"; material = "mud_shell"; silhouette = "broken_armor_fragment";
  } else if (/鳞|羽|素材|碎片|样本/.test(text)) {
    type = "material"; category = "material"; role = "loot_or_trace"; material = "organic_material"; silhouette = "fragment";
  } else if (/药|瓶|补给|绷带|食物/.test(text)) {
    type = "bottle"; category = "supply"; role = "resource"; material = "glass_or_wood_crate"; silhouette = "supply_container";
  } else if (/信|照片|书|文件|登记|地图|记录|document/.test(text)) {
    type = "paper"; category = "document"; role = "clue"; material = "paper"; silhouette = "document";
  } else if (/骨|符|钥匙|仪式|占卜/.test(text)) {
    type = "ritual_bone"; category = "ritual_tool"; role = "clue"; material = "bone_or_talisman"; silhouette = "ritual_object";
  } else if (/斧|剑|弓|枪|武器|刀|weapon/.test(text)) {
    type = "weapon"; category = "weapon"; role = "equipment"; material = "metal_or_bone"; silhouette = "weapon";
  }
  return { type, category, role, material, silhouette, source_text: conciseTitle(text, 120) };
}

function buildImagePrompt(title = "", detail = "", kind = "item") {
  const aspectRatio = kind === "scene" || kind === "map" ? "16:9" : "1:1";
  const stylePreset = "cinematic anime urban horror, Fate-inspired, controlled lighting";
  return {
    positive_prompt: conciseTitle(`${title}, ${detail}, ${stylePreset}, clear subject, coherent composition, readable details`, 420),
    negative_prompt: "low quality, blurry, text artifacts, watermark, logo, extra limbs, malformed hands, incoherent layout",
    aspect_ratio: aspectRatio,
    style_preset: stylePreset,
    quality: {
      steps: 30,
      cfg_scale: 6.5,
      sampler: "DPM++ 2M Karras",
      size: aspectRatio === "16:9" ? "1280x720" : "1024x1024",
    },
  };
}

function inferSceneVisualPrompt(title = "", detail = "") {
  const text = `${title} ${detail}`;
  let type = "scene_visual";
  let material = "environment";
  let silhouette = "scene_marker";
  if (/卷帘|红光|gate|red/i.test(text)) {
    type = "red_gate_signal";
    material = "metal_door_and_red_light";
    silhouette = "door_crack_light";
  } else if (/楼上|撞击|木门|裂/.test(text)) {
    type = "broken_door_impact";
    material = "wood_and_shadow";
    silhouette = "cracked_door";
  } else if (/门|door/i.test(text)) {
    type = "red_gate_signal";
    material = "metal_door_and_red_light";
    silhouette = "door_crack_light";
  } else if (/黑水|倒影|影/.test(text)) {
    type = "black_water_shadow";
    material = "dark_water_reflection";
    silhouette = "shadow_figures";
  }
  return { type, category: "scene_visual", role: "visual_record", material, silhouette, source_text: conciseTitle(text, 120) };
}

function drawRedGateSignalIcon(ctx, w, h, seed) {
  drawIconBase(ctx, w, h, "#c8a66c", "#6c472e");
  const x = w * 0.25;
  const y = h * 0.18;
  const doorW = w * 0.5;
  const doorH = h * 0.64;
  ctx.save();
  ctx.fillStyle = "#4c3829";
  ctx.fillRect(x, y, doorW, doorH);
  ctx.fillStyle = "#6e5840";
  ctx.fillRect(x + 8, y + 8, doorW - 16, doorH - 16);
  ctx.fillStyle = "#1f1713";
  ctx.fillRect(x + doorW * 0.48, y + 6, 5, doorH - 12);
  ctx.strokeStyle = "#bb8b36";
  ctx.lineWidth = 4;
  for (let i = 0; i < 4; i += 1) {
    const yy = y + 14 + i * (doorH - 28) / 3;
    ctx.beginPath();
    ctx.moveTo(x + 8, yy);
    ctx.lineTo(x + doorW - 8, yy);
    ctx.stroke();
  }
  const pulse = 10 + (seed % 9);
  const grad = ctx.createRadialGradient(w * 0.5, h * 0.55, 2, w * 0.5, h * 0.55, w * 0.34);
  grad.addColorStop(0, "rgba(255,62,47,.92)");
  grad.addColorStop(0.45, "rgba(202,31,38,.48)");
  grad.addColorStop(1, "rgba(255,62,47,0)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = "#f6d989";
  ctx.fillRect(w * 0.48, y + doorH - pulse, 6, pulse);
  ctx.restore();
}

function drawBrokenDoorImpactIcon(ctx, w, h, seed) {
  drawIconBase(ctx, w, h, "#b89b72", "#654629");
  ctx.save();
  const x = w * 0.22;
  const y = h * 0.16;
  const doorW = w * 0.56;
  const doorH = h * 0.68;
  ctx.fillStyle = "#6a4a31";
  ctx.fillRect(x, y, doorW, doorH);
  ctx.fillStyle = "#9b7449";
  ctx.fillRect(x + 9, y + 9, doorW - 18, doorH - 18);
  ctx.strokeStyle = "#3a2519";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(w * 0.53, y + 10);
  ctx.lineTo(w * 0.46, h * 0.38);
  ctx.lineTo(w * 0.58, h * 0.5);
  ctx.lineTo(w * 0.49, y + doorH - 8);
  ctx.stroke();
  ctx.fillStyle = "#231714";
  ctx.beginPath();
  ctx.moveTo(w * 0.49, h * 0.36);
  ctx.lineTo(w * 0.64, h * 0.43);
  ctx.lineTo(w * 0.55, h * 0.52);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "#d9b86b";
  ctx.lineWidth = 3;
  for (let i = 0; i < 3; i += 1) {
    const dy = (seed % 7) + i * 10;
    ctx.beginPath();
    ctx.moveTo(w * 0.2, h * 0.26 + dy);
    ctx.lineTo(w * 0.08, h * 0.2 + dy);
    ctx.moveTo(w * 0.8, h * 0.34 + dy);
    ctx.lineTo(w * 0.92, h * 0.27 + dy);
    ctx.stroke();
  }
  ctx.restore();
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

function drawMudArmorFragmentIcon(ctx, w, h) {
  ctx.save();
  ctx.translate(w * .5, h * .54);
  ctx.rotate(-0.18);
  ctx.fillStyle = "#8a6a43";
  ctx.beginPath();
  ctx.moveTo(-w * .26, -h * .22);
  ctx.lineTo(w * .2, -h * .31);
  ctx.lineTo(w * .32, -h * .03);
  ctx.lineTo(w * .14, h * .25);
  ctx.lineTo(-w * .22, h * .18);
  ctx.lineTo(-w * .35, -h * .04);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "#4f3725";
  ctx.lineWidth = Math.max(4, w * .035);
  ctx.stroke();
  ctx.strokeStyle = "#d2b16f";
  ctx.lineWidth = Math.max(3, w * .025);
  ctx.beginPath();
  ctx.moveTo(-w * .18, -h * .08);
  ctx.lineTo(w * .16, -h * .13);
  ctx.moveTo(-w * .1, h * .06);
  ctx.lineTo(w * .18, h * .02);
  ctx.stroke();
  ctx.fillStyle = "#5e422b";
  for (let i = 0; i < 5; i += 1) {
    ctx.beginPath();
    ctx.ellipse(-w * .2 + i * w * .1, h * (.16 - (i % 2) * .08), w * .035, h * .02, i, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
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

function drawPhoneIcon(ctx, w, h) {
  ctx.fillStyle = "#2b2b27";
  roundRectPath(ctx, w * .31, h * .18, w * .38, h * .64, 9);
  ctx.fill();
  ctx.fillStyle = "#111716";
  roundRectPath(ctx, w * .35, h * .24, w * .3, h * .46, 4);
  ctx.fill();
  ctx.strokeStyle = "#8b6635";
  ctx.lineWidth = 4;
  roundRectPath(ctx, w * .35, h * .24, w * .3, h * .46, 4);
  ctx.stroke();
  ctx.fillStyle = "#b23b2e";
  ctx.fillRect(w * .43, h * .43, w * .14, h * .05);
  ctx.fillRect(w * .48, h * .35, w * .04, h * .21);
  ctx.fillStyle = "#6f6046";
  ctx.fillRect(w * .43, h * .73, w * .14, h * .025);
  ctx.strokeStyle = "#c0a15c";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(w * .38, h * .2);
  ctx.lineTo(w * .46, h * .1);
  ctx.moveTo(w * .5, h * .18);
  ctx.lineTo(w * .5, h * .08);
  ctx.moveTo(w * .62, h * .2);
  ctx.lineTo(w * .54, h * .1);
  ctx.stroke();
  ctx.fillStyle = "rgba(255,245,215,.58)";
  ctx.fillRect(w * .38, h * .28, w * .16, h * .035);
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

function drawSwitchAxeIcon(ctx, w, h) {
  ctx.save();
  ctx.translate(w * .5, h * .54);
  ctx.rotate(-0.72);
  ctx.strokeStyle = "#4c3824";
  ctx.lineWidth = 10;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(-w * .34, h * .22);
  ctx.lineTo(w * .28, -h * .24);
  ctx.stroke();
  ctx.fillStyle = "#d8c089";
  ctx.beginPath();
  ctx.moveTo(w * .18, -h * .32);
  ctx.lineTo(w * .43, -h * .17);
  ctx.lineTo(w * .2, h * .02);
  ctx.lineTo(w * .05, -h * .1);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#7b5734";
  ctx.fillRect(-w * .05, -h * .03, w * .14, h * .1);
  ctx.fillStyle = "#9c7a45";
  ctx.fillRect(-w * .24, h * .07, w * .22, h * .08);
  ctx.fillStyle = "#e6d3a4";
  ctx.fillRect(w * .22, -h * .2, w * .15, h * .04);
  ctx.restore();
  ctx.fillStyle = "#5f4a2e";
  ctx.fillRect(w * .25, h * .78, w * .5, h * .04);
}

function drawRelicBoxIcon(ctx, w, h) {
  ctx.fillStyle = "#3b3b3a";
  roundRectPath(ctx, w * .25, h * .25, w * .5, h * .5, 10);
  ctx.fill();
  ctx.strokeStyle = "#b28b47";
  ctx.lineWidth = 5;
  roundRectPath(ctx, w * .29, h * .29, w * .42, h * .42, 7);
  ctx.stroke();
  ctx.fillStyle = "#171918";
  ctx.fillRect(w * .34, h * .42, w * .32, h * .08);
  ctx.fillStyle = "#9c1f2c";
  ctx.beginPath();
  ctx.arc(w * .5, h * .5, w * .075, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#d0a24d";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(w * .5, h * .31);
  ctx.lineTo(w * .5, h * .69);
  ctx.moveTo(w * .31, h * .5);
  ctx.lineTo(w * .69, h * .5);
  ctx.stroke();
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

function drawRitualIcon(ctx, w, h) {
  ctx.fillStyle = "#e5d0a2";
  ctx.beginPath();
  ctx.ellipse(w * .5, h * .58, w * .24, h * .15, -.2, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#5b3a25";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(w * .3, h * .62);
  ctx.quadraticCurveTo(w * .5, h * .34, w * .72, h * .58);
  ctx.stroke();
  ctx.fillStyle = "#7a4e2c";
  ctx.fillRect(w * .47, h * .35, w * .08, h * .34);
  ctx.fillStyle = "#c09a4a";
  ctx.beginPath();
  ctx.arc(w * .5, h * .3, w * .08, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#ead7a4";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(w * .35, h * .74);
  ctx.lineTo(w * .65, h * .74);
  ctx.stroke();
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

function createAssetCanvas(width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

function setAssetImage(targetImage, url) {
  if (!targetImage || !url) return;
  targetImage.classList.toggle("formalAsset", /cg_feedback|manual_cg|formal_cg|_VCG|:VCG/i.test(url));
  if (url.startsWith("/campaign-assets/")) {
    targetImage.src = `${url}${url.includes("?") ? "&" : "?"}v=${ASSET_GENERATOR_VERSION}`;
    return;
  }
  targetImage.src = url;
}

async function cacheCanvasAsset({ canvas, targetImage, kind, subdir, objectId, seedText, metadata, draw }) {
  const campaignId = state.activeCampaign;
  const campaignSeed = state.assetSeed || campaignId || "campaign";
  const safeId = slugify(objectId || seedText || kind);
  const key = `${kind}:${campaignId}:${campaignSeed}:${safeId}:v${ASSET_GENERATOR_VERSION}`;
  const safeSeed = slugify(campaignSeed).slice(0, 24) || "seed";
  const locked = lockedAvatarAsset(kind, safeId, metadata);
  if (locked?.url) {
    state.assetCache[key] = { url: locked.url };
    setAssetImage(targetImage, locked.url);
    return;
  }
  const memory = state.assetCache[key];
  if (memory === "pending") {
    draw();
    setAssetImage(targetImage, canvas.toDataURL("image/png"));
    return;
  }
  if (memory?.url) {
    setAssetImage(targetImage, memory.url);
    if (targetImage && canvas.id !== "mapCanvas") return;
    drawImageToCanvas(canvas, memory.url, draw);
    return;
  }
  state.assetCache[key] = "pending";
  try {
    const lookup = await api(`/api/asset?campaign_id=${encodeURIComponent(campaignId)}&key=${encodeURIComponent(key)}`);
    if (lookup.exists && lookup.url) {
      if (assetMetadataReusable(metadata, lookup.entry?.metadata)) {
        state.assetCache[key] = { url: lookup.url };
        setAssetImage(targetImage, lookup.url);
        if (targetImage && canvas.id !== "mapCanvas") return;
        drawImageToCanvas(canvas, lookup.url, draw);
        return;
      }
    }
    draw();
    const dataUrl = canvas.toDataURL("image/png");
    const saved = await api("/api/asset", {
      method: "POST",
      body: JSON.stringify({
        campaign_id: campaignId,
        key,
        kind,
        subdir,
        filename: `${kind}_${safeSeed}_${safeId}_v${ASSET_GENERATOR_VERSION}`,
        seed: String(seedText || key),
        asset_seed: state.assetSeed || undefined,
        style: "local_canvas_pixel",
        generator_version: ASSET_GENERATOR_VERSION,
        metadata: metadata || undefined,
        data_url: dataUrl,
      }),
    });
    state.assetCache[key] = saved.url ? { url: saved.url } : null;
    setAssetImage(targetImage, saved.url || dataUrl);
    if (saved.url) updateMapImageIfNeeded(canvas, saved.url);
  } catch (err) {
    console.warn("asset cache failed", err);
    state.assetCache[key] = null;
    draw();
    const dataUrl = canvas.toDataURL("image/png");
    setAssetImage(targetImage, dataUrl);
    updateMapImageIfNeeded(canvas, dataUrl);
  }
}

function lockedAvatarAsset(kind, safeId, metadata = {}) {
  if (!["portrait", "npc_portrait", "companion", "companion_portrait", "monster_portrait"].includes(String(kind))) return null;
  const requestedNames = new Set([
    safeId,
    metadata.title,
    metadata.object_id,
    metadata.actor_id,
  ].map(normalizeActorName).filter(Boolean));
  return (state.cachedAssets || []).find((asset) => {
    if (!asset?.exists || !asset.url || String(asset.kind || "") !== String(kind)) return false;
    if (assetVersionTag(asset) !== "VCG") return false;
    const assetMeta = asset.metadata || {};
    const assetNames = [
      assetMeta.title,
      assetMeta.object_id,
      assetMeta.actor_id,
      asset.key,
    ].map(normalizeActorName).filter(Boolean);
    return assetNames.some((name) => requestedNames.has(name));
  }) || null;
}

function assetMetadataReusable(requested, existing) {
  if (!requested) return true;
  if (!existing) return false;
  if (requested.map_canvas?.points?.length || requested.map_canvas?.ascii?.length) {
    return stableJson(requested.map_canvas) === stableJson(existing.map_canvas || {});
  }
  if (requested.map_route?.nodes?.length || requested.map_route?.edges?.length || requested.map_route?.markers?.length) {
    return stableJson(requested.map_route) === stableJson(existing.map_route || {});
  }
  return true;
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
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

function scopedSeed(value) {
  const seed = state.assetSeed || state.activeCampaign || "campaign";
  const raw = String(value || "asset");
  const prefix = `${seed}:`;
  return raw.startsWith(prefix) ? raw : `${prefix}${raw}`;
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


