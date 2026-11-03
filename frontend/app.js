// Presentation only: fetch computed data from the backend and render it.
const $ = (id) => document.getElementById(id);
const fmt = new Intl.NumberFormat();
// Chart colors come from the CSS tokens so there is one source of truth.
const palette = (from = document.documentElement) => {
  const rootStyle = getComputedStyle(from);
  return Array.from({ length: 8 }, (_, i) => rootStyle.getPropertyValue(`--chart-${i + 1}`).trim());
};
let langChart, lastProfile;

function setStatus(text, isError = false) {
  $("status").textContent = text;
  $("status").className = isError ? "status error" : "status";
  $("status").hidden = !text;
}

function el(tag, props = {}, children = []) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

function renderHeader(p) {
  lastProfile = p;
  const PALETTE = palette();
  $("avatar").src = p.avatar_url;
  $("avatar").alt = `${p.name} avatar`;
  $("name").textContent = p.name;
  $("handle").textContent = `@${p.username}`;
  $("handle").href = p.profile_url;
  $("bio").textContent = p.bio;
  $("followers").textContent = fmt.format(p.followers);
  $("stars").textContent = fmt.format(p.total_stars);
  $("repo-count").textContent = fmt.format(p.public_repos);

  const langs = p.top_languages.slice(0, 8);
  $("lang-basis").textContent = p.language_basis === "bytes" ? "by code size" : "by repo count";
  langChart?.destroy();
  langChart = new Chart($("lang-chart"), {
    type: "doughnut",
    data: {
      labels: langs.map((l) => l.language),
      datasets: [{ data: langs.map((l) => l.percent), backgroundColor: PALETTE, borderWidth: 0 }],
    },
    options: { maintainAspectRatio: false, cutout: "58%", plugins: { legend: { display: false } } },
  });
  $("lang-legend").replaceChildren(...langs.map((l, i) =>
    el("li", {}, [
      el("span", {}, [el("span", { className: "swatch", style: `background:var(--chart-${i + 1})` }), l.language]),
      el("span", { textContent: `${l.percent}%` }),
    ])
  ));
}

function renderRepos(repos, listId = "repos") {
  $(listId).replaceChildren(...repos.map((r) =>
    el("li", { className: "repo" }, [
      el("h3", {}, [el("a", { href: r.url, target: "_blank", rel: "noopener", textContent: r.name })]),
      el("p", { textContent: r.description || "No description." }),
      el("div", { className: "meta" }, [
        ...(r.language ? [el("span", { className: "lang-tag", textContent: r.language })] : []),
        el("span", { textContent: `★ ${fmt.format(r.stars)}`, title: "Stars" }),
        el("span", { textContent: `⑂ ${fmt.format(r.forks)}`, title: "Forks" }),
      ]),
    ])
  ));
}

async function loadActivity(username) {
  $("activity").hidden = true;
  const res = await fetch(`/api/contributions/${encodeURIComponent(username)}`);
  if (!res.ok) {
    // Heatmap is optional: say why it's missing instead of hiding the section.
    const err = await res.json().catch(() => ({}));
    $("heatmap").replaceChildren();
    $("activity-summary").replaceChildren(el("span", { className: "activity-error",
      textContent: `Contribution graph unavailable: ${err.detail || "GitHub didn't return activity data."}` }));
    $("activity").hidden = false;
    return;
  }
  const c = await res.json();
  // Pad so the first column starts on Sunday, like a calendar.
  const pad = new Date(c.days[0].date + "T00:00:00Z").getUTCDay();
  $("heatmap").replaceChildren(
    ...Array.from({ length: pad }, () => el("i", { style: "visibility:hidden" })),
    ...c.days.map((d) => el("i", { className: `l${d.level}`, title: `${d.count} contributions on ${d.date}` }))
  );
  $("heatmap").setAttribute("aria-label", `${c.total} contributions in the last year`);
  $("activity-summary").replaceChildren(
    el("strong", { textContent: fmt.format(c.total) }), " contributions in the last year, ",
    el("strong", { textContent: c.current_streak }), "-day current streak, ",
    el("strong", { textContent: c.longest_streak }), "-day longest streak."
  );
  $("activity").hidden = false;
}

