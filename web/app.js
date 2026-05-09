const state = {
  campaign: {
    campaigns: [],
    activeCampaign: "",
    selectedCampaign: "",
    lastCampaignState: {},
    frontendState: {},
    assetSeed: "",
    streamingPreview: false,
  },
  story: {},
  assets: {},
  gallery: {},
  map: {},
  character: {},
  writeback: {},
  job: {},
  ui: {},
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
  galleryFilterIds: ["all"],
  rawAssets: [],
  rawGallery: {},
  renderedMapKey: "",
  canvasRules: "",
  renderedRawAssets: [],
  cachedAssets: [],
  storyTurnsByCampaign: {},
  storyTurnSignatures: {},
  selectedGalleryKey: "",
  transientGalleryAsset: null,
  currentMapAsset: null,
  writebackReview: {},
  currentPressurePack: {},
  characterProfileExpanded: false,
  characterProfileCampaign: "",
  ruleFiles: [],
  selectedRule: "",
  frontendState: {},
  visualContracts: {},
  storyProgressPayload: {},
  storyProgressChapter: {},
  storyProgressNode: {},
  streamingPreview: false,
  modulePayloadCache: {},
  assetSeed: "",
  dragPanels: {},
  activeDragPanel: null,
  activeReferenceDrag: null,
  runProgress: {
    active: false,
    percent: 0,
    target: 0,
    timer: null,
    hideTimer: null,
    streamTimer: null,
    jobId: "",
    streamText: "",
    streamError: "",
    publicThink: [],
    publicNote: "",
    stage: "",
    needsHumanVerification: false,
    completing: false,
  },
};

document.documentElement.setAttribute("translate", "no");
document.documentElement.classList.add("notranslate");
document.body?.setAttribute("translate", "no");
document.body?.classList.add("notranslate");

const LEGACY_STATE_FIELDS = {
  campaigns: ["campaign", "campaigns"],
  activeCampaign: ["campaign", "activeCampaign"],
  selectedCampaign: ["campaign", "selectedCampaign"],
  lastCampaignState: ["campaign", "lastCampaignState"],
  frontendState: ["campaign", "frontendState"],
  assetSeed: ["campaign", "assetSeed"],
  streamingPreview: ["campaign", "streamingPreview"],
  storyTurnsByCampaign: ["story", "storyTurnsByCampaign"],
  storyTurnSignatures: ["story", "storyTurnSignatures"],
  currentPressurePack: ["story", "currentPressurePack"],
  storyProgressPayload: ["story", "storyProgressPayload"],
  storyProgressChapter: ["story", "storyProgressChapter"],
  storyProgressNode: ["story", "storyProgressNode"],
  assetCache: ["assets", "assetCache"],
  cachedAssets: ["assets", "cachedAssets"],
  canvasRules: ["assets", "canvasRules"],
  visualContracts: ["assets", "visualContracts"],
  modulePayloadCache: ["assets", "modulePayloadCache"],
  galleryFilter: ["gallery", "galleryFilter"],
  galleryFilterIds: ["gallery", "galleryFilterIds"],
  rawAssets: ["gallery", "rawAssets"],
  rawGallery: ["gallery", "rawGallery"],
  renderedRawAssets: ["gallery", "renderedRawAssets"],
  selectedGalleryKey: ["gallery", "selectedGalleryKey"],
  transientGalleryAsset: ["gallery", "transientGalleryAsset"],
  renderedMapKey: ["map", "renderedMapKey"],
  currentMapAsset: ["map", "currentMapAsset"],
  characterProfileExpanded: ["character", "characterProfileExpanded"],
  characterProfileCampaign: ["character", "characterProfileCampaign"],
  lastCharacterCardForRender: ["character", "lastCharacterCardForRender"],
  rawInventoryState: ["character", "rawInventoryState"],
  rawInventoryItems: ["character", "rawInventoryItems"],
  inventoryEvents: ["character", "inventoryEvents"],
  latestDossierPayload: ["character", "latestDossierPayload"],
  writebackReview: ["writeback", "writebackReview"],
  polling: ["job", "polling"],
  lastJobRunning: ["job", "lastJobRunning"],
  runProgress: ["job", "runProgress"],
  sideTab: ["ui", "sideTab"],
  activePanel: ["ui", "activePanel"],
  autoScroll: ["ui", "autoScroll"],
  collapsedPanels: ["ui", "collapsedPanels"],
  ruleFiles: ["ui", "ruleFiles"],
  selectedRule: ["ui", "selectedRule"],
  dragPanels: ["ui", "dragPanels"],
  activeDragPanel: ["ui", "activeDragPanel"],
  activeReferenceDrag: ["ui", "activeReferenceDrag"],
};

function partitionLegacyState() {
  Object.entries(LEGACY_STATE_FIELDS).forEach(([field, [section, key]]) => {
    state[section] = state[section] || {};
    if (Object.prototype.hasOwnProperty.call(state, field)) {
      state[section][key] = state[field];
      delete state[field];
    } else if (!Object.prototype.hasOwnProperty.call(state[section], key)) {
      state[section][key] = undefined;
    }
    Object.defineProperty(state, field, {
      configurable: false,
      enumerable: false,
      get() {
        return state[section][key];
      },
      set(value) {
        state[section][key] = value;
      },
    });
  });
}

partitionLegacyState();

function activeCampaignId() {
  return state.campaign.activeCampaign || "";
}

function currentFrontendState() {
  return state.campaign.frontendState || {};
}

function currentCampaignState() {
  return state.campaign.lastCampaignState || {};
}

function currentAssets() {
  return state.assets.cachedAssets || [];
}

function currentGalleryState() {
  return state.gallery || {};
}

function currentRunProgress() {
  return state.job.runProgress || {};
}

function currentAssetCache() {
  return state.assets.assetCache || {};
}

function currentModulePayloadCache() {
  return state.assets.modulePayloadCache || {};
}

function currentUiState() {
  return state.ui || {};
}

function currentStoryState() {
  return state.story || {};
}

const $ = (id) => document.getElementById(id);
const ASSET_GENERATOR_VERSION = 19;
const PORTRAIT_SPEC_VERSION = "story_linked_canvas_portrait.v1";
const DRAG_PANEL_STORAGE_KEY = "trpg.dragPanels.layout2.v18";
const PREVIOUS_DRAG_PANEL_STORAGE_KEYS = ["trpg.dragPanels.layout2.v17"];
const LEGACY_DRAG_PANEL_STORAGE_KEY = "trpg.dragPanels";
const FALLBACK_ASSET_CONTRACT = {
  core_gallery_categories: [
    { id: "prop", label: "道具", source: "core" },
    { id: "item", label: "物品", source: "core" },
    { id: "character", label: "角色", source: "core" },
    { id: "map", label: "地图", source: "core" },
    { id: "cg", label: "CG", source: "core" },
  ],
  custom_gallery_categories: [],
  max_custom_gallery_categories: 3,
};

function init() {
  drawBackground();
  bindControls();
  initDraggablePanels();
  hidePlayerHiddenAdminPanels();
  applyCollapseState();
  resetCampaignScopedUiState("");
  loadCanvasRules();
  loadAssetContract();
  refresh();
  state.job.polling = setInterval(refresh, 2500);
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
  document.getElementById("characterProfileToggle")?.addEventListener("click", () => {
    state.character.characterProfileExpanded = !state.character.characterProfileExpanded;
    renderCharacterProfile(state.character.lastCharacterCardForRender?.profile || {});
  });
  $("closeCompanionOverlay")?.addEventListener("click", closeCompanionOverlay);
  $("companionOverlay")?.addEventListener("click", (event) => {
    if (event.target.id === "companionOverlay") closeCompanionOverlay();
  });
  $("closeStoryProgressOverlay")?.addEventListener("click", closeStoryProgressOverlay);
  $("storyProgressOverlay")?.addEventListener("click", (event) => {
    if (event.target.id === "storyProgressOverlay") closeStoryProgressOverlay();
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
    if (event.key === "Escape") closeStoryProgressOverlay();
  });

  document.querySelectorAll("[data-command]").forEach((button) => {
    button.addEventListener("click", () => runCommand(button.dataset.command));
  });
  document.querySelectorAll("[data-panel-tab]").forEach((button) => {
    button.addEventListener("click", () => showPanel(button.dataset.panelTab));
  });
  document.querySelectorAll("[data-side-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      state.ui.sideTab = button.dataset.sideTab;
      document.querySelectorAll("[data-side-tab]").forEach((x) => x.classList.toggle("active", x === button));
      renderSidePanel(state.campaign.lastCampaignState);
    });
  });
  document.querySelectorAll("[data-collapse-panel]").forEach((button) => {
    button.addEventListener("click", () => toggleCollapsePanel(button.dataset.collapsePanel));
  });
  $("autoScrollBtn").addEventListener("click", () => {
    state.ui.autoScroll = !state.ui.autoScroll;
    $("autoScrollBtn").classList.toggle("active", state.ui.autoScroll);
  });
  $("storyProgressTopBtn")?.addEventListener("click", openStoryProgressOverlay);
  document.addEventListener("click", (event) => {
    if (!event.target.closest?.("#storyProgressTop")) closeStoryProgressMenu();
  });
  document.querySelectorAll("#galleryFilters button").forEach((button) => {
    button.addEventListener("click", () => setGalleryFilter(button.dataset.filter));
  });
  bindActionInputDrop();
}

function toggleCollapsePanel(name) {
  if (!Object.prototype.hasOwnProperty.call(state.ui.collapsedPanels, name)) return;
  state.ui.collapsedPanels[name] = !state.ui.collapsedPanels[name];
  applyCollapseState();
}

