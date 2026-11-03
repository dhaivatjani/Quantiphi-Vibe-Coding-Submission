# GitHub Developer Portfolio

Developer dashboard that visualizes GitHub activity, repo stats and coding streaks, with a JD "Tech Stack Compatibility" match.

## Structure
- `backend/` – FastAPI: GitHub API client, SQLite cache, all business logic
- `frontend/` – static HTML/JS: presentation only

## Run
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://localhost:8000