async function loadInsights(username) {
  $("insights").hidden = true;
  const res = await fetch(`/api/insights/${encodeURIComponent(username)}`);
  if (!res.ok) return;
  const i = await res.json();
  const plural = (n, w) => `${fmt.format(n)} ${w}${n === 1 ? "" : "s"}`;
  const facts = [
    ["On GitHub since", `${i.member_since} (${i.account_age_years} years)`],
    ["Repositories", `${plural(i.original_repos, "original")}, ${plural(i.forked_repos, "fork")}`],
    ["Recently active", `${plural(i.active_30d, "repo")} updated in the last 30 days`],
    ["Inactive", `${plural(i.inactive_1y, "repo")} untouched for over a year`],
    ["Average stars", `${fmt.format(i.avg_stars_per_repo)} per repo, ${plural(i.total_forks, "fork")} in total`],
    ...(i.top_weekday ? [
      ["Most active on", `${i.top_weekday}s`],
      ["Best day", `${plural(i.best_day.count, "contribution")} on ${i.best_day.date}`],
      ["Busiest month", `${i.busiest_month.month} (${plural(i.busiest_month.count, "contribution")})`],
    ] : []),
  ];
  $("insight-list").replaceChildren(...facts.map(([k, v]) => el("div", {}, [el("dt", { textContent: k }), el("dd", { textContent: v })])));
  $("topics").replaceChildren(...i.top_topics.map((t) => el("li", { textContent: t })));
  $("topics").hidden = !i.top_topics.length;
  $("insights").hidden = false;
}

async function loadFeed(username) {
  $("feed-section").hidden = true;
  const res = await fetch(`/api/events/${encodeURIComponent(username)}`);
  if (!res.ok) return;
  const items = await res.json();
  if (!items.length) return;
  $("feed").replaceChildren(...items.map((e) => el("li", {}, [
    el("a", { href: e.repo_url, target: "_blank", rel: "noopener", textContent: e.text }),
    el("time", { dateTime: e.created_at, textContent: e.when }),
  ])));
  $("feed-section").hidden = false;
}

async function loadCompare(username, other) {
  $("compare-result").hidden = true;
  $("compare-status").className = "status";
  $("compare-status").textContent = `Comparing with ${other}…`;
  const res = await fetch(`/api/compare/${encodeURIComponent(username)}/${encodeURIComponent(other)}`);
  const c = await res.json();
  if (!res.ok) {
    $("compare-status").className = "status error";
    $("compare-status").textContent = `${c.detail || "Couldn't compare."} Check the username and try again.`;
    return;
  }
  $("cmp-a").textContent = `@${c.a.username}`;
  $("cmp-b").textContent = `@${c.b.username}`;
  const cell = (v, lead) => el("td", { className: lead ? "lead" : "", textContent: v === null ? "n/a" : fmt.format(v) });
  $("compare-rows").replaceChildren(...c.rows.map((r) => el("tr", {}, [
    el("th", { scope: "row", textContent: r.metric }), cell(r.a, r.leader === "a"), cell(r.b, r.leader === "b"),
  ])));
  const list = (xs) => (xs.length ? xs.join(", ") : "none");
  $("compare-langs").replaceChildren(
    el("strong", { textContent: "Shared languages: " }), list(c.shared_languages), el("br"),
    el("strong", { textContent: `Only @${c.a.username}: ` }), list(c.only_a), el("br"),
    el("strong", { textContent: `Only @${c.b.username}: ` }), list(c.only_b));
  $("compare-status").textContent = `@${c.a.username} leads ${c.score.a}, @${c.b.username} leads ${c.score.b} of ${c.rows.length} metrics.`;
  $("compare-result").hidden = false;
  $("compare-reset").hidden = false;
}

function resetCompare() {
  $("compare-user").value = "";
  $("compare-status").textContent = "";
  $("compare-status").className = "status";
  $("compare-result").hidden = $("compare-reset").hidden = true;
}

$("compare-reset").addEventListener("click", () => {
  resetCompare();
  $("compare-user").focus();
});

