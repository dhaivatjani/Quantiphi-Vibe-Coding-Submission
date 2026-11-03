// Presentation only: fetch computed data from the backend and render it.
const $ = (id) => document.getElementById(id);
const fmt = new Intl.NumberFormat();
// Chart colors come from the CSS tokens so there is one source of truth.
const rootStyle = getComputedStyle(document.documentElement);
const PALETTE = Array.from({ length: 8 }, (_, i) => rootStyle.getPropertyValue(`--chart-${i + 1}`).trim());
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
let langChart;

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
  langChart?.destroy();
  langChart = new Chart($("lang-chart"), {
    type: "doughnut",
    data: {
      labels: langs.map((l) => l.language),
      datasets: [{ data: langs.map((l) => l.percent), backgroundColor: PALETTE, borderWidth: 0 }],
    },
    options: { maintainAspectRatio: false, cutout: "58%", animation: !reduceMotion, plugins: { legend: { display: false } } },
  });
  $("lang-legend").replaceChildren(...langs.map((l, i) =>
    el("li", {}, [
      el("span", {}, [el("span", { className: "swatch", style: `background:${PALETTE[i]}` }), l.language]),
      el("span", { textContent: `${l.percent}%` }),
    ])
  ));
}

function renderRepos(repos) {
  $("repos").replaceChildren(...repos.map((r) =>
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

async function load(username) {
  loadActivity(username).catch(() => {});
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
    $("profile").hidden = $("repos-section").hidden = false;
    $("chat-toggle").hidden = false;
    setStatus("");
    history.replaceState(null, "", `?user=${encodeURIComponent(username)}`);
  } catch (err) {
    $("profile").hidden = $("repos-section").hidden = $("activity").hidden = $("chat-toggle").hidden = true;
    setStatus(`${err.message} Check the username and try again.`, true);
  }
}

function renderMatch(m) {
  const badge = $("match-badge");
  badge.replaceChildren(
    el("span", { className: "pct", textContent: `${m.match_percent}%` }),
    el("span", { className: "label", textContent: m.message || "tech stack match" }),
    el("span", { className: "chips" }, [
      ...m.matched.map((l) => el("span", { className: "chip has", textContent: l, title: "In your repos" })),
      ...m.missing.map((l) => el("span", { className: "chip lacks", textContent: l, title: "Not in your repos" })),
    ])
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
    : [el("li", { textContent: a.message })]));
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
  $("match-dialog").showModal();
});
$("match-cancel").addEventListener("click", () => $("match-dialog").close());

$("lookup").addEventListener("submit", (e) => {
  e.preventDefault();
  load($("username").value.trim());
});

const initial = new URLSearchParams(location.search).get("user");
if (initial) {
  $("username").value = initial;
  load(initial);
}
