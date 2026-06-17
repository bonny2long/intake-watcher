const el = (id) => document.getElementById(id);

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = Number(bytes);
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(idx === 0 ? 0 : 1)} ${units[idx]}`;
}

function secondsToText(seconds) {
  if (!seconds && seconds !== 0) return "—";
  if (seconds < 60) return `${Math.round(seconds)} sec`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  return `${(seconds / 3600).toFixed(1)} hr`;
}

function statusClass(status, kind) {
  if (kind === "ready") return "ready";
  if ((status || "").startsWith("blocked")) return "blocked";
  return "waiting";
}

function setText(id, value) {
  el(id).textContent = value;
}

function renderPaths(config) {
  const rows = [
    ["Incoming", config.incoming_dir],
    ["Processing", config.processing_dir],
    ["Ready", config.ready_dir],
    ["Failed", config.failed_dir],
    ["Reports", config.reports_dir],
    ["Mode", `${config.mode}, stability ${secondsToText(config.stability_seconds)}`],
  ];
  el("paths").innerHTML = rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
}

function card(item, kind = "waiting") {
  const status = item.status || kind;
  const size = item.total_size_bytes !== undefined ? item.total_size_bytes : item.size_bytes;
  const fileLine = item.file_count !== undefined
    ? `${item.file_count} files · ${item.media_file_count || 0} media · ${item.temp_file_count || 0} temp`
    : `${item.kind || "item"}`;
  return `
    <article class="card">
      <h3>${escapeHtml(item.name || item.item_name || "Unnamed")}</h3>
      <div class="meta">
        <span>${escapeHtml(fileLine)}</span>
        <span>${formatBytes(size)}</span>
        <span>${escapeHtml(item.path || item.destination || "")}</span>
      </div>
      <span class="status ${statusClass(status, kind)}">${escapeHtml(status)}</span>
    </article>
  `;
}

function eventRow(event) {
  const title = event.event || event.status || "event";
  const item = event.item_name ? ` · ${event.item_name}` : "";
  const time = event.timestamp || "";
  return `<article class="event"><strong>${escapeHtml(title)}</strong>${escapeHtml(item)}<br>${escapeHtml(time)}</article>`;
}

function renderList(id, items, emptyText, kind) {
  const target = el(id);
  if (!items || items.length === 0) {
    target.className = id === "eventList" ? "events empty" : "cards empty";
    target.textContent = emptyText;
    return;
  }
  target.className = id === "eventList" ? "events" : "cards";
  target.innerHTML = items.map((item) => kind === "event" ? eventRow(item) : card(item, kind)).join("");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadDashboard() {
  const health = el("health");
  try {
    const response = await fetch("/api/dashboard", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const counts = data.counts || {};
    const items = data.items || {};

    health.className = counts.blocked || counts.failed ? "health warn" : "health ok";
    health.textContent = counts.blocked || counts.failed
      ? "Watcher is running. Some items need attention before they can move to ready."
      : "Watcher is running. No blocked items detected.";

    setText("countIncoming", counts.incoming || 0);
    setText("countWaiting", counts.waiting || 0);
    setText("countBlocked", counts.blocked || 0);
    setText("countReady", counts.ready || 0);
    setText("countFailed", counts.failed || 0);
    setText("waitingBadge", counts.waiting || 0);
    setText("blockedBadge", counts.blocked || 0);
    setText("readyBadge", counts.ready || 0);
    setText("problemBadge", (counts.processing || 0) + (counts.failed || 0));
    setText("eventBadge", counts.events || 0);

    renderPaths(data.config || {});
    renderList("waitingList", items.waiting || [], "No waiting items.", "waiting");
    renderList("blockedList", items.blocked || [], "No blocked items.", "blocked");
    renderList("readyList", items.ready || [], "Nothing ready yet.", "ready");
    renderList("problemList", [...(items.processing || []), ...(items.failed || [])], "No processing or failed items.", "blocked");
    renderList("eventList", (data.events || []).slice(-40).reverse(), "No events yet.", "event");
  } catch (error) {
    health.className = "health warn";
    health.textContent = `Could not load dashboard: ${error.message}`;
  }
}

async function runOnce() {
  const button = el("checkBtn");
  button.disabled = true;
  button.textContent = "Checking…";
  try {
    const response = await fetch("/api/run-once", { method: "POST" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await loadDashboard();
  } catch (error) {
    el("health").className = "health warn";
    el("health").textContent = `Check failed: ${error.message}`;
  } finally {
    button.disabled = false;
    button.textContent = "Check now";
  }
}

el("refreshBtn").addEventListener("click", loadDashboard);
el("checkBtn").addEventListener("click", runOnce);
loadDashboard();
setInterval(loadDashboard, 15000);