$("compare-form").addEventListener("submit", (e) => {
  e.preventDefault();
  loadCompare(currentUser(), $("compare-user").value.trim()).catch(() => {});
});

async function load(username) {
  resetCompare(); // a comparison is per visit: refresh or a new profile starts clean
  loadActivity(username).catch(() => {});
  loadFeed(username).catch(() => {});
  loadInsights(username).catch(() => {});
  $("match-badge").hidden = $("advice").hidden = true;
  setChatOpen(false);
  $("chat-log").replaceChildren(el("li", { className: "bot", textContent: `Hi! Ask me anything about ${username}'s GitHub profile.` }));
  renderSuggestions(["Which languages are used most?", "Which repo is the most popular?", "How active is this developer?"]);
  setStatus(`Loading ${username}…`);
  try {
    const res = await fetch(`/api/profile/${encodeURIComponent(username)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not load this profile.");
    renderHeader(data);
    renderRepos(data.repos);
    renderRepos(data.pinned, "pinned");
    $("pinned-section").hidden = !data.pinned.length;
    $("profile").hidden = $("repos-section").hidden = false;
    $("chat-toggle").hidden = $("print-btn").hidden = false;
    $("compare-section").hidden = false;
    setStatus("");
    history.replaceState(null, "", `?user=${encodeURIComponent(username)}`);
  } catch (err) {
    $("profile").hidden = $("repos-section").hidden = $("activity").hidden = $("insights").hidden = $("pinned-section").hidden = $("feed-section").hidden = $("compare-section").hidden = $("chat-toggle").hidden = $("print-btn").hidden = true;
    setStatus(`${err.message} Check the username and try again.`, true);
  }
}

function renderMatch(m) {
  const badge = $("match-badge");
  const inferred = m.inferred || {};
  const chipTitle = (l, base) => (inferred[l] ? `${base} (inferred from "${inferred[l]}")` : base);
  const note = Object.entries(inferred).map(([l, phrase]) => `${l} from "${phrase}"`).join(", ");
  badge.replaceChildren(
    el("span", { className: "pct", textContent: `${m.match_percent}%` }),
    el("span", { className: "label", textContent: m.message || "tech stack match" }),
    el("span", { className: "chips" }, [
      ...m.matched.map((l) => el("span", { className: "chip has", textContent: inferred[l] ? `${l}*` : l, title: chipTitle(l, "In your repos") })),
      ...m.missing.map((l) => el("span", { className: "chip lacks", textContent: inferred[l] ? `${l}*` : l, title: chipTitle(l, "Not in your repos") })),
    ]),
    ...(note ? [el("span", { className: "inferred-note", textContent: `* Inferred from skills: ${note}` })] : [])
  );
  badge.hidden = false;
}

$("match-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = new URLSearchParams(location.search).get("user");
  const res = await fetch(`/api/match/${encodeURIComponent(username)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: $("jd").value }),
  });
  const data = await res.json();
  if (!res.ok) {
    $("match-error").textContent = "Couldn't check the match. Paste at least a sentence of the job description.";
    $("match-error").hidden = false;
    return;
  }
  renderMatch(data);
  $("match-dialog").close();
  loadAdvice(username);
});

async function loadAdvice(username) {
  const res = await fetch(`/api/advice/${encodeURIComponent(username)}`);
  const a = await res.json();
  if (!res.ok || !a.has_jd) return;
  $("advice-list").replaceChildren(...(a.suggestions.length
    ? a.suggestions.map((s) => el("li", {}, [el("strong", { textContent: s.language }), el("span", { textContent: s.idea })]))
    : [el("li", { className: "note", textContent: a.message })]));
  $("advice").hidden = false;
}

// Portfolio assistant: the backend detects intent and writes the reply.
const currentUser = () => new URLSearchParams(location.search).get("user");

function addMessage(text, who) {
  $("chat-log").append(el("li", { className: who, textContent: text }));
  $("chat-log").scrollTop = $("chat-log").scrollHeight;
}