function applyCollapseState() {
  const leftColumn = document.querySelector(".leftColumn");
  Object.entries(state.ui.collapsedPanels).forEach(([name, collapsed]) => {
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

function initDraggablePanels() {
  state.ui.dragPanels = loadDragPanelState();
  [
    { id: "task", selector: ".taskPanel", handle: ".panelTitle", label: "任务物品卡" },
    { id: "memory", selector: ".memoryPanel", handle: ".panelTitle", label: "近期记忆卡" },
    { id: "gallery", selector: ".galleryPanel", handle: ".panelTitle", label: "资产夹资料卡" },
  ].forEach((config) => setupDraggablePanel(config));
  window.addEventListener("resize", clampFloatingPanels);
}

function setupDraggablePanel({ id, selector, handle, label }) {
  const panel = document.querySelector(selector);
  const dragHandle = panel?.querySelector(handle);
  if (!panel || !dragHandle) return;
  panel.dataset.dragPanel = id;
  panel.classList.add("draggablePanel");
  dragHandle.classList.add("dragHandle");
  dragHandle.title = `${label}：拖动标题可移动，双击恢复位置`;
  dragHandle.addEventListener("pointerdown", (event) => beginPanelDrag(event, id, panel));
  dragHandle.addEventListener("dblclick", () => resetDragPanel(id, panel));
  applyDragPanelState(id, panel);
}

function beginPanelDrag(event, id, panel) {
  if (event.button !== 0) return;
  if (event.target.closest("button, input, textarea, select, a")) return;
  if (window.matchMedia("(max-width: 900px)").matches) return;
  const rect = panel.getBoundingClientRect();
  const bounds = floatingPanelBounds();
  const width = Math.min(Math.max(260, rect.width), bounds.width);
  const height = Math.min(Math.max(160, rect.height), Math.max(180, bounds.height * 0.9));
  state.ui.activeDragPanel = {
    id,
    panel,
    offsetX: event.clientX - rect.left,
    offsetY: event.clientY - rect.top,
    width,
    height,
  };
  panel.classList.add("is-dragging");
  panel.style.width = `${width}px`;
  panel.style.height = `${height}px`;
  panel.setPointerCapture?.(event.pointerId);
  document.addEventListener("pointermove", movePanelDrag);
  document.addEventListener("pointerup", endPanelDrag, { once: true });
  event.preventDefault();
}

function movePanelDrag(event) {
  const drag = state.ui.activeDragPanel;
  if (!drag) return;
  const bounds = floatingPanelBounds();
  const maxLeft = Math.max(bounds.left, bounds.right - drag.width);
  const maxTop = Math.max(bounds.top, bounds.bottom - drag.height);
  const left = Math.max(bounds.left, Math.min(maxLeft, event.clientX - drag.offsetX));
  const top = Math.max(bounds.top, Math.min(maxTop, event.clientY - drag.offsetY));
  drag.panel.classList.add("floatingPanel");
  drag.panel.style.left = `${left}px`;
  drag.panel.style.top = `${top}px`;
  drag.panel.style.zIndex = String(nextFloatingZIndex());
}

function endPanelDrag() {
  const drag = state.ui.activeDragPanel;
  if (!drag) return;
  drag.panel.classList.remove("is-dragging");
  const rect = drag.panel.getBoundingClientRect();
  state.ui.dragPanels[drag.id] = {
    left: Math.round(rect.left),
    top: Math.round(rect.top),
    width: Math.round(rect.width),
    height: Math.round(rect.height),
  };
  saveDragPanelState();
  document.removeEventListener("pointermove", movePanelDrag);
  state.ui.activeDragPanel = null;
}

function applyDragPanelState(id, panel) {
  const saved = state.ui.dragPanels[id];
  if (!saved || window.matchMedia("(max-width: 900px)").matches) return;
  const bounds = floatingPanelBounds();
  const width = Math.min(Math.max(260, Number(saved.width) || panel.offsetWidth), bounds.width);
  const height = Math.min(Math.max(160, Number(saved.height) || panel.offsetHeight), bounds.height);
  panel.classList.add("floatingPanel");
  panel.style.left = `${Math.max(bounds.left, Math.min(bounds.right - width, Number(saved.left) || bounds.left))}px`;
  panel.style.top = `${Math.max(bounds.top, Math.min(bounds.bottom - height, Number(saved.top) || bounds.top))}px`;
  panel.style.width = `${width}px`;
  panel.style.height = `${height}px`;
  panel.style.zIndex = String(nextFloatingZIndex());
}

function resetDragPanel(id, panel) {
  delete state.ui.dragPanels[id];
  panel.classList.remove("floatingPanel", "is-dragging");
  ["left", "top", "width", "height", "zIndex"].forEach((prop) => {
    panel.style[prop] = "";
  });
  saveDragPanelState();
}

function clampFloatingPanels() {
  const bounds = floatingPanelBounds();
  document.querySelectorAll(".floatingPanel").forEach((panel) => {
    const rect = panel.getBoundingClientRect();
    const width = Math.min(rect.width, bounds.width);
    const height = Math.min(rect.height, bounds.height);
    const left = Math.max(bounds.left, Math.min(bounds.right - width, rect.left));
    const top = Math.max(bounds.top, Math.min(bounds.bottom - height, rect.top));
    panel.style.width = `${width}px`;
    panel.style.height = `${height}px`;
    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;
  });
}

function floatingPanelBounds() {
  const shell = document.querySelector(".appShell")?.getBoundingClientRect();
  if (shell && shell.width > 0 && shell.height > 0) {
    return {
      left: Math.round(shell.left),
      top: Math.round(shell.top),
      right: Math.round(shell.right),
      bottom: Math.round(shell.bottom),
      width: Math.round(shell.width),
      height: Math.round(shell.height),
    };
  }
  const margin = 8;
  return {
    left: margin,
    top: margin,
    right: window.innerWidth - margin,
    bottom: window.innerHeight - margin,
    width: window.innerWidth - margin * 2,
    height: window.innerHeight - margin * 2,
  };
}

function nextFloatingZIndex() {
  const current = Number(document.documentElement.dataset.floatZ || 40) + 1;
  document.documentElement.dataset.floatZ = String(current);
  return current;
}

function loadDragPanelState() {
  try {
    localStorage.removeItem(LEGACY_DRAG_PANEL_STORAGE_KEY);
    PREVIOUS_DRAG_PANEL_STORAGE_KEYS.forEach((key) => localStorage.removeItem(key));
    return JSON.parse(localStorage.getItem(DRAG_PANEL_STORAGE_KEY) || "{}") || {};
  } catch (err) {
    return {};
  }
}

function saveDragPanelState() {
  localStorage.setItem(DRAG_PANEL_STORAGE_KEY, JSON.stringify(state.ui.dragPanels || {}));
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

async function loadModulePayload(ref, moduleName = "") {
  return loadModulePayloadWithOptions(ref, moduleName);
}

async function loadModulePayloadWithOptions(ref, moduleName = "", options = {}) {
  if (!ref || ref.startsWith("asset://")) return null;
  const key = `${state.campaign.activeCampaign}:${moduleName}:${ref}`;
  if (!options.force && state.assets.modulePayloadCache[key]) return state.assets.modulePayloadCache[key];
  const data = await api(ref);
  if (data.campaign_id && state.campaign.activeCampaign && data.campaign_id !== state.campaign.activeCampaign) return null;
  state.assets.modulePayloadCache[key] = data;
  return data;
}

async function runTurn() {
  const action = $("actionInput").value.trim();
  if (!action) {
    showPanel("logs");
    return setLog("玩家行动不能为空。");
  }
  await submitActionEvent(action, "input");
}

async function submitActionEvent(action, source = "action") {
  const value = String(action || "").trim();
  if (!value) {
    showPanel("logs");
    return setLog("玩家行动不能为空。");
  }
  await startJob(
    "/api/run-turn",
    { action: value, campaign_id: state.campaign.activeCampaign, source },
    { storyProgress: true, clearInputOnSuccess: true, actionEvent: true },
  );
}

async function prepareOnly() {
  const action = $("actionInput").value.trim();
  if (!action) {
    showPanel("logs");
    return setLog("玩家行动不能为空。");
  }
  await startJob("/api/prepare", { action, campaign_id: state.campaign.activeCampaign });
}

async function runCommand(name) {
  await startJob("/api/command", { name, campaign_id: state.campaign.activeCampaign });
}

function exportCampaign() {
  const params = state.campaign.activeCampaign ? `?campaign_id=${encodeURIComponent(state.campaign.activeCampaign)}` : "";
  window.open(`/api/export-campaign${params}`, "_blank");
}

async function startJob(path, payload, options = {}) {
  try {
    setBusy(true);
    if (options.storyProgress) {
      showPanel("story");
      if (options.actionEvent) invalidateModulePayloadCache("story_log");
      beginRunProgress();
      scrollStoryToBottom(true);
      setLog("命令已提交，后台开始执行。");
    } else {
      showPanel("logs");
      setLog("命令已提交，后台开始执行。");
    }
    const data = await api(path, { method: "POST", body: JSON.stringify(payload) });
    if (options.storyProgress && data?.job?.stream_enabled && data?.job?.job_id) {
      startRunStreamPolling(data.job.job_id);
    }
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
    const previousCampaign = activeCampaignId();
    const nextCampaign = data.active_campaign || "";
    state.campaign.frontendState = data.frontend_state || {};
    state.campaign.streamingPreview = Boolean(data.streaming_preview);
    state.campaign.activeCampaign = nextCampaign;
    state.campaign.assetSeed = state.campaign.frontendState.asset_seed || state.campaign.frontendState.campaign?.asset_seed || nextCampaign || "";
    if (previousCampaign !== nextCampaign) {
      resetCampaignScopedUiState(nextCampaign);
      await loadAssetContract(nextCampaign);
    }
    state.story.currentPressurePack = data.output?.pressure_pack || {};
    if (Array.isArray(data.assets)) {
      state.assets.cachedAssets = data.assets.filter(isAssetForCurrentCampaign);
    }
    if (previousCampaign !== nextCampaign) await loadCachedAssets();
    await loadRawGallery(nextCampaign);
    await loadRawInventory(nextCampaign);
    renderStatus(data);
    updateRunProgressFromPipeline(data.pipeline || {}, data.job || {}, data.output || {});
    renderFrontendState(state.campaign.frontendState, data.campaign_state || {});
    renderOutput(data.output || {});
  } catch (err) {
    setBusy(false, true);
    showPanel("logs");
    setLog(err.message);
  }
}

function renderStatus(data) {
  state.campaign.campaigns = data.campaign_list || [];
  state.campaign.activeCampaign = data.active_campaign || "";
  state.campaign.selectedCampaign = state.campaign.selectedCampaign || activeCampaignId();
  setText("campaignName", campaignTitle(activeCampaignId()) || "-");

  const scene = data.campaign_state?.recent?.current_scene || {};
  const chapterName = currentCampaignMeta()?.chapter || "";
  const chapterBtn = $("chapterBtn");
  if (chapterBtn) {
    const hasChapter = Boolean(chapterName && chapterName !== "current");
    chapterBtn.classList.toggle("hidden", !hasChapter);
    if (hasChapter) setText("chapterName", chapterName);
  }
  setText("mapLabel", scene.location || "当前路线");

  const job = data.job || {};
  const failed = job.returncode !== null && job.returncode !== 0;
  setBusy(Boolean(job.running), failed);
  setText("jobText", job.running ? "运行中" : failed ? "已停止" : "待机");

  const cmd = job.command && job.command.length ? `\n\n$ ${job.command.join(" ")}` : "";
  const output = [job.output, job.error, cmd].filter(Boolean).join("\n");
  if (output) setLog(output);

  if (state.job.lastJobRunning && !job.running && !failed) showPanel("story");
  state.job.lastJobRunning = Boolean(job.running);
}

async function loadCanvasRules() {
  try {
    const data = await api("/api/canvas-rules");
    state.assets.canvasRules = data.rules || "";
  } catch (err) {
    console.warn("canvas rules unavailable", err);
    state.assets.canvasRules = "";
  }
}

function normalizeAssetContract(raw = {}) {
  const source = raw && typeof raw === "object" ? raw : {};
  const fallback = FALLBACK_ASSET_CONTRACT;
  const maxCustom = Number(source.max_custom_gallery_categories || fallback.max_custom_gallery_categories) || 3;
  return {
    ...source,
    core_gallery_categories: normalizeAssetContractRows(source.core_gallery_categories, "core", fallback.core_gallery_categories),
    custom_gallery_categories: normalizeAssetContractRows(source.custom_gallery_categories, "campaign", []).slice(0, maxCustom),
    max_custom_gallery_categories: maxCustom,
  };
}

function normalizeAssetContractRows(rows, source, fallback = []) {
  const input = Array.isArray(rows) && rows.length ? rows : fallback;
  const seen = new Set();
  return input.map((row) => {
    const id = String(row?.id || row?.key || "").trim().toLowerCase();
    const label = String(row?.label || row?.title || id).trim();
    if (!id || id === "scene" || id === "all" || id === "hidden" || seen.has(id)) return null;
    seen.add(id);
    return { id, label: label || id, source: row?.source || source };
  }).filter(Boolean);
}

async function loadAssetContract(campaignId = state.campaign.activeCampaign) {
  if (!campaignId) {
    state.assets.assetContract = normalizeAssetContract(FALLBACK_ASSET_CONTRACT);
    renderGalleryFilters();
    return state.assets.assetContract;
  }
  try {
    const data = await api(`/api/asset-contract?campaign_id=${encodeURIComponent(campaignId)}`);
    if (campaignId && campaignId !== state.campaign.activeCampaign) return state.assets.assetContract || normalizeAssetContract(FALLBACK_ASSET_CONTRACT);
    state.assets.assetContract = normalizeAssetContract(data);
  } catch (err) {
    console.warn("asset contract unavailable", err);
    state.assets.assetContract = normalizeAssetContract(FALLBACK_ASSET_CONTRACT);
  }
  renderGalleryFilters();
  return state.assets.assetContract;
}

async function loadCachedAssets() {
  if (!state.campaign.activeCampaign) {
    state.assets.cachedAssets = [];
    return;
  }
  try {
    const data = await api(`/api/assets?campaign_id=${encodeURIComponent(state.campaign.activeCampaign)}`);
    state.assets.cachedAssets = (Array.isArray(data.assets) ? data.assets : []).filter(isAssetForCurrentCampaign);
  } catch (err) {
    console.warn("asset list unavailable", err);
    state.assets.cachedAssets = [];
  }
}

async function loadRawGallery(campaignId = state.campaign.activeCampaign) {
  if (!campaignId) {
    state.gallery.rawGallery = {};
    state.gallery.rawAssets = [];
    renderGalleryFilters();
    return [];
  }
  try {
    const data = await api(`/api/extensions/gallery?campaign_id=${encodeURIComponent(campaignId)}`);
    if (campaignId && campaignId !== state.campaign.activeCampaign) return state.gallery.rawAssets || [];
    const raw = data.raw && typeof data.raw === "object" ? data.raw : {};
    state.gallery.rawGallery = raw;
    state.gallery.rawAssets = Array.isArray(raw.assets) ? raw.assets : [];
  } catch (err) {
    console.warn("raw gallery unavailable", err);
    state.gallery.rawGallery = {};
    state.gallery.rawAssets = [];
  }
  renderGalleryFilters();
  return state.gallery.rawAssets;
}

async function loadRawInventory(campaignId = state.campaign.activeCampaign) {
  if (!campaignId) {
    state.character.rawInventoryState = {};
    state.character.rawInventoryItems = [];
    state.character.inventoryEvents = [];
    return [];
  }
  try {
    const data = await api(`/api/extensions/inventory?campaign_id=${encodeURIComponent(campaignId)}`);
    if (campaignId && campaignId !== state.campaign.activeCampaign) return state.character.rawInventoryItems || [];
    const rawState = data.state && typeof data.state === "object" ? data.state : {};
    const rawEvents = data.events && typeof data.events === "object" ? data.events : {};
    state.character.rawInventoryState = rawState;
    state.character.rawInventoryItems = Array.isArray(rawState.items) ? rawState.items : [];
    state.character.inventoryEvents = Array.isArray(rawEvents.events) ? rawEvents.events : [];
  } catch (err) {
    console.warn("raw inventory unavailable", err);
    state.character.rawInventoryState = {};
    state.character.rawInventoryItems = [];
    state.character.inventoryEvents = [];
  }
  return state.character.rawInventoryItems;
}

function invalidateModulePayloadCache(moduleName) {
  const needle = `:${moduleName}:`;
  Object.keys(state.assets.modulePayloadCache || {}).forEach((key) => {
    if (key.includes(needle)) delete state.assets.modulePayloadCache[key];
  });
}

function resetCampaignScopedUiState(campaignId) {
  state.map.renderedMapKey = "";
  state.map.currentMapAsset = null;
  state.assets.assetCache = {};
  state.assets.cachedAssets = [];
  state.assets.assetContract = normalizeAssetContract(FALLBACK_ASSET_CONTRACT);
  state.assets.visualContracts = {};
  state.assets.modulePayloadCache = {};
  state.gallery.rawGallery = {};
  state.gallery.rawAssets = [];
  state.gallery.renderedRawAssets = [];
  state.gallery.selectedGalleryKey = "";
  state.gallery.transientGalleryAsset = null;
  state.story.currentPressurePack = {};
  state.story.storyProgressPayload = {};
  state.story.storyProgressChapter = {};
  state.story.storyProgressNode = {};
  state.character.rawInventoryState = {};
  state.character.rawInventoryItems = [];
  state.character.inventoryEvents = [];
  state.character.latestDossierPayload = null;
  clearImageElement("avatarImage");
  clearImageElement("companionImage");
  clearImageElement("mapImage");
  clearImageElement("galleryInspectorImage");
  clearImageElement("companionDialogImage");
  showAvatarPlaceholder("avatarImage");
  showAvatarPlaceholder("companionImage");
  clearMapPlaceholder();
  clearGalleryDomIfNeeded();
  resetStoryProgressDropdown();
  document.querySelector(".characterPanel")?.classList.remove("has-companion");
  document.querySelector(".characterPanel")?.classList.add("no-companion");
  document.querySelector(".companionCard")?.setAttribute("hidden", "");
}

function clearImageElement(id) {
  const img = $(id);
  if (!img) return;
  img.removeAttribute("src");
  img.dataset.assetKey = "";
  img.dataset.campaignId = "";
  img.classList.add("is-empty");
}

function clearGalleryDomIfNeeded() {
  const grid = $("galleryGrid");
  if (grid) grid.innerHTML = "";
  renderGalleryInspector(null);
}

function resetStoryProgressDropdown() {
  setText("storyProgressTopTitle", "未启用结构化进度");
  setText("storyProgressTopPace", "normal");
  setText("storyProgressMenuTitle", "未启用结构化进度");
  setText("storyProgressOverallText", "0%");
  setText("storyProgressChapterName", "-");
  setText("storyProgressChapterPercent", "0%");
  setText("storyProgressNodeName", "-");
  setText("storyProgressNodePercent", "0%");
  setText("storyProgressPace", "normal");
  setText("storyProgressPaceBadge", "稳定");
  setText("storyProgressStatusText", "未启用结构化故事进度");
  setText("storyPace", "normal");
  setText("storyOverallProgress", "0%");
  setText("storyChapterName", "-");
  setText("storyChapterProgress", "0%");
  setText("storyNodeName", "-");
  setText("storyNodeProgress", "0%");
  setText("storyProgressStatus", "未启用结构化故事进度");
  const bar = $("storyProgressOverallBar");
  if (bar) bar.style.width = "0%";
  const legacyBar = $("storyOverallBar");
  if (legacyBar) legacyBar.style.width = "0%";
  const details = $("storyProgressDetails");
  if (details) details.innerHTML = "";
  state.story.storyProgressPayload = {};
  state.story.storyProgressChapter = {};
  state.story.storyProgressNode = {};
  setText("storyProgressDialogOverall", "0%");
  setText("storyProgressDialogChapter", "-");
  setText("storyProgressDialogNode", "-");
  setText("storyProgressDialogPace", "normal");
  const dialogBar = $("storyProgressDialogBar");
  if (dialogBar) dialogBar.style.width = "0%";
  const dialogDetails = $("storyProgressDialogDetails");
  if (dialogDetails) dialogDetails.innerHTML = "";
  closeStoryProgressOverlay();
  closeStoryProgressMenu();
}

function toggleStoryProgressMenu(event) {
  event?.stopPropagation?.();
  const menu = $("storyProgressMenu");
  const button = $("storyProgressTopBtn");
  if (!menu) return;
  const open = menu.classList.toggle("hidden") === false;
  if (button) button.setAttribute("aria-expanded", String(open));
}

function closeStoryProgressMenu() {
  const menu = $("storyProgressMenu");
  const button = $("storyProgressTopBtn");
  if (menu) menu.classList.add("hidden");
  if (button) button.setAttribute("aria-expanded", "false");
}

function openStoryProgressOverlay(event) {
  event?.stopPropagation?.();
  closeStoryProgressMenu();
  renderStoryProgressOverlayContent();
  const overlay = $("storyProgressOverlay");
  const button = $("storyProgressTopBtn");
  if (!overlay) return;
  overlay.classList.remove("hidden");
  overlay.setAttribute("aria-hidden", "false");
  if (button) button.setAttribute("aria-expanded", "true");
}

function closeStoryProgressOverlay() {
  const overlay = $("storyProgressOverlay");
  const button = $("storyProgressTopBtn");
  if (overlay) {
    overlay.classList.add("hidden");
    overlay.setAttribute("aria-hidden", "true");
  }
  if (button) button.setAttribute("aria-expanded", "false");
}

function isAssetForCurrentCampaign(asset) {
  if (!asset) return false;
  const cid = asset.campaign_id || asset.campaignId || "";
  const seed = asset.asset_seed || asset.assetSeed || "";
  if (!cid || cid !== state.campaign.activeCampaign) return false;
  if (seed && state.campaign.assetSeed && seed !== state.campaign.assetSeed) return false;
  if (asset.placeholder || asset.is_placeholder) return false;
  return true;
}

function findCurrentCampaignAsset(predicate) {
  return (state.assets.cachedAssets || []).find((asset) => isAssetForCurrentCampaign(asset) && predicate(asset));
}

function visualContractFor(entityKey = "", entityType = "", displayName = "") {
  const rows = state.assets.visualContracts || {};
  if (entityKey && rows[entityKey]) return rows[entityKey];
  const normalizedType = slugify(entityType || "");
  const normalizedDisplay = slugify(displayName || "");
  const candidateKey = normalizedType && normalizedDisplay ? `${normalizedType}:${normalizedDisplay}` : "";
  if (candidateKey && rows[candidateKey]) return rows[candidateKey];
  return Object.values(rows).find((row) => {
    if (!row || typeof row !== "object") return false;
    if (entityType && row.entity_type !== entityType) return false;
    return normalizedDisplay && slugify(row.display_name || "") === normalizedDisplay;
  }) || {};
}

function hasVisualContract(contract = {}) {
  return Boolean(contract && typeof contract === "object" && Object.keys(contract).length);
}

function visualPromptFromContract(contract = {}) {
  if (!contract || typeof contract !== "object") return {};
  const identity = contract.visual_identity || {};
  const physical = identity.physical || {};
  const actor = identity.actor || {};
  const render = contract.render_intent || {};
  return {
    archetype: physical.item_type || render.primary || contract.entity_type || "",
    source_text: [
      contract.display_name,
      physical.description,
      actor.role,
      actor.relationship,
      identity.summary,
    ].filter(Boolean).join(" / "),
    canvas_style: physical.canvas_rule || {},
    style_constraints: contract.style_constraints || {},
    negative_constraints: contract.negative_constraints || [],
  };
}

function makeScopedAssetKey(kind, objectId, variant = "default") {
  const campaignId = state.campaign.activeCampaign || "unknown_campaign";
  const seed = state.campaign.assetSeed || campaignId;
  const object = slugify(objectId || "unknown");
  return `${campaignId}:${seed}:${kind}:${object}:${variant}:v${ASSET_GENERATOR_VERSION}`;
}

function isValidMapRoute(route) {
  return Boolean(route && typeof route === "object" && Array.isArray(route.nodes) && route.nodes.length > 0);
}

function isAttributeStarAsset(asset = {}) {
  const metadata = asset.metadata || {};
  const text = [
    asset.key,
    asset.path,
    asset.filename,
    asset.kind,
    asset.title,
    asset.display_name,
    metadata.kind,
    metadata.source,
    metadata.object_id,
    metadata.title,
    metadata.display_name,
  ].join(" ").toLowerCase();
  return text.includes("attribute_star") || text.includes("属性星图") || text.includes("六芒星");
}

function isValidCachedMapAsset(asset = {}) {
  if (!asset.url || asset.exists === false) return false;
  if (asset.placeholder || asset.is_placeholder) return false;
  if (String(asset.display_zone || "").toLowerCase() === "hidden") return false;
  const category = String(asset.gallery_category || "").toLowerCase();
  const use = String(asset.asset_use || "").toLowerCase();
  const zone = String(asset.display_zone || "").toLowerCase();
  return category === "map" || use === "map" || zone === "map";
}

function isRawMapAsset(asset = {}) {
  const type = String(asset?.type || "").trim().toLowerCase();
  const zone = String(asset?.display_zone || "").trim().toLowerCase();
  return zone === "map" || type === "map";
}

function rawGalleryAssetMediaUrl(asset = {}) {
  const media = asset.media && typeof asset.media === "object" ? asset.media : {};
  const payload = asset.payload && typeof asset.payload === "object" ? asset.payload : {};
  const payloadMedia = payload.media && typeof payload.media === "object" ? payload.media : {};
  return asset.url || asset.image || asset.image_url || media.url || media.image || payload.url || payload.image || payload.image_url || payloadMedia.url || payloadMedia.image || "";
}

function bestRawMapAsset() {
  return (state.gallery.rawAssets || []).find((asset) => isRawMapAsset(asset)) || null;
}

function mapAssetPriority(asset = {}) {
  if (!isValidCachedMapAsset(asset)) return -1;
  const zone = String(asset.display_zone || "").toLowerCase();
  const category = String(asset.gallery_category || "").toLowerCase();
  const use = String(asset.asset_use || "").toLowerCase();
  if (zone === "map") return 30;
  if (category === "map") return 20;
  if (use === "map") return 10;
  return 0;
}

function bestCurrentMapAsset() {
  const rawMap = bestRawMapAsset();
  if (rawMap) return protocolRawGalleryAsset(rawMap);
  return null;
}

function renderCachedMap(scene, mapPanel = {}) {
  const modulePayload = mapPanel.payload || mapPanel.latest_map || {};
  const mode = mapPanel.mode || (mapPanel.keep_previous ? "keep_previous" : "none");
  const updateRequested = mapPanel.update_requested === true;
  const seed = scene.location || state.campaign.activeCampaign || "map";
  const route = modulePayload.map_route || {};
  const mapCanvas = modulePayload.map_canvas || mapCanvasFromDrawInstructions(modulePayload.canvas_draw_instructions || {});
  const routeKey = mapCanvas.title || route.title || (route.nodes || []).map((node) => node.label || node.id).join("_");
  const visualContract = hasVisualContract(modulePayload.visual_contract) ? modulePayload.visual_contract : visualContractFor(modulePayload.visual_contract_key || "", "map", route.title || modulePayload.title || scene.location || "");
  setText("mapLabel", route.title || modulePayload.title || scene.location || "当前路线");
  if (mode === "no_update" || mode === "none") return;
  if (!updateRequested || mode === "keep_previous") {
    const cached = bestCurrentMapAsset();
    const url = modulePayload.url && isUrlForCurrentCampaign(modulePayload.url, modulePayload.asset_key)
      ? modulePayload.url
      : cached?.cachedUrl || "";
    if (!url) {
      state.map.currentMapAsset = null;
      showMapEmptyState();
      return;
    }
    state.map.currentMapAsset = galleryMapAssetFromEntry(cached, modulePayload, scene, route, mapCanvas);
    showMapImage(url, modulePayload.asset_key || cached?.key || "");
    return;
  }
  if (!isValidMapRoute(route)) {
    console.warn("skip map redraw: empty route payload", mapPanel);
    showMapEmptyState();
    return;
  }
  const objectId = slugify(`${scene.location || "current_map"}:${routeKey || "base"}`);
  const mapKey = makeScopedAssetKey("map", objectId, "route");
  const mapScene = { ...scene, map_route: route, map_canvas: mapCanvas };
  state.map.currentMapAsset = {
    kind: "map",
    key: mapKey,
    title: route.title || scene.location || "当前区域地图",
    meta: "当前地图",
    detail: routeKey || scene.immediate_pressure || "当前展示的区域地图。",
    seed: scopedSeed(seed),
    scene: mapScene,
    cachedUrl: modulePayload.url || "",
    status: "current",
  };
  if (state.map.renderedMapKey === mapKey) return;
  state.map.renderedMapKey = mapKey;
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
      visual_contract_key: visualContract.entity_key || modulePayload.visual_contract_key || "",
      visual_contract_hash: visualContract.visual_contract_hash || modulePayload.visual_contract_hash || "",
      visual_contract: visualContract,
    },
    force: true,
  });
}

function galleryMapAssetFromEntry(entry, modulePayload = {}, scene = {}, route = {}, mapCanvas = {}) {
  const url = modulePayload.url || entry?.cachedUrl || entry?.url || "";
  return {
    kind: "map",
    key: modulePayload.asset_key || entry?.key || "",
    title: modulePayload.title || entry?.title || scene.location || "当前区域地图",
    meta: galleryKindLabel(entry?.gallery_category || entry?.type || "map"),
    detail: entry?.detail || scene.immediate_pressure || "当前展示的区域地图。",
    seed: scopedSeed(scene.location || state.campaign.activeCampaign || "map"),
    scene: { ...scene, map_route: route, map_canvas: mapCanvas },
    cachedUrl: url,
    status: "cached",
    campaign_id: state.campaign.activeCampaign,
    asset_seed: state.campaign.assetSeed,
  };
}

function mapCanvasFromDrawInstructions(draw = {}) {
  if (!draw || typeof draw !== "object" || Array.isArray(draw)) return {};
  const nodes = Array.isArray(draw.nodes) ? draw.nodes : [];
  const routes = Array.isArray(draw.routes) ? draw.routes : [];
  const hazards = Array.isArray(draw.hazards) ? draw.hazards : [];
  const legend = Array.isArray(draw.legend) ? draw.legend : [];
  return {
    style: draw.style || "",
    background: draw.background || "",
    points: nodes,
    routes,
    hazards,
    legend,
  };
}

function renderCampaignState(campaignState) {
  state.campaign.lastCampaignState = campaignState;
  const title = campaignState.title || campaignTitle(state.campaign.activeCampaign) || "未命名跑团";
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
  const profile = normalizeCharacterProfile(provided.profile || prompt.profile || {});
  const mechanics = campaignState.mechanics || {};
  const strictReady = hasStrictVitals(provided.vitals) || hasStrictAttributes(provided.attributes);
  const requestedMode = provided.mode || (strictReady ? "strict_stats" : "narrative_status");
  const mode = requestedMode === "auto" ? (strictReady ? "strict_stats" : "narrative_status") : requestedMode;
  const name = identity.name || extractPlayerName(player, prompt) || "未命名角色";
  const roleParts = [
    identity.ancestry,
    identity.class_or_role || identity.role,
    identity.level_or_stage,
  ].filter(Boolean);
  const fallback = characterFallback(campaignState, name, scene);
  const fallbackRole = identity.summary || fallback.meta || campaignState.genre || "身份待确认";
  const progression = normalizeProgression(provided.progression, mode, fallback);
  const companionSource = provided.companion || prompt.companion_card || identity.companion || null;
  const vitalsSource = hasStrictVitals(provided.vitals)
    ? provided.vitals
    : deriveVitalsFromThreeAttributes(provided.attributes);
  return {
    enabled: provided.enabled !== false,
    mode,
    name,
    meta: roleParts.length ? roleParts.join(" / ") : fallbackRole,
    profile,
    visual_profile: provided.visual_profile || state.campaign.frontendState?.character_card?.visual_profile || buildPlayerVisualProfile({ name, meta: roleParts.join(" / "), profile }, campaignState),
    progression,
    vitals: normalizeVitals(vitalsSource, mode, fallback),
    conditions: normalizeConditions(provided.conditions || provided.tags || provided.badges, campaignState, scene),
    attributes: normalizeCharacterAttributes(provided.attributes || fallback.attributes),
    companion: normalizeCompanion(companionSource),
  };
}

function normalizeCharacterProfile(raw = {}) {
  const source = raw && typeof raw === "object" ? raw : {};
  return {
    background: String(source.background || "").trim() || "背景待确认",
    motivation: String(source.motivation || "").trim(),
    personality: String(source.personality || "").trim(),
    notes: Array.isArray(source.notes) ? source.notes : [],
  };
}

function normalizeCharacterAttributes(raw) {
  const empty = { enabled: false, visible: false, cap: 20, float_ratio: 1.2, float_cap: 24, three: null, six: null, legacy: [] };
  if (!raw) return empty;
  if (Array.isArray(raw)) {
    return { ...empty, enabled: true, visible: true, legacy: normalizeAttributes(raw, "strict_stats", {}) };
  }
  if (typeof raw !== "object") return empty;
  const cap = Number(raw.cap) > 0 ? Number(raw.cap) : 20;
  const floatRatio = Number(raw.float_ratio) >= 1 ? Number(raw.float_ratio) : 1.2;
  const normalizeGroup = (group, fallbackTemplate = "") => {
    if (!group || typeof group !== "object") return null;
    const items = Array.isArray(group.items) ? group.items : [];
    return {
      template: group.template || fallbackTemplate,
      source: group.source || "",
      items: items.map((item, index) => ({
        key: String(item.key || `attr_${index}`),
        label: String(item.label || item.key || `属性${index + 1}`),
        value: item.value === null || item.value === "" || item.value === undefined ? null : Number(item.value),
      })),
    };
  };
  const legacyItems = Array.isArray(raw.items) ? normalizeAttributes(raw.items, "strict_stats", {}) : [];
  return {
    enabled: raw.enabled !== false,
    visible: raw.visible !== false,
    cap,
    float_ratio: floatRatio,
    float_cap: Number(raw.float_cap) > 0 ? Number(raw.float_cap) : Math.ceil(cap * floatRatio),
    three: normalizeGroup(raw.three, "three"),
    six: normalizeGroup(raw.six, "six"),
    legacy: legacyItems,
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
  state.campaign.lastCampaignState = campaignState;
  state.assets.visualContracts = fs.visual_contracts?.contracts || {};
  state.assets.assetContract = normalizeAssetContract(fs.asset_contract || state.assets.assetContract || FALLBACK_ASSET_CONTRACT);
  renderCharacterCard(protocolCharacterCard(fs.character_card, campaignState));
  renderCompanionCard(protocolCompanionCard(fs.companion_card, campaignState));
  renderRollActions(fs.roll_actions || []);
  renderStoryProgressDropdown(fs);
  ["story_progress", "map_panel", "gallery", "inventory", "dossier", "character_card", "canvas_jobs"].forEach((name) => {
    renderModule(name, modules[name], fs, campaignState);
  });
  renderSidePanel(campaignState, fs);
  renderMemoryPanel(campaignState);
  renderGalleryFilters();
  if (!modules.gallery || modules.gallery.mode !== "no_update") {
    renderGallery(campaignState, fs.gallery || {}, modules.gallery);
  }
  hydrateLazyFrontendModules(modules, fs, campaignState);
  renderQuickActions(fs.quick_actions || []);
}

function hydrateLazyFrontendModules(modules = {}, frontendState = {}, campaignState = {}) {
  Object.entries(modules || {}).forEach(([name, moduleState]) => {
    if (!moduleState?.payload_ref) return;
    const shouldLoad = name !== "gallery" && (
      moduleState.update_requested === true
      || (name === "story_log" && ["story", "summary", "logs"].includes(state.ui.activePanel))
    );
    if (!shouldLoad) return;
    loadModulePayload(moduleState.payload_ref, name)
      .then((data) => {
        if (!data?.payload || (data.campaign_id && data.campaign_id !== state.campaign.activeCampaign)) return;
        if (name === "story_log") {
          renderOutput({
            campaign_id: data.campaign_id,
            source: data.payload.source || "module:story-log",
            parsed: data.payload,
            pressure_pack: state.story.currentPressurePack || {},
          });
        } else if (name === "map_panel") {
          updateMapModule(data.payload || {}, campaignState);
        } else if (name === "dossier") {
          state.character.latestDossierPayload = data.payload || [];
        }
      })
      .catch((err) => console.warn(`module payload unavailable: ${name}`, err));
  });
}

async function refreshStoryLogNow() {
  if (!state.campaign.activeCampaign) return;
  invalidateModulePayloadCache("story_log");
  const moduleState = state.campaign.frontendState?.modules?.story_log || {};
  const ref = moduleState.payload_ref || `/api/module/story-log?campaign_id=${encodeURIComponent(state.campaign.activeCampaign)}&limit=40`;
  const data = await loadModulePayloadWithOptions(ref, "story_log", { force: true });
  if (!data?.payload || (data.campaign_id && data.campaign_id !== state.campaign.activeCampaign)) return;
  renderOutput({
    campaign_id: data.campaign_id || state.campaign.activeCampaign,
    source: data.payload.source || "module:story-log",
    parsed: data.payload,
    pressure_pack: state.story.currentPressurePack || {},
  });
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
  if (ref && !ref.startsWith("asset://") && isUrlForCurrentCampaign(ref, moduleState.payload?.asset_key)) {
    showMapImage(ref, moduleState.payload?.asset_key || "");
    return;
  }
  const rawMap = bestCurrentMapAsset();
  if (rawMap?.cachedUrl) {
    state.map.currentMapAsset = rawMap;
    showMapImage(rawMap.cachedUrl, rawMap.key);
  } else {
    state.map.currentMapAsset = rawMap || null;
    showMapEmptyState();
  }
}

function updateMapModule(moduleState = {}, campaignState = {}) {
  if (moduleState.mode === "keep_previous") return keepPreviousModule("map_panel", moduleState);
  if (moduleState.mode !== "update" || moduleState.update_requested !== true) return;
  renderCachedMap(campaignState?.recent?.current_scene || {}, moduleState);
}

function renderMap(moduleState = {}, campaignState = currentCampaignState()) {
  return updateMapModule(moduleState, campaignState);
}

function updateGalleryModule(moduleState = {}, campaignState = {}) {
  if (moduleState.payload_ref && moduleState.update_requested === true) return;
  if (moduleState.mode !== "update" || moduleState.update_requested !== true) return;
  renderGallery(campaignState, { module_payload: moduleState.payload || {} }, moduleState);
}

function renderStory(output = {}) {
  const parsed = output.parsed || {};
  return renderStoryBlocks(parsed.blocks || [], parsed.body || output.public_text || "");
}

function renderCharacterPanel(card = {}) {
  return renderCharacterCard(card);
}

function renderJobStatus(pipeline = {}, job = {}, output = {}) {
  return updateRunProgressFromPipeline(pipeline, job, output);
}

function renderLayout() {
  applyCollapseState();
  clampFloatingPanels();
}

function updateInventoryModule(moduleState = {}) {
  return;
}

function updateDossierModule(moduleState = {}) {
  if (moduleState.mode !== "update" || moduleState.update_requested !== true) return;
  state.character.latestDossierPayload = moduleState.payload || [];
}

function updateCharacterCardModule(moduleState = {}, campaignState = {}) {
  if (moduleState.mode !== "update" || moduleState.update_requested !== true || !moduleState.payload) return;
  const rules = state.campaign.frontendState?.rules_config || {};
  if (rules.character_card_enabled === false) return;
  renderCharacterCard(protocolCharacterCard({ ...moduleState.payload, stat_visibility: rules.stat_visibility || moduleState.payload.stat_visibility }, campaignState));
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
      const visualContract = hasVisualContract(job.visual_contract) ? job.visual_contract : visualContractFor(job.visual_contract_key || "", "map", job.title || mapModule.payload?.title || "");
      const payload = { ...(mapModule.payload || {}) };
      if (visualContract.entity_key) {
        payload.visual_contract = visualContract;
        payload.visual_contract_key = visualContract.entity_key;
        payload.visual_contract_hash = visualContract.visual_contract_hash || "";
      }
      const route = payload.map_route || {};
      const mapCanvasPayload = payload.map_canvas || mapCanvasFromDrawInstructions(payload.canvas_draw_instructions || {});
      const hasCanvas = hasSemanticMapCanvas(mapCanvasPayload) || hasSemanticMapCanvas(campaignState?.recent?.current_scene?.map_canvas || {});
      if (!isValidMapRoute(route) && !hasCanvas) {
        console.warn("skip map canvas job without route or MapCanvas", job);
        return;
      }
      renderCachedMap(campaignState?.recent?.current_scene || {}, { mode: "update", update_requested: true, payload });
      return;
    }
    if (["portrait", "player_portrait"].includes(job.kind)) {
      const card = frontendState.modules?.character_card?.payload || frontendState.character_card || {};
      const seed = card.name || job.asset_key || state.campaign.activeCampaign || "portrait";
      const visualContract = hasVisualContract(job.visual_contract) ? job.visual_contract : hasVisualContract(card.visual_contract) ? card.visual_contract : visualContractFor(job.visual_contract_key || "", "player", card.name || seed);
      const visualProfile = card.visual_profile || buildPlayerVisualProfile(card, campaignState || state.campaign.lastCampaignState || {});
      const visualHash = visualProfileHash(visualProfile);
      drawPixelActorPortrait(seed, {
        cache: true,
        objectId: slugify(job.asset_key || card.name || "portrait"),
        seedText: scopedSeed(`${state.campaign.activeCampaign}:${job.asset_key}:${visualHash}:${currentStoryVisualContext()}`),
        role: "player",
        kind: "player_portrait",
        visualProfile,
        metadata: {
          title: card.name || "player",
          display_name: card.name || "player",
          role: "player",
          runtime_role: "player",
          entity_key: makeEntityKey("player", card.name || "player"),
          avatar_key: makeEntityKey("player", card.name || "player"),
          portrait_asset_kind: "player_portrait",
          gallery_category: "hidden",
          visible_in_gallery: false,
          not_in_gallery_filters: true,
          display_slot: "main_character_card",
          detail_slot: "main_character_detail",
          render_tier: "player",
          source_size: 512,
          detail_level: "high",
          visual_spec: "story_linked_canvas_portrait",
          portrait_spec_version: PORTRAIT_SPEC_VERSION,
          visual_profile: visualProfile,
          visual_profile_hash: visualHash,
          visual_contract_key: visualContract.entity_key || job.visual_contract_key || "",
          visual_contract_hash: visualContract.visual_contract_hash || job.visual_contract_hash || "",
          visual_contract: visualContract,
          variant: `vp_${visualHash}`,
          background_context: currentStoryVisualContext(),
        },
      });
      return;
    }
    if (["character_portrait", "npc_portrait", "monster_portrait"].includes(job.kind)) {
      const name = job.display_name || job.title || job.asset_key || "character";
      const actorRole = job.kind === "monster_portrait" ? "monster" : "npc";
      const visualContract = hasVisualContract(job.visual_contract) ? job.visual_contract : visualContractFor(job.visual_contract_key || "", actorRole, name);
      drawPixelActorPortrait(name, {
        cache: true,
        objectId: slugify(job.asset_key || name),
        role: actorRole,
        kind: "npc_portrait",
        metadata: {
          title: name,
          display_name: name,
          role: actorRole,
          runtime_role: actorRole,
          entity_key: makeEntityKey(actorRole, name),
          portrait_asset_kind: "npc_portrait",
          gallery_category: "character",
          visible_in_gallery: true,
          source: "director_canvas_job",
          visual_contract_key: visualContract.entity_key || job.visual_contract_key || "",
          visual_contract_hash: visualContract.visual_contract_hash || job.visual_contract_hash || "",
          visual_contract: visualContract,
        },
      });
      return;
    }
    if (["item", "prop"].includes(job.kind)) {
      const visualContract = hasVisualContract(job.visual_contract) ? job.visual_contract : visualContractFor(job.visual_contract_key || "", "item", job.title || job.asset_key || "");
      const visualPrompt = job.visual_prompt || visualPromptFromContract(visualContract);
      drawPixelItemIcon(job.asset_key || job.title || job.job_id, {
        cache: true,
        objectId: slugify(job.asset_key || job.job_id),
        asset: {
          key: job.asset_key,
          title: job.title || job.asset_key,
          kind: job.kind,
          detail: job.detail || job.input_ref,
          visualPrompt: Object.keys(visualPrompt || {}).length ? visualPrompt : job.canvas_style || {},
          visual_contract: visualContract,
        },
        metadata: {
          title: job.title || job.asset_key,
          display_name: job.title || job.asset_key,
          role: job.kind,
          runtime_role: job.kind,
          entity_key: makeEntityKey(job.kind, job.title || job.asset_key),
          gallery_category: job.kind,
          source: "director_canvas_job",
          initial_asset_id: job.initial_asset_id || "",
          canvas_style: job.canvas_style || {},
          visual_prompt: Object.keys(visualPrompt || {}).length ? visualPrompt : undefined,
          visual_contract_key: visualContract.entity_key || job.visual_contract_key || "",
          visual_contract_hash: visualContract.visual_contract_hash || job.visual_contract_hash || "",
          visual_contract: visualContract,
        },
      });
      return;
    }
    if (job.kind === "cg") {
      const visualContract = hasVisualContract(job.visual_contract) ? job.visual_contract : visualContractFor(job.visual_contract_key || "", "cg", job.title || job.asset_key || "");
      const prompt = job.cg_prompt && typeof job.cg_prompt === "object" ? job.cg_prompt : {};
      const seedText = [
        state.campaign.activeCampaign,
        job.asset_key,
        job.title,
        job.detail,
        prompt.positive,
      ].filter(Boolean).join(":");
      const canvas = createAssetCanvas(192, 128);
      cacheCanvasAsset({
        canvas,
        kind: "cg_image",
        subdir: "generated",
        objectId: slugify(job.asset_key || job.job_id || job.title || "opening_cg"),
        seedText: scopedSeed(seedText || "opening_cg"),
        metadata: {
          title: job.title || "Opening CG",
          display_name: job.title || "Opening CG",
          detail: job.detail || prompt.positive || "",
          meta: "CG",
          role: "cg",
          runtime_role: "cg",
          entity_key: visualContract.entity_key || makeEntityKey("cg", job.title || job.asset_key || "opening_cg"),
          gallery_category: "cg",
          source: "director_canvas_job",
          generation_instruction: job.generation_instruction || "",
          cg_prompt: prompt,
          image_prompt: prompt,
          visual_contract_key: visualContract.entity_key || job.visual_contract_key || "",
          visual_contract_hash: visualContract.visual_contract_hash || job.visual_contract_hash || "",
          visual_contract: visualContract,
        },
        draw: () => drawPixelItemIcon(seedText || job.title || "opening_cg", {
          cache: false,
          canvas,
          targetImage: null,
          asset: {
            title: job.title || "Opening CG",
            kind: "cg",
            detail: job.detail || prompt.positive || "",
            imagePrompt: prompt,
          },
        }),
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
  if (!state.campaign.activeCampaign || !state.campaign.assetSeed) return false;
  return true;
}

function renderStoryProgressModule(moduleState = {}) {
  const payload = moduleState.payload || state.campaign.frontendState?.story_progress || {};
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

function renderStoryProgressDropdown(frontendState = {}) {
  const modules = frontendState.modules || {};
  const payload = modules.story_progress?.payload || frontendState.story_progress || {};
  if (!payload || payload.enabled === false || Object.keys(payload).length === 0) {
    resetStoryProgressDropdown();
    return;
  }
  const overall = clampPercent(payload.overall_progress);
  const chapter = payload.current_chapter || {};
  const node = payload.current_node || {};
  const chapterName = chapter.name || chapter.title || "-";
  const nodeName = node.name || node.title || "-";
  const pace = payload.pace_command || "normal";
  const status = payload.status_text || payload.progress_label || "故事进度正常。";
  state.story.storyProgressPayload = payload;
  state.story.storyProgressChapter = chapter;
  state.story.storyProgressNode = node;
  setText("storyProgressTopTitle", chapterName !== "-" ? chapterName : "结构化进度");
  setText("storyProgressTopPace", pace);
  setText("storyProgressMenuTitle", chapterName !== "-" ? chapterName : "结构化进度");
  setText("storyProgressOverallText", `${overall}%`);
  setText("storyProgressChapterName", chapterName);
  setText("storyProgressChapterPercent", `${clampPercent(payload.chapter_progress ?? chapter.progress)}%`);
  setText("storyProgressNodeName", nodeName);
  setText("storyProgressNodePercent", `${clampPercent(payload.node_progress ?? node.progress)}%`);
  setText("storyProgressPace", pace);
  setText("storyProgressPaceBadge", pace === "accelerate" ? "加速" : pace === "slow" ? "放缓" : "稳定");
  setText("storyProgressStatusText", status);
  renderStoryProgressDetails(payload, chapter, node);
  const bar = $("storyProgressOverallBar");
  if (bar) bar.style.width = `${overall}%`;
  if (!$("storyProgressOverlay")?.classList.contains("hidden")) renderStoryProgressOverlayContent();
}

function renderStoryProgressDetails(payload = {}, chapter = {}, node = {}, targetId = "storyProgressDetails") {
  const holder = $(targetId);
  if (!holder) return;
  holder.innerHTML = "";
  const rows = [];
  const chapterSummary = String(chapter.summary || chapter.description || "").trim();
  if (chapterSummary) rows.push({ label: "章节摘要", value: chapterSummary });
  const nodeGoal = String(node.goal || node.summary || node.description || "").trim();
  if (nodeGoal) rows.push({ label: "节点目标", value: nodeGoal });
  const targetChars = Number(node.target_chars || node.target_total_chars || 0);
  const charsInNode = Number(node.chars_in_node || payload.chars_in_node || 0);
  if (targetChars > 0) rows.push({ label: "目标字数", value: `${charsInNode > 0 ? `${charsInNode} / ` : ""}${targetChars}` });
  const completed = Number(payload.completed_node_count || 0);
  const total = Number(payload.total_node_count || 0);
  if (total > 0) rows.push({ label: "节点计数", value: `${completed} / ${total}` });
  rows.forEach((row) => holder.appendChild(storyProgressDetailRow(row.label, row.value)));

  const beats = Array.isArray(node.beat_checklist) ? node.beat_checklist : [];
  if (beats.length) {
    const section = document.createElement("div");
    section.className = "storyProgressDetailSection";
    const title = document.createElement("b");
    title.textContent = "检查点";
    const list = document.createElement("ul");
    beats.slice(0, 6).forEach((beat) => {
      const item = document.createElement("li");
      const status = String(beat.status || "pending");
      item.dataset.status = status;
      item.textContent = `${beat.text || beat.label || beat.id || "未命名检查点"}${status !== "pending" ? ` · ${status}` : ""}`;
      list.appendChild(item);
    });
    section.append(title, list);
    holder.appendChild(section);
  }

  const nextNodes = Array.isArray(node.next_nodes) ? node.next_nodes : [];
  const nextText = nextNodes.map((item) => item.name || item.title || item.id).filter(Boolean).join(" / ");
  if (nextText) holder.appendChild(storyProgressDetailRow("下一节点", nextText));
  holder.classList.toggle("is-empty", !holder.children.length);
}

function storyProgressDetailRow(label, value) {
  const row = document.createElement("div");
  row.className = "storyProgressDetailRow";
  const key = document.createElement("span");
  key.textContent = label;
  const text = document.createElement("p");
  text.textContent = value;
  row.append(key, text);
  return row;
}

function renderStoryProgressOverlayContent() {
  const payload = state.story.storyProgressPayload || {};
  const chapter = state.story.storyProgressChapter || payload.current_chapter || {};
  const node = state.story.storyProgressNode || payload.current_node || {};
  const overall = clampPercent(payload.overall_progress);
  const chapterName = chapter.name || chapter.title || "-";
  const nodeName = node.name || node.title || "-";
  const pace = payload.pace_command || "normal";
  setText("storyProgressDialogOverall", `${overall}%`);
  setText("storyProgressDialogChapter", chapterName);
  setText("storyProgressDialogNode", nodeName);
  setText("storyProgressDialogPace", pace);
  const bar = $("storyProgressDialogBar");
  if (bar) bar.style.width = `${overall}%`;
  renderStoryProgressDetails(payload, chapter, node, "storyProgressDialogDetails");
  const details = $("storyProgressDialogDetails");
  if (details && !details.children.length) {
    details.appendChild(storyProgressDetailRow("状态", payload.status_text || payload.progress_label || "未启用结构化故事进度"));
  }
}

function clampPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(0, Math.min(100, Math.round(number)));
}

function protocolCharacterCard(card = {}, campaignState = {}) {
  if (card?.enabled === false) {
    return {
      enabled: false,
      mode: "disabled",
      statVisibility: card.stat_visibility || "narrative",
      name: "角色卡未启用",
      meta: "本团不显示明文角色卡数值",
      progression: { label: "状态", value: "叙事记录", percent: null },
      vitals: [],
      conditions: ["角色卡未启用"],
      attributes: [],
    };
  }
  if (!card || !card.name) {
    const title = campaignState.title || campaignTitle(state.campaign.activeCampaign) || "未命名跑团";
    const scene = campaignState.recent?.current_scene || {};
    const localCard = buildCharacterCard(campaignState, title, scene);
    return {
      ...localCard,
      visual_profile: card.visual_profile || localCard.visual_profile,
      portrait: card.portrait || localCard.portrait || {},
    };
  }
  const provided = campaignState.player?.character_card || campaignState.character_prompt?.character_card || {};
  if (provided && (provided.profile || (provided.attributes && !Array.isArray(provided.attributes)))) {
    const title = campaignState.title || campaignTitle(state.campaign.activeCampaign) || "未命名跑团";
    const scene = campaignState.recent?.current_scene || {};
    return buildCharacterCard(campaignState, title, scene);
  }
  const statVisibility = card.stat_visibility || "narrative";
  return {
    enabled: true,
    mode: "narrative_status",
    statVisibility,
    name: card.name,
    meta: card.identity || "身份待确认",
    portrait: card.portrait || {},
    visual_profile: card.visual_profile || buildPlayerVisualProfile({ name: card.name, meta: card.identity, profile: card.profile || {} }, campaignState),
    progression: {
      label: card.progress?.label || "进展",
      value: card.progress?.text || "",
      percent: Number(card.progress?.percent || 0),
    },
    vitals: (card.core_stats || []).map((stat, index) => {
      const current = Number(stat.current);
      const max = Number(stat.max) || 100;
      const explicitPercent = Number(stat.percent);
      const hasNumeric = statVisibility === "numeric" && Number.isFinite(current);
      const percent = Number.isFinite(explicitPercent)
        ? explicitPercent
        : (hasNumeric ? Math.max(0, Math.min(100, (current / max) * 100)) : null);
      return {
        key: stat.key || `core_${index}`,
        label: stat.label || "状态",
        state: stat.text || (hasNumeric ? `${current} / ${max}` : "叙事状态"),
        percent,
        tone: stat.tone || ["red", "blue", "green"][index % 3],
        current: hasNumeric ? current : undefined,
        max: hasNumeric ? max : undefined,
      };
    }),
    conditions: Array.isArray(card.tags) ? card.tags : [],
    attributes: statVisibility === "narrative" ? [] : (Array.isArray(card.attributes) ? card.attributes : []),
    companion: protocolCompanionCard(state.campaign.frontendState?.companion_card, campaignState),
  };
}

function protocolCompanionCard(companion = {}, campaignState = {}) {
  if (companion?.enabled === false) return null;
  if (companion && companion.name) {
    const raw = companion.meta || companion;
    return {
      name: companion.name,
      meta: companion.identity || companion.archetype || "伙伴",
      seed: raw.visual_seed || companion.visual_seed || companion.portrait?.asset_key || companion.name,
      archetype: companion.archetype || "companion",
      portrait: companion.portrait || {},
      visual_profile: companion.visual_profile || raw.visual_profile || buildCompanionVisualProfile({ ...companion, meta: raw }, campaignState, {}, {}),
      raw,
      pending: Boolean(companion.pending),
    };
  }
  return null;
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

function renderRollActions(actions) {
  const composer = document.querySelector(".composer");
  if (!composer) return;
  let bar = composer.querySelector(".rollActionBar");
  if (!Array.isArray(actions) || !actions.length) {
    if (bar) bar.remove();
    return;
  }
  if (!bar) {
    bar = document.createElement("div");
    bar.className = "rollActionBar";
    const input = composer.querySelector(".inputWrap");
    composer.insertBefore(bar, input || composer.firstChild);
  }
  bar.innerHTML = "";
  actions.forEach((action) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `🎲 ROLL ${action.label || "检定"}`;
    button.addEventListener("click", () => insertRollAction(action));
    bar.appendChild(button);
  });
}

function insertRollAction(action = {}) {
  const input = $("actionInput");
  const label = String(action.label || "").trim();
  if (!input || !label) return;
  const mode = String(action.roll_mode || "");
  const suffix = mode === "d20_attribute" ? "属性检定" : mode === "percentile" ? "百分骰检定" : "检定";
  const text = `进行【${label}】${suffix}`;
  input.value = text;
  input.focus();
}

function applyQuickAction(action) {
  const input = $("actionInput");
  if (!input || !action) return;
  input.value = action;
  input.focus();
  submitActionEvent(action, "quick_action");
}

function characterFallback(campaignState, name, scene = {}) {
  return {
    kind: "generic",
    meta: "角色 / 状态待确认",
    progression: { label: "进展", value: "记录中", percent: 0 },
    vitals: [
      { key: "condition", label: "状态", state: "稳定", percent: 60, tone: "green" },
      { key: "focus", label: "专注", state: "待记录", percent: 50, tone: "blue" },
      { key: "resource", label: "资源", state: "待记录", percent: 50, tone: "amber" },
    ],
    attributes: [],
  };
}

function normalizeCompanion(companion) {
  if (!companion || typeof companion !== "object") return null;
  const name = String(companion.name || "").trim();
  if (!name) return null;
  const archetype = "companion";
  const rawMeta = companion.personality || companion.meta || defaultCompanionMeta(archetype);
  return {
    name,
    meta: companionDisplayMeta(rawMeta, archetype),
    seed: companion.visual_seed || `companion:${state.campaign.activeCampaign}:${name}`,
    archetype,
    raw: companion,
  };
}

function defaultCompanionMeta(archetype) {
  return "同行伙伴";
}

function companionDisplayMeta(meta, archetype) {
  const text = String(meta || "").trim();
  return text || "同行伙伴";
}

function inferCompanionArchetype(name, meta = "") {
  return "companion";
}

function hasStrictVitals(vitals) {
  return Array.isArray(vitals) && vitals.some((item) => Number.isFinite(item?.current) && Number.isFinite(item?.max));
}

function hasStrictAttributes(attributes) {
  if (Array.isArray(attributes)) return attributes.some((item) => Number.isFinite(item?.value));
  if (attributes && typeof attributes === "object") {
    return [attributes.three, attributes.six].some((group) => Array.isArray(group?.items) && group.items.some((item) => Number.isFinite(Number(item?.value))));
  }
  return false;
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

function deriveVitalsFromThreeAttributes(attributes = {}) {
  if (!attributes || typeof attributes !== "object" || Array.isArray(attributes)) return [];
  const group = attributes.three || {};
  const items = Array.isArray(group.items) ? group.items : [];
  if (!items.length) return [];
  const floatCap = Number(attributes.float_cap || Math.ceil((Number(attributes.cap) || 20) * (Number(attributes.float_ratio) || 1.2))) || 24;
  const findItem = (keys, fallbackIndex) => items.find((item) => keys.includes(String(item.key || "").toUpperCase())) || items[fallbackIndex] || {};
  return [
    ["status", "状态", findItem(["BODY"], 0), "green"],
    ["focus", "专注", findItem(["ACTION", "REFLEX", "SKILL", "OBSERVE"], 1), "blue"],
    ["resource", "资源", findItem(["MIND", "SANITY"], 2), "amber"],
  ].map(([key, label, item, tone]) => {
    const value = Number(item.value);
    const safeValue = Number.isFinite(value) ? value : 0;
    const attrLabel = item.label || item.key || label;
    return {
      key,
      label,
      current: safeValue,
      max: floatCap,
      text: `${attrLabel} ${safeValue}/${floatCap}`,
      tone,
    };
  });
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
    "稳定",
    mechanics.use_dice ? "数值待同步" : "叙事记录",
    scene?.immediate_pressure ? "现场压力" : "待记录",
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
    { label: "一", text: "属性" },
    { label: "二", text: "属性" },
    { label: "三", text: "属性" },
    { label: "四", text: "属性" },
    { label: "五", text: "属性" },
    { label: "六", text: "属性" },
  ];
}

function renderCharacterCard(card) {
  const panel = document.querySelector(".characterPanel");
  panel?.classList.toggle("character-disabled", card.enabled === false);
  setText("characterName", card.name || "未命名角色");
  setText("characterMeta", card.meta || "身份待确认");
  renderCharacterProfile(card.profile || {});
  const visibility = card.statVisibility || "narrative";
  state.lastCharacterCardForRender = card;
  setText("characterCardMode", card.enabled === false ? "未启用" : visibility === "numeric" ? "数值卡" : visibility === "hybrid" ? "半数值卡" : "叙事卡");
  setText("progressLabel", card.progression.label);
  setText("progressValue", card.progression.value);
  const progressBar = $("progressBar");
  if (progressBar) {
    const percent = Number(card.progression.percent);
    progressBar.style.width = Number.isFinite(percent) ? `${Math.max(4, Math.min(100, percent))}%` : "0%";
    progressBar.parentElement?.classList.toggle("noNumericTrack", !Number.isFinite(percent));
  }
  renderVitals(card.vitals, visibility);
  renderConditionBadges(card.conditions);
  renderAttributePanel(card.attributes, card.name, visibility);
  if (card.enabled === false) {
    clearImageElement("avatarImage");
    return;
  }
  renderCharacterPortrait(card);
}

function renderCharacterProfile(profile) {
  const holder = $("characterBackground");
  const toggle = $("characterProfileToggle");
  const details = $("characterProfileDetails");
  if (!holder) return;
  if (state.character.characterProfileCampaign !== state.campaign.activeCampaign) {
    state.character.characterProfileCampaign = state.campaign.activeCampaign;
    state.character.characterProfileExpanded = false;
  }
  const normalized = normalizeCharacterProfile(profile);
  holder.textContent = normalized.background || "背景待确认";
  if (!toggle || !details) return;
  const hasDetails = Boolean(
    normalized.background ||
    normalized.motivation ||
    normalized.personality ||
    (Array.isArray(normalized.notes) && normalized.notes.length)
  );
  toggle.hidden = !hasDetails;
  toggle.textContent = state.character.characterProfileExpanded ? "主角资料 · 收起" : "主角资料 · 展开";
  toggle.setAttribute("aria-expanded", state.character.characterProfileExpanded ? "true" : "false");
  details.hidden = !state.character.characterProfileExpanded || !hasDetails;
  details.innerHTML = "";
  if (details.hidden) return;
  renderCharacterProfileDetails(details, normalized);
}

function renderCharacterProfileDetails(holder, profile) {
  const rows = [
    ["背景", profile.background || "背景待确认"],
    ["动机", profile.motivation || "动机待确认"],
    ["性格", profile.personality || "性格待确认"],
  ];
  rows.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "characterProfileRow";
    const key = document.createElement("span");
    key.textContent = label;
    const text = document.createElement("p");
    text.textContent = value;
    row.append(key, text);
    holder.appendChild(row);
  });
  const notes = Array.isArray(profile.notes) ? profile.notes.map((item) => String(item || "").trim()).filter(Boolean) : [];
  if (notes.length) {
    const row = document.createElement("div");
    row.className = "characterProfileRow";
    const key = document.createElement("span");
    key.textContent = "备注";
    const list = document.createElement("ul");
    notes.slice(0, 5).forEach((note) => {
      const item = document.createElement("li");
      item.textContent = note;
      list.appendChild(item);
    });
    row.append(key, list);
    holder.appendChild(row);
  }
}

function renderCompanionCard(companion) {
  const card = document.querySelector(".companionCard");
  const panel = document.querySelector(".characterPanel");
  if (!companion) {
    if (card) card.hidden = true;
    panel?.classList.add("no-companion");
    panel?.classList.remove("has-companion");
    clearImageElement("companionImage");
    return;
  }
  if (card) card.hidden = false;
  panel?.classList.add("has-companion");
  panel?.classList.remove("no-companion");
  setText("companionName", companion.name);
  setText("companionMeta", companion.meta);
  if (companion.pending) {
    clearImageElement("companionImage");
    return;
  }
  const visualProfile = companion.visual_profile || buildCompanionVisualProfile(companion, state.campaign.lastCampaignState || {}, {}, {});
  const visualHash = visualProfileHash(visualProfile);
  const visualContract = hasVisualContract(companion.visual_contract) ? companion.visual_contract : visualContractFor("", "companion", companion.name || "");
  const resolved = resolveVisualAsset({ ...companion, visual_profile: visualProfile, type: "companion", role: "companion", portrait: companion.portrait || {} });
  if (resolved.url && resolved.asset_key && String(resolved.asset_key).includes(`:v${ASSET_GENERATOR_VERSION}`)) {
    showAvatarImage("companionImage", resolved.url, resolved.asset_key || "");
    return;
  }
  drawPixelCompanionPortrait(resolved.fallback_seed || companion.seed || companion.name, {
    cache: true,
    objectId: slugify(resolved.entity_key || companion.name || "companion"),
    seedText: scopedSeed(`${resolved.fallback_seed || companion.seed || companion.name || "companion"}:${visualHash}:${currentStoryVisualContext()}`),
    archetype: visualProfile.companion_type_preset || "custom",
    visualProfile,
    kind: "companion_portrait",
    metadata: {
      title: resolved.display_name || companion.name,
      display_name: resolved.display_name || companion.name,
      role: "companion",
      runtime_role: "companion",
      companion_type: visualProfile.companion_type_raw,
      companion_type_raw: visualProfile.companion_type_raw,
      companion_type_preset: visualProfile.companion_type_preset,
      archetype: companion.meta?.archetype || companion.archetype || companion.meta?.kind || "",
      species: companion.meta?.species || "",
      visual_profile: visualProfile,
      entity_key: resolved.entity_key || makeEntityKey("companion", companion.name),
      avatar_key: resolved.entity_key || makeEntityKey("companion", companion.name),
      portrait_asset_kind: "companion_portrait",
      gallery_category: "hidden",
      visible_in_gallery: false,
      not_in_gallery_filters: true,
      display_slot: "companion_card",
      detail_slot: "companion_detail",
      render_tier: "companion",
      source_size: 512,
      detail_level: "high",
      visual_spec: "story_linked_canvas_portrait",
      portrait_spec_version: PORTRAIT_SPEC_VERSION,
      visual_profile: visualProfile,
      visual_profile_hash: visualHash,
      visual_contract_key: visualContract.entity_key || "",
      visual_contract_hash: visualContract.visual_contract_hash || "",
      visual_contract: visualContract,
      variant: `vp_${visualHash}`,
      background_context: currentStoryVisualContext(),
    },
  });
}

function renderVitals(vitals, statVisibility = "narrative") {
  const holder = $("vitalList");
  if (!holder) return;
  holder.innerHTML = "";
  const attributes = normalizeCharacterAttributes((state.lastCharacterCardForRender || {}).attributes);
  if (attributes.enabled !== false && attributes.visible !== false && attributes.three?.items?.length) {
    return;
  }
  if (!Array.isArray(vitals) || !vitals.length) {
    const row = document.createElement("div");
    row.className = "vitalRow narrative";
    const label = document.createElement("span");
    label.textContent = "状态";
    const value = document.createElement("b");
    value.textContent = "角色卡未启用";
    row.append(label, value);
    holder.appendChild(row);
    return;
  }
  vitals.slice(0, 4).forEach((vital) => {
    const row = document.createElement("div");
    row.className = `vitalRow ${vital.tone || ""}`;
    const label = document.createElement("span");
    label.textContent = vital.label;
    const value = document.createElement("b");
    value.textContent = vital.state;
    row.append(label, value);
    const percent = Number(vital.percent);
    if (statVisibility !== "narrative" && Number.isFinite(percent)) {
      const track = document.createElement("em");
      track.className = "statTrack";
      const bar = document.createElement("i");
      bar.style.width = `${Math.max(4, Math.min(100, percent))}%`;
      track.appendChild(bar);
      row.appendChild(track);
    }
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

function renderAttributes(attributes, characterName = "player", statVisibility = "narrative") {
  const wrap = $("attributeStar");
  if (wrap) wrap.hidden = statVisibility === "narrative" || !Array.isArray(attributes) || !attributes.length;
  if (statVisibility === "narrative" || !Array.isArray(attributes) || !attributes.length) return;
  renderAttributeStar(attributes, characterName);
}

function renderAttributePanel(attributes, characterName = "player", statVisibility = "narrative") {
  const wrap = $("attributeStar");
  const threeSlot = $("threeAttributeSlot");
  if (threeSlot) threeSlot.innerHTML = "";
  if (!wrap) return;
  const normalized = normalizeCharacterAttributes(attributes);
  wrap.hidden = normalized.enabled === false || normalized.visible === false;
  if (wrap.hidden) return;
  wrap.querySelectorAll(".threeAttributeBars,.sixAttributeList,.attributeGroupTitle").forEach((node) => node.remove());
  const image = $("attributeStarImage");
  if (image) image.hidden = true;
  if (normalized.three?.items?.length) renderThreeAttributeBars(normalized.three, normalized.cap, normalized.float_cap, threeSlot || wrap);
  if (normalized.six?.items?.length) {
    renderSixAttributeRadar(normalized.six, characterName, normalized.float_cap);
  } else if (normalized.legacy?.length) {
    renderLegacyAttributeList(normalized.legacy);
  }
}

function renderThreeAttributeBars(group, cap = 20, floatCap = 24, target = $("attributeStar")) {
  const wrap = target || $("attributeStar");
  if (!wrap) return;
  const title = document.createElement("div");
  title.className = "attributeGroupTitle";
  title.textContent = "三维属性";
  const box = document.createElement("div");
  box.className = "threeAttributeBars";
  (group.items || []).forEach((item) => {
    const row = document.createElement("div");
    row.className = "attributeBarRow";
    const label = document.createElement("span");
    label.textContent = item.label || item.key;
    const track = document.createElement("em");
    track.className = "attributeBarTrack";
    const fill = document.createElement("i");
    const value = Number(item.value);
    fill.style.width = `${Number.isFinite(value) ? Math.max(4, Math.min(100, value / Math.max(1, floatCap || cap) * 100)) : 0}%`;
    track.appendChild(fill);
    const num = document.createElement("b");
    num.textContent = Number.isFinite(value) ? String(value) : "-";
    row.append(label, track, num);
    box.appendChild(row);
  });
  wrap.append(title, box);
}

function renderSixAttributeRadar(group, characterName = "player", floatCap = 24) {
  const wrap = $("attributeStar");
  const image = $("attributeStarImage");
  if (image) image.hidden = false;
  const rows = (group.items || []).map((item) => ({ ...item, max: floatCap, text: item.label }));
  if (rows.length >= 3) renderAttributeStar(rows, characterName);
  const title = document.createElement("div");
  title.className = "attributeGroupTitle";
  title.textContent = "六维属性";
  wrap?.appendChild(title);
  renderLegacyAttributeList(rows, "sixAttributeList");
}

function renderLegacyAttributeList(attributes, className = "sixAttributeList") {
  const wrap = $("attributeStar");
  if (!wrap) return;
  const box = document.createElement("div");
  box.className = className;
  (attributes || []).slice(0, 6).forEach((item) => {
    const row = document.createElement("div");
    row.className = "sixAttributeItem";
    const label = document.createElement("span");
    label.textContent = item.label || item.key || "属性";
    const key = document.createElement("span");
    key.textContent = item.key || item.text || "";
    const value = document.createElement("b");
    const number = Number(item.value);
    value.textContent = Number.isFinite(number) ? String(number) : (item.text || "-");
    row.append(label, key, value);
    box.appendChild(row);
  });
  wrap.appendChild(box);
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
  if (state.campaign.activeCampaign && image) {
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
  return state.campaign.campaigns.find((campaign) => campaign.campaign_id === state.campaign.activeCampaign) || null;
}

function renderSidePanel(campaignState, frontendState = state.campaign.frontendState || {}) {
  const list = $("sideList");
  if (!list) return;
  const rows = state.ui.sideTab === "items" ? protocolInventoryRows(frontendState, campaignState) : protocolQuestRows(frontendState, campaignState);
  const fallback = state.ui.sideTab === "items" ? ["暂无物品记录"] : ["暂无任务记录"];
  const visibleRows = state.ui.sideTab === "items" ? rows : rows.slice(-5);
  list.innerHTML = "";
  (visibleRows.length ? visibleRows : fallback.map((title) => ({ title, tag: "record" }))).forEach((row, index) => {
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
    makeTextDraggable(li, `${row.title || row}${row.detail ? `：${row.detail}` : ""}`, row.tag || state.ui.sideTab);
    list.appendChild(li);
  });
}

function questRows(campaignState) {
  const quests = campaignState.quests || {};
  return dedupeRows([...normalizeFactRows(quests.quest_updates), ...normalizeFactRows(quests.facts)])
    .map((row) => ({ ...row, tag: row.tag || "任务" }));
}

function itemRows(campaignState) {
  const equipment = campaignState.equipment || {};
  const sourceRows = [];
  if (equipment.items && typeof equipment.items === "object" && !Array.isArray(equipment.items)) {
    Object.entries(equipment.items).forEach(([id, item]) => {
      if (item && typeof item === "object") sourceRows.push({ id, ...item });
    });
  }
  ["inventory_updates", "structured_inventory_updates"].forEach((key) => {
    if (Array.isArray(equipment[key])) sourceRows.push(...equipment[key]);
  });
  return dedupeInventoryRows(sourceRows.flatMap(canonicalInventoryRows)).slice(-8);
}

function dedupeInventoryRows(rows = []) {
  const byKey = new Map();
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    if (!row || !row.title) return;
    const key = slugify(row.id || `${row.item_type || row.category || "item"}:${row.title}`);
    byKey.set(key, row);
  });
  return Array.from(byKey.values());
}

function factSourceTexts(rows) {
  const list = Array.isArray(rows) ? rows : rows ? [rows] : [];
  return list.map((row) => {
    if (typeof row === "string") return row;
    if (!row || typeof row !== "object") return "";
    if (row.value && typeof row.value === "object") return row.value;
    return row.value || row.summary || row.title || row.name || row.text || row.description || row.detail || "";
  }).filter((text) => (typeof text === "object" && text) || String(text || "").trim());
}

function canonicalInventoryRows(input) {
  if (input && typeof input === "object") {
    const name = input.name || input.title || input.display_name || "";
    const description = input.short_description || input.description || input.detail || input.summary || input.source_evidence || "";
    const cleanObjectText = `${name} ${description}`.trim();
    if (!name || isNegativeInventoryText(cleanObjectText)) return [];
    if (!inventoryOwnerAllowed(input.owner, input.owner_ref, input.source_evidence || description)) return [];
    const prompt = normalizeDirectorItemVisualPrompt(input);
    const category = input.category || prompt.category || "item";
    const itemType = input.item_type || prompt.archetype || prompt.type || "generic";
    return [{
      id: slugify(input.id || `${itemType}:${name}`),
      title: conciseTitle(name, 20),
      detail: conciseTitle(description || input.source_evidence || name, 96),
      tag: input.tag || inventoryCategoryLabel(category),
      category,
      item_type: itemType,
      status: input.status || itemStatusFromText(cleanObjectText),
      source_evidence: input.source_evidence || description || name,
      certainty: input.certainty || "confirmed",
      owner: input.owner || "",
      owner_ref: input.owner_ref || "",
      simple_prompt: input.simple_prompt || "",
      canvas_style: input.canvas_style || {},
      visual_hint: { ...prompt, archetype: prompt.archetype || itemType, category },
    }];
  }
  return [];
}

function inventoryOwnerAllowed(owner = "", ownerRef = "", evidence = "") {
  const value = String(owner || "").trim().toLowerCase();
  if (value === "player" || value === "companion") return true;
  if (value !== "party") return false;
  const relation = `${ownerRef || ""} ${evidence || ""}`.toLowerCase();
  return /player|protagonist|companion|主角|玩家|伙伴|同伴|随身|携带|持有|共用/.test(relation);
}

function normalizeDirectorItemVisualPrompt(input = {}) {
  const canvas = input.canvas_style && typeof input.canvas_style === "object" ? input.canvas_style : {};
  const hint = input.visual_hint && typeof input.visual_hint === "object" ? input.visual_hint : {};
  const itemType = input.item_type || hint.archetype || hint.type || canvas.shape || "generic";
  return {
    ...hint,
    type: itemType,
    archetype: itemType,
    category: input.category || hint.category || "item",
    canvas_style: canvas,
    simple_prompt: input.simple_prompt || hint.simple_prompt || "",
    source_text: input.source_evidence || input.short_description || hint.source_text || "",
  };
}

function inventoryCategoryLabel(category = "") {
  return {
    weapon: "武器",
    resource: "资源",
    relic: "遗物",
    supply: "补给",
    clue: "线索",
    material: "材料",
    misc: "物品",
  }[String(category || "").toLowerCase()] || "物品";
}

function inventoryEvidenceFor(text, token) {
  const parts = String(text || "").split(/[；;。]/).map((part) => part.trim()).filter(Boolean);
  return parts.find((part) => part.includes(token)) || parts.find((part) => /携带|持有|可用|剩余|不稳|发热|损坏/.test(part)) || "";
}

function isNegativeInventoryText(text = "") {
  const value = String(text || "").replace(/\s+/g, "");
  return /(?:暂无|没有|无|未发现|尚无|不存在).{0,14}(?:伤势|损坏|装备损坏|物品|装备|线索)/.test(value)
    || /(?:伤势|装备损坏|损坏).{0,10}(?:暂无|没有|无|未发现)/.test(value);
}

function itemStatusFromText(text = "") {
  const value = String(text || "");
  if (/损坏|破损|断裂/.test(value) && !isNegativeInventoryText(value)) return "damaged";
  if (/不稳|偏低|剩余|有限|消耗|减少/.test(value)) return "limited";
  if (/未确认|不明|未知/.test(value)) return "uncertain";
  return "confirmed";
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
    makeTextDraggable(li, String(row || ""), "memory");
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
  if (output.campaign_id && state.campaign.activeCampaign && output.campaign_id !== state.campaign.activeCampaign) {
    clearStoryTurnHistory(state.campaign.activeCampaign);
    renderStoryBlocks([], "当前跑团暂无正文记录。");
    setText("summaryText", `已拦截其他跑团的正文记录：${output.campaign_id}`);
    setText("directorText", JSON.stringify({
      warning: "output campaign mismatch",
      active_campaign: state.campaign.activeCampaign,
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
  if (!state.campaign.activeCampaign) return;
  try {
    const data = await api(`/api/writeback-review?campaign_id=${encodeURIComponent(state.campaign.activeCampaign)}`);
    state.writeback.writebackReview = data;
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
  const campaignId = state.campaign.activeCampaign || output.campaign_id || "default";
  const rows = visibleStoryBlocks(blocks);
  const turnBlocks = rows.length ? rows : fallbackPlayerInstructionBlocks(fallbackText);
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
  return dedupeAdjacentPlayerActions((state.storyTurnsByCampaign[campaignId] || []).flatMap((turn) => turn.blocks));
}

function fallbackPlayerInstructionBlocks(fallbackText = "") {
  const text = String(fallbackText || "").trim();
  if (text && !isEmptyStoryPlaceholder(text)) return legacyTextBlocks(text);
  return [{
    type: "system_check",
    speaker: "系统",
    actor_id: "system",
    body: "请开始游戏。",
    time: "现在",
  }];
}

function dedupeAdjacentPlayerActions(blocks = []) {
  const output = [];
  (Array.isArray(blocks) ? blocks : []).forEach((block) => {
    const prev = output[output.length - 1];
    const currentIsPlayer = block?.type === "player_action";
    const prevIsPlayer = prev?.type === "player_action";
    const sameActor = normalizeActorName(block?.actor_id || block?.speaker || "") === normalizeActorName(prev?.actor_id || prev?.speaker || "");
    const sameBody = String(block?.body || "").trim() && String(block?.body || "").trim() === String(prev?.body || "").trim();
    if (currentIsPlayer && prevIsPlayer && sameActor && sameBody) return;
    output.push(block);
  });
  return output;
}

function isEmptyStoryPlaceholder(text = "") {
  const normalized = String(text || "").replace(/\s+/g, "");
  return !normalized || ["暂无正文。", "暂无正文", "当前跑团暂无正文记录。", "当前跑团暂无正文记录"].includes(normalized);
}

function clearStoryTurnHistory(campaignId = state.campaign.activeCampaign || "default") {
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
    campaign_id: output.campaign_id || state.campaign.activeCampaign || "",
    blocks: simplified,
  });
}

function renderCharacterPortrait(card) {
  const visualProfile = card.visual_profile || buildPlayerVisualProfile(card, state.campaign.lastCampaignState || {});
  const visualHash = visualProfileHash(visualProfile);
  const visualContract = hasVisualContract(card.visual_contract) ? card.visual_contract : visualContractFor("", "player", card?.name || "");
  const resolved = resolveVisualAsset({ ...card, visual_profile: visualProfile, type: "player", role: "player", portrait: card?.portrait || {} });
  if (resolved.url && resolved.asset_key && String(resolved.asset_key).includes(`:v${ASSET_GENERATOR_VERSION}`)) {
    showAvatarImage("avatarImage", resolved.url, resolved.asset_key || "");
    return;
  }
  drawPixelActorPortrait(resolved.fallback_seed || card?.name || "player", {
    cache: true,
    role: "player",
    kind: "player_portrait",
    objectId: slugify(resolved.entity_key || card?.name || "player"),
    seedText: scopedSeed(`${resolved.fallback_seed || card?.name || "player"}:${visualHash}:${currentStoryVisualContext()}`),
    visualProfile,
    targetImage: $("avatarImage"),
    metadata: {
      title: resolved.display_name || card?.name || "player",
      display_name: resolved.display_name || card?.name || "player",
      role: "player",
      runtime_role: "player",
      entity_key: resolved.entity_key,
      avatar_key: resolved.entity_key,
      portrait_asset_kind: "player_portrait",
      gallery_category: "hidden",
      visible_in_gallery: false,
      not_in_gallery_filters: true,
      display_slot: "main_character_card",
      detail_slot: "main_character_detail",
      render_tier: "player",
      source_size: 512,
      detail_level: "high",
      visual_spec: "story_linked_canvas_portrait",
      portrait_spec_version: PORTRAIT_SPEC_VERSION,
      visual_profile: visualProfile,
      visual_profile_hash: visualHash,
      visual_contract_key: visualContract.entity_key || "",
      visual_contract_hash: visualContract.visual_contract_hash || "",
      visual_contract: visualContract,
      variant: `vp_${visualHash}`,
      background_context: currentStoryVisualContext(),
    },
  });
}

function currentStoryVisualContext() {
  const scene = state.campaign.lastCampaignState?.recent?.current_scene || {};
  const pressure = state.story.currentPressurePack || {};
  return [
    scene.location,
    scene.immediate_pressure,
    scene.mood,
    pressure.human_readable_note,
  ].filter(Boolean).join(" / ").slice(0, 180);
}

function findPortraitUrl(assetKey = "", kinds = ["portrait", "player_portrait"]) {
  const key = String(assetKey || "");
  const allowed = new Set(kinds);
  const byKey = key ? findCurrentCampaignAsset((asset) => asset.exists && asset.url && asset.key === key && allowed.has(String(asset.kind || ""))) : null;
  if (byKey?.url) return byKey.url;
  const byKind = findCurrentCampaignAsset((asset) => asset.exists && asset.url && allowed.has(String(asset.kind || "")));
  return byKind?.url || "";
}

function showAvatarPlaceholder(id) {
  const img = $(id);
  if (!img) return;
  img.removeAttribute("src");
  img.classList.add("is-empty");
  img.dataset.assetKey = "";
  img.dataset.campaignId = state.campaign.activeCampaign || "";
}

function showAvatarImage(id, url, assetKey = "") {
  const img = $(id);
  if (!img || !url) return showAvatarPlaceholder(id);
  img.onload = () => img.classList.remove("is-empty");
  img.onerror = () => showAvatarPlaceholder(id);
  img.dataset.assetKey = assetKey;
  img.dataset.campaignId = state.campaign.activeCampaign || "";
  setAssetImage(img, url);
}

function resolveVisualAsset(entityLike = {}, frontendState = state.campaign.frontendState || {}, cachedAssets = state.assets.cachedAssets || []) {
  return resolveActorAvatar(entityLike, frontendState, cachedAssets);
}

function normalizeAssetIdentity(asset = {}, campaignState = state.campaign.frontendState || {}) {
  const metadata = asset.metadata || {};
  const rawRole = metadata.runtime_role || metadata.role || asset.runtime_role || asset.role || roleFromEntityKey(metadata.entity_key || asset.entity_key || "") || asset.kind || "";
  const runtimeRole = normalizeRuntimeRole(rawRole);
  const galleryCategory = String(metadata.gallery_category || asset.gallery_category || normalizeGalleryKind(asset.kind) || "").toLowerCase();
  const entityKey = metadata.entity_key || asset.entity_key || makeEntityKey(runtimeRole, asset.display_name || metadata.display_name || metadata.title || asset.title || asset.key || runtimeRole);
  const portraitAssetKind = metadata.portrait_asset_kind || asset.portrait_asset_kind || asset.kind || assetKindForRole(runtimeRole);
  return {
    entity_key: entityKey,
    runtime_role: runtimeRole,
    role: metadata.role || asset.role || runtimeRole,
    companion_type: metadata.companion_type || asset.companion_type || "",
    archetype: metadata.archetype || asset.archetype || "",
    species: metadata.species || asset.species || "",
    asset_kind: asset.kind || portraitAssetKind,
    portrait_asset_kind: portraitAssetKind,
    display_slot: metadata.display_slot || asset.display_slot || "",
    detail_slot: metadata.detail_slot || asset.detail_slot || "",
    gallery_category: runtimeRole === "player" || runtimeRole === "companion" ? "hidden" : galleryCategory,
    visible_in_gallery: runtimeRole !== "player" && runtimeRole !== "companion" && asset.visible_in_gallery !== false && metadata.visible_in_gallery !== false && galleryCategory !== "hidden",
    not_in_gallery_filters: Boolean(metadata.not_in_gallery_filters || asset.not_in_gallery_filters || runtimeRole === "player" || runtimeRole === "companion"),
    avatar_key: metadata.avatar_key || asset.avatar_key || entityKey,
    render_tier: metadata.render_tier || asset.render_tier || runtimeRole,
    avatar_locked_by_vcg: Boolean(metadata.avatar_locked_by_vcg || isVcgAvatarAsset(asset)),
  };
}

function resolveActorIdentity(source = {}, campaignState = state.campaign.frontendState || {}, assets = state.assets.cachedAssets || []) {
  const registry = campaignState.visual_registry || {};
  const avatarIndex = campaignState.avatar_index || registry.avatar_index || {};
  const rawName = source.display_name || source.name || source.title || source.speaker || source.actor_id || source.key || "";
  const explicitKey = source.entity_key || source.entityKey || source.metadata?.entity_key || "";
  if (explicitKey && avatarIndex[explicitKey]) return { ...avatarIndex[explicitKey], display_name: rawName || explicitKey };
  const registryMatch = findVisualRegistryEntity(source, registry);
  if (registryMatch?.entity_key) return { ...normalizeAssetIdentity(registryMatch, campaignState), ...registryMatch, display_name: registryMatch.display_name || rawName };
  const role = normalizeRuntimeRole(roleFromEntityKey(explicitKey) || source.actor_kind || source.role || source.kind || source.type || inferRoleFromEntity(source));
  const entityKey = explicitKey || makeEntityKey(role, rawName || role);
  if (avatarIndex[entityKey]) return { ...avatarIndex[entityKey], display_name: rawName || entityKey };
  const byAsset = assets.find((asset) => {
    const id = normalizeAssetIdentity(asset, campaignState);
    return id.entity_key === entityKey;
  });
  if (byAsset) return normalizeAssetIdentity(byAsset, campaignState);
  return {
    entity_key: entityKey,
    runtime_role: role,
    role,
    asset_kind: assetKindForRole(role),
    portrait_asset_kind: assetKindForRole(role),
    display_name: rawName || entityKey,
    gallery_category: role === "player" || role === "companion" ? "hidden" : normalizeGalleryKind(source.kind) || role,
    visible_in_gallery: !["player", "companion"].includes(role),
    not_in_gallery_filters: ["player", "companion"].includes(role),
    fallback_seed: `${state.campaign.activeCampaign}:${entityKey}:${role}`,
  };
}

function selectBestAvatarAsset(entityKey, portraitAssetKind, assets = state.assets.cachedAssets || [], expectedVisualHash = "") {
  const matches = (Array.isArray(assets) ? assets : []).filter((asset) => {
    if (!asset?.exists || !asset.url) return false;
    if (isAttributeStarAsset(asset)) return false;
    if (!avatarAssetAcceptsVisualProfile(asset, expectedVisualHash)) return false;
    const id = normalizeAssetIdentity(asset);
    return id.entity_key === entityKey && (id.portrait_asset_kind === portraitAssetKind || asset.kind === portraitAssetKind);
  });
  matches.sort((a, b) => avatarPriority(b) - avatarPriority(a));
  return matches[0] || null;
}

function resolveActorAvatar(source = {}, campaignState = state.campaign.frontendState || {}, assets = state.assets.cachedAssets || []) {
  const identity = resolveActorIdentity(source, campaignState, assets);
  const visualProfile = source.visual_profile || identity.visual_profile || {};
  const expectedVisualHash = visualProfileHash(visualProfile);
  const portraitKey = source.portrait?.asset_key || source.asset_key || source.avatar_key || identity.selected_avatar_key || "";
  const byKey = portraitKey ? findCurrentCampaignAsset((asset) => asset.exists && asset.url && asset.key === portraitKey && avatarAssetAcceptsVisualProfile(asset, expectedVisualHash)) : null;
  const best = selectBestAvatarAsset(identity.entity_key, identity.portrait_asset_kind || identity.asset_kind || assetKindForRole(identity.runtime_role), assets, expectedVisualHash);
  const directUrl = source.portrait?.url || source.url || source.cachedUrl || source.cached_url || "";
  const selected = best || byKey || null;
  const selectedKey = selected?.key || (!expectedVisualHash ? identity.selected_avatar_key : "") || portraitKey || "";
  const selectedUrl = selected?.url || (!expectedVisualHash ? identity.selected_avatar_url : "") || "";
  const directOk = isUrlForCurrentCampaign(directUrl, portraitKey);
  return {
    ...identity,
    role: normalizeRuntimeRole(identity.runtime_role || identity.role),
    asset_kind: identity.portrait_asset_kind || identity.asset_kind || assetKindForRole(identity.runtime_role),
    asset_key: selectedKey,
    url: selectedUrl && isUrlForCurrentCampaign(selectedUrl, selectedKey) ? selectedUrl : (directOk ? directUrl : ""),
    display_name: identity.display_name || source.display_name || source.name || source.title || identity.entity_key,
    visual_profile: visualProfile,
    visual_profile_hash: expectedVisualHash,
    fallback_seed: identity.fallback_seed || `${state.campaign.activeCampaign}:${identity.entity_key}:${identity.runtime_role || identity.role}`,
    renderer: identity.runtime_role === "item" ? "item_icon" : "actor_portrait",
    visible_in_gallery: Boolean(identity.visible_in_gallery),
  };
}

function avatarAssetAcceptsVisualProfile(asset = {}, expectedVisualHash = "") {
  if (!expectedVisualHash) return true;
  if (isVcgAvatarAsset(asset)) return true;
  const metadata = asset.metadata || {};
  const role = normalizeRuntimeRole(metadata.runtime_role || metadata.role || asset.role || "");
  if (!["player", "companion"].includes(role)) return true;
  return metadata.visual_profile_hash === expectedVisualHash && metadata.portrait_spec_version === PORTRAIT_SPEC_VERSION;
}

function normalizeRuntimeRole(value = "") {
  const raw = normalizeActorName(value);
  if (raw.includes("companion") || raw.includes("伙伴")) return "companion";
  if (raw.includes("player") || raw.includes("main_character") || raw.includes("主角")) return "player";
  if (raw.includes("key_character") || raw.includes("key character") || raw.includes("关键")) return "key_character";
  if (raw.includes("master") || raw.includes("servant") || raw.includes("npc")) return raw.includes("master") || raw.includes("servant") ? "key_character" : "npc";
  return "npc";
}

function isVcgAvatarAsset(asset = {}) {
  const metadata = asset.metadata || {};
  const text = [asset.key, asset.path, asset.filename, metadata.avatar_source, metadata.source, metadata.generator_version].join(" ").toLowerCase();
  return String(asset.key || "").toLowerCase().includes(":vcg") || text.includes("_vcg") || metadata.avatar_source === "VCG" || ["formal_cg_crop", "cg_feedback", "manual_import_cg_crop", "vcg"].includes(String(metadata.source || "").toLowerCase()) || String(metadata.generator_version || "").toUpperCase() === "VCG";
}

function avatarPriority(asset = {}) {
  const metadata = asset.metadata || {};
  if (isAttributeStarAsset(asset)) return -1;
  const source = String(metadata.source || metadata.avatar_source || "").toLowerCase();
  const version = Number(asset.generator_version || 0);
  if (isVcgAvatarAsset(asset)) return 500000 + version;
  if (["manual_import_cg_crop", "formal_cg_crop", "cg_feedback"].includes(source)) return 400000 + version;
  if (version >= ASSET_GENERATOR_VERSION) return 300000 + version;
  if (asset.placeholder || metadata.placeholder) return 0;
  return 200000 + version;
}

function canonicalEntityKeyForBlock(block = {}) {
  const registry = state.campaign.frontendState?.visual_registry || {};
  const playerName = state.campaign.frontendState?.character_card?.name || $("characterName")?.textContent || "";
  if (block.type === "player_action") return makeEntityKey("player", playerName || displaySpeaker(block) || block.actor_id || "player");
  if (block.type !== "npc_dialogue") return "";
  const match = findVisualRegistryEntity({
    name: displaySpeaker(block) || block.speaker || block.actor_id || block.avatar_key,
    speaker: block.speaker,
    actor_id: block.actor_id,
    avatar_key: block.avatar_key,
    role: block.actor_kind || "",
  }, registry);
  if (match?.entity_key) return match.entity_key;
  const candidate = bestEntityCandidateName(block.avatar_key, block.actor_id, block.speaker, displaySpeaker(block));
  const prefixRole = roleFromEntityKey(block.avatar_key);
  const role = isCompanionActorName(candidate) ? "companion" : normalizeVisualRole(prefixRole || block.actor_kind || "npc");
  return makeEntityKey(role, candidate || displaySpeaker(block) || block.actor_id || "npc");
}

function findVisualRegistryEntity(entityLike = {}, registry = state.campaign.frontendState?.visual_registry || {}) {
  const actorRows = Object.values(registry.actors || {});
  const objectRows = Object.values(registry.objects || {});
  const rows = [...actorRows, ...objectRows];
  const explicitEntity = entityLike.entity_key || entityLike.entityKey || "";
  if (explicitEntity) {
    const direct = rows.find((row) => row?.entity_key === explicitEntity);
    if (direct) return direct;
  }
  const assetKey = entityLike.portrait?.asset_key || entityLike.asset_key || entityLike.avatar_key || "";
  const indexedEntity = assetKey ? registry.asset_key_index?.[assetKey] : "";
  if (indexedEntity) {
    const indexed = rows.find((row) => row?.entity_key === indexedEntity);
    if (indexed) return indexed;
  }
  const candidates = [
    entityLike.name,
    entityLike.display_name,
    entityLike.title,
    entityLike.speaker,
    entityLike.actor_id,
    entityLike.avatar_key,
    entityLike.key,
  ].flatMap(entityNameCandidates).filter(Boolean);
  const companion = visibleCompanion();
  if (companion?.name && candidates.some((name) => normalizeActorName(name) === normalizeActorName(companion.name))) {
    const key = makeEntityKey("companion", companion.name);
    return (registry.actors || {})[key] || {
      entity_key: key,
      role: "companion",
      asset_kind: "companion_portrait",
      portrait_asset_kind: "companion_portrait",
      display_name: companion.name,
      fallback_seed: `${state.campaign.activeCampaign}:${key}:companion`,
      renderer: "actor_portrait",
      visible_in_gallery: false,
      gallery_category: "hidden",
      not_in_gallery_filters: true,
    };
  }
  for (const candidate of candidates) {
    const normalized = normalizeActorName(candidate);
    const match = rows.find((row) => {
      if (!row) return false;
      const display = normalizeActorName(row.display_name || "");
      const suffix = normalizeActorName(String(row.entity_key || "").split(":").pop() || "");
      return normalized && (normalized === display || normalized === suffix);
    });
    if (match) return match;
  }
  return null;
}

function entityNameCandidates(...values) {
  return values.flatMap((value) => {
    const text = String(value || "").trim();
    if (!text) return [];
    const withoutPrefix = text.includes(":") ? text.split(":").slice(1).join(":") : text;
    return [text, withoutPrefix, withoutPrefix.replace(/[_-]+/g, " ")];
  });
}

function bestEntityCandidateName(...values) {
  return entityNameCandidates(...values).find((value) => normalizeActorName(value)) || "";
}

function roleFromEntityKey(value = "") {
  const prefix = String(value || "").split(":", 1)[0] || "";
  return prefix && String(value).includes(":") ? normalizeVisualRole(prefix) : "";
}

function normalizeVisualRole(value = "") {
  const raw = normalizeActorName(value);
  if (raw.includes("companion") || raw.includes("伙伴")) return "companion";
  if (raw.includes("player") || raw.includes("protagonist") || raw.includes("主角") || raw.includes("玩家")) return "player";
  if (raw.includes("key_character") || raw.includes("key character") || raw.includes("关键")) return "key_character";
  if (raw.includes("master") || raw.includes("servant") || raw.includes("御主") || raw.includes("从者")) return "key_character";
  if (raw.includes("monster") || raw.includes("enemy") || raw.includes("boss") || raw.includes("怪物")) return "monster";
  if (raw.includes("item") || raw.includes("weapon") || raw.includes("equipment") || raw.includes("物品") || raw.includes("装备")) return "item";
  if (raw.includes("prop") || raw.includes("tool") || raw.includes("道具")) return "prop";
  if (raw.includes("scene") || raw.includes("map") || raw.includes("location") || raw.includes("场景") || raw.includes("地图")) return "map";
  if (raw.includes("cg") || raw.includes("剧情图") || raw.includes("生图")) return "cg";
  if (raw.includes("npc")) return "npc";
  return "npc";
}

function inferRoleFromEntity(entityLike = {}) {
  if (entityLike.type === "player" || entityLike.kind === "player") return "player";
  if (entityLike.type === "companion" || entityLike.archetype) return "companion";
  if (entityLike.type === "key_character" || entityLike.kind === "key_character") return "key_character";
  return entityLike.actor_kind || entityLike.kind || "npc";
}

function makeEntityKey(role, name) {
  return `${normalizeVisualRole(role)}:${slugify(normalizeActorName(name || "unknown"))}`;
}

function assetKindForRole(role) {
  return {
    player: "player_portrait",
    companion: "companion_portrait",
    key_character: "key_character_portrait",
    npc: "npc_portrait",
    monster: "monster_image",
    item: "item_icon",
    prop: "item_icon",
    scene: "map_image",
    map: "map_image",
    cg: "cg_image",
  }[role] || "npc_portrait";
}

function visibleStoryBlocks(blocks) {
  return (Array.isArray(blocks) ? blocks : []).filter((block) => !["summary", "backend_note"].includes(block.type));
}

function renderWritebackReview(data) {
  const decision = data.decision || "not_audited";
  const labels = { accept: "导演接受", revise: "导演修订", reject: "导演拒绝", not_audited: "未审核" };
  setText("writebackDecision", labels[decision] || decision);
  const reason = data.audit_result?.reason || (data.warnings || []).join("；") || "解析演员回复后，可在这里审核并应用状态回写。";
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
    setText("writebackDecision", "导演审核中");
    const data = await api("/api/audit-writeback", {
      method: "POST",
      body: JSON.stringify({ campaign_id: state.campaign.activeCampaign }),
    });
    renderWritebackReview(data);
  } catch (err) {
    setText("writebackDecision", "审核失败");
    setText("writebackHint", err.message);
  }
}

async function applyWriteback() {
  const decision = state.writeback.writebackReview?.decision;
  if (!["accept", "revise"].includes(decision)) return;
  if (!window.confirm("写入长期记忆？系统会先备份将被修改的记忆文件。")) return;
  try {
    const data = await api("/api/apply-writeback", {
      method: "POST",
      body: JSON.stringify({ campaign_id: state.campaign.activeCampaign }),
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
  renderInlineRunProgress();
  scrollActiveFeed();
  if (state.job.runProgress.active && blocks.length) scrollStoryToBottom(true);
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
  const rows = Array.isArray(state.character.rawInventoryItems) ? state.character.rawInventoryItems : [];
  return rows.map(protocolRawInventoryItem).filter(Boolean);
}

function protocolRawInventoryItem(item = {}) {
  if (!item || typeof item !== "object") return null;
  const itemId = String(item.item_id || "").trim();
  const title = String(item.title || itemId || "").trim();
  if (!itemId || !title) return null;
  const rawState = item.state && typeof item.state === "object" ? item.state : {};
  const rawPayload = item.payload && typeof item.payload === "object" ? item.payload : {};
  const sourceItemId = String(item.source_item_id || "").trim();
  const detailParts = [
    ...inventoryKeyValueRows(rawState),
    ...inventoryKeyValueRows(rawPayload),
  ];
  if (sourceItemId) detailParts.push(`source_item_id: ${sourceItemId}`);
  return {
    id: itemId,
    item_id: itemId,
    title,
    detail: detailParts.join(" | "),
    tag: sourceItemId ? "derived" : "item",
    state: rawState,
    payload: rawPayload,
    source_item_id: sourceItemId,
    raw_item: item,
  };
}

function inventoryKeyValueRows(value = {}) {
  return Object.entries(value || {})
    .filter(([key]) => String(key || "").trim())
    .map(([key, row]) => `${key}: ${inventoryDisplayValue(row)}`);
}

function inventoryDisplayValue(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) return value.map(inventoryDisplayValue).join(", ");
  if (value && typeof value === "object") return JSON.stringify(value);
  return String(value ?? "");
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
    return normalizeVisualRole(roleFromEntityKey(canonicalEntityKeyForBlock(block)) || "npc");
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
  const usingDemoCampaigns = !state.campaign.campaigns.length;
  const availableCampaigns = state.campaign.campaigns.length ? state.campaign.campaigns : demoCampaigns();
  if (!state.campaign.selectedCampaign && availableCampaigns[0]) {
    state.campaign.selectedCampaign = availableCampaigns[0].campaign_id;
  }
  availableCampaigns.forEach((campaign) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `campaignRailItem${campaign.campaign_id === state.campaign.selectedCampaign ? " active" : ""}`;
    button.innerHTML = `<b>${escapeHtml(campaign.title || campaign.name || campaign.campaign_id)}</b>`;
    button.addEventListener("click", () => {
      state.campaign.selectedCampaign = campaign.campaign_id;
      renderStoryPicker();
    });
    campaigns.appendChild(button);
  });
  const selected = availableCampaigns.find((x) => x.campaign_id === state.campaign.selectedCampaign) || availableCampaigns[0];
  if (!selected) return;
  const isActive = selected.campaign_id === state.campaign.activeCampaign;
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
  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "pickerAction danger";
  deleteBtn.textContent = "删除故事";
  deleteBtn.disabled = usingDemoCampaigns;
  deleteBtn.addEventListener("click", () => deleteCampaign(selected.campaign_id, selected.title || selected.name || selected.campaign_id));
  const actions = document.createElement("div");
  actions.className = "pickerActionRow";
  actions.append(switchBtn, deleteBtn);
  stories.append(detail, actions);
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
    if (state.campaign.selectedCampaign !== campaignId) return;
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
  return state.campaign.campaigns.find((campaign) => campaign.campaign_id === campaignId) || {};
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
  state.campaign.activeCampaign = campaignId;
  state.campaign.selectedCampaign = campaignId;
  resetCampaignScopedUiState(campaignId);
  closeStoryPicker();
  await refresh();
}

async function deleteCampaign(campaignId, title = "") {
  if (!campaignId) return;
  const label = title || campaignId;
  const confirmed = window.confirm(`永久删除跑团“${label}”？\n\n这会删除该跑团目录和索引记录，无法恢复。`);
  if (!confirmed) return;
  try {
    const data = await api("/api/delete-campaign", {
      method: "POST",
      body: JSON.stringify({ campaign_id: campaignId }),
    });
    const status = data.status || {};
    state.campaign.campaigns = status.campaign_list || [];
    state.campaign.activeCampaign = status.active_campaign || "";
    state.campaign.selectedCampaign = state.campaign.activeCampaign || state.campaign.campaigns[0]?.campaign_id || "";
    resetCampaignScopedUiState(state.campaign.activeCampaign);
    await refresh();
    renderStoryPicker();
    window.alert("故事已删除。");
  } catch (err) {
    setPickerNotice(err.message);
  }
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
    state.campaign.selectedCampaign = campaignId;
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
  const campaignId = state.campaign.selectedCampaign || state.campaign.activeCampaign;
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
  const campaignId = state.campaign.selectedCampaign || state.campaign.activeCampaign;
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
  const campaignId = state.campaign.selectedCampaign || state.campaign.activeCampaign;
  if (!campaignId) return setPickerNotice("请先选择跑团。");
  try {
    await api("/api/campaign-status", {
      method: "POST",
      body: JSON.stringify({ campaign_id: campaignId, status }),
    });
    await refresh();
    state.campaign.selectedCampaign = campaignId;
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
  state.ui.activePanel = name;
  ["story", "director", "writeback", "memory", "logs", "summary"].forEach((item) => {
    const el = $(`${item}Tab`);
    if (el) el.classList.toggle("hidden", item !== name);
  });
  document.querySelectorAll("[data-panel-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.panelTab === name);
  });
  if (["story", "summary", "logs"].includes(name)) {
    hydrateLazyFrontendModules(state.campaign.frontendState?.modules || {}, state.campaign.frontendState || {}, state.campaign.lastCampaignState || {});
  }
  scrollActiveFeed();
}

function setGalleryFilter(filter) {
  state.gallery.galleryFilter = filter || "all";
  document.querySelectorAll("#galleryFilters button").forEach((button) => {
    button.classList.toggle("active", button.dataset.filter === state.gallery.galleryFilter);
  });
  let visibleCount = 0;
  document.querySelectorAll("#galleryGrid article").forEach((card) => {
    const visible = galleryAssetMatchesFilter({
      gallery_category: card.dataset.galleryCategory,
      display_zone: card.dataset.displayZone,
    }, state.gallery.galleryFilter);
    card.classList.toggle("hidden", !visible);
    card.hidden = !visible;
    if (visible) visibleCount += 1;
  });
  const button = $("viewAllBtn");
  if (button) button.textContent = `显示全部资料（${visibleCount}）`;
  if (!$("galleryOverlay")?.classList.contains("hidden")) renderGalleryDialog();
}

function makeTextDraggable(element, text, kind = "record") {
  if (!element || !text) return;
  element.draggable = false;
  element.classList.add("dragSource");
  element.title = "可拖到行动输入";
  element.dataset.dragText = String(text || "").trim();
  element.addEventListener("pointerdown", (event) => beginReferenceDrag(event, element.dataset.dragText));
  element.addEventListener("dragstart", (event) => {
    const payload = String(text || "").trim();
    event.dataTransfer.effectAllowed = "copy";
    event.dataTransfer.setData("text/plain", payload);
    event.dataTransfer.setData("application/trpg-reference", JSON.stringify({ kind, text: payload }));
  });
}

function makeAssetDraggable(element, asset) {
  if (!element || !asset) return;
  element.draggable = false;
  element.classList.add("dragSource");
  element.title = "可拖到行动输入";
  const title = asset.title || asset.key || "资料";
  const dragText = `查看资料《${title}》：`;
  element.dataset.dragText = dragText;
  element.addEventListener("pointerdown", (event) => beginReferenceDrag(event, dragText));
  element.addEventListener("dragstart", (event) => {
    const text = dragText;
    event.dataTransfer.effectAllowed = "copy";
    event.dataTransfer.setData("text/plain", text);
    event.dataTransfer.setData("application/trpg-reference", JSON.stringify({
      kind: asset.gallery_category || "asset",
      key: asset.key || "",
      title,
      text,
    }));
  });
}

function beginReferenceDrag(event, text) {
  if (event.button !== 0 || !text) return;
  if (event.target.closest("button, input, textarea, select, a")) return;
  state.ui.activeReferenceDrag = {
    text,
    startX: event.clientX,
    startY: event.clientY,
    moved: false,
    ghost: null,
  };
  document.addEventListener("pointermove", moveReferenceDrag);
  document.addEventListener("pointerup", endReferenceDrag, { once: true });
}

function moveReferenceDrag(event) {
  const drag = state.ui.activeReferenceDrag;
  if (!drag) return;
  const distance = Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY);
  if (!drag.moved && distance < 6) return;
  drag.moved = true;
  if (!drag.ghost) {
    drag.ghost = document.createElement("div");
    drag.ghost.className = "dragGhost";
    drag.ghost.textContent = drag.text;
    document.body.appendChild(drag.ghost);
    document.body.classList.add("referenceDragging");
  }
  drag.ghost.style.left = `${event.clientX + 12}px`;
  drag.ghost.style.top = `${event.clientY + 12}px`;
  $("actionInput")?.classList.toggle("dropTarget", isPointInsideElement(event.clientX, event.clientY, $("actionInput")));
  event.preventDefault();
}

function endReferenceDrag(event) {
  const drag = state.ui.activeReferenceDrag;
  if (!drag) return;
  const input = $("actionInput");
  if (drag.moved && isPointInsideElement(event.clientX, event.clientY, input)) {
    appendToActionInput(drag.text);
  }
  drag.ghost?.remove();
  input?.classList.remove("dropTarget");
  document.body.classList.remove("referenceDragging");
  document.removeEventListener("pointermove", moveReferenceDrag);
  state.ui.activeReferenceDrag = null;
}

function isPointInsideElement(x, y, element) {
  if (!element) return false;
  const rect = element.getBoundingClientRect();
  return x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;
}

function appendToActionInput(text) {
  const input = $("actionInput");
  const value = String(text || "").trim();
  if (!input || !value) return;
  input.value = input.value.trim() ? `${input.value.trim()}\n${value}` : value;
  input.focus();
}

function bindActionInputDrop() {
  const input = $("actionInput");
  if (!input) return;
  input.addEventListener("dragover", (event) => {
    if (!dataTransferHasType(event.dataTransfer, "text/plain")) return;
    event.preventDefault();
    input.classList.add("dropTarget");
    event.dataTransfer.dropEffect = "copy";
  });
  input.addEventListener("dragleave", () => input.classList.remove("dropTarget"));
  input.addEventListener("drop", (event) => {
    event.preventDefault();
    input.classList.remove("dropTarget");
    const text = event.dataTransfer.getData("text/plain").trim();
    appendToActionInput(text);
  });
}

function dataTransferHasType(dataTransfer, type) {
  const types = dataTransfer?.types;
  if (!types) return false;
  if (typeof types.includes === "function") return types.includes(type);
  if (typeof types.contains === "function") return types.contains(type);
  return Array.from(types).includes(type);
}

function renderGallery(campaignState, galleryState = {}, moduleState = null) {
  const grid = $("galleryGrid");
  if (!grid) return;
  const assets = rawGalleryAssets()
    .filter((asset) => !asset.campaign_id || asset.campaign_id === state.campaign.activeCampaign);
  state.gallery.renderedRawAssets = assets;
  grid.innerHTML = "";
  if (!assets.length) {
    const empty = document.createElement("div");
    empty.className = "galleryEmpty";
    empty.textContent = "暂无资产";
    grid.appendChild(empty);
  }
  assets.forEach((asset) => {
    const card = document.createElement("article");
    card.dataset.kind = asset.gallery_category;
    card.dataset.key = asset.key;
    card.dataset.galleryCategory = asset.gallery_category || "";
    card.dataset.displayZone = asset.display_zone || "";
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    card.setAttribute("aria-label", `查看资料：${asset.title}`);
    makeAssetDraggable(card, asset);
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
  setGalleryFilter(state.gallery.galleryFilter);
}
function renderGalleryFilters() {
  const holder = $("galleryFilters");
  if (!holder) return;
  const resolvedFilters = rawGalleryFilters();
  state.gallery.galleryFilterIds = resolvedFilters.map((filter) => filter.id).filter(Boolean);
  const current = resolvedFilters.some((filter) => filter.id === state.gallery.galleryFilter) ? state.gallery.galleryFilter : "all";
  state.gallery.galleryFilter = current;
  holder.innerHTML = "";
  resolvedFilters.forEach((filter) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.filter = filter.id;
    button.textContent = filter.label || filter.id;
    button.title = filter.label || filter.id;
    button.classList.toggle("active", filter.id === state.gallery.galleryFilter);
    button.addEventListener("click", () => setGalleryFilter(filter.id));
    holder.appendChild(button);
  });
}

function galleryFiltersFromAssetContract(contract = {}) {
  const normalized = normalizeAssetContract(contract);
  const rows = [{ id: "all", label: "All", source: "ui" }];
  const categories = [
    ...(Array.isArray(normalized.core_gallery_categories) ? normalized.core_gallery_categories : []),
    ...(Array.isArray(normalized.custom_gallery_categories) ? normalized.custom_gallery_categories : []),
  ];
  categories.forEach((row) => {
    const id = String(row?.id || "").trim().toLowerCase();
    if (!id || ["all", "hidden", "player", "companion", "scene"].includes(id)) return;
    if (rows.some((item) => item.id === id)) return;
    rows.push({ id, label: row.label || id, source: row.source || "" });
  });
  return rows;
}

function rawGalleryFilters() {
  const rows = [{ id: "all", label: "All", source: "raw_gallery" }];
  const seen = new Set(["all"]);
  (state.gallery.rawAssets || []).forEach((asset) => {
    const normalized = protocolRawGalleryAsset(asset);
    if (!normalized) return;
    [normalized.gallery_category, normalized.kind].forEach((value) => {
      const id = String(value || "").trim().toLowerCase();
      if (!id || id === "hidden" || seen.has(id)) return;
      seen.add(id);
      rows.push({ id, label: galleryKindLabel(id), source: "raw_gallery" });
    });
  });
  return rows;
}

function registeredGalleryCategoryIds() {
  return new Set(rawGalleryFilters()
    .map((row) => row.id)
    .filter((id) => id && id !== "all"));
}

function protocolGalleryAsset(asset) {
  return protocolRawGalleryAsset(asset);
}

function rawGalleryAssets() {
  return (state.gallery.rawAssets || []).map(protocolRawGalleryAsset).filter(Boolean);
}

function protocolRawGalleryAsset(asset) {
  if (!asset || typeof asset !== "object") return null;
  const id = String(asset.id || "").trim();
  const type = String(asset.type || "").trim().toLowerCase();
  const title = String(asset.title || "").trim();
  if (!id || !type || !title) return null;
  const galleryCategory = String(asset.category || asset.type || "").trim().toLowerCase();
  const displayZone = String(asset.display_zone || "").trim().toLowerCase();
  const detail = asset.detail || "";
  return {
    ...asset,
    kind: type,
    key: id,
    id,
    type,
    title: conciseTitle(title, 22),
    meta: galleryKindLabel(galleryCategory),
    seed: scopedSeed(title || id || type),
    detail,
    cachedUrl: rawGalleryAssetMediaUrl(asset),
    createdAt: asset.created_at || asset.createdAt || "",
    campaign_id: asset.campaign_id || state.campaign.activeCampaign,
    gallery_category: galleryCategory,
    display_zone: displayZone,
    raw_asset: asset,
    exists: asset.exists !== false,
  };
}

function legacyProtocolGalleryAsset(asset) {
  const galleryCategory = String(asset.gallery_category || "").trim().toLowerCase();
  const displayZone = String(asset.display_zone || "").trim().toLowerCase();
  if (!galleryCategory) {
    console.warn("asset missing gallery_category; hidden from gallery", asset);
    return null;
  }
  if (!displayZone) {
    console.warn("asset missing display_zone; hidden from gallery", asset);
    return null;
  }
  if (["hidden", "portrait", "review"].includes(displayZone) || galleryCategory === "hidden") return null;
  if (displayZone !== "gallery" && !(displayZone === "map" && galleryCategory === "map")) return null;
  if (!registeredGalleryCategoryIds().has(galleryCategory)) return null;
  const detail = asset.detail || "";
  const subjectKey = asset.subject_key || "";
  const logicalKey = asset.key || galleryCategory + ":" + (asset.title || "asset");
  return {
    kind: galleryCategory,
    key: logicalKey,
    title: conciseTitle(asset.title || asset.key || "资料", 22),
    meta: galleryKindLabel(galleryCategory),
    seed: scopedSeed(asset.title || asset.key || galleryCategory),
    detail,
    cachedUrl: asset.url || "",
    createdAt: asset.created_at || "",
    campaign_id: asset.campaign_id || state.campaign.activeCampaign,
    asset_seed: asset.asset_seed || state.campaign.assetSeed,
    actor_role: asset.actor_role || "unknown",
    gallery_category: galleryCategory,
    asset_use: asset.asset_use || "",
    display_zone: displayZone,
    asset_kind: asset.asset_kind || "",
    asset_subtype: asset.asset_subtype || "",
    asset_tags: Array.isArray(asset.asset_tags) ? asset.asset_tags : [],
    subject_key: subjectKey,
    certainty: asset.certainty || "",
    cache_policy: asset.cache_policy || "",
    source_type: asset.source_type || "",
    exists: asset.exists !== false,
  };
}

function openAssetFromGallery(asset) {
  if (asset?.gallery_category === "cg" || asset?.asset_use === "cg") {
    openCgOverlay(asset.cachedUrl, asset.detail || galleryDetail(asset));
    return;
  }
  openGalleryOverlay(asset.key);
}

function markGalleryArchiveState(assets) {
  let currentSceneMarked = false;
  return assets.map((asset) => {
    if (asset.gallery_category !== "map" || !asset.cachedUrl) return asset;
    if (!currentSceneMarked) {
      currentSceneMarked = true;
      return { ...asset, status: "current", archived: false };
    }
    return { ...asset, status: asset.status || "archived", archived: true };
  });
}

function openCurrentMapOverlay() {
  if (!state.map.currentMapAsset) return;
  openGalleryOverlay(state.map.currentMapAsset.key, state.map.currentMapAsset);
}

function openGalleryOverlay(assetKey = "", transientAsset = null) {
  state.gallery.transientGalleryAsset = transientAsset;
  const requested = state.gallery.renderedRawAssets.find((asset) => asset.key === assetKey);
  if (requested && !galleryAssetMatchesFilter(requested, state.gallery.galleryFilter)) {
    state.gallery.galleryFilter = requested.gallery_category || "all";
    setGalleryFilter(state.gallery.galleryFilter);
  }
  const assets = filteredGalleryAssets();
  state.gallery.selectedGalleryKey = assetKey || state.gallery.selectedGalleryKey || assets[0]?.key || state.gallery.renderedRawAssets[0]?.key || "";
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
  state.gallery.transientGalleryAsset = null;
}

function filteredGalleryAssets() {
  const rows = state.gallery.renderedRawAssets.filter((asset) => galleryAssetMatchesFilter(asset, state.gallery.galleryFilter));
  if (state.gallery.transientGalleryAsset) {
    return [state.gallery.transientGalleryAsset, ...rows.filter((asset) => asset.key !== state.gallery.transientGalleryAsset.key)];
  }
  return rows;
}

function galleryAssetMatchesFilter(asset, filter) {
  const value = filter || "all";
  const category = String(asset?.gallery_category || "").trim().toLowerCase();
  const zone = String(asset?.display_zone || "").trim().toLowerCase();
  if (!category) {
    console.warn("raw gallery asset missing category/type; hidden from gallery", asset);
    return false;
  }
  if (!registeredGalleryCategoryIds().has(category)) return false;
  if (["hidden", "portrait", "review"].includes(zone)) return false;
  if (value === "all") return true;
  return category === value;
}

function renderGalleryDialog() {
  const list = $("galleryDialogList");
  if (!list) return;
  const assets = filteredGalleryAssets();
  list.innerHTML = "";
  if (!assets.length) {
    const empty = document.createElement("div");
    empty.className = "galleryEmpty";
    empty.textContent = "当前分类暂无资料";
    list.appendChild(empty);
    renderGalleryInspector(null);
    return;
  }
  if (!assets.some((asset) => asset.key === state.gallery.selectedGalleryKey)) {
    state.gallery.selectedGalleryKey = assets[0].key;
  }
  assets.forEach((asset) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = `galleryDialogItem${asset.key === state.gallery.selectedGalleryKey ? " active" : ""}`;
    row.innerHTML = `<b>${escapeHtml(asset.title)}</b><small>${escapeHtml(galleryDetail(asset))}</small><span>${escapeHtml(assetStatusLabel(asset))}</span>`;
    row.addEventListener("click", () => {
      state.gallery.selectedGalleryKey = asset.key;
      renderGalleryDialog();
    });
    list.appendChild(row);
  });
  renderGalleryInspector(assets.find((asset) => asset.key === state.gallery.selectedGalleryKey) || assets[0]);
}

function renderGalleryInspector(asset) {
  const image = $("galleryInspectorImage");
  const title = $("galleryInspectorTitle");
  const detail = $("galleryInspectorDetail");
  const meta = $("galleryInspectorMeta");
  const useButton = $("useGalleryAssetBtn");
  const inspector = $("galleryInspector");
  if (inspector) inspector.dataset.kind = asset?.gallery_category || "";
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
  const asset = state.gallery.renderedRawAssets.find((item) => item.key === state.gallery.selectedGalleryKey);
  if (!asset || !canUseGalleryAsset(asset)) return;
  const input = $("actionInput");
  if (!input) return;
  const text = `查看资料《${asset.title}》：`;
  input.value = input.value.trim() ? `${input.value.trim()}\n${text}` : text;
  input.focus();
  closeGalleryOverlay();
}

function canUseGalleryAsset(asset) {
  return asset && asset.display_zone === "gallery" && ["item", "prop", "character", "map", "cg"].includes(asset.gallery_category);
}

function assetStatusLabel(asset) {
  const status = String(asset?.status || "").toLowerCase();
  const base = asset?.meta || galleryKindLabel(asset?.gallery_category);
  if (asset?.archived) return `${base} / 已归档`;
  if (status.includes("dead") || status.includes("死亡") || status.includes("阵亡")) return `${base} / 已死亡`;
  if (status.includes("lost") || status.includes("失联")) return `${base} / 失联`;
  if (status.includes("consumed") || status.includes("消耗")) return `${base} / 已消耗`;
  if (status.includes("current")) return `${base} / 当前`;
  if (asset?.gallery_category === "map" && asset?.createdAt) return `${base} / 历史`;
  return base;
}

async function loadMemoryReport() {
  try {
    const params = state.campaign.activeCampaign ? `?campaign_id=${encodeURIComponent(state.campaign.activeCampaign)}` : "";
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
    state.ui.ruleFiles = data.rules || [];
    renderRulesList(data);
    const first = (data.matches && data.matches[0]) || state.ui.ruleFiles.find((item) => item.name === state.ui.selectedRule) || state.ui.ruleFiles[0];
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
    button.className = `ruleItem${rule.name === state.ui.selectedRule ? " active" : ""}`;
    const snippets = (rule.snippets || []).map((item) => `<small>${escapeHtml(item)}</small>`).join("");
    button.innerHTML = `<b>${escapeHtml(rule.title || rule.name)}</b><span>${escapeHtml(rule.name)}</span>${snippets}`;
    button.addEventListener("click", () => openRuleFile(rule.name));
    list.appendChild(button);
  });
}

async function openRuleFile(name) {
  if (!name) return;
  state.ui.selectedRule = name;
  document.querySelectorAll(".ruleItem").forEach((item) => item.classList.toggle("active", item.querySelector("span")?.textContent === name));
  const data = await api(`/api/rules?name=${encodeURIComponent(name)}`);
  setText("rulesViewerTitle", data.name || name);
  setText("rulesContent", data.content || "文件为空。");
}

function galleryDetail(asset) {
  const status = assetStatusLabel(asset);
  const suffix = status ? `（${status}）` : "";
  if (asset.detail) return conciseTitle(`${asset.detail}${suffix}`, 96);
  return "";
}

function buildVisualAssets(campaignState) {
  const recent = campaignState.recent || {};
  const scene = recent.current_scene || {};
  const protectedActors = protectedActorNames(campaignState);
  const pressureAssets = pressureVisualAssets(protectedActors);
  const rows = [];
  (scene.active_npcs || [])
    .filter((name) => !isProtectedActorName(name, protectedActors))
    .slice(0, 4)
    .forEach((name) => {
    rows.push({
      kind: "npc",
      key: makeScopedAssetKey("npc_portrait", name, "gallery"),
      title: name,
      meta: "NPC",
      seed: scopedSeed(name),
      campaign_id: state.campaign.activeCampaign,
      asset_seed: state.campaign.assetSeed,
    });
  });
  itemRows(campaignState).slice(-6).forEach((item, index) => {
    const itemEntity = makeEntityKey("item", item.title || item.key || `item-${index}`);
    rows.push({
      kind: "item",
      key: makeScopedAssetKey("item_icon", itemEntity, "memory"),
      title: conciseTitle(item.title, 20),
      meta: item.tag || "物品",
      seed: scopedSeed(`${item.title}:${item.detail}`),
      detail: item.detail,
      campaign_id: state.campaign.activeCampaign,
      asset_seed: state.campaign.assetSeed,
      role: "",
      entity_key: itemEntity,
      assetKind: "item_icon",
      status: item.status || "",
      visualPrompt: item.visual_hint || {},
      sourceMemory: item.source_evidence || "",
    });
  });
  return dedupeAssets([...rows, ...pressureAssets]).slice(0, 16);
}

function pressureVisualAssets(protectedActors = protectedActorNames(state.campaign.lastCampaignState || {})) {
  const assets = Array.isArray(state.story.currentPressurePack?.visual_assets) ? state.story.currentPressurePack.visual_assets : [];
  return assets.map((asset, index) => {
    const rawKind = String(asset.kind || "").toLowerCase();
    const displayZone = String(asset.display_zone || "").toLowerCase();
    let kind = normalizePressureKind(asset.kind);
    if (kind === "item" && !inventoryOwnerAllowed(asset.owner, asset.owner_ref, asset.source_evidence || asset.detail || "")) return null;
    const title = asset.title || asset.id || `${galleryKindLabel(kind)} ${index + 1}`;
    const detail = asset.detail || asset.source_memory || "";
    const visualPrompt = kind === "item"
      ? normalizeDirectorItemVisualPrompt(asset)
      : asset.visual_prompt || asset.visualPrompt || {};
    return {
      kind,
      key: makeScopedAssetKey(`gallery_${kind}`, asset.id || title || index, "director"),
      title: conciseTitle(title, 22),
      meta: asset.certainty === "confirmed" ? galleryKindLabel(kind) : `${galleryKindLabel(kind)} / ${asset.certainty || "clue"}`,
      seed: scopedSeed(`${asset.id || title}:${detail}`),
      detail,
      certainty: asset.certainty || "clue",
      displayZone: asset.display_zone || "gallery",
      cachePolicy: asset.cache_policy || "stable",
      sourceMemory: asset.source_memory || "",
      visualPrompt,
      imagePrompt: asset.image_prompt || asset.imagePrompt || buildImagePrompt(title, detail, kind),
      campaign_id: state.campaign.activeCampaign,
      asset_seed: state.campaign.assetSeed,
    };
  }).filter(Boolean)
    .filter((asset) => asset.kind !== "map" || asset.displayZone === "map")
    .filter((asset) => !(asset.kind === "npc" && isProtectedActorName(asset.title, protectedActors)));
}

function normalizePressureKind(kind) {
  const value = String(kind || "").toLowerCase();
  if (value === "map" || value === "scene") return "map";
  if (value === "character" || value === "npc" || value === "key_character") return "npc";
  if (value === "cg") return "cg";
  if (value === "clue" || value === "document") return value;
  if (value === "item" || value === "weapon" || value === "supply" || value === "ritual_tool") return "item";
  return "map";
}

function cachedGalleryAssets() {
  return (state.assets.cachedAssets || []).filter((entry) => {
    if (!isAssetForCurrentCampaign(entry)) return false;
    if (!entry.exists || !entry.url) return false;
    const category = String(entry.gallery_category || "").toLowerCase();
    const zone = String(entry.display_zone || "").toLowerCase();
    if (!category || !zone || category === "hidden") return false;
    if (["hidden", "portrait", "review"].includes(zone)) return false;
    if (zone !== "gallery" && !(zone === "map" && category === "map")) return false;
    return true;
  }).map((entry) => ({
    kind: entry.gallery_category,
    key: entry.key,
    title: conciseTitle(entry.title || entry.key, 22),
    meta: galleryKindLabel(entry.gallery_category),
    detail: entry.detail || "",
    cachedUrl: entry.url,
    sourceObjectId: entry.subject_key || "",
    campaign_id: entry.campaign_id || state.campaign.activeCampaign,
    asset_seed: entry.asset_seed || state.campaign.assetSeed,
    actor_role: entry.actor_role || "unknown",
    gallery_category: entry.gallery_category,
    asset_use: entry.asset_use || "",
    asset_kind: entry.asset_kind || "",
    asset_subtype: entry.asset_subtype || "",
    asset_tags: Array.isArray(entry.asset_tags) ? entry.asset_tags : [],
    subject_key: entry.subject_key || "",
    display_zone: entry.display_zone || "",
    certainty: entry.certainty || "",
    cache_policy: entry.cache_policy || "",
    source_type: entry.source_type || "",
    exists: entry.exists !== false,
  }));
}

function looksLikeGeneratedAssetTitle(title = "", key = "") {
  const text = normalizeActorName(title);
  const seed = normalizeActorName(state.campaign.assetSeed || "");
  const campaign = normalizeActorName(state.campaign.activeCampaign || "");
  const rawKey = normalizeActorName(key || "");
  if (!text) return true;
  if (seed && text.includes(seed.slice(0, 10))) return true;
  if (campaign && text.includes(campaign.slice(0, 16))) return true;
  if (/^[0-9a-f]{10,}/i.test(String(title || ""))) return true;
  if (/npcportrait|gallerynpc|playerportrait|companionportrait|itemicon/.test(text) && rawKey.includes(text.replace(/[^a-z0-9]/g, ""))) return true;
  return false;
}

function protectedActorNames(campaignState = state.campaign.lastCampaignState || {}) {
  const card = buildCharacterCard(campaignState, campaignTitle(state.campaign.activeCampaign) || state.campaign.activeCampaign || "玩家角色", campaignState.recent?.current_scene || {});
  return new Set([
    card.name,
    card.companion?.name,
  ].map(normalizeActorName).filter(Boolean));
}

function currentCompanion() {
  return buildCharacterCard(
    state.campaign.lastCampaignState || {},
    campaignTitle(state.campaign.activeCampaign) || state.campaign.activeCampaign || "玩家角色",
    state.campaign.lastCampaignState?.recent?.current_scene || {},
  ).companion;
}

function buildPlayerVisualProfile(card = {}, campaignState = state.campaign.lastCampaignState || {}) {
  const profile = normalizeCharacterProfile(card.profile || {});
  const context = [
    card.name,
    card.meta,
    profile.background,
    profile.motivation,
    profile.personality,
    ...(profile.notes || []),
    campaignState.template,
    campaignState.genre,
    campaignState.tone,
    campaignState.campaign_direction?.background_direction,
    campaignState.campaign_direction?.core_concept,
    campaignState.campaign_direction?.opening_situation,
    currentStoryVisualContext(),
  ].flat().filter(Boolean).join(" ");
  const text = normalizeActorName(context);
  const equipment = [];
  const motifs = [];
  const palette = [];
  if (/剑|盾|勇者|骑士|冒险|神殿|遗迹|地城|sword|shield|hero|knight|adventure|temple|ruin|dungeon/.test(text)) {
    equipment.push("travel cloak", "adventurer belts", "sword or shield marker");
    motifs.push("ancient triangle mark", "ruin light", "destiny emblem");
    palette.push("forest green", "leather brown", "ancient gold");
  }
  if (/森林|林|精灵|自然|forest|wood|elf|nature/.test(text)) {
    motifs.push("leaf silhouette", "forest backlight");
    palette.push("moss green", "warm bark");
  }
  if (/调查|侦探|旧案|失踪|悬疑|恐怖|克苏鲁|detective|investigation|mystery|horror/.test(text)) {
    equipment.push("notebook", "lantern", "long coat");
    motifs.push("paper clue", "low shadow");
    palette.push("lamp amber", "deep shadow");
  }
  if (/魔法|法术|命运|灵|圣杯|magic|spell|fate|spirit|grail/.test(text)) {
    motifs.push("soft magical glow", "arcane badge");
    palette.push("blue glow", "silver accent");
  }
  return {
    source: "campaign_initialization",
    role: "player",
    identity_markers: normalizeProfileList([card.name, card.meta].filter(Boolean).join(" / ")).slice(0, 6),
    background_markers: normalizeProfileList([profile.background, campaignState.campaign_direction?.background_direction, currentStoryVisualContext()].flat().filter(Boolean).join(" / ")).slice(0, 8),
    personality_markers: normalizeProfileList(profile.personality).slice(0, 6),
    motivation_markers: normalizeProfileList(profile.motivation).slice(0, 6),
    costume_or_equipment: [...new Set(equipment.length ? equipment : ["campaign travel outfit", "role-readable gear"])],
    palette_hints: [...new Set(palette.length ? palette : [campaignState.genre, campaignState.tone, campaignState.template].filter(Boolean))].slice(0, 8),
    pose_rules: ["full-body readable silhouette", "protagonist posture", "do not crop to only face"],
    symbolic_motifs: [...new Set(motifs.length ? motifs : ["campaign fate marker"])].slice(0, 8),
    campaign_style_markers: normalizeProfileList([campaignState.template, campaignState.genre, campaignState.tone].filter(Boolean).join(" / ")).slice(0, 8),
    avoid: ["do_not_use_generic_placeholder", "do_not_reuse_companion_silhouette", "do_not_ignore_story_background"],
  };
}

function buildCompanionVisualProfile(companion = {}, campaignState = state.campaign.lastCampaignState || {}, styleProfile = {}, imageProfile = {}) {
  const existing = companion.visual_profile || companion.meta?.visual_profile;
  if (existing && typeof existing === "object") return existing;
  const meta = companion.meta || {};
  const rawType = String(meta.companion_type_raw || meta.companion_type || meta.kind || meta.type || companion.companion_type_raw || companion.kind || companion.archetype || "").trim();
  const speciesText = [meta.species, meta.race, companion.species].filter(Boolean).join(" ");
  const archetypeText = [meta.archetype, meta.class, companion.archetype].filter(Boolean).join(" ");
  const equipmentText = normalizeProfileList(meta.equipment || meta.gear || meta.weapon || companion.equipment).join(" ");
  const temperament = normalizeProfileList(meta.personality || meta.temperament || companion.personality || companion.meta);
  const campaignStyle = normalizeProfileList([
    campaignState.template,
    campaignState.genre,
    campaignState.tone,
    campaignState.recent?.current_scene?.mood,
    campaignState.campaign_direction?.background_direction,
    styleProfile.style,
    imageProfile.style_preset,
  ].filter(Boolean).join(" / "));
  const profileText = normalizeActorName([rawType, speciesText, archetypeText, equipmentText, temperament.join(" ")].join(" "));
  const preset = companionVisualPreset(profileText);
  const profile = {
    source: "resolved_from_campaign_memory",
    companion_type_raw: rawType,
    companion_type_preset: preset || "custom",
    body_form: rawType || archetypeText || "custom distinct companion",
    body_structure: ["distinct companion silhouette", "not the player body template"],
    species_or_origin: normalizeProfileList(speciesText || archetypeText),
    material_traits: ["campaign-appropriate material markers"],
    costume_or_equipment: normalizeProfileList(equipmentText),
    temperament,
    campaign_style_markers: campaignStyle,
    background_markers: normalizeProfileList([campaignState.campaign_direction?.background_direction, currentStoryVisualContext()].flat().filter(Boolean).join(" / ")).slice(0, 8),
    relationship_markers: normalizeProfileList(companion.relationship_to_protagonist || companion.meta?.relationship_to_protagonist || companion.raw?.relationship_to_protagonist).slice(0, 6),
    scale: meta.scale || "companion scale",
    silhouette_rules: ["must differ from the main player silhouette", "support non-human forms when implied"],
    face_rules: ["do not reuse player face template", "do not draw as ordinary NPC unless confirmed"],
    pose_rules: ["clear role silhouette", "companion-focused posture"],
    color_rules: ["separate from the player palette", "use campaign mood accents"],
    avoid: ["do_not_reuse_player_face_template", "do_not_draw_as_ordinary_npc_unless_confirmed", "do_not_ignore_non_human_structure"],
    certainty: rawType || speciesText || archetypeText ? "confirmed" : "fallback",
  };
  applyCompanionVisualPreset(profile, preset, profileText);
  return profile;
}

function normalizeProfileList(value) {
  if (Array.isArray(value)) return value.map((item) => typeof item === "object" ? (item.label || item.name || item.title || item.type || "") : item).map(String).map((item) => item.trim()).filter(Boolean);
  return String(value || "").split(/[,\n/|；;、]+/).map((item) => item.trim()).filter(Boolean);
}

function companionVisualPreset(text = "") {
  if (/palico|felyne|cat|feline|猫|艾露/.test(text)) return "palico";
  if (/servant|assassin|caster|saber|knight|rider|lancer|archer|从者|英灵|骑士|术士|暗杀/.test(text)) return "servant";
  if (/familiar|spirit|ghost|wisp|summon|灵|魔宠|使魔|召唤/.test(text)) return "familiar";
  if (/mechanical|construct|robot|drone|ai|android|mecha|机械|构装|无人机|机器人/.test(text)) return "mechanical";
  if (/ship|vehicle|bike|car|mount|载具|船|车|坐骑/.test(text)) return "vehicle";
  return "custom";
}

function applyCompanionVisualPreset(profile, preset, text = "") {
  if (preset === "palico") {
    profile.body_form = "small feline companion";
    profile.body_structure.push("large ears", "tail marker", "compact hunter-support body");
    profile.material_traits.push("fur", "cloth or leather support gear");
    profile.face_rules.push("cat nose", "whisker marks", "non-human muzzle");
    profile.costume_or_equipment.push("support gear marker");
  } else if (preset === "servant") {
    profile.body_form = "class-readable high-spec humanoid companion";
    profile.body_structure.push("ceremonial posture", "sharp class silhouette");
    profile.material_traits.push("ritual cloth", "metal or shadow accents");
    profile.face_rules.push("mask or stylized face option");
  } else if (preset === "familiar") {
    profile.body_form = "spiritual or magical familiar";
    profile.body_structure.push("floating or compact magical body", "non-ordinary companion outline");
    profile.material_traits.push("glow", "mist", "soft magical edges");
    profile.face_rules.push("symbolic face");
  } else if (preset === "mechanical") {
    profile.body_form = "mechanical companion";
    profile.body_structure.push("segmented chassis", "visible joints", "device-like head");
    profile.material_traits.push("metal", "glass", "indicator lights");
    profile.face_rules.push("sensor face", "no human skin template");
  } else if (preset === "vehicle") {
    profile.body_form = "vehicle or mount companion";
    profile.body_structure.push("vehicle silhouette", "front marker", "utility attachments");
    profile.material_traits.push("painted shell", "metal", "worn utility surfaces");
    profile.face_rules.push("no human face");
  } else if (/shadow|暗影|影/.test(text)) {
    profile.body_form = "shadow-like custom companion";
    profile.material_traits.push("shadow", "soft edge glow");
    profile.body_structure.push("non-player silhouette");
  }
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
  return protocolCompanionCard(state.campaign.frontendState?.companion_card, state.campaign.lastCampaignState || {}) || currentCompanion();
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
    const visualProfile = companion.visual_profile || buildCompanionVisualProfile(companion, state.campaign.lastCampaignState || {}, {}, {});
    const visualHash = visualProfileHash(visualProfile);
    const resolved = resolveVisualAsset({ ...companion, visual_profile: visualProfile, type: "companion", role: "companion", portrait: companion.portrait || {} });
    if (resolved.url) {
      setAssetImage(image, resolved.url);
    } else {
      drawPixelCompanionPortrait(resolved.fallback_seed || companion.seed || companion.name, {
        cache: true,
        objectId: slugify(resolved.entity_key || companion.name || "companion"),
        targetImage: image,
        seedText: scopedSeed(`${resolved.fallback_seed || companion.seed || companion.name || "companion"}:${visualHash}:${currentStoryVisualContext()}`),
        archetype: visualProfile.companion_type_preset || "companion",
        visualProfile,
        kind: "companion_portrait",
        metadata: {
          title: resolved.display_name || companion.name,
          display_name: resolved.display_name || companion.name,
          role: "companion",
          entity_key: makeEntityKey("companion", companion.name),
          runtime_role: "companion",
          visual_profile: visualProfile,
          visual_profile_hash: visualHash,
          portrait_spec_version: PORTRAIT_SPEC_VERSION,
          visual_spec: "story_linked_canvas_portrait",
          variant: `vp_${visualHash}`,
          visible_in_gallery: false,
        },
      });
    }
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
  const candidates = entityNameCandidates(value);
  return Boolean(companion?.name && candidates.some((candidate) => normalizeActorName(candidate) === normalizeActorName(companion.name)));
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
  const existing = new Set(primary.flatMap((asset) => galleryDedupeKeys(asset)));
  cached.forEach((asset) => {
    const keys = galleryDedupeKeys(asset);
    if (!keys.some((key) => existing.has(key))) {
      rows.push(asset);
      keys.forEach((key) => existing.add(key));
    }
  });
  return rows.slice(0, 120);
}

function galleryDedupeKeys(asset = {}) {
  const kind = asset.gallery_category || "asset";
  const title = normalizeActorName(asset.title || "");
  const entity = normalizeActorName(asset.subject_key || "");
  const key = slugify(asset.key || asset.title);
  return [
    key,
    title ? `${kind}:${title}` : "",
    entity ? `${kind}:${entity}` : "",
  ].filter(Boolean);
}

function normalizeGalleryKind(kind) {
  const value = String(kind || "").toLowerCase();
  if (["cg_image", "gallery_image"].includes(value)) return "cg";
  if (value === "companion_portrait") return "hidden";
  if (value === "master_portrait") return "character";
  if (value === "npc_portrait") return "character";
  if (["scene_image", "map_image"].includes(value)) return "map";
  if (value === "item_icon") return "item";
  if (value.includes("companion")) return "hidden";
  if (["cg", "generated_cg", "gallery_image", "formal_cg", "剧情图", "生图"].some((token) => value.includes(token))) return "cg";
  if (value.includes("master") || value.includes("御主")) return "character";
  if (value.includes("document") || value.includes("文献")) return "item";
  if (value.includes("clue") || value.includes("线索")) return "item";
  if (value.includes("anomaly") || value.includes("异常")) return "prop";
  if (value.includes("quest") || value.includes("任务")) return "prop";
  if (value.includes("character") || value.includes("角色")) return "character";
  if (value.includes("map") || value.includes("scene") || value.includes("location")) return "map";
  if (value.includes("npc") || value.includes("portrait")) return "character";
  if (["prop", "tool", "道具"].some((token) => value.includes(token))) return "prop";
  if (["item", "weapon", "supply", "material", "ritual_tool", "equipment", "物品", "装备", "补给", "材料", "仪式"].some((token) => value.includes(token))) return "item";
  return "";
}

function fixedGalleryKind(kind) {
  const raw = String(kind || "").toLowerCase();
  if (["hidden", "companion", "companion_portrait"].includes(raw)) return "";
  if (raw.includes("gallery_npc")) return "";
  if (["generated_cg", "gallery_image", "formal_cg", "cg_image"].some((token) => raw.includes(token))) {
    return (state.gallery.galleryFilterIds || []).includes("cg") ? "cg" : "";
  }
  const allowed = new Set((state.gallery.galleryFilterIds || []).filter((key) => key && key !== "all"));
  if (!allowed.size) return normalizeGalleryKind(kind);
  if (allowed.has(raw)) return raw;
  let value = normalizeGalleryKind(kind);
  if (["hidden", "companion"].includes(value)) return "";
  const aliases = {
    location: "map",
    scene: "map",
    npc: "character",
    master: "character",
    servant: "character",
    document: "item",
    clue: "item",
    anomaly: "prop",
    quest: "prop",
    weapon: "item",
    supply: "item",
    material: "item",
    ritual_tool: "item",
  };
  value = aliases[value] || value;
  if (allowed.has(value)) return value;
  return "";
}

function normalizeGalleryAssetForFixedFilters(asset) {
  if (isAttributeStarAsset(asset || {})) return null;
  const identity = normalizeAssetIdentity(asset || {});
  if (identity.runtime_role === "player" || identity.runtime_role === "companion") return null;
  if (identity.visible_in_gallery === false || identity.not_in_gallery_filters) return null;
  const explicitKind = identity.gallery_category && identity.gallery_category !== "hidden" ? fixedGalleryKind(identity.gallery_category) : "";
  const kind = explicitKind || fixedGalleryKind(asset?.kind);
  if (kind === "item" && isInvalidGalleryItemAsset(asset)) return null;
  if (kind === "map" && (asset?.kind === "map" || asset?.kind === "map_image" || asset?.metadata?.source === "map_route") && !isValidCachedMapAsset(asset)) return null;
  if (!kind) return null;
  return { ...asset, kind };
}

function isInvalidGalleryItemAsset(asset = {}) {
  const metadata = asset.metadata || {};
  const text = [
    asset.title,
    asset.display_name,
    asset.detail,
    asset.meta,
    asset.key,
    metadata.title,
    metadata.display_name,
    metadata.detail,
    metadata.meta,
    metadata.source_memory,
  ].filter(Boolean).join(" ");
  if (isNegativeInventoryText(text)) return true;
  if (/(attribute_star|六维星图|属性星图)/i.test(text)) return true;
  const kind = fixedGalleryKind(asset.kind || metadata.kind || metadata.gallery_category);
  if (kind !== "item") return false;
  const title = String(asset.title || asset.display_name || metadata.title || metadata.display_name || "");
  const concrete = /短剑|剑|刀|油灯|提灯|灯笼|三角吊坠|吊坠|护身符|药瓶|钥匙|登记册|任务板|碎羽|鳞|素材|样本|碎片/.test(title);
  if (!concrete && /携带|持有|带着|装备有/.test(title)) return true;
  if (metadata.source === "gallery" && /本地记忆中的物品、装备或现场线索/.test(String(metadata.detail || "")) && /(可用|火苗|估计|剩余|在身|携带)/.test(title)) return true;
  if (metadata.source === "gallery" && /本地记忆中的物品、装备或现场线索/.test(String(metadata.detail || "")) && /暂无|没有|无|未发现/.test(text)) return true;
  return false;
}

function readableAssetTitle(key, kind) {
  const text = String(key || kind || "asset")
    .replace(/^gallery_[^:]+:/, "")
    .replace(/^[^:]+:/, "")
    .replace(/:v\d+$/, "")
    .replace(new RegExp(`^${escapeRegExp(state.campaign.activeCampaign)}:`), "")
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
  const row = galleryFiltersFromAssetContract(state.assets.assetContract || FALLBACK_ASSET_CONTRACT)
    .find((item) => item.id === kind);
  return row?.label || { prop: "道具", cg: "CG", character: "角色", map: "地图", item: "物品" }[kind] || "资料";
}

function drawGalleryAsset(targetImage, asset) {
  if (asset?.cachedUrl) {
    setAssetImage(targetImage, asset.cachedUrl);
    return;
  }
  if (targetImage) {
    targetImage.dataset.assetKey = asset.key || asset.id || "";
    targetImage.dataset.campaignId = state.campaign.activeCampaign || "";
    targetImage.dataset.fallbackSeed = asset.key || asset.title || "";
  }
  const rawCanvas = createAssetCanvas(128, 128);
  if (asset.kind === "map") drawPixelMap(asset.seed, { cache: false, canvas: rawCanvas, scene: asset.scene || {}, compact: true });
  else drawPixelItemIcon(asset.seed || asset.title, { cache: false, canvas: rawCanvas, targetImage: null, asset });
  if (targetImage) setAssetImage(targetImage, rawCanvas.toDataURL("image/png"));
  return;
  const resolved = resolveVisualAsset({ ...asset, role: asset.role || asset.kind, type: asset.kind });
  if (targetImage) {
    targetImage.dataset.assetKey = resolved.asset_key || asset.key || "";
    targetImage.dataset.campaignId = state.campaign.activeCampaign || "";
    targetImage.dataset.fallbackSeed = resolved.fallback_seed || resolved.entity_key || asset.key || asset.title || "";
  }
  if (resolved.url && resolved.asset_key && String(resolved.asset_key).includes(`:v${ASSET_GENERATOR_VERSION}`)) {
    setAssetImage(targetImage, resolved.url);
    return;
  }
  if (asset.cachedUrl && String(asset.key || "").includes(`:v${ASSET_GENERATOR_VERSION}`) && isCurrentGeneratorAssetUrl(asset.cachedUrl)) {
    if (isUrlForCurrentCampaign(asset.cachedUrl, asset.key)) setAssetImage(targetImage, asset.cachedUrl);
    return;
  }
  const canvas = createAssetCanvas(128, 128);
  const kind = galleryRenderKindForAsset(asset, resolved);
  const subdir = gallerySubdirForRenderKind(kind, asset.kind);
  const draw = () => {
    if (asset.kind === "map") drawPixelMap(asset.seed, { cache: false, canvas, scene: asset.scene, compact: true });
    else if (asset.kind === "companion") drawPixelCompanionPortrait(asset.seed || resolved.fallback_seed || asset.title, { cache: false, canvas, targetImage: null, archetype: "companion" });
    else if (asset.kind === "npc") drawPixelActorPortrait(asset.seed, { cache: false, role: "npc", canvas, targetImage: null });
    else drawPixelItemIcon(asset.seed || asset.title, { cache: false, canvas, targetImage: null, asset });
  };
  if (state.campaign.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      targetImage,
      kind,
      subdir,
      objectId: slugify(resolved.entity_key || asset.entity_key || asset.key || asset.title),
      seedText: scopedSeed(asset.seed || asset.title),
      metadata: {
        title: asset.title,
        detail: galleryDetail(asset),
        meta: asset.meta || galleryKindLabel(asset.kind),
        source: "gallery",
        object_id: asset.key || asset.title,
        display_name: asset.title,
        role: resolved.role,
        entity_key: resolved.entity_key,
        visible_in_gallery: resolved.visible_in_gallery,
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

function galleryRenderKindForAsset(asset = {}, resolved = {}) {
  const explicit = String(asset.assetKind || asset.asset_kind || asset.render_kind || resolved.asset_kind || "").toLowerCase();
  const galleryKind = String(asset.kind || "").toLowerCase();
  if (["map", "map_image", "scene", "scene_image"].includes(explicit)) return "map_image";
  if (["cg", "cg_image", "gallery_image"].includes(explicit)) return explicit === "cg" ? "cg_image" : explicit;
  if (["item", "prop", "item_icon"].includes(explicit)) return "item_icon";
  if (["monster", "monster_image"].includes(explicit)) return "monster_image";
  if (["player", "player_portrait", "portrait"].includes(explicit)) return "player_portrait";
  if (["companion", "companion_portrait"].includes(explicit)) return "companion_portrait";
  if (["npc", "character", "npc_portrait"].includes(explicit)) return "npc_portrait";
  if (galleryKind === "scene" || galleryKind === "map") return "map_image";
  if (galleryKind === "cg") return "cg_image";
  if (galleryKind === "item" || galleryKind === "prop") return "item_icon";
  if (galleryKind === "companion") return "companion_portrait";
  if (galleryKind === "npc" || galleryKind === "character") return "npc_portrait";
  return `gallery_${slugify(galleryKind || "asset")}`;
}

function gallerySubdirForRenderKind(renderKind = "", galleryKind = "") {
  const kind = String(renderKind || "").toLowerCase();
  if (kind === "map_image" || kind === "scene_image" || ["scene", "map"].includes(String(galleryKind || "").toLowerCase())) return "map";
  if (kind === "cg_image" || kind === "gallery_image" || String(galleryKind || "").toLowerCase() === "cg") return "generated";
  if (kind.includes("portrait")) return "portraits";
  return "items";
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
  clearTimeout(state.job.runProgress.hideTimer);
  stopRunStreamPolling();
  state.job.runProgress.active = true;
  state.job.runProgress.completing = false;
  state.job.runProgress.percent = 0;
  state.job.runProgress.target = 12;
  state.job.runProgress.jobId = "";
  state.job.runProgress.streamText = "";
  state.job.runProgress.streamError = "";
  state.job.runProgress.publicThink = [];
  state.job.runProgress.publicNote = "";
  state.job.runProgress.stage = "";
  state.job.runProgress.needsHumanVerification = false;
  const panel = $("runProgress");
  if (panel) panel.classList.add("hidden");
  renderInlineRunProgress();
  setRunProgress(8, "发送行动中");
  startRunProgressTween();
}

function startRunProgressTween() {
  if (state.job.runProgress.timer) return;
  state.job.runProgress.timer = setInterval(() => {
    if (!state.job.runProgress.active) return;
    const diff = state.job.runProgress.target - state.job.runProgress.percent;
    if (Math.abs(diff) < 0.35) {
      state.job.runProgress.percent = state.job.runProgress.target;
    } else {
      state.job.runProgress.percent += diff * 0.14;
    }
    paintRunProgress(state.job.runProgress.percent);
  }, 80);
}

function setRunProgress(target, label) {
  state.job.runProgress.target = Math.max(state.job.runProgress.target, Math.min(100, Number(target) || 0));
  setText("runProgressLabel", label || "处理中");
  setText("runProgressInlineLabel", label || "处理中");
  startRunProgressTween();
}

function startRunStreamPolling(jobId) {
  state.job.runProgress.jobId = jobId || "";
  if (!state.job.runProgress.jobId) return;
  if (state.job.runProgress.streamTimer) clearInterval(state.job.runProgress.streamTimer);
  pollRunStream();
  state.job.runProgress.streamTimer = setInterval(pollRunStream, 700);
}

function stopRunStreamPolling() {
  if (state.job.runProgress.streamTimer) clearInterval(state.job.runProgress.streamTimer);
  state.job.runProgress.streamTimer = null;
}

function stopRunProgressTween() {
  if (state.job.runProgress.timer) clearInterval(state.job.runProgress.timer);
  state.job.runProgress.timer = null;
}

async function pollRunStream() {
  if (!state.job.runProgress.jobId) return;
  try {
    const data = await api(`/api/run-turn-stream?job_id=${encodeURIComponent(state.job.runProgress.jobId)}`);
    state.job.runProgress.publicThink = Array.isArray(data.public_think) ? data.public_think : state.job.runProgress.publicThink || [];
    state.job.runProgress.publicNote = data.public_note || state.job.runProgress.publicNote || "";
    state.job.runProgress.stage = data.stage || state.job.runProgress.stage || "";
    state.job.runProgress.needsHumanVerification = Boolean(data.needs_human_verification);
    state.job.runProgress.streamError = data.error_tail || "";
    renderInlineRunProgress();
    if (!data.running) stopRunStreamPolling();
  } catch (err) {
    state.job.runProgress.streamError = err.message;
    renderInlineRunProgress();
    stopRunStreamPolling();
  }
}

function updateRunProgressFromPipeline(pipeline, job, output) {
  if (!state.job.runProgress.active && !job.running) return;
  const stage = pipeline.stage || output.stage || "";
  const labels = {
    director_ready: "导演层完成",
    actor_parsed: "演员层完成",
    audited: "审核层完成",
    synced: "已同步到页面",
    pending_parse: "等待解析层",
  };
  if (pipeline.percent) {
    setRunProgress(pipeline.percent, labels[stage] || pipeline.label || "处理中");
  } else if (stage === "pending_parse") {
    setRunProgress(30, labels.pending_parse);
  } else if (job.running) {
    setRunProgress(Math.max(state.job.runProgress.target, 18), "后台执行中");
  }
  const succeeded = job.returncode === 0 || job.returncode === undefined || job.returncode === null;
  const failed = job.returncode !== undefined && job.returncode !== null && job.returncode !== 0;
  if (!job.running && failed) {
    failRunProgress();
    return;
  }
  if (!job.running && succeeded && (pipeline.percent >= 100 || output.stage === "parsed")) {
    completeRunProgress().catch((err) => {
      console.warn("story hot refresh failed", err);
      scrollStoryToBottom(true);
    });
  }
}

async function completeRunProgress() {
  if (!state.job.runProgress.active || state.job.runProgress.completing) return;
  state.job.runProgress.completing = true;
  setRunProgress(100, "已同步到页面");
  stopRunStreamPolling();
  stopRunProgressTween();
  clearTimeout(state.job.runProgress.hideTimer);
  state.job.runProgress.active = false;
  const progress = $("runProgress");
  if (progress) progress.classList.add("hidden");
  renderInlineRunProgress();
  await refreshStoryLogNow();
  scrollStoryToBottom(true);
}

function failRunProgress() {
  if (!state.job.runProgress.active) return;
  setText("runProgressLabel", "执行失败");
  setText("runProgressInlineLabel", "执行失败");
  const panel = $("runProgress");
  if (panel) panel.classList.add("complete");
  const inline = $("runProgressInline");
  if (inline) inline.classList.add("failed");
  stopRunStreamPolling();
  stopRunProgressTween();
  clearTimeout(state.job.runProgress.hideTimer);
  state.job.runProgress.hideTimer = setTimeout(() => {
    state.job.runProgress.active = false;
    const progress = $("runProgress");
    if (progress) progress.classList.add("hidden");
    renderInlineRunProgress();
  }, 2200);
}

function paintRunProgress(percent) {
  const value = Math.round(Math.max(0, Math.min(100, percent)));
  const bar = $("runProgressBar");
  if (bar) bar.style.width = `${value}%`;
  const inlineBar = $("runProgressInlineBar");
  if (inlineBar) inlineBar.style.width = `${value}%`;
  setText("runProgressPercent", `${value}%`);
  setText("runProgressInlinePercent", `${value}%`);
}

function renderInlineRunProgress() {
  const container = $("storyText");
  if (!container) return;
  const existing = $("runProgressInline");
  if (!state.job.runProgress.active) {
    existing?.remove();
    return;
  }
  const panel = existing || document.createElement("section");
  panel.id = "runProgressInline";
  panel.className = `runProgress inline${state.job.runProgress.percent >= 99 ? " complete" : ""}${state.job.runProgress.streamError && !state.job.runProgress.active ? " failed" : ""}`;
  panel.setAttribute("aria-live", "polite");
  panel.innerHTML = `
    <div class="runProgressHeader">
      <b id="runProgressInlineLabel">${escapeHtml($("runProgressLabel")?.textContent || "AI 正在生成")}</b>
      <span id="runProgressInlinePercent">${Math.round(Math.max(0, Math.min(100, state.job.runProgress.percent)))}%</span>
    </div>
    <div class="runProgressTrack"><span id="runProgressInlineBar" style="width:${Math.round(Math.max(0, Math.min(100, state.job.runProgress.percent)))}%"></span></div>
    <div class="runProgressStream" id="runProgressStreamText"></div>
  `;
  if (!existing) container.appendChild(panel);
  else if (panel.parentElement !== container || panel !== container.lastElementChild) container.appendChild(panel);
  renderRunStreamText();
}

function renderRunStreamText() {
  const stream = $("runProgressStreamText");
  if (!stream) return;
  const think = Array.isArray(state.job.runProgress.publicThink) ? state.job.runProgress.publicThink : [];
  const note = String(state.job.runProgress.publicNote || "").trim();
  const error = String(state.job.runProgress.streamError || "").trim();
  if (state.job.runProgress.needsHumanVerification) {
    stream.textContent = "等待人工验证。请在常驻浏览器里完成验证，完成后系统会继续。";
    stream.classList.remove("empty");
    return;
  }
  if (think.length) {
    stream.innerHTML = think.map((item) => {
      const stage = escapeHtml(item.stage || "处理进度");
      const text = escapeHtml(item.text || "");
      return `<p><b>${stage}</b><span>${text}</span></p>`;
    }).join("");
    stream.classList.remove("empty");
    return;
  }
  if (note) {
    stream.textContent = note;
    stream.classList.remove("empty");
    return;
  }
  stream.textContent = error ? `执行日志：${error.slice(-800)}` : "等待公开导演进度...";
  stream.classList.add("empty");
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
  const row = state.campaign.campaigns.find((campaign) => campaign.campaign_id === campaignId);
  return row?.title || row?.name || campaignId;
}

function scrollActiveFeed() {
  if (!state.ui.autoScroll) return;
  const feed = $(`${state.ui.activePanel}Tab`);
  if (feed) feed.scrollTop = feed.scrollHeight;
}

function scrollStoryToBottom(force = false) {
  const feed = $("storyTab");
  if (!feed) return;
  if (force || state.ui.activePanel === "story" || state.ui.autoScroll) {
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
  const playerName = state.campaign.frontendState?.character_card?.name || $("characterName")?.textContent || "";
  const entityKey = canonicalEntityKeyForBlock(block) || makeEntityKey(role, displaySpeaker(block) || block.actor_id || role);
  const canonicalRole = normalizeVisualRole(roleFromEntityKey(entityKey) || role);
  const speakerName = canonicalRole === "player" ? playerName : "";
  const resolved = resolveVisualAsset({
    name: speakerName || displaySpeaker(block) || block.speaker || block.actor_id || role,
    actor_id: block.actor_id,
    avatar_key: block.avatar_key,
    actor_kind: canonicalRole,
    type: canonicalRole,
    role: canonicalRole,
    entity_key: entityKey,
  });
  if (resolved.url) {
    if (targetImage) {
      targetImage.dataset.assetKey = resolved.asset_key || "";
      targetImage.dataset.campaignId = state.campaign.activeCampaign || "";
      targetImage.dataset.fallbackSeed = resolved.fallback_seed || resolved.entity_key || "";
    }
    setAssetImage(targetImage, resolved.url);
    return;
  }
  const actorKey = resolved.entity_key || entityKey || block.avatar_key || block.actor_id || block.speaker || canonicalRole;
  const actorSeed = scopedSeed(resolved.fallback_seed || actorKey);
  const canvas = createAssetCanvas(canonicalRole === "companion" ? 160 : 96, canonicalRole === "companion" ? 160 : 96);

  let kind, draw;
  if (canonicalRole === "companion") {
    const companion = visibleCompanion();
    const visualProfile = buildCompanionVisualProfile(companion || { name: actorKey }, state.campaign.lastCampaignState || {}, {}, {});
    const companionSeed = scopedSeed(resolved.fallback_seed || companion?.seed || companion?.name || actorKey);
    kind = "companion_portrait";
    draw = () => drawCompanionToCanvas(canvas, companionSeed, visualProfile.companion_type_preset || "custom", visualProfile);
    if (state.campaign.activeCampaign) {
      cacheCanvasAsset({
        canvas,
        targetImage,
        kind,
        subdir: "portraits",
        objectId: slugify(resolved.entity_key || companion?.name || actorKey),
        seedText: companionSeed,
        metadata: {
          title: companion?.name || resolved.display_name || actorKey,
          display_name: companion?.name || resolved.display_name || actorKey,
          role: "companion",
          runtime_role: "companion",
          companion_type: visualProfile.companion_type_raw,
          companion_type_raw: visualProfile.companion_type_raw,
          companion_type_preset: visualProfile.companion_type_preset,
          archetype: companion?.meta?.archetype || companion?.archetype || companion?.meta?.kind || "",
          species: companion?.meta?.species || "",
          visual_profile: visualProfile,
          entity_key: resolved.entity_key || makeEntityKey("companion", companion?.name || actorKey),
          avatar_key: resolved.entity_key || makeEntityKey("companion", companion?.name || actorKey),
          portrait_asset_kind: "companion_portrait",
          gallery_category: "hidden",
          visible_in_gallery: false,
          not_in_gallery_filters: true,
          display_slot: "companion_card",
          detail_slot: "companion_detail",
          render_tier: "companion",
          source_size: 512,
          detail_level: "high",
        },
        draw,
      });
      return;
    }
  } else if (canonicalRole === "npc") {
    kind = resolved.asset_kind || "npc_portrait";
    draw = () => drawPixelActorPortrait(actorSeed, { cache: false, role: "npc", canvas, targetImage: null });
  } else {
    kind = resolved.asset_kind || "player_portrait";
    draw = () => drawPixelActorPortrait(actorSeed, { cache: false, role: "player", canvas, targetImage: null });
  }

  if (state.campaign.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      targetImage,
      kind,
      subdir: "portraits",
      objectId: slugify(actorKey),
      seedText: actorSeed,
      metadata: {
        title: resolved.display_name || actorKey,
        display_name: resolved.display_name || actorKey,
        role: resolved.role,
        runtime_role: resolved.role,
        entity_key: resolved.entity_key,
        avatar_key: resolved.entity_key,
        portrait_asset_kind: kind,
        gallery_category: resolved.role === "player" ? "hidden" : "npc",
        not_in_gallery_filters: resolved.role === "player",
        render_tier: resolved.role === "player" ? "player" : "npc",
        source_size: resolved.role === "player" ? 512 : 256,
        detail_level: resolved.role === "player" ? "high" : "standard",
        visible_in_gallery: resolved.visible_in_gallery,
      },
      draw,
    });
    return;
  }
  draw();
  setAssetImage(targetImage, canvas.toDataURL("image/png"));
}

function isCurrentGeneratorAssetUrl(url = "") {
  const text = String(url || "");
  if (!text || /cg_feedback|manual_cg|formal_cg|_VCG|:VCG/i.test(text)) return true;
  const match = text.match(/[_-]v(\d+)\.png/i) || text.match(/[?&]v=(\d+)/i);
  return !match || Number(match[1]) === ASSET_GENERATOR_VERSION;
}

function formalPortraitFeedbackAsset(actorKey = "", speaker = "", role = "") {
  const names = new Set([actorKey, speaker].map(normalizeActorName).filter(Boolean));
  if (!names.size) return null;
  const roleKinds = role === "player"
    ? new Set(["portrait", "player_portrait"])
    : role === "companion"
      ? new Set(["companion", "companion_portrait"])
      : new Set(["npc_portrait"]);
  const candidates = (state.assets.cachedAssets || []).filter((asset) => {
    if (!isAssetForCurrentCampaign(asset)) return false;
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

function drawPixelActorPortrait(seedText, options = {}) {
  const role = normalizeVisualRole(options.role || "npc");
  const canvas = options.canvas || createAssetCanvas(["player", "companion"].includes(role) ? 192 : 96, ["player", "companion"].includes(role) ? 192 : 96);
  const targetImage = options.targetImage === undefined ? $("avatarImage") : options.targetImage;
  const effectiveSeed = options.seedText || scopedSeed(`${state.campaign.activeCampaign}:${seedText}:${role}`);
  const kind = options.kind || assetKindForRole(role);
  const visualProfile = options.visualProfile || {};
  if (options.cache && state.campaign.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      targetImage,
      kind,
      subdir: "portraits",
      objectId: options.objectId || slugify(seedText),
      seedText: effectiveSeed,
      metadata: options.metadata || {
        title: String(seedText || role),
        display_name: String(seedText || role),
        role,
        runtime_role: role,
        entity_key: makeEntityKey(role, seedText),
        avatar_key: makeEntityKey(role, seedText),
        portrait_asset_kind: kind,
        gallery_category: role === "player" || role === "companion" ? "hidden" : "npc",
        visible_in_gallery: role !== "player" && role !== "companion",
        not_in_gallery_filters: role === "player" || role === "companion",
        display_slot: role === "player" ? "main_character_card" : role === "companion" ? "companion_card" : "dossier_gallery",
        detail_slot: role === "player" ? "main_character_detail" : role === "companion" ? "companion_detail" : "dossier_detail",
        render_tier: role === "player" ? "player" : role === "companion" ? "companion" : "npc",
        source_size: role === "player" || role === "companion" ? 512 : 256,
        detail_level: role === "player" || role === "companion" ? "high" : "standard",
      },
      draw: () => drawPixelActorPortrait(effectiveSeed, { cache: false, role, canvas, targetImage: null, visualProfile }),
    });
    return;
  }
  if (role === "player") {
    drawHighSpecPlayerPortraitToCanvas(canvas, effectiveSeed, visualProfile);
  } else {
    drawPixelPortraitToCanvas(canvas, effectiveSeed, role);
  }
  if (targetImage) setAssetImage(targetImage, canvas.toDataURL("image/png"));
}

function drawPixelCompanionPortrait(seedText, options = {}) {
  return drawCompanionAvatar(seedText, options);
}

function drawPixelItemIcon(seedText, options = {}) {
  const canvas = options.canvas || createAssetCanvas(128, 128);
  const targetImage = options.targetImage || null;
  const asset = options.asset || { title: seedText, detail: "", kind: "item", seed: seedText };
  if (options.cache && state.campaign.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      targetImage,
      kind: "item_icon",
      subdir: "items",
      objectId: options.objectId || slugify(seedText),
      seedText: options.seedText || scopedSeed(seedText),
      metadata: options.metadata || {
        title: asset.title || seedText,
        display_name: asset.title || seedText,
        role: "",
        entity_key: `item:${slugify(asset.title || seedText)}`,
        visible_in_gallery: true,
        visual_prompt: asset.visualPrompt || asset.visual_prompt || normalizeDirectorItemVisualPrompt(asset),
      },
      draw: () => drawCanvasItem(canvas, asset),
    });
    return;
  }
  drawCanvasItem(canvas, asset);
  if (targetImage) setAssetImage(targetImage, canvas.toDataURL("image/png"));
}

function drawPixelSystemIcon(kind = "system") {
  const canvas = createAssetCanvas(96, 96);
  drawIconBase(canvas.getContext("2d"), canvas.width, canvas.height, "#d9d0be", "#6f6252");
  return canvas.toDataURL("image/png");
}

function drawPixelFallbackAvatar(seedText, options = {}) {
  return drawPixelActorPortrait(seedText, { ...options, role: options.role || "npc", cache: false });
}

function drawHighSpecPlayerPortraitToCanvas(canvas, seedText, visualProfile = {}) {
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(`player-high:${seedText}:${stableJson(visualProfile || {})}`);
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
  const text = normalizeActorName(stableJson(visualProfile || {}));
  const palette = playerPortraitPalette(seed, visualProfile);
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, size, size);
  drawStoryContextBackdrop(canvas, `${seedText}:${stableJson(visualProfile || {})}`, palette.bg, 32);
  if (/森林|forest|leaf|wood|moss/.test(text)) {
    px(2, 5, 5, 2, "rgba(84,116,67,.42)");
    px(25, 7, 4, 2, "rgba(84,116,67,.38)");
    px(4, 9, 2, 8, "rgba(92,70,42,.28)");
  }
  if (/神殿|遗迹|ruin|temple|ancient|triangle/.test(text)) {
    px(23, 5, 5, 1, "rgba(177,145,76,.45)");
    px(24, 6, 1, 6, "rgba(143,116,72,.38)");
    px(28, 6, 1, 6, "rgba(143,116,72,.38)");
    px(25, 8, 3, 1, "rgba(230,201,124,.46)");
  }
  px(5, 28, 22, 2, "rgba(76, 58, 39, .28)");
  const skin = palette.skin;
  const hair = palette.hair;
  const cloth = palette.cloth;
  const cloak = palette.cloak;
  const leather = palette.leather;
  const accent = palette.accent;
  const hood = /斗篷|cloak|hood|mystery|shadow|阴影/.test(text);
  const investigator = /调查|侦探|notebook|lantern|旧案|detective|investigation/.test(text);
  const magic = /魔法|法术|灵|magic|spell|glow|arcane/.test(text);
  const adventurer = /剑|盾|冒险|勇者|sword|shield|adventure|hero|knight/.test(text);
  if (hood) {
    px(8, 3, 16, 8, cloak);
    mirror(7, 8, 3, 8, cloak);
  } else {
    px(10, 3, 12, 3, hair);
    px(9, 5, 14, 3, hair);
    mirror(8, 7, 3, 4, hair);
  }
  px(10, 7, 12, 8, skin);
  mirror(9, 9, 2, 4, shadeColor(skin, -18));
  px(12, 9, 8, 3, shadeColor(skin, 18));
  mirror(12, 10, 2, 1, "#101615");
  px(15, 12, 2, 1, "#805338");
  px(13, 14, 6, 1, "#4e2c24");
  px(9, 16, 14, 9, cloth);
  px(10, 16, 12, 2, accent);
  px(12, 19, 8, 5, shadeColor(cloth, -12));
  mirror(6, 17, 4, 8, leather);
  if (hood || adventurer) {
    px(7, 16, 18, 3, cloak);
    px(8, 19, 3, 8, cloak);
    px(21, 19, 3, 8, cloak);
  }
  px(8, 24, 6, 5, "#3a3329");
  px(18, 24, 6, 5, "#3a3329");
  px(7, 29, 7, 1, "#25221d");
  px(18, 29, 7, 1, "#25221d");
  if (adventurer) {
    px(23, 12, 2, 13, accent);
    px(24, 11, 1, 3, "#efe0ad");
    px(5, 20, 4, 5, shadeColor(accent, -18));
  }
  if (investigator) {
    px(22, 18, 4, 5, "#d8c49a");
    px(23, 19, 2, 1, "#725d3b");
    px(6, 11, 2, 6, "#e8c875");
    px(5, 16, 4, 3, "rgba(230,190,90,.52)");
  }
  if (magic) {
    px(25, 9, 2, 2, "rgba(141,202,230,.75)");
    px(27, 7, 1, 1, "rgba(225,245,255,.9)");
    px(4, 12, 1, 1, "rgba(141,202,230,.65)");
    px(14, 17, 4, 1, "rgba(141,202,230,.55)");
  }
}

function playerPortraitPalette(seed, visualProfile = {}) {
  const text = normalizeActorName(stableJson(visualProfile || {}));
  const rows = [
    { bg: "#d8c7a8", skin: "#d7a06c", hair: "#2b241c", cloth: "#385046", cloak: "#2f483b", leather: "#7b5734", accent: "#d2b56b" },
    { bg: "#d3ccb7", skin: "#c48a5c", hair: "#463423", cloth: "#314c5d", cloak: "#253947", leather: "#65452b", accent: "#9fb7c7" },
    { bg: "#d6c2a5", skin: "#e0b17d", hair: "#1d2528", cloth: "#4a3e58", cloak: "#302b45", leather: "#8a623b", accent: "#b66c45" },
  ];
  const base = { ...rows[Math.abs(seed) % rows.length] };
  if (/森林|forest|leaf|moss/.test(text)) Object.assign(base, { bg: "#c8d0ad", cloth: "#385a3f", cloak: "#2e4935", accent: "#c7b86a" });
  if (/调查|侦探|horror|detective|investigation/.test(text)) Object.assign(base, { bg: "#c7beb0", cloth: "#3f464b", cloak: "#2d3034", accent: "#d0a24d" });
  if (/魔法|magic|spell|arcane/.test(text)) Object.assign(base, { cloth: "#3b4264", cloak: "#2f3158", accent: "#8dcade" });
  return base;
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
  if (options.cache && state.campaign.activeCampaign) {
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
  drawStoryContextBackdrop(canvas, seedText, bg, 32);
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
}

function drawStoryContextBackdrop(canvas, seedText, baseColor = "#d8c7a8", cells = 32) {
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(`story-bg:${state.campaign.activeCampaign}:${currentStoryVisualContext()}:${seedText}`);
  const cell = canvas.width / cells;
  const fill = (x, y, w, h, color) => {
    ctx.fillStyle = color;
    ctx.fillRect(Math.round(x * cell), Math.round(y * cell), Math.ceil(w * cell), Math.ceil(h * cell));
  };
  ctx.fillStyle = baseColor;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  const context = `${currentStoryVisualContext()} ${state.campaign.activeCampaign}`.toLowerCase();
  const night = /夜|雨|黑|暗|shadow|night|rain/.test(context) || ((seed >>> 4) & 1);
  const warm = /店|灯|市|火|market|light/.test(context) || ((seed >>> 6) & 1);
  fill(0, 0, cells, Math.max(7, Math.floor(cells * .36)), night ? "rgba(34,42,54,.42)" : "rgba(225,215,194,.58)");
  fill(0, Math.floor(cells * .68), cells, Math.ceil(cells * .32), night ? "rgba(55,49,45,.34)" : "rgba(128,104,76,.18)");
  if (warm) {
    fill(Math.floor(cells * .68), Math.floor(cells * .12), Math.floor(cells * .18), Math.floor(cells * .22), "rgba(218,161,68,.42)");
    fill(Math.floor(cells * .73), Math.floor(cells * .16), Math.max(1, Math.floor(cells * .04)), Math.floor(cells * .16), "rgba(255,230,150,.65)");
  }
  if (/门|巷|街|gate|door|alley|street/.test(context)) {
    fill(Math.floor(cells * .08), Math.floor(cells * .18), Math.floor(cells * .2), Math.floor(cells * .56), "rgba(83,64,48,.32)");
    fill(Math.floor(cells * .11), Math.floor(cells * .23), Math.max(1, Math.floor(cells * .03)), Math.floor(cells * .43), "rgba(36,32,30,.28)");
  }
  if (/水|雨|water|rain/.test(context)) {
    fill(0, Math.floor(cells * .76), cells, Math.max(2, Math.floor(cells * .08)), "rgba(70,93,103,.28)");
    for (let i = 0; i < 5; i += 1) fill((seed >>> (i * 3)) % cells, Math.floor(cells * (.8 + i * .025)), Math.floor(cells * .22), 1, "rgba(210,225,221,.28)");
  }
}

function drawCompanionAvatar(seedText, options = {}) {
  const canvas = options.canvas || createAssetCanvas(192, 192);
  const targetImage = options.targetImage === undefined ? $("companionImage") : options.targetImage;
  const effectiveSeed = options.seedText || seedText;
  const visualProfile = options.visualProfile || buildCompanionVisualProfile({ name: seedText, meta: options.metadata || {}, archetype: options.archetype }, state.campaign.lastCampaignState || {}, {}, {});
  const profileHash = visualProfileHash(visualProfile);
  const metadata = {
    ...(options.metadata || {
      title: String(seedText || "companion"),
      display_name: String(seedText || "companion"),
      role: "companion",
      runtime_role: "companion",
      companion_type: visualProfile.companion_type_raw,
      companion_type_raw: visualProfile.companion_type_raw,
      companion_type_preset: visualProfile.companion_type_preset,
      archetype: options.archetype || "",
      species: options.species || "",
      entity_key: makeEntityKey("companion", seedText),
      avatar_key: makeEntityKey("companion", seedText),
      portrait_asset_kind: "companion_portrait",
      gallery_category: "hidden",
      visible_in_gallery: false,
      not_in_gallery_filters: true,
      display_slot: "companion_card",
      detail_slot: "companion_detail",
      render_tier: "companion",
      source_size: 512,
      detail_level: "high",
    }),
    visual_profile: visualProfile,
    visual_profile_hash: profileHash,
    portrait_spec_version: PORTRAIT_SPEC_VERSION,
    visual_spec: "story_linked_canvas_portrait",
    variant: (options.metadata && options.metadata.variant) || `vp_${profileHash}`,
  };
  if (options.cache && state.campaign.activeCampaign) {
    cacheCanvasAsset({
      canvas,
      targetImage,
      kind: options.kind || "companion_portrait",
      subdir: "portraits",
      objectId: options.objectId || slugify(seedText),
      seedText: effectiveSeed,
      metadata,
      draw: () => drawCompanionToCanvas(canvas, effectiveSeed, options.archetype, visualProfile),
    });
    return;
  }
  drawCompanionToCanvas(canvas, effectiveSeed, options.archetype, visualProfile);
  if (targetImage) setAssetImage(targetImage, canvas.toDataURL("image/png"));
}

function drawCompanionToCanvas(canvas, seedText, archetype = "", visualProfile = {}) {
  drawHighSpecCompanionToCanvas(canvas, seedText, archetype || visualProfile.companion_type_preset || "custom", visualProfile);
}

function drawHighSpecCompanionToCanvas(canvas, seedText, archetype = "", visualProfile = {}) {
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(`${seedText}:${JSON.stringify(visualProfile || {})}`);
  const cell = canvas.width / 32;
  const px = (x, y, w, h, color) => {
    ctx.fillStyle = color;
    ctx.fillRect(Math.round(x * cell), Math.round(y * cell), Math.ceil(w * cell), Math.ceil(h * cell));
  };
  const palette = companionPalette(seed, visualProfile);
  drawCompanionBackdrop(ctx, canvas.width, canvas.height, palette);
  const text = normalizeActorName([
    archetype,
    visualProfile.companion_type_preset,
    visualProfile.companion_type_raw,
    visualProfile.body_form,
    ...(visualProfile.body_structure || []),
    ...(visualProfile.species_or_origin || []),
    ...(visualProfile.material_traits || []),
    ...(visualProfile.background_markers || []),
    ...(visualProfile.relationship_markers || []),
    ...(visualProfile.temperament || []),
  ].join(" "));
  if (/palico|felyne|cat|feline|猫|艾露/.test(text)) {
    drawFelineCompanion(px, palette);
  } else if (/mechanical|construct|robot|drone|ai|android|mecha|机械|构装|无人机|机器人|metal|sensor/.test(text)) {
    drawMechanicalCompanion(px, palette);
  } else if (/vehicle|ship|bike|car|mount|载具|船|车|坐骑/.test(text)) {
    drawVehicleCompanion(px, palette);
  } else if (/familiar|spirit|ghost|wisp|summon|灵|魔宠|使魔|召唤|shadow|mist|glow/.test(text)) {
    drawSpiritCompanion(px, palette, seed);
  } else if (/quadruped|animal|deer|wolf|hound|bird|beast|动物|兽|鹿|狼|鸟/.test(text)) {
    drawAnimalCompanion(px, palette);
  } else {
    drawCustomHumanoidCompanion(px, palette, seed, visualProfile);
  }
  drawCompanionProfileMarks(px, visualProfile, palette);
}

function companionPalette(seed, visualProfile = {}) {
  const text = normalizeActorName(stableJson(visualProfile || {}));
  const presets = [
    ["#2d3242", "#c9b37e", "#6f8f9c", "#f1e6c8"],
    ["#2f2838", "#9c7ec9", "#c2d58a", "#f4e9f2"],
    ["#243536", "#80b59c", "#d8c07a", "#edf4df"],
    ["#342b25", "#c6845a", "#6d7e9c", "#f4dfc5"],
  ];
  const row = presets[seed % presets.length];
  if (String(visualProfile.body_form || "").toLowerCase().includes("mechanical")) return ["#27323a", "#8fb0bf", "#d8edf2", "#f0c86a"];
  if (/forest|森林|leaf|wood/.test(text)) return ["#243536", "#80b59c", "#d8c07a", "#edf4df"];
  if (/spirit|灵|magic|glow|命运/.test(text)) return ["#272b42", "#8aa5d9", "#d8c07a", "#f3f1ff"];
  if (/guide|向导|伙伴|relationship/.test(text)) return ["#342b25", "#c6845a", "#86a66b", "#f4dfc5"];
  return row;
}

function drawCompanionBackdrop(ctx, w, h, palette) {
  ctx.clearRect(0, 0, w, h);
  const grad = ctx.createLinearGradient(0, 0, w, h);
  grad.addColorStop(0, palette[0]);
  grad.addColorStop(1, shadeColor(palette[0], 22));
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = "rgba(255,255,255,.08)";
  ctx.fillRect(w * .12, h * .12, w * .76, h * .08);
  ctx.fillRect(w * .2, h * .82, w * .6, h * .05);
}

function drawFelineCompanion(px, p) {
  px(11, 7, 4, 6, p[1]); px(17, 7, 4, 6, p[1]);
  px(12, 9, 2, 3, "#e9b7a3"); px(18, 9, 2, 3, "#e9b7a3");
  px(9, 12, 14, 12, p[3]);
  px(8, 20, 16, 8, p[1]);
  px(12, 16, 2, 2, "#1f2024"); px(18, 16, 2, 2, "#1f2024");
  px(15, 18, 2, 1, "#5d3c3c");
  px(7, 18, 5, 1, p[2]); px(20, 18, 5, 1, p[2]);
  px(6, 23, 5, 3, p[2]); px(21, 23, 5, 3, p[2]);
  px(22, 25, 5, 2, p[3]);
}

function drawMechanicalCompanion(px, p) {
  px(8, 10, 16, 12, p[1]);
  px(10, 12, 12, 8, "#5b6f7d");
  px(13, 14, 3, 2, p[2]); px(18, 14, 3, 2, p[3]);
  px(6, 22, 20, 5, "#42515b");
  px(7, 27, 4, 3, p[1]); px(21, 27, 4, 3, p[1]);
  px(5, 14, 3, 2, p[3]); px(24, 14, 3, 2, p[3]);
}

function drawVehicleCompanion(px, p) {
  px(5, 17, 22, 8, p[1]);
  px(9, 13, 12, 5, p[2]);
  px(7, 24, 5, 5, "#22262b"); px(20, 24, 5, 5, "#22262b");
  px(8, 25, 3, 3, p[3]); px(21, 25, 3, 3, p[3]);
  px(23, 15, 4, 2, p[3]);
}

function drawSpiritCompanion(px, p, seed) {
  px(12, 8, 8, 3, "rgba(255,255,255,.22)");
  px(9, 11, 14, 13, p[2]);
  px(11, 14, 10, 11, shadeColor(p[2], 34));
  px(13, 16, 2, 2, p[0]); px(18, 16, 2, 2, p[0]);
  px(10, 25, 12, 2, "rgba(255,255,255,.22)");
  for (let i = 0; i < 5; i += 1) px((seed >>> (i * 3)) % 26 + 3, 6 + i * 4, 1, 1, p[3]);
}

function drawAnimalCompanion(px, p) {
  px(8, 16, 15, 8, p[1]);
  px(19, 12, 7, 7, p[3]);
  px(21, 9, 2, 4, p[3]); px(24, 9, 2, 4, p[3]);
  px(23, 15, 1, 1, "#1d1e22");
  px(9, 24, 3, 5, p[0]); px(18, 24, 3, 5, p[0]);
  px(5, 17, 5, 2, p[2]);
}

function drawCustomHumanoidCompanion(px, p, seed, visualProfile = {}) {
  const hood = /assassin|shadow|mask|暗|影/.test(normalizeActorName(JSON.stringify(visualProfile)));
  px(11, 7, 10, 6, hood ? p[0] : p[2]);
  px(10, 12, 12, 9, hood ? "#2b2b34" : p[3]);
  px(13, 15, 2, 2, hood ? p[3] : p[0]); px(18, 15, 2, 2, hood ? p[3] : p[0]);
  px(8, 21, 16, 9, p[1]);
  px(7, 18, 3, 10, p[2]); px(22, 18, 3, 10, p[2]);
  if (seed % 2) px(24, 12, 2, 14, p[3]); else px(6, 12, 2, 14, p[3]);
}

function drawCompanionProfileMarks(px, visualProfile = {}, p) {
  const gear = normalizeProfileList(visualProfile.costume_or_equipment || "").join(" ").toLowerCase();
  const marks = normalizeActorName([
    ...(visualProfile.background_markers || []),
    ...(visualProfile.relationship_markers || []),
    ...(visualProfile.temperament || []),
  ].join(" "));
  if (/blade|sword|knife|bow|枪|剑|刀|弓/.test(gear)) px(25, 8, 2, 17, p[3]);
  if (/goggle|visor|护目|面罩|mask/.test(gear + " " + (visualProfile.face_rules || []).join(" "))) {
    px(11, 14, 10, 2, "rgba(20,25,30,.75)");
  }
  if (/森林|forest|leaf/.test(marks)) {
    px(4, 8, 3, 1, p[2]); px(5, 7, 1, 3, p[2]);
  }
  if (/命运|fate|spirit|灵|magic/.test(marks)) {
    px(25, 6, 2, 2, p[3]); px(27, 5, 1, 1, "rgba(255,255,255,.85)");
  }
  if (/向导|guide|support|守护|protect/.test(marks)) {
    px(5, 24, 4, 3, p[3]);
  }
  px(4, 28, 24, 2, "rgba(0,0,0,.22)");
}

function drawPixelMap(seedText, options = {}) {
  const canvas = options.canvas || $("mapCanvas");
  if (!canvas) return;
  const effectiveSeed = options.seedText || scopedSeed(seedText);
  if (options.cache && state.campaign.activeCampaign) {
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
  const prompt = asset.visual_hint || asset.visualHint || asset.visualPrompt || asset.visual_prompt || asset.metadata?.visual_prompt || {};
  const canvasStyle = prompt.canvas_style || asset.canvas_style || asset.canvasStyle || asset.metadata?.canvas_style || {};
  const archetype = String(prompt.archetype || prompt.type || "").toLowerCase();
  const shape = String(canvasStyle.shape || archetype || "").toLowerCase();
  const keyParts = Array.isArray(canvasStyle.key_parts) ? canvasStyle.key_parts.join(" ").toLowerCase() : "";
  const iconRules = Array.isArray(canvasStyle.icon_rules) ? canvasStyle.icon_rules.join(" ").toLowerCase() : "";
  const drawingText = `${shape} ${keyParts} ${iconRules}`;
  if (/short_sword|dagger|blade|剑|短剑|刀/.test(drawingText)) return drawShortSwordIcon(ctx, canvas.width, canvas.height, seed);
  if (/lantern|lamp|灯|油灯|提灯/.test(drawingText)) return drawOilLanternIcon(ctx, canvas.width, canvas.height, seed);
  if (/pendant|amulet|relic|吊坠|护符|徽记/.test(drawingText)) return drawPendantIcon(ctx, canvas.width, canvas.height, seed);
  if (/phone|screen|device|终端|屏幕/.test(drawingText)) return drawPhoneIcon(ctx, canvas.width, canvas.height, seed);
  if (/bottle|vial|potion|药瓶|瓶/.test(drawingText)) return drawBottleIcon(ctx, canvas.width, canvas.height, seed);
  if (/document|letter|paper|book|文档|书信|纸/.test(drawingText)) return drawSignIcon(ctx, canvas.width, canvas.height, seed);
  if (/fragment|scale|material|碎片|鳞|素材/.test(drawingText)) return drawScaleIcon(ctx, canvas.width, canvas.height, seed);
  if (/box|case|chest|盒|匣/.test(drawingText)) return drawRelicBoxIcon(ctx, canvas.width, canvas.height, seed);
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
  } else if (/家传短剑|短剑|匕首|小刀|short\s*sword|dagger/i.test(text)) {
    type = "short_sword"; category = "weapon"; role = "equipment"; material = "steel_and_leather"; silhouette = "short_sword";
  } else if (/油灯|提灯|灯笼|灯油|火苗|lantern/i.test(text)) {
    type = "oil_lantern"; category = "resource"; role = "light_source"; material = "brass_glass_oil"; silhouette = "lantern";
  } else if (/三角吊坠|吊坠|护身符|符坠|pendant|relic/i.test(text)) {
    type = "pendant"; category = "relic"; role = "story_relic"; material = "old_metal"; silhouette = "pendant";
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
  return { type, archetype: type, category, role, material, silhouette, source_text: conciseTitle(text, 120) };
}

function buildImagePrompt(title = "", detail = "", kind = "item") {
  const aspectRatio = kind === "map" ? "16:9" : "1:1";
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

function drawShortSwordIcon(ctx, w, h, seed) {
  drawIconBase(ctx, w, h, "#cdb280", "#725434");
  ctx.save();
  ctx.translate(w * 0.5, h * 0.5);
  ctx.rotate(-0.72 + ((seed % 5) - 2) * 0.015);
  ctx.fillStyle = "#d9e1dc";
  ctx.strokeStyle = "#5b5f5d";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(0, -h * 0.37);
  ctx.lineTo(w * 0.085, -h * 0.02);
  ctx.lineTo(0, h * 0.12);
  ctx.lineTo(-w * 0.085, -h * 0.02);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.strokeStyle = "#eef5f1";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, -h * 0.31);
  ctx.lineTo(0, h * 0.08);
  ctx.stroke();
  ctx.fillStyle = "#8b6737";
  ctx.fillRect(-w * 0.19, h * 0.1, w * 0.38, h * 0.055);
  ctx.fillStyle = "#4f3424";
  ctx.fillRect(-w * 0.04, h * 0.13, w * 0.08, h * 0.22);
  ctx.fillStyle = "#c49a44";
  ctx.fillRect(-w * 0.06, h * 0.32, w * 0.12, h * 0.055);
  ctx.restore();
}

function drawOilLanternIcon(ctx, w, h, seed) {
  drawIconBase(ctx, w, h, "#c8ab72", "#765637");
  ctx.save();
  const cx = w * 0.5;
  const top = h * 0.22;
  ctx.strokeStyle = "#5d4630";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.arc(cx, top + h * 0.06, w * 0.16, Math.PI, 0);
  ctx.stroke();
  ctx.fillStyle = "#7c5c38";
  ctx.fillRect(cx - w * 0.17, top + h * 0.08, w * 0.34, h * 0.1);
  ctx.fillStyle = "#d8c38c";
  ctx.strokeStyle = "#60462e";
  ctx.lineWidth = 4;
  roundRectPath(ctx, cx - w * 0.19, top + h * 0.18, w * 0.38, h * 0.4, 8);
  ctx.fill();
  ctx.stroke();
  const grad = ctx.createRadialGradient(cx, top + h * 0.38, 2, cx, top + h * 0.38, w * 0.22);
  grad.addColorStop(0, "rgba(255,225,122,.95)");
  grad.addColorStop(0.5, "rgba(235,150,50,.62)");
  grad.addColorStop(1, "rgba(235,150,50,0)");
  ctx.fillStyle = grad;
  ctx.fillRect(cx - w * 0.24, top + h * 0.2, w * 0.48, h * 0.38);
  ctx.fillStyle = "#f7c85a";
  ctx.beginPath();
  ctx.moveTo(cx, top + h * 0.25);
  ctx.quadraticCurveTo(cx + w * 0.08, top + h * (0.35 + (seed % 3) * 0.01), cx, top + h * 0.48);
  ctx.quadraticCurveTo(cx - w * 0.075, top + h * 0.37, cx, top + h * 0.25);
  ctx.fill();
  ctx.fillStyle = "#684a2d";
  ctx.fillRect(cx - w * 0.22, top + h * 0.6, w * 0.44, h * 0.08);
  ctx.restore();
}

function drawPendantIcon(ctx, w, h, seed) {
  drawIconBase(ctx, w, h, "#c7b483", "#715638");
  ctx.save();
  const cx = w * 0.5;
  ctx.strokeStyle = "#59412e";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(w * 0.33, h * 0.18);
  ctx.quadraticCurveTo(cx, h * 0.36, w * 0.67, h * 0.18);
  ctx.stroke();
  ctx.fillStyle = "#b88734";
  ctx.strokeStyle = "#4f3825";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(cx, h * 0.34);
  ctx.lineTo(w * 0.72, h * 0.7);
  ctx.lineTo(w * 0.28, h * 0.7);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#e4c36b";
  ctx.beginPath();
  ctx.moveTo(cx, h * 0.44);
  ctx.lineTo(w * 0.61, h * 0.64);
  ctx.lineTo(w * 0.39, h * 0.64);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = seed % 2 ? "#75a4bf" : "#87b37a";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(cx, h * 0.58, w * 0.06, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
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
  if (!targetImage) return;
  const source = String(url || "");
  if (!source) {
    targetImage.removeAttribute("src");
    targetImage.classList.add("is-empty");
    return;
  }
  targetImage.classList.toggle("formalAsset", /cg_feedback|manual_cg|formal_cg|_VCG|:VCG/i.test(source));
  targetImage.classList.add("pixelAsset");
  targetImage.onerror = () => {
    if (targetImage.dataset.fallbackApplied === "true") {
      targetImage.removeAttribute("src");
      targetImage.classList.add("is-empty");
      return;
    }
    targetImage.dataset.fallbackApplied = "true";
    targetImage.classList.remove("formalAsset");
    targetImage.src = fallbackImageDataUrl(targetImage.dataset.fallbackSeed || targetImage.dataset.assetKey || targetImage.alt || "fallback");
  };
  targetImage.onload = () => {
    targetImage.classList.remove("is-empty");
    targetImage.dataset.fallbackApplied = "";
  };
  if (source.startsWith("/campaign-assets/")) {
    targetImage.src = `${source}${source.includes("?") ? "&" : "?"}v=${ASSET_GENERATOR_VERSION}`;
    return;
  }
  targetImage.src = source;
}

function fallbackImageDataUrl(seedText = "fallback") {
  const canvas = createAssetCanvas(96, 96);
  drawPixelFallbackAvatar(seedText, { canvas, targetImage: null, role: "npc" });
  return canvas.toDataURL("image/png");
}

function isUrlForCurrentCampaign(url = "", assetKey = "") {
  const text = String(url || "");
  if (!text) return false;
  if (text.startsWith("/campaign-assets/")) {
    return text.startsWith(`/campaign-assets/${encodeURIComponent(state.campaign.activeCampaign)}/`)
      || text.startsWith(`/campaign-assets/${state.campaign.activeCampaign}/`);
  }
  if (assetKey) {
    return String(assetKey).includes(state.campaign.activeCampaign || "") && (!state.campaign.assetSeed || String(assetKey).includes(state.campaign.assetSeed));
  }
  return !text.startsWith("/campaign-assets/");
}

function showMapEmptyState(message = "暂无区域地图") {
  const img = $("mapImage");
  const empty = $("mapEmptyState");
  if (img) {
    img.removeAttribute("src");
    img.classList.add("hidden");
    img.classList.add("is-empty");
    img.dataset.assetKey = "";
    img.dataset.campaignId = state.campaign.activeCampaign || "";
  }
  if (empty) {
    empty.classList.remove("hidden");
    const title = empty.querySelector("b");
    if (title) title.textContent = message;
  }
}

function showMapImage(url, assetKey = "") {
  const img = $("mapImage");
  const empty = $("mapEmptyState");
  if (!img || !url) return showMapEmptyState();
  img.onload = () => {
    img.classList.remove("hidden");
    img.classList.remove("is-empty");
    if (empty) empty.classList.add("hidden");
  };
  img.onerror = () => showMapEmptyState("地图加载失败");
  img.dataset.assetKey = assetKey;
  img.dataset.campaignId = state.campaign.activeCampaign || "";
  setAssetImage(img, url);
}

function clearMapPlaceholder() {
  showMapEmptyState();
}

function assetUseForCanvasKind(kind, metadata = {}) {
  const explicit = String(metadata.asset_use || "").trim();
  if (explicit) return explicit;
  const value = String(kind || "").toLowerCase();
  if (value === "map" || value === "map_image" || value.includes("gallery_map")) return "map";
  if (value === "prop" || value.includes("prop")) return "prop";
  if (value === "item" || value === "item_icon" || value.includes("item")) return "item";
  if (value === "cg" || value === "cg_image") return "cg";
  if (value.includes("portrait") || value === "character" || value === "npc") return "portrait";
  return "";
}

function galleryCategoryForAssetUse(assetUse, metadata = {}) {
  const explicit = String(metadata.gallery_category || "").trim();
  if (explicit && explicit !== "hidden") return explicit;
  return {
    portrait: "character",
    item: "item",
    prop: "prop",
    map: "map",
    cg: "cg",
  }[assetUse] || "";
}

function assetContractPayload({ key, kind, safeId, metadata = {}, dataUrl }) {
  const assetUse = assetUseForCanvasKind(kind, metadata);
  return {
    campaign_id: state.campaign.activeCampaign,
    key,
    kind: String(kind || assetUse || ""),
    id: String(metadata.id || metadata.object_id || safeId || key),
    title: String(metadata.title || metadata.display_name || safeId || key),
    detail: metadata.detail || "",
    gallery_category: galleryCategoryForAssetUse(assetUse, metadata),
    asset_use: assetUse,
    actor_role: metadata.actor_role || "unknown",
    certainty: metadata.certainty || "confirmed",
    display_zone: metadata.display_zone || (assetUse === "map" ? "map" : "gallery"),
    cache_policy: metadata.cache_policy || "stable",
    asset_subtype: metadata.asset_subtype || metadata.kind || "",
    asset_tags: Array.isArray(metadata.asset_tags) ? metadata.asset_tags : [],
    subject_key: metadata.subject_key || metadata.entity_key || "",
    display_name: metadata.display_name || metadata.title || "",
    source_type: metadata.source_type || (assetUse === "map" ? "server_canvas" : "image_api"),
    visual_contract_key: metadata.visual_contract_key || "",
    visual_contract_hash: metadata.visual_contract_hash || metadata.visual_profile_hash || "",
    filename: `${String(kind || assetUse || "asset")}_${slugify(state.campaign.assetSeed || state.campaign.activeCampaign || "seed").slice(0, 24)}_${safeId}_v${ASSET_GENERATOR_VERSION}`,
    asset_seed: state.campaign.assetSeed || undefined,
    data_url: dataUrl,
  };
}

async function cacheCanvasAsset({ canvas, targetImage, kind, subdir, objectId, seedText, metadata, draw }) {
  const campaignId = state.campaign.activeCampaign;
  const campaignSeed = state.campaign.assetSeed || campaignId || "campaign";
  const safeId = slugify(objectId || seedText || kind);
  const key = makeScopedAssetKey(kind, safeId, metadata?.variant || "default");
  const safeSeed = slugify(campaignSeed).slice(0, 24) || "seed";
  if (targetImage) {
    targetImage.dataset.assetKey = key;
    targetImage.dataset.campaignId = campaignId || "";
    targetImage.dataset.fallbackSeed = seedText || key;
  }
  if (isPlaceholderAssetRequest({ key, kind, metadata, seedText })) {
    draw();
    if (targetImage) setAssetImage(targetImage, canvas.toDataURL("image/png"));
    return;
  }
  const locked = lockedAvatarAsset(kind, safeId, metadata);
  if (locked?.url) {
    state.assets.assetCache[key] = { url: locked.url };
    setAssetImage(targetImage, locked.url);
    return;
  }
  const memory = state.assets.assetCache[key];
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
  state.assets.assetCache[key] = "pending";
  try {
    const lookup = await api(`/api/asset?campaign_id=${encodeURIComponent(campaignId)}&key=${encodeURIComponent(key)}`);
    if (lookup.exists && lookup.url) {
      if (assetMetadataReusable(metadata, lookup.entry || lookup)) {
        state.assets.assetCache[key] = { url: lookup.url };
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
      body: JSON.stringify(assetContractPayload({ key, kind, safeId, metadata: metadata || {}, dataUrl })),
    });
    state.assets.assetCache[key] = saved.url ? { url: saved.url } : null;
    setAssetImage(targetImage, saved.url || dataUrl);
    if (saved.url) updateMapImageIfNeeded(canvas, saved.url);
    if (saved.url) {
      await loadCachedAssets();
      if (state.campaign.lastCampaignState) renderGallery(state.campaign.lastCampaignState);
    }
  } catch (err) {
    console.warn("asset cache failed", err);
    state.assets.assetCache[key] = null;
    draw();
    const dataUrl = canvas.toDataURL("image/png");
    setAssetImage(targetImage, dataUrl);
    updateMapImageIfNeeded(canvas, dataUrl);
  }
}

function lockedAvatarAsset(kind, safeId, metadata = {}) {
  if (!["portrait", "npc_portrait", "companion", "companion_portrait", "monster_portrait"].includes(String(kind))) return null;
  const entityKey = metadata.entity_key || metadata.avatar_key || "";
  const portraitKind = metadata.portrait_asset_kind || kind;
  if (entityKey) {
    const locked = selectBestAvatarAsset(entityKey, portraitKind, state.assets.cachedAssets || []);
    if (locked && isVcgAvatarAsset(locked)) return locked;
  }
  return (state.assets.cachedAssets || []).find((asset) => {
    if (!isAssetForCurrentCampaign(asset)) return false;
    if (!asset?.exists || !asset.url || String(asset.kind || "") !== String(kind)) return false;
    if (assetVersionTag(asset) !== "VCG") return false;
    return Boolean(entityKey && (asset.entity_key === entityKey || asset.metadata?.entity_key === entityKey));
  }) || null;
}

function isPlaceholderAssetRequest({ key = "", kind = "", metadata = {}, seedText = "" }) {
  const text = `${key} ${kind} ${seedText} ${metadata?.title || ""} ${metadata?.source || ""} ${metadata?.status || ""}`.toLowerCase();
  if (metadata?.placeholder || metadata?.fallback || metadata?.cache_policy === "placeholder") return true;
  return /placeholder|fallback|default_trpg|empty_map|base_map/.test(text);
}

function assetMetadataReusable(requested, existing) {
  if (!requested) return true;
  if (!existing) return false;
  if (requested.visual_contract_hash || requested.visual_contract_key) {
    if (requested.visual_contract_key !== existing.visual_contract_key
      || requested.visual_contract_hash !== existing.visual_contract_hash) return false;
    if (requested.visual_profile_hash || requested.portrait_spec_version) {
      return requested.visual_profile_hash === existing.visual_profile_hash
        && requested.portrait_spec_version === existing.portrait_spec_version;
    }
    return true;
  }
  if (requested.visual_profile_hash || requested.portrait_spec_version) {
    return requested.visual_profile_hash === existing.visual_profile_hash
      && requested.portrait_spec_version === existing.portrait_spec_version;
  }
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

function visualProfileHash(profile = {}) {
  if (!profile || typeof profile !== "object" || !Object.keys(profile).length) return "";
  return Math.abs(hashSeed(stableJson(profile))).toString(16).slice(0, 10);
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
  if (url) showMapImage(url, state.map.currentMapAsset?.key || "");
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
  const seed = state.campaign.assetSeed || state.campaign.activeCampaign || "campaign";
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
