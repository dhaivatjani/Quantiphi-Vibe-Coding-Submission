# GitHub Developer Portfolio

A personal branding dashboard for any GitHub user. It visualizes repository stats, language usage and daily coding activity, scores how well the user's tech stack fits a job description, and includes a portfolio chatbot that answers questions about the profile.

Built for the Quantiphi × DAU Vibe Coding round.

**All business logic runs on the server** (FastAPI). The frontend is plain HTML/CSS/JS that only fetches computed results and renders them.

---

## Features

### Core requirements

| Feature | What it does | Where the logic lives |
|---|---|---|
| **Profile header** | Avatar, name, bio, follower count, total stars, public repo count | `services.build_profile` |
| **Top Languages chart** | Doughnut chart of **bytes of code per language** across the user's own repos (one GraphQL call). Without a token it falls back to the share of repos per primary language | `services.languages_with_basis`, `byte_breakdown` |
| **Repository cards** | Name, description, language tag, stars and forks for every repo, sorted by stars | `services._repo_card` |
| **Contribution heatmap** | Last 12 months of daily contributions as a calendar grid, colored in 5 intensity levels, plus total contributions, current streak and longest streak | `services.build_contributions`, `intensity_level`, `streaks` |
| **GitHub API integration** | REST API for user and repos (with pagination); GraphQL API for the contribution calendar | `github_client.py` |
| **SQLite caching engine** | Caches every GitHub response for 1 hour, and stores user settings (the last job description per user) | `cache.py` |
| **Vibe Check: Tech Stack Compatibility** | Paste or upload a job description; the server extracts the languages it asks for, compares them with the languages in the user's cached repos, and returns a **Match %** badge shown at the top of the profile | `matcher.py`, `services.build_match` |

### Two extra features (chatbot capabilities)

1. **Portfolio assistant (chatbot).** A chat panel ("Ask about this portfolio") that answers questions about the profile: top languages, most popular repo, activity and streaks, stats, job fit, or any repo by name. It uses rule-based intent detection on the server, with answers built from cached data, and offers suggested-question chips.
2. **JD gap advisor.** For every language a job description asks for that the user's repos don't have, it suggests a concrete project to close the gap. It appears as an "Improve your match" list and is also available in the chat ("How can the job match improve?").

### More insights from the GitHub profile

| Feature | What it shows | Logic |
|---|---|---|
| **At a glance** | Member since / account age, original vs forked repos, repos active in the last 30 days vs inactive for over a year, average stars per repo, total forks, most active weekday, best day, busiest month, repo topics | `services.build_insights`, `activity_patterns`, `repo_freshness` |
| **Pinned repositories** | The repos the developer chose to pin on GitHub, shown before the full list | GraphQL `pinnedItems` → `services.pinned_cards` |
| **Recent activity feed** | Last 10 public events ("Pushed 3 commits to X", "Opened pull request #12", "Starred Y") with relative times | `services.build_events`, `describe_event`, `time_ago` |
| **Compare developers** | Side-by-side followers, stars, forks, repos, contributions and longest streak, the leader for each metric, and shared / unique languages. A reset button clears it, and refreshing the page starts fresh | `services.build_compare`, `compare_rows` |
| **Download as PDF** | A print stylesheet hides controls and the chat, so the browser's "Save as PDF" produces a clean portfolio | `styles.css` `@media print` |
| **Dark mode** | Follows the OS setting, with a toggle that remembers your choice. All colors come from the same CSS variables | `styles.css` tokens |

### Additional details
- **Job description upload:** PDF or `.txt` files; the text is extracted on the server with `pypdf` and shown in the box for review before matching.
- **Skill-based inference:** many job descriptions (e.g. ML internships) list skills instead of languages. Terms like "machine learning" or "statistical modeling" imply Python or Jupyter Notebook. Inferred languages are marked with `*`, and the badge says which phrase triggered each one.
- **Shareable URLs:** `/?user=<username>` loads a profile directly.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | **FastAPI** (Python 3.10+) | Typed request validation with Pydantic, automatic API docs at `/docs` |
| HTTP client | **httpx** | Simple sync client for GitHub REST and GraphQL |
| Cache / settings | **SQLite** via Python's built-in `sqlite3` | Zero setup, a single file, no extra dependency |
| PDF parsing | **pypdf** | Pure Python, no system libraries |
| Frontend | **Vanilla HTML, CSS, JS** | No build step; the frontend only does presentation |
| Chart | **Chart.js 4** (CDN) | Doughnut chart for top languages |
| Fonts | Bricolage Grotesque, IBM Plex Sans (Google Fonts) | |

