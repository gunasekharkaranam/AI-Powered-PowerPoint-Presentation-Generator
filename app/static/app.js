// All text from the server is inserted with textContent / .value (never innerHTML).
const $ = (id) => document.getElementById(id);
const TYPES = ["bullets", "two_column", "stats", "chart", "timeline", "quote", "section"];
let planId = null, provider = null, outline = null;

function el(tag, attrs = {}, text) {
  const e = document.createElement(tag);
  Object.assign(e, attrs);
  if (text !== undefined) e.textContent = text;
  return e;
}
function showError(msg) { $("error").textContent = msg; $("error").hidden = !msg; }
function step(n) {
  [1, 2, 3].forEach((i) => { $("step" + i).hidden = i !== n; $("s" + i).classList.toggle("on", i <= n); });
}
async function api(url, body) {
  const r = await fetch(url, body ? { method: "POST", headers: { "Content-Type": "application/json" },
                                      body: JSON.stringify(body) } : {});
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Request failed (" + r.status + ")");
  return data;
}

// ---------- step 1 ----------
async function makePlan(extra = {}) {
  showError("");
  const btn = document.querySelector("#plan-form .primary");
  btn.disabled = true; btn.textContent = "Researching and planning...";
  try {
    const d = await api("/api/plan", {
      topic: $("topic").value.trim(), audience: $("audience").value, tone: $("tone").value,
      n_slides: +$("n").value, web_research: $("research").checked, ...extra,
    });
    planId = d.plan_id; provider = d.provider; outline = d.outline;
    renderOutline(); renderSources(d.sources); step(2);
  } catch (e) { showError(e.message); }
  finally { btn.disabled = false; btn.textContent = "Plan outline →"; }
}
$("plan-form").addEventListener("submit", (e) => { e.preventDefault(); makePlan(); });
$("demo").addEventListener("click", () => {
  $("topic").value = "Climate change: evidence and action";
  makePlan({ provider: "demo" });
});

// ---------- step 2: outline editor ----------
function renderOutline() {
  $("deck-title").textContent = outline.title;
  $("provider").textContent = provider === "demo" ? "demo mode" : "AI: " + provider;
  const box = $("outline");
  box.replaceChildren();
  outline.items.forEach((it, i) => {
    const row = el("div", { className: "item" });
    row.append(el("span", { className: "num" }, String(i + 1)));
    const title = el("input", { value: it.title, maxLength: 90, className: "t" });
    title.oninput = () => (it.title = title.value);
    const type = el("select");
    TYPES.forEach((t) => type.append(el("option", { value: t, selected: t === it.type }, t.replace("_", " "))));
    type.onchange = () => (it.type = type.value);
    const msg = el("input", { value: it.key_message, maxLength: 240, className: "m", placeholder: "key message" });
    msg.oninput = () => (it.key_message = msg.value);
    const tools = el("div", { className: "tools" });
    const mv = (d) => { const j = i + d; if (j < 0 || j >= outline.items.length) return;
      [outline.items[i], outline.items[j]] = [outline.items[j], outline.items[i]]; renderOutline(); };
    tools.append(el("button", { type: "button", title: "up", onclick: () => mv(-1) }, "↑"),
                 el("button", { type: "button", title: "down", onclick: () => mv(1) }, "↓"),
                 el("button", { type: "button", title: "delete",
                   onclick: () => { outline.items.splice(i, 1); renderOutline(); } }, "✕"));
    const main = el("div", { className: "fields" });
    const top = el("div", { className: "top" });
    top.append(title, type);
    main.append(top, msg);
    row.append(main, tools);
    box.append(row);
  });
}
$("add").onclick = () => {
  outline.items.push({ title: "New slide", type: "bullets", key_message: "What this slide should say" });
  renderOutline();
};
function renderSources(list) {
  $("sources-sum").textContent = `${list.length} sources found`;
  $("sources").replaceChildren(...list.map((s) => {
    const li = el("li");
    const a = el("a", { href: s.url, target: "_blank", rel: "noopener noreferrer" }, s.title);
    li.append(a);
    return li;
  }));
}

// ---------- step 3 ----------
$("build").onclick = async () => {
  showError("");
  if (!outline.items.length) return showError("Add at least one slide.");
  step(3); $("done").hidden = true; $("log").replaceChildren(el("li", {}, "Starting..."));
  try {
    const { job_id } = await api("/api/build", {
      plan_id: planId, outline, theme: $("theme").value, images: $("images").checked });
    poll(job_id);
  } catch (e) { showError(e.message); step(2); }
};

async function poll(id) {
  const j = await api("/api/jobs/" + id).catch((e) => ({ status: "error", error: e.message }));
  $("log").replaceChildren(...(j.messages || []).map((m) => el("li", {}, m)));
  if (j.status === "running") return setTimeout(() => poll(id), 1200);
  if (j.status === "error") { showError(j.error); return; }
  $("final-title").textContent = j.title;
  $("download").href = `/api/jobs/${id}/download`;
  const pv = $("previews");
  pv.replaceChildren();
  for (let i = 0; i < (j.previews || 0); i++) pv.append(el("img", { src: `/api/jobs/${id}/preview/${i}.png`, alt: "slide " + (i + 1) }));
  if (!j.previews) pv.append(el("p", { className: "hint" }, "Previews need LibreOffice on the server. Download the file to view it."));
  renderReport(j.report);
  $("done").hidden = false;
}

function renderReport(r) {
  const rows = [
    ["Score", r.score + " / 100"], ["Slides", r.slides], ["Layouts used", r.layouts_used.join(", ")],
    ["Sources found", r.sources_found], ["Content slides with a citation", r.content_slides_with_citation],
    ["Avg words per bullet", r.avg_words_per_bullet], ["Text overflows", r.text_overflows.length || "none"],
    ["Photos", r.photos], ["Speaker notes", r.speaker_notes], ["LLM attempts", r.llm_attempts],
    ["Grounding fixes", r.grounding_fixes.length ? r.grounding_fixes.join("; ") : "none needed"],
    ["Time", r.seconds + " s"],
  ];
  $("report").replaceChildren(...rows.map(([k, v]) => {
    const d = el("div", { className: "kv" });
    d.append(el("span", {}, k), el("b", {}, String(v)));
    return d;
  }));
}
$("restart").onclick = () => step(1);
