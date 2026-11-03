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
| **Top Languages chart** | Doughnut chart and legend of the share of repos per primary language | `services.language_breakdown` |
| **Repository cards** | Name, description, language tag, stars and forks for every repo, sorted by stars | `services._repo_card` |
| **Contribution heatmap** | Last 12 months of daily contributions as a calendar grid, colored in 5 intensity levels, plus total contributions, current streak and longest streak | `services.build_contributions`, `intensity_level`, `streaks` |
| **GitHub API integration** | REST API for user and repos (with pagination); GraphQL API for the contribution calendar | `github_client.py` |
| **SQLite caching engine** | Caches every GitHub response for 1 hour, and stores user settings (the last job description per user) | `cache.py` |
| **Vibe Check: Tech Stack Compatibility** | Paste or upload a job description; the server extracts the languages it asks for, compares them with the languages in the user's cached repos, and returns a **Match %** badge shown at the top of the profile | `matcher.py`, `services.build_match` |

### Two extra features (chatbot capabilities)

1. **Portfolio assistant (chatbot).** A chat panel ("Ask about this portfolio") that answers questions about the profile: top languages, most popular repo, activity and streaks, stats, job fit, or any repo by name. It uses rule-based intent detection on the server, with answers built from cached data, and offers suggested-question chips.
2. **JD gap advisor.** For every language a job description asks for that the user's repos don't have, it suggests a concrete project to close the gap. It appears as an "Improve your match" list and is also available in the chat ("How can the job match improve?").

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
```

---

## API reference

| Method | Endpoint | Body | Returns |
|---|---|---|---|
| GET | `/api/health` | | `{status}` |
| GET | `/api/profile/{username}` | | User info, `total_stars`, `total_forks`, `top_languages[]`, `repos[]` |
| GET | `/api/contributions/{username}` | | `total`, `current_streak`, `longest_streak`, `active_days`, `days[{date, count, level}]` |
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
Each repo's primary language (as reported by GitHub) is counted, then converted to a percentage of all repos that have a language.

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

- **Language data is the primary language per repo.** A Dockerfile or C++ code inside a Python repo isn't counted. Using `/repos/{repo}/languages` would give byte-level accuracy at the cost of one extra API call per repo.
- **Matching is keyword-based.** Every required language counts equally; "must have" and "nice to have" aren't distinguished. Tools without a language (AWS, Kubernetes) aren't scored.
- **The chatbot is rule-based, not generative.** It answers reliably for the supported intents but won't understand arbitrary phrasing. An LLM could be added behind the same `/api/chat` endpoint.
- **Project ideas are a fixed lookup table** per language, not generated for the specific job description.
- **Scanned (image-only) PDFs** aren't supported, because that would need OCR. Neither are `.docx` files.
- **The heatmap requires `GITHUB_TOKEN`.** Without it the page explains that the graph is unavailable, and everything else still works.