---

## Architecture

```
Browser (frontend/: presentation only)
   │  fetch JSON
   ▼
FastAPI routes (main.py)   ← input validation: username regex, JD length, file size/type
   │
   ▼
Business logic
   ├── services.py    profile stats, language %, heatmap levels, streaks
   ├── matcher.py     JD → languages (explicit + inferred), match %
   ├── advisor.py     missing languages → project ideas
   ├── chatbot.py     intent detection → reply from cached data
   └── documents.py   PDF/TXT → text
   │
   ▼
github_client.py  ── cache-first ──►  cache.py (SQLite: api_cache, settings)
   │ on cache miss
   ▼
GitHub REST + GraphQL APIs
```

**Caching flow:** every GitHub call first checks the `api_cache` table by key (`user:<name>`, `repos:<name>`, `contrib:<name>`). A cache hit younger than 1 hour is returned directly. Otherwise the API is called and the result is stored. In testing, the first profile load took about 1.7 s and a cached reload about 0.28 s.

---

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app, routes, validation, serves frontend/
│   │   ├── config.py         # .env loader, token, DB path, cache TTL
│   │   ├── cache.py          # SQLite cache + settings tables
│   │   ├── github_client.py  # GitHub REST/GraphQL client (cache-first)
│   │   ├── services.py       # Profile stats, language breakdown, heatmap, streaks, match
│   │   ├── matcher.py        # Tech Stack Compatibility (keyword + inference rules)
│   │   ├── advisor.py        # JD gap advisor (project idea per missing language)
│   │   ├── chatbot.py        # Rule-based portfolio assistant
│   │   └── documents.py      # PDF/TXT text extraction
│   ├── tests/
│   │   └── test_services.py  # Assert-based tests for the business logic
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── styles.css            # Design tokens as CSS custom properties
│   └── app.js                # Fetch + render only
├── .env.example
└── README.md
```

---

## Getting started

### 1. Prerequisites
- Python 3.10+
- A GitHub personal access token. This is optional but recommended: it raises the rate limit from 60 to 5,000 requests per hour and is **required for the contribution heatmap** (GitHub's GraphQL API needs authentication). A classic token with **no scopes** is enough for public data.

### 2. Configure
```bash
cp .env.example .env
# then edit .env:
# GITHUB_TOKEN=ghp_your_token_here
```
`.env` is git-ignored.

### 3. Install and run
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```
Open **http://localhost:8000**, enter a GitHub username, or go straight to `http://localhost:8000/?user=torvalds`.

Interactive API docs: **http://localhost:8000/docs**

### 4. Run the tests
```bash
cd backend
python -m tests.test_services
```
Expected output:
```
ok
matcher ok
chatbot ok
plural ok
documents ok
inference ok
insights ok
bytes ok
events ok
compare ok
```

---

## API reference

| Method | Endpoint | Body | Returns |
|---|---|---|---|
| GET | `/api/health` | | `{status}` |
| GET | `/api/profile/{username}` | | User info, `total_stars`, `total_forks`, `top_languages[]`, `language_basis` (`bytes` or `repos`), `pinned[]`, `repos[]` |
| GET | `/api/contributions/{username}` | | `total`, `current_streak`, `longest_streak`, `active_days`, `days[{date, count, level}]` |
| GET | `/api/insights/{username}` | | `member_since`, `account_age_years`, `original_repos`, `forked_repos`, `active_30d`, `inactive_1y`, `avg_stars_per_repo`, `total_forks`, `top_topics[]`, `top_weekday`, `best_day`, `busiest_month` |
| GET | `/api/events/{username}` | | `[{text, type, repo_url, when, created_at}]` (up to 10) |
| GET | `/api/compare/{a}/{b}` | | `a`, `b`, `rows[{metric, a, b, leader}]`, `score`, `shared_languages`, `only_a`, `only_b` |
| POST | `/api/job-description/extract` | multipart `file` (.pdf / .txt, ≤ 5 MB) | `{filename, text}` |
| POST | `/api/match/{username}` | `{job_description}` (10–20,000 chars) | `match_percent`, `required`, `matched`, `missing`, `inferred`, `message` |
| GET | `/api/advice/{username}` | | `has_jd`, `match_percent`, `suggestions[{language, idea}]`, `message` |
| POST | `/api/chat/{username}` | `{message}` (1–500 chars) | `intent`, `reply`, `suggestions[]` |

