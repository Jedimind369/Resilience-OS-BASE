const state = {
  lastStatus: null,
  lastStale: null,
};

const UI_VERSION = "2026-01-06-2";

// =========================================
// ANTI-FLASHBANG: Remove preload class after load
// =========================================
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    document.body.classList.remove('preload');
  }, 100);

  // Theme toggle button
  const toggleBtn = document.getElementById('theme-toggle');
  const html = document.documentElement;
  const storageKey = 'resilience_theme';

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      if (html.classList.contains('night-mode')) {
        html.classList.remove('night-mode');
        localStorage.setItem(storageKey, 'light');
      } else {
        html.classList.add('night-mode');
        localStorage.setItem(storageKey, 'dark');
      }
    });
  }
});

const els = {
  sourceTimestamp: document.getElementById("source-timestamp"),
  localTime: document.getElementById("local-time"),
  liquidityValue: document.getElementById("liquidity-value"),
  runwayValue: document.getElementById("runway-value"),
  inflowsList: document.getElementById("inflows-list"),
  burnValue: document.getElementById("burn-value"),
  staleStatus: document.getElementById("stale-status"),
  apiMeta: document.getElementById("api-meta"),
  uiVersion: document.getElementById("ui-version"),
  cardLiquidity: document.getElementById("card-liquidity"),
  cardRunway: document.getElementById("card-runway"),
  cardInflows: document.getElementById("card-inflows"),
  cardBurn: document.getElementById("card-burn"),
  cardOffline: document.getElementById("card-offline"),
  alert: document.getElementById("nuclear-alert"),
  alertMessage: document.getElementById("alert-message"),
  offlineOllama: document.getElementById("offline-ollama"),
  offlineMac: document.getElementById("offline-mac"),
  offlineMobile: document.getElementById("offline-mobile"),
  offlineMacCard: document.getElementById("offline-mac-card"),
  offlineMobileCard: document.getElementById("offline-mobile-card"),
  offlinePromptCard: document.getElementById("offline-prompt-card"),
  copyPrompt: document.getElementById("copy-prompt"),
  copyContext: document.getElementById("copy-context"),
  promptPreview: document.getElementById("prompt-preview"),
  contextPreview: document.getElementById("context-preview"),
  runModelCheck: document.getElementById("run-model-check"),
  modelCheckStatus: document.getElementById("model-check-status"),
  modelCheckOutput: document.getElementById("model-check-output"),
  staleOverlaySub: document.getElementById("stale-overlay-sub"),
  runRefresh: document.getElementById("run-refresh"),
  runRefreshStatus: document.getElementById("run-refresh-status"),
  runRefreshLog: document.getElementById("run-refresh-log"),
  cardAi: document.getElementById("card-ai"),
  aiTier: document.getElementById("ai-tier"),
  aiSend: document.getElementById("ai-send"),
  aiPrompt: document.getElementById("ai-prompt"),
  aiMeta: document.getElementById("ai-meta"),
  aiOutput: document.getElementById("ai-output"),
  makeUsable: document.getElementById("make-usable"),
  makeUsableStatus: document.getElementById("make-usable-status"),
  makeUsableOutput: document.getElementById("make-usable-output"),
  tmPlan: document.getElementById("tm-plan"),
  tmCopy: document.getElementById("tm-copy"),
  tmStatus: document.getElementById("tm-status"),
  tmOutput: document.getElementById("tm-output"),
  opsKiwix: document.getElementById("ops-kiwix"),
  opsStorage: document.getElementById("ops-storage"),
  opsLogistics: document.getElementById("ops-logistics"),
  cardOps: document.getElementById("card-ops"),
  pwStart: document.getElementById("pw-start"),
  pwStop: document.getElementById("pw-stop"),
  pwCopy: document.getElementById("pw-copy"),
  pwStatus: document.getElementById("pw-status"),
  pwOutput: document.getElementById("pw-output"),
  memRefresh: document.getElementById("mem-refresh"),
  memStubs: document.getElementById("mem-stubs"),
  memCopy: document.getElementById("mem-copy"),
  memStatus: document.getElementById("mem-status"),
  memOutput: document.getElementById("mem-output"),
  chatPackCopy: document.getElementById("chat-pack-copy"),
  chatPackPreview: document.getElementById("chat-pack-preview"),
};

const numberFormat = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return `${numberFormat.format(value)} EUR`;
}

function formatDays(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return `${value.toFixed(2)} days`;
}

function applyTrend(el, value, isGoodIfPositive = true) {
  if (!el) {
    return;
  }
  if (value === null || value === undefined || Number.isNaN(value)) {
    el.textContent = "—";
    el.className = "trend neutral";
    return;
  }
  if (value === 0) {
    el.textContent = "±0%";
    el.className = "trend neutral";
    return;
  }

  const isPositive = value > 0;
  const colorClass = isGoodIfPositive
    ? (isPositive ? "positive" : "negative")
    : (isPositive ? "negative" : "positive");
  const arrow = isPositive ? "▲" : "▼";
  el.textContent = `${arrow} ${Math.abs(value).toFixed(1)}%`;
  el.className = `trend ${colorClass}`;
}

function showToast(message, type = "warning") {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined || Number.isNaN(bytes)) {
    return "--";
  }
  const b = Number(bytes);
  const gib = b / (1024 * 1024 * 1024);
  if (gib >= 1024) {
    return `${(gib / 1024).toFixed(2)} TiB`;
  }
  if (gib >= 1) {
    return `${gib.toFixed(1)} GiB`;
  }
  const mib = b / (1024 * 1024);
  return `${mib.toFixed(1)} MiB`;
}

function setCardState(card, stateName) {
  card.setAttribute("data-state", stateName);
}

function updateLocalTime() {
  const now = new Date();
  const text = now.toLocaleString("en-GB", { hour12: false });
  els.localTime.textContent = text;
}

