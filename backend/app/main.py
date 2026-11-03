import re

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from . import services
from .config import FRONTEND_DIR
from .github_client import GitHubError

app = FastAPI(title="GitHub Developer Portfolio")

# GitHub usernames: alphanumeric or single hyphens, max 39 chars
USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")


def _validate_username(username: str) -> str:
    if not USERNAME_RE.match(username):
        raise HTTPException(400, "Invalid GitHub username")
    return username


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/profile/{username}")
def profile(username: str):
    try:
        return services.build_profile(_validate_username(username))
    except GitHubError as e:
        raise HTTPException(e.status, str(e))


# Frontend is presentation only; served as static files by the same app.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
