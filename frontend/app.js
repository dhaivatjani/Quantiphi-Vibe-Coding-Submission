// Presentation only: fetch computed data from the backend and render it.
const $ = (id) => document.getElementById(id);
const fmt = new Intl.NumberFormat();
const PALETTE = ["#2f5bd3", "#f2b134", "#14213d", "#6c8fe8", "#c9862a", "#8a97b0", "#b8c7f2", "#4a5875"];
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
    options: { maintainAspectRatio: false, cutout: "58%", plugins: { legend: { display: false } } },
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
  if (!res.ok) return; // heatmap is optional; profile still renders
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
  $("match-badge").hidden = true;
  setStatus(`Loading ${username}…`);
  try {
    const res = await fetch(`/api/profile/${encodeURIComponent(username)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not load this profile.");
    renderHeader(data);
    renderRepos(data.repos);
    $("profile").hidden = $("repos-section").hidden = false;
    setStatus("");
    history.replaceState(null, "", `?user=${encodeURIComponent(username)}`);
  } catch (err) {
    $("profile").hidden = $("repos-section").hidden = $("activity").hidden = true;
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
  if (!res.ok) return setStatus("Couldn't check the match. Paste at least a sentence of the job description.", true);
  renderMatch(data);
  $("match-panel").open = false;
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