async function ask(message) {
  addMessage(message, "me");
  try {
    const res = await fetch(`/api/chat/${encodeURIComponent(currentUser())}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    addMessage(res.ok ? data.reply : "I couldn't answer that. Try one of the suggested questions.", "bot");
    if (res.ok) renderSuggestions(data.suggestions);
  } catch {
    addMessage("The assistant is unreachable. Check that the server is running.", "bot");
  }
}

function renderSuggestions(list) {
  $("chat-suggestions").replaceChildren(...list.map((q) =>
    el("button", { type: "button", textContent: q, onclick: () => ask(q) })));
}

function setChatOpen(open) {
  const wasOpen = !$("chat").hidden;
  $("chat").hidden = !open;
  $("chat-toggle").hidden = open;
  $("chat-toggle").setAttribute("aria-expanded", open);
  if (open) $("chat-input").focus();
  else if (wasOpen) $("chat-toggle").focus(); // return focus to where the user was
}

$("chat-toggle").addEventListener("click", () => setChatOpen(true));
$("chat-close").addEventListener("click", () => setChatOpen(false));
$("chat").addEventListener("keydown", (e) => { if (e.key === "Escape") setChatOpen(false); });
$("chat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const msg = $("chat-input").value.trim();
  if (!msg) return;
  $("chat-input").value = "";
  ask(msg);
});

$("match-open").addEventListener("click", () => {
  $("match-error").hidden = true;
  $("jd-file-status").textContent = "";
  $("match-dialog").showModal();
});
$("match-cancel").addEventListener("click", () => $("match-dialog").close());

// The backend extracts the text; we just show it so the user can review before matching.
$("jd-file").addEventListener("change", async () => {
  const file = $("jd-file").files[0];
  if (!file) return;
  const status = $("jd-file-status");
  status.className = "upload-status";
  status.textContent = `Reading ${file.name}…`;
  const form = new FormData();
  form.append("file", file);
  try {
    const res = await fetch("/api/job-description/extract", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Couldn't read this file.");
    $("jd").value = data.text;
    status.textContent = `Loaded ${data.filename}. Review the text, then check the match.`;
  } catch (err) {
    status.className = "upload-status error";
    status.textContent = err.message;
  } finally {
    $("jd-file").value = ""; // allow re-uploading the same file
  }
});

$("lookup").addEventListener("submit", (e) => {
  e.preventDefault();
  load($("username").value.trim());
});

const initial = new URLSearchParams(location.search).get("user");
if (initial) {
  $("username").value = initial;
  load(initial);
}

// Theme: explicit choice overrides the OS preference; the chart re-reads its colors.
function currentTheme() {
  return document.documentElement.dataset.theme
    || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}
function syncThemeButton() {
  const dark = currentTheme() === "dark";
  const label = dark ? "Switch to light mode" : "Switch to dark mode";
  // Show the icon of the mode you'll switch to: moon in light mode, sun in dark mode.
  document.querySelector(".icon-moon").toggleAttribute("hidden", dark);
  document.querySelector(".icon-sun").toggleAttribute("hidden", !dark);
  $("theme-toggle").setAttribute("aria-label", label);
  $("theme-toggle").title = label;
}
$("theme-toggle").addEventListener("click", () => {
  const next = currentTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch {}
  syncThemeButton();
  if (lastProfile) renderHeader(lastProfile);
});
syncThemeButton();

$("print-btn").addEventListener("click", () => window.print());

// PDFs always use light colors. The page itself stays as-is: CSS swaps tokens for print,
// and the canvas chart is replaced by a light-colored snapshot drawn off-screen.
addEventListener("beforeprint", () => {
  if (!lastProfile) return;
  const langs = lastProfile.top_languages.slice(0, 8);
  const canvas = Object.assign(document.createElement("canvas"), { width: 360, height: 360 });
  const chart = new Chart(canvas, {
    type: "doughnut",
    data: { labels: langs.map((l) => l.language),
            datasets: [{ data: langs.map((l) => l.percent), backgroundColor: palette($("light-probe")), borderWidth: 0 }] },
    options: { responsive: false, animation: false, cutout: "58%", plugins: { legend: { display: false } } },
  });
  $("lang-chart-print").src = canvas.toDataURL("image/png");
  chart.destroy();
});