**Errors:**
- `400`: invalid username, unsupported or unreadable file.
- `404`: GitHub user not found.
- `422`: request body fails validation.
- `503`: GitHub rate limit reached, or the token is missing for the heatmap.

---

## How the key calculations work

### Language breakdown
One GraphQL query fetches the language sizes (bytes) of the user's own non-fork repos and sums them per language: `percent = bytes_of_language / total_bytes × 100`. Without a token, each repo's primary language is counted instead, and the chart caption says which basis is used ("by code size" or "by repo count").

The Vibe Check uses **every language found**, primary languages plus all languages in the byte breakdown. So a Dockerfile or Shell script inside a Python repo now counts.

### Heatmap intensity
`level = ceil(4 × count / busiest_day_count)`, capped at 4; days with no contributions are level 0. Levels are relative to the user's own busiest day.

### Streaks
- **Longest:** the longest run of consecutive days with at least 1 contribution.
- **Current:** counted backwards from today. A day with zero contributions *today* does not break the streak yet, because the day isn't over.

### Match percentage (Vibe Check)
1. **Explicit languages:** regex patterns map language names and frameworks to GitHub language names (e.g. `React`/`Node` → JavaScript, `Django`/`PyTorch` → Python, `.NET` → C#, `Golang` → Go). Ambiguous short names (`C`, `R`, `Go`) are matched case-sensitively, so "C++", "C#" and "go live" don't trigger them.
2. **Inferred languages:** if a language isn't named, domain terms can still imply it (e.g. "machine learning" → Python, "statistical modeling" → Jupyter Notebook).
3. `required = explicit ∪ inferred` and `user = {primary languages of the user's repos}`.
4. `match % = |required ∩ user| / |required| × 100`.

The last job description is saved in the SQLite `settings` table, so the advisor and the chatbot can reuse it.

### Insights
- **Most active weekday:** contributions summed per weekday over the last year.
- **Best day:** the single day with the most contributions.
- **Busiest month:** contributions summed per calendar month.
- **Freshness:** days since each repo's `updated_at`; ≤ 30 counts as active, > 365 as inactive.

### Compare
For each metric, the higher value leads (or it's a tie). The score is the number of metrics each developer leads. Languages are compared as sets: shared = A ∩ B, only A = A − B, and only B = B − A.

### Chatbot intent detection
The server first checks whether the message names one of the user's repos. If not, it tests ordered regex rules (advice → match → languages → best repo → activity → stats) and falls back to a help message. Each intent has a reply builder that reads from the cached profile and contribution data.

---

## Design

- **Look:** a blue-grey "drafting paper" background, navy ink, a cobalt accent and a marigold highlight. The contribution heatmap uses a cobalt scale rather than GitHub's green. The oversized name is the one bold element on the page.
- **Tokens:** all colors are CSS custom properties in `styles.css` (`--paper`, `--ink`, `--cobalt`, `--heat-0…4`, `--chart-1…8`, and so on). The JS reads the chart colors from them.
- **Accessibility:**
  - Every text color passes WCAG AA contrast.
  - Inputs have real labels and keyboard focus is clearly visible.
  - The job dialog uses the native `<dialog>`, so focus is trapped and Esc closes it.
  - The chat closes on Esc and returns focus to its button, and new messages are announced (`aria-live`).
  - Errors use `role="alert"`.
  - User content is always inserted with `textContent`, so it can't inject HTML.
- **Responsive:** single column below 760px, with no horizontal page scroll at 375px wide.

---

## Limitations and future work

- **Byte-level languages cover the 100 most recently pushed repos** (one GraphQL page). Users with more repos would need pagination.
- **The activity feed** only covers GitHub's public events from roughly the last 90 days, and GitHub can delay new events by a few minutes or more.
- **Matching is keyword-based.** Every required language counts equally; "must have" and "nice to have" aren't distinguished. Tools without a language (AWS, Kubernetes) aren't scored.
- **The chatbot is rule-based, not generative.** It answers reliably for the supported intents but won't understand arbitrary phrasing. An LLM could be added behind the same `/api/chat` endpoint.
- **Project ideas are a fixed lookup table** per language, not generated for the specific job description.
- **Scanned (image-only) PDFs** aren't supported, because that would need OCR. Neither are `.docx` files.
- **The heatmap requires `GITHUB_TOKEN`.** Without it the page explains that the graph is unavailable, and everything else still works.
