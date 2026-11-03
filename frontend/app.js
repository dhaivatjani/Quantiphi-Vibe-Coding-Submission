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

async function load(username) {
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
    $("profile").hidden = $("repos-section").hidden = true;
    setStatus(`${err.message} Check the username and try again.`, true);
  }
}

$("lookup").addEventListener("submit", (e) => {
  e.preventDefault();
  load($("username").value.trim());
});

const initial = new URLSearchParams(location.search).get("user");
if (initial) {
  $("username").value = initial;
  load(initial);
}
