const state = {
  campaigns: [],
  activeCampaign: "",
  selectedCampaign: "",
  polling: null,
};

const $ = (id) => document.getElementById(id);

function init() {
  drawBackground();
  drawPixelAvatar("怪猎长夜团");
  drawPixelMap("长夜据点");
  bindControls();
  refresh();
  state.polling = setInterval(refresh, 2500);
}

function bindControls() {
  $("runTurnBtn").addEventListener("click", () => runTurn());
  $("prepareBtn").addEventListener("click", () => prepareOnly());
  $("refreshBtn").addEventListener("click", () => refresh());
  $("exportBtn").addEventListener("click", () => window.open("/api/export", "_blank"));
  $("storySelectBtn").addEventListener("click", openStoryPicker);
  $("activeCampaignBtn").addEventListener("click", openStoryPicker);
  $("chapterBtn").addEventListener("click", openStoryPicker);
  $("closeStoryPicker").addEventListener("click", closeStoryPicker);
  $("storyOverlay").addEventListener("click", (event) => {
    if (event.target.id === "storyOverlay") closeStoryPicker();
  });
  document.querySelectorAll("[data-open-story-picker]").forEach((button) => {
    button.addEventListener("click", openStoryPicker);
  });
  document.querySelectorAll("[data-command]").forEach((button) => {
    button.addEventListener("click", () => runCommand(button.dataset.command));
  });
  document.querySelectorAll(".mode").forEach((button, index) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".mode").forEach((x) => x.classList.remove("active"));
      button.classList.add("active");
      if (index === 1) showPanel("director");
      else if (index === 2) runCommand("rewrite-plan");
      else if (index === 3) showPanel("logs");
      else showPanel("story");
    });
  });
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
  if (!action) return setLog("玩家行动不能为空。");
  await startJob("/api/run-turn", { action, campaign_id: state.activeCampaign });
}

async function prepareOnly() {
  const action = $("actionInput").value.trim();
  if (!action) return setLog("玩家行动不能为空。");
  await startJob("/api/prepare", { action, campaign_id: state.activeCampaign });
}

async function runCommand(name) {
  await startJob("/api/command", { name, campaign_id: state.activeCampaign });
}

async function startJob(path, payload) {
  try {
    setBusy(true);
    setLog("命令已提交，后台开始执行。");
    await api(path, { method: "POST", body: JSON.stringify(payload) });
    await refresh();
  } catch (err) {
    setBusy(false, true);
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
    setLog(err.message);
  }
}

function renderStatus(data) {
  state.campaigns = data.campaign_list || [];
  state.activeCampaign = data.active_campaign || "";
  state.selectedCampaign = state.selectedCampaign || state.activeCampaign;
  setText("campaignName", state.activeCampaign || "-");
  setText("chapterName", data.campaign_state?.recent?.current_scene?.location || "当前现场");
  drawPixelAvatar(state.activeCampaign || "TRPG");
  drawPixelMap(data.campaign_state?.recent?.current_scene?.location || state.activeCampaign || "map");

  const job = data.job || {};
  const failed = job.returncode !== null && job.returncode !== 0;
  setBusy(Boolean(job.running), failed);
  setText("jobText", job.running ? "运行中" : failed ? "已停止" : "待机");

  const cmd = job.command && job.command.length ? `\n\n$ ${job.command.join(" ")}` : "";
  const output = [job.output, job.error, cmd].filter(Boolean).join("\n");
  if (output) setLog(output);
}

function renderCampaignState(campaignState) {
  const title = campaignState.title || state.activeCampaign || "未命名跑团";
  const player = campaignState.player || {};
  const recent = campaignState.recent || {};
  setText("characterName", extractPlayerName(player) || title);
  setText("characterMeta", campaignState.genre || "身份与规则待记录");
  setText("characterXp", recent.current_scene?.immediate_pressure || "当前压力待记录");
  renderStoryCards();
  renderTaskPanel(campaignState.quests || {});
  renderMemoryPanel(campaignState);
}

function extractPlayerName(player) {
  const facts = Array.isArray(player.facts) ? player.facts.join(" ") : "";
  if (facts.includes("玩家")) return "玩家角色";
  return "";
}

function renderStoryCards() {
  const cards = document.querySelectorAll(".storyCard:not(.newStory)");
  state.campaigns.slice(0, 3).forEach((campaign, index) => {
    const card = cards[index];
    if (!card) return;
    card.classList.toggle("active", campaign.campaign_id === state.activeCampaign);
    card.querySelector("b").textContent = campaign.title || campaign.name;
    card.querySelector("small").textContent = `${campaign.status || "active"} · ${campaign.conversation || "未绑定对话"}`;
  });
}

function renderTaskPanel(quests) {
  const list = document.querySelector(".taskPanel ul");
  if (!list) return;
  const updates = quests.quest_updates || quests.facts || [];
  const rows = updates.length ? updates.slice(-3) : ["暂无任务记录"];
  list.innerHTML = "";
  rows.forEach((row, index) => {
    const li = document.createElement("li");
    const b = document.createElement("b");
    b.textContent = typeof row === "string" ? row : row.summary || row.title || JSON.stringify(row);
    const span = document.createElement("span");
    span.textContent = index < 2 ? "进行中" : "记录";
    li.append(b, span);
    list.appendChild(li);
  });
}