function renderInflows(inflows) {
  if (!inflows || inflows.length === 0) {
    els.inflowsList.textContent = "No pending inflows.";
    return;
  }
  const lines = inflows.map((item) => {
    const amount = formatCurrency(item.amount);
    const status = item.status ? ` (${item.status})` : "";
    const expected = item.expected ? `, ${item.expected}` : "";
    return `${item.name}: ${amount}${status}${expected}`;
  });
  els.inflowsList.innerHTML = lines.map((line) => `<div>${line}</div>`).join("");
}

function escapeHtml(text) {
  const span = document.createElement("span");
  span.textContent = text == null ? "" : String(text);
  return span.innerHTML;
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Request failed: ${response.status} ${text}`);
  }
  return response.json();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollRunStatus(maxSeconds) {
  const end = Date.now() + maxSeconds * 1000;
  while (Date.now() < end) {
    const st = await fetchJson("/api/run_status");
    renderRunStatus(st);
    if (!st.running) {
      return st;
    }
    await sleep(500);
  }
  return null;
}

function renderStatus(data) {
  state.lastStatus = data;
  els.sourceTimestamp.textContent = data.source_timestamp || "--";

  const net = typeof data.net_liquidity === "number" ? data.net_liquidity : null;
  const runway = typeof data.runway_days === "number" ? data.runway_days : null;
  const burn = typeof data.monthly_burn === "number" ? data.monthly_burn : null;

  els.liquidityValue.textContent = formatCurrency(net);
  els.runwayValue.textContent = formatDays(runway);
  els.burnValue.textContent = formatCurrency(burn);

  const trends = data && data.trends ? data.trends : {};
  const daysOfData = typeof trends.days_of_data === "number" ? trends.days_of_data : 0;
  const runwayTrend = typeof trends.runway_trend === "number" ? trends.runway_trend : null;
  const liquidityTrend = typeof trends.liquidity_trend === "number" ? trends.liquidity_trend : null;
  applyTrend(els.runwayTrend, daysOfData >= 2 ? runwayTrend : null, true);
  applyTrend(els.liquidityTrend, daysOfData >= 2 ? liquidityTrend : null, true);

  if (net === null) {
    setCardState(els.cardLiquidity, "uncertain");
  } else if (net >= 0) {
    setCardState(els.cardLiquidity, "success");
  } else {
    setCardState(els.cardLiquidity, "critical");
  }

  if (runway === null) {
    setCardState(els.cardRunway, "uncertain");
  } else if (runway >= 7) {
    setCardState(els.cardRunway, "success");
  } else {
    setCardState(els.cardRunway, "critical");
  }

  setCardState(els.cardBurn, burn === null ? "uncertain" : "neutral");
  setCardState(els.cardInflows, data.pending_inflows && data.pending_inflows.length ? "success" : "neutral");

  renderInflows(data.pending_inflows || []);

  if (data.alerts && data.alerts.length) {
    const first = data.alerts[0];
    els.alertMessage.textContent = first.message || "Critical condition";
    els.alert.hidden = false;
  } else {
    els.alert.hidden = true;
  }
}

function renderStaleness(data) {
  state.lastStale = data;
  const stale = Boolean(data.stale);
  document.body.classList.toggle("stale", stale);
  const reason = data.reason ? ` (${data.reason})` : "";
  const age = typeof data.age_seconds === "number" ? formatAge(data.age_seconds) : null;
  els.staleStatus.textContent = `Staleness: ${stale ? "STALE" : "FRESH"}${age ? ` · age ${age}` : ""}${reason}`;
  if (els.staleOverlaySub) {
    const threshold = typeof data.stale_after_seconds === "number" ? Math.round(data.stale_after_seconds / 60) : 15;
    els.staleOverlaySub.textContent = stale
      ? `Data is older than ${threshold} minutes${age ? ` (age ${age})` : ""}. Proceed with caution.`
      : "Data is fresh.";
  }
}

function formatAge(ageSeconds) {
  const s = Math.max(0, Math.floor(ageSeconds));
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const mins = Math.floor((s % 3600) / 60);
  if (days > 0) {
    return `${days}d ${hours}h`;
  }
  if (hours > 0) {
    return `${hours}h ${mins}m`;
  }
  return `${mins}m`;
}

function renderRunStatus(data) {
  if (!data || !els.runRefreshStatus) {
    return;
  }
  const running = Boolean(data.running);
  const exitCode = data.exit_code;
  const label = running
    ? "running"
    : exitCode === 0
      ? "idle (last ok)"
      : exitCode === null
        ? "idle"
        : "idle (last warn)";

  const stamp = running ? data.started_at : data.ended_at || data.started_at;
  els.runRefreshStatus.textContent = `Status: ${label}${stamp ? ` · ${stamp}` : ""}`;
  if (els.runRefreshLog) {
    els.runRefreshLog.textContent = data.log_tail ? data.log_tail.slice(0, 200) : "--";
  }
}

function renderAiStatus(data) {
  if (!els.aiMeta) {
    return;
  }
  const battery = typeof data.battery_percent === "number" ? `${data.battery_percent}%` : "--";
  const plugged = data.plugged ? "plugged" : "battery";
  const ollama = (data.ollama || {}).reachable ? "on" : "off";
  const locally = (data.locally_ai || {}).reachable ? "on" : "off";
  const locallyHasModels = Array.isArray((data.locally_ai || {}).local_models) && (data.locally_ai || {}).local_models.length > 0;
  const last = data.last_run || {};
  const lastEngine = last.engine ? `${last.engine}:${last.model || "--"}` : "--";
  const locallyHint = locally === "off" && locallyHasModels
    ? " · To use MLX models: open Locally AI → enable Local API server (OpenAI-compatible) on 8080/1234."
    : "";
  els.aiMeta.textContent = `Engines: Ollama ${ollama}, LocallyAI ${locally} · Power: ${battery} (${plugged}) · Last: ${lastEngine}${locallyHint}`;
}

function setAiBusy(busy, label) {
  if (els.aiSend) {
    els.aiSend.disabled = busy;
    els.aiSend.textContent = label || (busy ? "Working..." : "Ask");
  }
  if (els.aiTier) {
    els.aiTier.disabled = busy;
  }
  if (els.aiPrompt) {
    els.aiPrompt.disabled = busy;
  }
}

async function refreshAiStatus() {
  if (!els.aiMeta) {
    return;
  }
  return fetchJson("/api/ai_status")
    .then((data) => {
      renderAiStatus(data || {});
      if (els.cardAi) {
        setCardState(els.cardAi, (data.ollama || {}).reachable ? "success" : "uncertain");
      }
    })
    .catch(() => {
      els.aiMeta.textContent = "Engines: -- (ai_status unavailable)";
      if (els.cardAi) {
        setCardState(els.cardAi, "uncertain");
      }
    });
}

let mobilePromptText = "";
let tmCommandsText = "";
let pwCommandsText = "";
let offlineContextText = "";
let memoryIndexText = "";
let chatPackText = "";

function renderOffline(data, promptText) {
  const ollama = data && data.ollama ? data.ollama : {};
  const recommended = data && data.recommended ? data.recommended : {};
  const models = Array.isArray(ollama.models) ? ollama.models : [];

  els.offlineOllama.textContent = ollama.reachable ? "reachable" : "not reachable";
  els.offlineMac.textContent = recommended.mac || models[0] || "--";
  els.offlineMobile.textContent = recommended.mobile || "--";
  els.offlineMacCard.textContent = recommended.mac || models[0] || "--";
  els.offlineMobileCard.textContent = recommended.mobile || "--";
  els.offlinePromptCard.textContent = promptText ? "ready" : "missing";

  mobilePromptText = promptText || "";
  if (els.promptPreview) {
    const preview = mobilePromptText.split("\n").slice(0, 12).join("\n");
    els.promptPreview.textContent = preview || "--";
  }

  setCardState(els.cardOffline, mobilePromptText ? "success" : "uncertain");
}

function renderOps(kiwix, missionLog) {
  if (els.opsKiwix) {
    if (!kiwix || !kiwix.ok) {
      els.opsKiwix.textContent = `Kiwix: ${kiwix && kiwix.error ? kiwix.error : "--"}`;
    } else if (kiwix.files && kiwix.files.length) {
      const newest = kiwix.newest || {};
      const size = typeof newest.size_bytes === "number" ? formatBytes(newest.size_bytes) : "--";
      els.opsKiwix.textContent = `Kiwix: ${newest.name || "--"} · ${size}`;
    } else {
      els.opsKiwix.textContent = "Kiwix: no .zim found (download not started yet?)";
    }
  }

  if (els.opsLogistics) {
    const list = missionLog && Array.isArray(missionLog.critical_logistics) ? missionLog.critical_logistics : [];
    if (!list.length) {
      els.opsLogistics.textContent = "No logistics entries.";
      return;
    }
    const lines = list.slice(0, 6).map((item) => {
      const title = escapeHtml(item.item || "--");
      const status = escapeHtml(item.status || "--");
      const deadline = escapeHtml(item.deadline || "--");
      const where = escapeHtml(item.location || "--");
      const tracking = escapeHtml(item.tracking_id || "—");
      return `<div><strong>${title}</strong><br><span>${status}</span> · <span>${deadline}</span><br><span>${where}</span> · <span>Tracking: ${tracking}</span></div>`;
    });
    els.opsLogistics.innerHTML = lines.join("<hr style=\"border:0;border-top:1px solid rgba(255,255,255,0.08);margin:10px 0;\">");
  }

  if (els.cardOps) {
    const kiwixOk = Boolean(kiwix && kiwix.ok);
    setCardState(els.cardOps, kiwixOk ? "neutral" : "uncertain");
  }
}

function renderPowerWatchdog(data) {
  if (!els.pwStatus || !els.pwOutput || !els.pwCopy) {
    return;
  }
  const ok = Boolean(data && data.ok);
  if (!ok) {
    els.pwStatus.textContent = "Status: FAIL";
    els.pwOutput.textContent = "Power Watchdog status unavailable.";
    els.pwCopy.disabled = true;
    pwCommandsText = "";
    return;
  }

  const installed = Boolean(data.installed);
  const loaded = Boolean(data.loaded);
  const last = data.last_status || {};
  const lastHit = last.last_hit_title ? `${last.last_hit_title}` : "--";
  const lastAt = last.last_hit_at ? `${last.last_hit_at}` : "--";
  const lastErr = last.last_error ? `${last.last_error}` : "";
  const checked = last.checked_sources != null ? String(last.checked_sources) : "--";
  const hits = last.hits != null ? String(last.hits) : "--";
  const stateText = loaded ? "RUNNING" : installed ? "INSTALLED" : "OFF";

  els.pwStatus.textContent = `Status: ${stateText} · checked: ${last.updated_at || "--"} · hits: ${last.hits ?? "--"}`;
  const lines = [];
  lines.push("POWER WATCHDOG");
  lines.push(`- State: ${stateText}`);
  lines.push(`- Last hit: ${lastAt}`);
  lines.push(`- Title: ${lastHit}`);
  lines.push(`- Sources checked: ${checked} · hits: ${hits}`);
  if (lastErr) {
    lines.push(`- Last error: ${lastErr}`);
  }

  if (data.stderr_tail) {
    const tail = String(data.stderr_tail).trim();
    if (tail) {
      lines.push("");
      lines.push("stderr tail (why nothing happens):");
      lines.push(tail.split("\n").slice(-6).join("\n"));
    }
  }

  const latest = last.latest_items || {};
  const sources = Object.keys(latest);
  if (sources.length) {
    lines.push("");
    lines.push("Latest headlines:");
    for (const src of sources.slice(0, 6)) {
      lines.push(`- ${src}:`);
      const items = Array.isArray(latest[src]) ? latest[src] : [];
      for (const item of items.slice(0, 4)) {
        const title = item && item.title ? String(item.title) : "--";
        const link = item && item.link ? String(item.link) : "";
        lines.push(`  - ${title}${link ? ` · ${link}` : ""}`);
      }
    }
  }
  lines.push("");
  lines.push("Setup (copy/paste):");
  const cmds = Array.isArray(data.plan_commands) ? data.plan_commands : [];
  if (cmds.length) {
    pwCommandsText = cmds.join("\n");
    els.pwCopy.disabled = false;
    for (const c of cmds) {
      lines.push(c);
    }
  } else {
    pwCommandsText = "";
    els.pwCopy.disabled = true;
    lines.push("(no commands)");
  }
  lines.push("");
  lines.push("Recent log tail:");
  if (data.log_tail) {
    lines.push(String(data.log_tail).trim());
  } else {
    lines.push("(empty)");
  }
  els.pwOutput.textContent = lines.join("\n").trim();
}

function renderStorage(data) {
  if (!els.opsStorage) {
    return;
  }
  if (!data || !data.ok) {
    els.opsStorage.textContent = `Storage: ${data && data.error ? data.error : "--"}`;
    return;
  }
  const vols = data.volumes || {};
  const k = vols.KiwixVault || {};
  const tm = vols.Jedi_OS_Backup || {};
  const free = (v) => (v && v.ok && typeof v.free_bytes === "number" ? v.free_bytes : null);
  const used = (v) => (v && v.ok && typeof v.used_bytes === "number" ? v.used_bytes : null);
  const samePool = free(k) != null && free(tm) != null && Math.abs(free(k) - free(tm)) < 1024 * 1024 * 10;

  const kiwixInv = ((data.kiwix || {}).zim_inventory) || {};
  const zimTotal = kiwixInv && typeof kiwixInv.total_bytes === "number" ? kiwixInv.total_bytes : null;
  const zimCount = kiwixInv && typeof kiwixInv.count === "number" ? kiwixInv.count : null;

  const parts = [];
  parts.push(`KiwixVault free ${formatBytes(free(k))} · used ${formatBytes(used(k))}`);
  parts.push(`TM free ${formatBytes(free(tm))} · used ${formatBytes(used(tm))}`);
  if (zimTotal != null) {
    parts.push(`ZIM ${formatBytes(zimTotal)}${zimCount != null ? ` (${zimCount} files)` : ""}`);
  }

  const minFreeGiB = 200;
  const freeGiB = free(k) != null ? free(k) / (1024 * 1024 * 1024) : null;
  const warn = freeGiB != null && freeGiB < minFreeGiB;
  const poolNote = samePool ? " · APFS shared pool" : "";
  const warnNote = warn ? " · LOW SPACE (models get cranky)" : "";
  els.opsStorage.textContent = `Storage: ${parts.join(" | ")}${poolNote}${warnNote}`;
}

async function refresh() {
  try {
    const [capabilities, status, staleness, offlineBrain, mobilePrompt, offlineContext, chatPack, memoryIndex, runStatus, kiwix, missionLog, power, storage] = await Promise.all([
      fetchJson("/api/capabilities"),
      fetchJson("/api/status"),
      fetchJson("/api/staleness"),
      fetchJson("/api/offline_brain"),
      fetchJson("/api/mobile_prompt"),
      fetchJson("/api/offline_context"),
      fetchJson("/api/new_chat_pack"),
      fetchJson("/api/memory_index"),
      fetchJson("/api/run_status"),
      fetchJson("/api/kiwix_download"),
      fetchJson("/api/mission_log"),
      fetchJson("/api/power_watchdog_status"),
      fetchJson("/api/storage_status"),
    ]);
    if (els.apiMeta) {
      const apiV = capabilities && capabilities.api_version ? String(capabilities.api_version) : "--";
      const port = capabilities && capabilities.port ? String(capabilities.port) : "--";
      els.apiMeta.textContent = `API: ${apiV} · Port: ${port}`;
    }
    renderStatus(status);
    renderStaleness(staleness);
    renderOffline(offlineBrain, (mobilePrompt || {}).text || "");
    renderOfflineContext(offlineContext || {});
    renderChatPack(chatPack || {});
    renderMemoryIndex(memoryIndex || {});
    renderRunStatus(runStatus);
    renderOps(kiwix, missionLog);
    renderPowerWatchdog(power);
    renderStorage(storage);

    // Transport Scout (New)
    const transport = await fetchJson("/api/transport");
    renderTransport(transport);

    // Connectivity Status
    const connectivity = await fetchJson("/api/connectivity");
    renderConnectivity(connectivity);

    // Crisis Intel
    const crisis = await fetchJson("/api/crisis_intel");
    renderCrisisIntel(crisis);

  } catch (error) {
    renderStaleness({ stale: true, reason: "fetch_failed" });
    if (els.apiMeta) {
      els.apiMeta.textContent = "API: offline (fetch_failed)";
    }
    showToast("Dashboard cannot reach local API. Run OMEGA_ONE_CLICK.command.", "danger");
  }
}

function renderOfflineContext(data) {
  offlineContextText = (data && data.text) ? String(data.text) : "";
  const mini = (data && data.min) ? String(data.min) : "";
  if (els.copyContext) {
    els.copyContext.disabled = !offlineContextText;
  }
  if (els.contextPreview) {
    const preview = (mini || offlineContextText).split("\n").slice(0, 18).join("\n");
    els.contextPreview.textContent = preview || "--";
  }
}

function renderChatPack(data) {
  chatPackText = (data && data.text) ? String(data.text) : "";
  if (els.chatPackCopy) {
    els.chatPackCopy.disabled = !chatPackText;
  }
  if (els.chatPackPreview) {
    const preview = (data && data.preview) ? String(data.preview) : "";
    els.chatPackPreview.textContent = preview || "--";
  }
}

function renderMemoryIndex(data) {
  const minText = (data && data.min_text) ? String(data.min_text) : "";
  memoryIndexText = minText;
  if (els.memCopy) {
    els.memCopy.disabled = !memoryIndexText;
  }
  if (els.memOutput) {
    const preview = (memoryIndexText || "--").split("\n").slice(0, 18).join("\n");
    els.memOutput.textContent = preview || "--";
  }
  if (els.memStatus) {
    const idx = data && data.index ? data.index : {};
    const cov = idx && idx.coverage ? idx.coverage : {};
    const strict = (cov && typeof cov.coverage_percent_strict === "number") ? cov.coverage_percent_strict : null;
    const strictNoStub = (cov && typeof cov.coverage_percent_strict_no_stub === "number") ? cov.coverage_percent_strict_no_stub : null;
    const textOnly = (cov && typeof cov.coverage_percent_text_only === "number") ? cov.coverage_percent_text_only : null;
    const indexed = (cov && typeof cov.coverage_percent_indexed === "number") ? cov.coverage_percent_indexed : null;
    const digested = cov && (cov.digested_files_strict != null) ? cov.digested_files_strict : null;
    const totalFiles = cov && (cov.total_files != null) ? cov.total_files : null;
    const missing = cov && (cov.binary_files_missing_companion != null) ? cov.binary_files_missing_companion : null;
    const criticalMissing = cov && (cov.critical_pending_count != null) ? cov.critical_pending_count : null;
    const gen = idx && idx.generated ? idx.generated : "--";
    const covText = (strict != null && strictNoStub != null && textOnly != null && indexed != null)
      ? `Coverage: ${strict}% strict · ${strictNoStub}% no-stub · ${textOnly}% text · ${indexed}% indexed`
      : "Coverage: --";
    const countText = (digested != null && totalFiles != null) ? `${digested}/${totalFiles} digested` : "--";
    const missingText = (missing != null) ? `Missing: ${missing}${criticalMissing ? ` (${criticalMissing} critical)` : ""}` : "Missing: --";
    els.memStatus.textContent = `Status: ${countText} · ${missingText} · ${covText} · ${gen}`;
  }
}

updateLocalTime();
setInterval(updateLocalTime, 1000);
if (els.uiVersion) {
  els.uiVersion.textContent = `UI: ${UI_VERSION}`;
}
refresh();
refreshAiStatus();
setInterval(refresh, 60000);
setInterval(refreshAiStatus, 5 * 60000);

if (els.copyPrompt) {
  els.copyPrompt.addEventListener("click", async () => {
    if (!mobilePromptText) {
      return;
    }
    try {
      await navigator.clipboard.writeText(mobilePromptText);
      els.copyPrompt.textContent = "Copied";
      setTimeout(() => {
        els.copyPrompt.textContent = "Copy Mobile Prompt";
      }, 1500);
    } catch (error) {
      els.copyPrompt.textContent = "Copy Failed";
      setTimeout(() => {
        els.copyPrompt.textContent = "Copy Mobile Prompt";
      }, 1500);
    }
  });
}

if (els.copyContext) {
  els.copyContext.addEventListener("click", async () => {
    if (!offlineContextText) {
      return;
    }
    try {
      await navigator.clipboard.writeText(offlineContextText);
      els.copyContext.textContent = "Copied";
      setTimeout(() => {
        els.copyContext.textContent = "Copy Offline Context";
      }, 1500);
    } catch (error) {
      els.copyContext.textContent = "Copy Failed";
      setTimeout(() => {
        els.copyContext.textContent = "Copy Offline Context";
      }, 1500);
    }
  });
}

if (els.chatPackCopy) {
  els.chatPackCopy.addEventListener("click", async () => {
    if (!chatPackText) {
      return;
    }
    try {
      await navigator.clipboard.writeText(chatPackText);
      els.chatPackCopy.textContent = "Copied";
      setTimeout(() => {
        els.chatPackCopy.textContent = "Copy NEW CHAT PACK";
      }, 1500);
    } catch (error) {
      els.chatPackCopy.textContent = "Copy Failed";
      setTimeout(() => {
        els.chatPackCopy.textContent = "Copy NEW CHAT PACK";
      }, 1500);
    }
  });
}

if (els.memRefresh && els.memStatus && els.memOutput) {
  const refreshMemory = async () => {
    const original = els.memRefresh.textContent;
    els.memRefresh.disabled = true;
    els.memRefresh.textContent = "Working...";
    els.memStatus.textContent = "Status: running…";
    try {
      const result = await postJson("/api/refresh_memory", {});
      renderMemoryIndex({ index: result.memory_index || {}, min_text: result.min_text || "" });
      els.memStatus.textContent = `Status: ${result.ok ? "OK" : "WARN"} · exit ${result.exit_code ?? "--"}`;
    } catch (error) {
      els.memStatus.textContent = "Status: FAIL";
      els.memOutput.textContent = "Memory refresh failed. Try Run Refresh or check server logs.";
    } finally {
      els.memRefresh.disabled = false;
      els.memRefresh.textContent = original;
    }
  };
  els.memRefresh.addEventListener("click", refreshMemory);

  if (els.memStubs) {
    els.memStubs.addEventListener("click", async () => {
      const original = els.memStubs.textContent;
      els.memStubs.disabled = true;
      els.memStubs.textContent = "Creating...";
      els.memStatus.textContent = "Status: creating stubs…";
      try {
        const result = await postJson("/api/create_summary_stubs", { limit: 0 });
        const created = (result.result && Array.isArray(result.result.created)) ? result.result.created.length : "--";
        els.memStatus.textContent = `Status: ${result.ok ? "OK" : "WARN"} · stubs ${created}`;
        await refreshMemory();
      } catch (error) {
        els.memStatus.textContent = "Status: FAIL";
        els.memOutput.textContent = "Stub creation failed. You can still add OCR/summary files manually.";
      } finally {
        els.memStubs.disabled = false;
        els.memStubs.textContent = original;
      }
    });
  }
}

if (els.memCopy) {
  els.memCopy.addEventListener("click", async () => {
    if (!memoryIndexText) {
      return;
    }
    try {
      await navigator.clipboard.writeText(memoryIndexText);
      els.memCopy.textContent = "Copied";
      setTimeout(() => {
        els.memCopy.textContent = "Copy Memory Index (MIN)";
      }, 1500);
    } catch {
      els.memCopy.textContent = "Copy Failed";
      setTimeout(() => {
        els.memCopy.textContent = "Copy Memory Index (MIN)";
      }, 1500);
    }
  });
}

if (els.runModelCheck) {
  els.runModelCheck.addEventListener("click", async () => {
    els.modelCheckStatus.textContent = "Status: running...";
    els.modelCheckOutput.textContent = "--";
    try {
      const result = await fetchJson("/api/model_check");
      const ok = result && result.ok;
      els.modelCheckStatus.textContent = `Status: ${ok ? "PASS" : "WARN"} (${result.model || "model"})`;
      els.modelCheckOutput.textContent = `OK TEST: ${result.ok_test || "--"}\nSAFETY TEST: ${result.safety_test || "--"}`;
    } catch (error) {
      els.modelCheckStatus.textContent = "Status: FAIL";
      els.modelCheckOutput.textContent = "Model check failed. Ensure Ollama is running.";
    }
  });
}

if (els.runRefresh) {
  els.runRefresh.addEventListener("click", async () => {
    const originalLabel = els.runRefresh.textContent;
    els.runRefresh.disabled = true;
    els.runRefresh.textContent = "Running...";
    els.runRefreshStatus.textContent = "Status: running...";
    if (els.runRefreshLog) {
      els.runRefreshLog.textContent = "--";
    }
    try {
      const result = await fetchJson("/api/run_once");
      renderRunStatus(result);
      await pollRunStatus(60);
    } catch (error) {
      els.runRefreshStatus.textContent = "Status: FAIL";
      if (els.runRefreshLog) {
        els.runRefreshLog.textContent = "Refresh failed. Check Ollama or logs.";
      }
    } finally {
      els.runRefresh.disabled = false;
      els.runRefresh.textContent = originalLabel;
      // Force immediate status update just in case
      refresh();
      refreshAiStatus();
    }
  });
}

if (els.makeUsable && els.makeUsableStatus && els.makeUsableOutput) {
  const run = async () => {
    const original = els.makeUsable.textContent;
    const lines = [];
    const log = (text) => {
      lines.push(text);
      els.makeUsableOutput.textContent = lines.join("\n");
    };

    const setStatus = (text) => {
      els.makeUsableStatus.textContent = `Status: ${text}`;
    };

    els.makeUsable.disabled = true;
    els.makeUsable.textContent = "Working...";
    els.makeUsableOutput.textContent = "--";
    setStatus("booting");

    log("Step 0/4: Waking up the system. If it was already awake, pretend this was intentional.");

    // Step 1: check AI engines (fast)
    setStatus("checking engines");
    log("Step 1/4: Checking local AI engines...");
    let aiStatus = null;
    try {
      aiStatus = await fetchJson("/api/ai_status");
      renderAiStatus(aiStatus);
      const ollamaOk = Boolean((aiStatus.ollama || {}).reachable);
      const locallyOk = Boolean((aiStatus.locally_ai || {}).reachable);
      log(`  - Ollama: ${ollamaOk ? "OK" : "OFF"} · Locally AI: ${locallyOk ? "OK" : "OFF"}`);
      if (!ollamaOk && !locallyOk) {
        log("  - FIX NEEDED: Start Ollama (or enable Locally AI local server).");
      }
    } catch {
      log("  - FIX NEEDED: ai_status unavailable (dashboard server mismatch or not updated).");
    }

    // Step 2: model self-check (safety + basic response)
    setStatus("model self-check");
    log("Step 2/4: Poking the model. If it hisses, we’ll know.");
    try {
      const mc = await fetchJson("/api/model_check");
      const ok = Boolean(mc && mc.ok);
      const model = mc.model || "--";
      log(`  - Model check: ${ok ? "PASS" : "WARN"} · model=${model}`);
      if (!ok) {
        log("  - FIX NEEDED: Model check failed (ensure Ollama is running and the model responds).");
      }
    } catch {
      log("  - FIX NEEDED: Model self-check failed (Ollama down or request error).");
    }

    // Step 3: run refresh in the background and wait for completion
    setStatus("refreshing");
    log("Step 3/4: Running refresh (KPI snapshot + audit). This is the part where computers contemplate life.");
    try {
      const started = await fetchJson("/api/run_once");
      renderRunStatus(started);
      const done = await pollRunStatus(75);
      if (!done) {
        log("  - FIX NEEDED: Refresh did not finish within 75s (still running).");
      } else if (done.exit_code === 0) {
        log(`  - Refresh: OK · ${done.log_tail || ""}`);
      } else {
        log(`  - FIX NEEDED: Refresh exit_code=${done.exit_code} · ${done.error || ""}`);
      }
    } catch {
      log("  - FIX NEEDED: Could not start refresh (server error).");
    }

    // Step 4: staleness check + quick UI refresh
    setStatus("final checks");
    log("Step 4/4: Verifying freshness + reloading dashboard data.");
    try {
      await refresh();
      const st = await fetchJson("/api/staleness");
      const stale = Boolean(st && st.stale);
      const age = typeof st.age_seconds === "number" ? formatAge(st.age_seconds) : "--";
      log(`  - Staleness: ${stale ? "STALE" : "FRESH"} · age ${age}`);
      if (stale) {
        log("  - FIX NEEDED: Data is stale. Run refresh again or run: python3 OS/01_SCRIPTS/update_kernel_balances.py");
      }
    } catch {
      log("  - FIX NEEDED: Could not verify staleness (API error).");
    }

    // Optional tiny AI query to confirm end-to-end
    setStatus("sanity ping");
    log("Bonus: End-to-end AI ping (ECO)...");
    try {
      const r = await postJson("/api/ai_query", { prompt: "Reply exactly with: OK", tier: "ECO" });
      if (r && r.ok && String(r.text || "").toUpperCase().includes("OK")) {
        log(`  - AI ping: OK · engine=${r.engine || "--"}:${r.model || "--"}`);
      } else {
        log("  - FIX NEEDED: AI ping failed (engine/model mismatch or timeout).");
      }
    } catch {
      log("  - FIX NEEDED: AI ping failed (ai_query error).");
    }

    log("");
    log("Need disk space for Kiwix/LLMs? Use: Free Disk Space (Time Machine) → Generate Cleanup Plan.");

    // Summary
    const fixNeeded = lines.some((l) => l.includes("FIX NEEDED"));
    setStatus(fixNeeded ? "needs fixes" : "OK");
    log("");
    log(fixNeeded ? "Result: FIX NEEDED. The system is close, but not fully usable yet." : "Result: OK. System usable. Proceed without drama.");

    els.makeUsable.disabled = false;
    els.makeUsable.textContent = original;
  };

  els.makeUsable.addEventListener("click", run);
}

if (els.tmPlan && els.tmOutput && els.tmStatus && els.tmCopy) {
  const renderTmPlan = (plan) => {
    const ok = Boolean(plan && plan.ok);
    tmCommandsText = "";
    els.tmCopy.disabled = true;
    if (!ok) {
      els.tmStatus.textContent = "Status: FAIL";
      const msg = plan && (plan.message || plan.error) ? `${plan.message || ""}\n${plan.error || ""}` : "Plan failed.";
      els.tmOutput.textContent = msg.trim() || "Plan failed.";
      return;
    }

    const total = typeof plan.total_backups === "number" ? plan.total_backups : 0;
    const deletable = typeof plan.total_deletable === "number" ? plan.total_deletable : 0;
    const keepLatest = typeof plan.keep_latest === "number" ? plan.keep_latest : 2;
    const commands = Array.isArray(plan.commands) ? plan.commands : [];

    const lines = [];
    lines.push("TIME MACHINE CLEANUP PLAN (DRY RUN)");
    lines.push(`- Found backups: ${total}`);
    lines.push(`- Deletable: ${deletable} (keeping last ${keepLatest})`);
    lines.push("");
    lines.push("Copy/paste into Terminal (will ask for your Mac password):");
    lines.push("");
    if (commands.length === 0) {
      lines.push("(Nothing to delete. Your disk hoarding is under control. For now.)");
    } else {
      for (const c of commands) {
        lines.push(c);
      }
      tmCommandsText = commands.join("\n");
      els.tmCopy.disabled = false;
    }

    els.tmStatus.textContent = `Status: OK · ${deletable} deletable`;
    els.tmOutput.textContent = lines.join("\n");
  };

  const loadPlan = async () => {
    const original = els.tmPlan.textContent;
    els.tmPlan.disabled = true;
    els.tmPlan.textContent = "Scanning...";
    els.tmCopy.disabled = true;
    els.tmStatus.textContent = "Status: scanning…";
    els.tmOutput.textContent = "--";
    try {
      const plan = await fetchJson("/api/tm_cleanup_plan");
      renderTmPlan(plan);
    } catch {
      els.tmStatus.textContent = "Status: FAIL";
      els.tmOutput.textContent = "Could not generate plan. Try again or run `tmutil listbackups` in Terminal.";
    } finally {
      els.tmPlan.disabled = false;
      els.tmPlan.textContent = original;
    }
  };

  els.tmPlan.addEventListener("click", loadPlan);
  els.tmCopy.addEventListener("click", async () => {
    if (!tmCommandsText) {
      return;
    }
    try {
      await navigator.clipboard.writeText(tmCommandsText);
      els.tmCopy.textContent = "Copied";
      setTimeout(() => {
        els.tmCopy.textContent = "Copy Commands";
      }, 1500);
    } catch {
      els.tmCopy.textContent = "Copy Failed";
      setTimeout(() => {
        els.tmCopy.textContent = "Copy Commands";
      }, 1500);
    }
  });
}

if (els.pwStart && els.pwStop && els.pwCopy && els.pwStatus && els.pwOutput) {
  const runAction = async (action) => {
    els.pwStart.disabled = true;
    els.pwStop.disabled = true;
    els.pwCopy.disabled = true;
    els.pwStatus.textContent = `Status: ${action}...`;
    try {
      await postJson("/api/power_watchdog_action", { action });
    } catch {
      // ignore; refresh will show error
    } finally {
      els.pwStart.disabled = false;
      els.pwStop.disabled = false;
      refresh();
    }
  };

  els.pwStart.addEventListener("click", () => runAction("start"));
  els.pwStop.addEventListener("click", () => runAction("stop"));
  els.pwCopy.addEventListener("click", async () => {
    if (!pwCommandsText) {
      return;
    }
    try {
      await navigator.clipboard.writeText(pwCommandsText);
      els.pwCopy.textContent = "Copied";
      setTimeout(() => {
        els.pwCopy.textContent = "Copy Setup";
      }, 1500);
    } catch {
      els.pwCopy.textContent = "Copy Failed";
      setTimeout(() => {
        els.pwCopy.textContent = "Copy Setup";
      }, 1500);
    }
  });
}

if (els.aiSend && els.aiPrompt) {
  const submit = async () => {
    const prompt = (els.aiPrompt.value || "").trim();
    if (!prompt) {
      return;
    }
    const tierRaw = els.aiTier ? els.aiTier.value : "";
    const tier = tierRaw ? tierRaw : null;
    setAiBusy(true, "Working...");
    if (els.aiOutput) {
      els.aiOutput.textContent = "--";
    }
    if (els.cardAi) {
      setCardState(els.cardAi, "neutral");
    }
    try {
      const result = await postJson("/api/ai_query", { prompt, tier });
      const ok = Boolean(result && result.ok);
      const engine = result.engine ? `${result.engine}:${result.model || "--"}` : "--";
      if (els.aiMeta) {
        els.aiMeta.textContent = `Engine: ${engine} · Tier: ${result.tier || tier || "AUTO"} · ${result.duration_s || "--"}s`;
      }
      if (els.aiOutput) {
        els.aiOutput.textContent = result.text || "(empty response)";
      }
      if (els.cardAi) {
        setCardState(els.cardAi, ok ? "success" : "critical");
      }
    } catch (error) {
      if (els.aiMeta) {
        els.aiMeta.textContent = "Engine: -- (request failed)";
      }
      if (els.aiOutput) {
        els.aiOutput.textContent = "AI request failed. Ensure Ollama is running or enable Locally AI server.";
      }
      if (els.cardAi) {
        setCardState(els.cardAi, "critical");
      }
    } finally {
      setAiBusy(false, "Ask");
      refreshAiStatus();
    }
  };

  els.aiSend.addEventListener("click", submit);
  els.aiPrompt.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      submit();
    }
  });
}

// =========================================
// AUTO-REFRESH: Keeps data fresh (60s interval)
// =========================================
setInterval(() => {
  console.log("🔄 Auto-Refreshing Dashboard Data...");
  refresh().catch((err) => {
    console.warn("Auto-refresh failed:", err);
    showToast("Verbindung verloren", "warning");
  });
}, 60000);

console.log("✅ Dashboard loaded. Auto-refresh every 60s.");

// =========================================
// TRANSPORT SCOUT (Survival Mode)
// =========================================
function renderTransport(res) {
  const container = document.getElementById("transport-checks");
  const decisionContainer = document.getElementById("hub-decision");
  if (!container || !decisionContainer) return;

  if (!res || !res.ok || !res.data) {
    container.innerHTML = '<div class="scout-loading">Transport data unavailable</div>';
    return;
  }
  const data = res.data;

  // Render Checks
  container.innerHTML = "";
  if (data.checks && Array.isArray(data.checks)) {
    for (const check of data.checks) {
      const a = document.createElement("a");
      a.className = "check-btn";
      a.href = check.url;
      a.target = "_blank";
      a.rel = "noopener";
      a.innerHTML = `
        <div class="check-name">${check.name}</div>
        <div class="check-detail">${check.critical_for}</div>
      `;
      container.appendChild(a);
    }
  }

  // Render Decision Logic
  if (data.decision_tree) {
    const hub = data.decision_tree.hub_choice || "--";
    const rules = data.decision_tree.charlottenburg_rules || [];
    let rulesHtml = "";
    for (const rule of rules) {
      rulesHtml += "<li>" + rule + "</li>";
    }
    decisionContainer.innerHTML = `
      <div class="decision-hub">🧭 ${hub}</div>
      <ul class="decision-rules">${rulesHtml}</ul>
    `;
  }
}

function renderConnectivity(res) {
  const kiwixDot = document.getElementById("conn-kiwix");
  const ollamaDot = document.getElementById("conn-ollama");
  const dashboardDot = document.getElementById("conn-dashboard");

  if (!res || !res.ok) {
    [kiwixDot, ollamaDot, dashboardDot].forEach(d => {
      if (d) d.className = "conn-dot offline";
    });
    return;
  }

  if (kiwixDot) kiwixDot.className = "conn-dot " + (res.kiwix ? "online" : "offline");
  if (ollamaDot) ollamaDot.className = "conn-dot " + (res.ollama ? "online" : "offline");
  if (dashboardDot) dashboardDot.className = "conn-dot " + (res.dashboard ? "online" : "offline");
}

function renderCrisisIntel(res) {
  const container = document.getElementById("crisis-intel");
  if (!container) return;

  if (!res || !res.ok || !res.data) {
    container.hidden = true;
    return;
  }
  container.hidden = false;
  const data = res.data;

  // Update Timestamp
  const ts = document.getElementById("crisis-ts");
  if (ts && data.timestamp) ts.textContent = "Refreshed: " + data.timestamp.split("T")[1].split(".")[0];

  // Render Alerts
  const alertsDiv = document.getElementById("crisis-alerts");
  if (alertsDiv && data.alerts) {
    alertsDiv.innerHTML = data.alerts.map(a =>
      `<div class="crisis-alert ${a.level.toLowerCase()}">${a.level}: ${a.msg}</div>`
    ).join("");
  }

  // Render Resources
  const resDiv = document.getElementById("crisis-resources");
  if (resDiv && data.resources) {
    let html = "";
    if (data.resources.warmth) {
      html += "<div class='resource-group'><div class='res-label'>WARMTH</div>";
      html += data.resources.warmth.map(w =>
        `<div class='res-item'><span>${w.loc}</span><span class='res-status ${w.status}'>${w.status} (${w.cap})</span></div>`
      ).join("");
      html += "</div>";
    }
    if (data.resources.power) {
      html += "<div class='resource-group'><div class='res-label'>POWER</div>";
      html += data.resources.power.map(p =>
        `<div class='res-item'><span>${p.loc}</span><span class='res-status ${p.status}'>${p.status}</span></div>`
      ).join("");
      html += "</div>";
    }
    resDiv.innerHTML = html;
  }
}