function renderMemoryPanel(campaignState) {
  const list = document.querySelector(".memoryPanel ul");
  if (!list) return;
  const recent = campaignState.recent?.recent_summary || [];
  const threads = campaignState.threads?.main_threads || [];
  const rows = [...recent.slice(-2), ...threads.slice(-2)].filter(Boolean).slice(-3);
  list.innerHTML = "";
  (rows.length ? rows : ["暂无近期记忆"]).forEach((row, index) => {
    const li = document.createElement("li");
    li.textContent = typeof row === "string" ? row : row.summary || row.title || row.id || JSON.stringify(row);
    const span = document.createElement("span");
    span.textContent = `${index + 1}条`;
    li.appendChild(span);
    list.appendChild(li);
  });
}

function renderOutput(output) {
  const parsed = output.parsed || {};
  renderStory(parsed.body || "暂无正文。");
  setText("choicesText", parsed.choices || "暂无选择点。");
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
    const role = index === 0 ? "gm" : index % 5 === 2 ? "player" : index % 7 === 3 ? "system" : "gm";
    card.className = `msg ${role}`;
    const badge = document.createElement("div");
    badge.className = "badge";
    badge.textContent = role === "player" ? "玩" : role === "system" ? "检" : "叙";
    const body = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = role === "player" ? "玩家行动" : role === "system" ? "系统检定" : "GM 叙述";
    const content = document.createElement("div");
    content.textContent = part;
    body.append(title, content);
    const time = document.createElement("time");
    time.textContent = `15:${String(21 + index).padStart(2, "0")}`;
    card.append(badge, body, time);
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
  state.campaigns.forEach((campaign) => {
    const button = document.createElement("button");
    button.className = campaign.campaign_id === state.selectedCampaign ? "active" : "";
    button.innerHTML = `<b>${escapeHtml(campaign.title || campaign.name)}</b><small>${escapeHtml(campaign.genre || campaign.status || "")}</small>`;
    button.addEventListener("click", () => {
      state.selectedCampaign = campaign.campaign_id;
      renderStoryPicker();
    });
    campaigns.appendChild(button);
  });
  const selected = state.campaigns.find((x) => x.campaign_id === state.selectedCampaign) || state.campaigns[0];
  if (!selected) return;
  const story = document.createElement("button");
  story.className = "active";
  story.innerHTML = `<b>${escapeHtml(selected.conversation || selected.title || selected.name)}</b><small>Project: ${escapeHtml(selected.project || "未绑定")}</small>`;
  story.addEventListener("click", () => selectCampaign(selected.campaign_id));
  stories.appendChild(story);
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
  ["story", "choices", "director", "logs"].forEach((item) => {
    const el = $(`${item}Tab`);
    if (el) el.classList.toggle("hidden", item !== name);
  });
}

function setBusy(running, error = false) {
  const pill = $("jobPill");
  pill.classList.toggle("running", running);
  pill.classList.toggle("error", !running && error);
  document.querySelectorAll("button").forEach((button) => {
    if (button.closest(".storyOverlay")) return;
    button.disabled = running;
  });
}

function setLog(text) {
  setText("logText", text || "");
}

function setText(id, text) {
  const el = $(id);
  if (el) el.textContent = text;
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

function drawPixelAvatar(seedText) {
  const canvas = $("avatarCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const seed = hashSeed(seedText);
  const size = canvas.width;
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, size, size);
  ctx.fillStyle = "#e7c996";
  ctx.fillRect(0, 0, size, size);
  const cell = 8;
  const colors = ["#2c241c", "#5f432b", "#d3a56f", "#f0d6a5", "#334044"];
  for (let y = 1; y < 11; y++) {
    for (let x = 1; x < 6; x++) {
      const bit = (seed >> ((x + y * 3) % 24)) & 1;
      const mirror = 11 - x;
      const color = colors[(x + y + seed) % colors.length];
      if (bit || (x > 2 && y > 2 && y < 9)) {
        ctx.fillStyle = color;
        ctx.fillRect(x * cell, y * cell, cell, cell);
        ctx.fillRect(mirror * cell, y * cell, cell, cell);
      }
    }
  }
  ctx.fillStyle = "#1f1b18";
  ctx.fillRect(4 * cell, 5 * cell, cell, cell);
  ctx.fillRect(7 * cell, 5 * cell, cell, cell);
  ctx.fillStyle = "#8a5d2a";
  ctx.fillRect(5 * cell, 8 * cell, 3 * cell, cell);
}

function drawPixelMap(seedText) {
  const canvas = $("mapCanvas");
  if (!canvas) return;
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
  for (let i = 0; i < 38; i++) {
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
    for (const m of marks) {
      ctx.strokeStyle = `rgba(120, 92, 55, ${m.a})`;
      ctx.beginPath();
      ctx.arc(m.x, m.y, m.r, 0, Math.PI * 1.35);
      ctx.stroke();
      m.x += m.s;
      if (m.x - m.r > window.innerWidth + 80) m.x = -m.r;
    }
    requestAnimationFrame(frame);
  }
  window.addEventListener("resize", resize);
  resize();
  frame();
}

init();
