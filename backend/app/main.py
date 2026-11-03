import re

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import advisor, chatbot, documents, services
from .documents import MAX_UPLOAD_BYTES, DocumentError
from .config import FRONTEND_DIR
from .github_client import GitHubError
from .matcher import MAX_JD_LENGTH

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


@app.get("/api/contributions/{username}")
def contributions(username: str):
    try:
        return services.build_contributions(_validate_username(username))
    except GitHubError as e:
        raise HTTPException(e.status, str(e))


@app.get("/api/insights/{username}")
def insights(username: str):
    try:
        return services.build_insights(_validate_username(username))
    except GitHubError as e:
        raise HTTPException(e.status, str(e))


@app.post("/api/job-description/extract")
async def extract_job_description(file: UploadFile):
    data = await file.read(MAX_UPLOAD_BYTES + 1)  # read one extra byte to detect oversize files
    try:
        return {"filename": file.filename, "text": documents.extract_text(file.filename, data)}
    except DocumentError as e:
        raise HTTPException(400, str(e))


class MatchRequest(BaseModel):
    job_description: str = Field(min_length=10, max_length=MAX_JD_LENGTH)


@app.post("/api/match/{username}")
def match(username: str, body: MatchRequest):
    try:
        return services.build_match(_validate_username(username), body.job_description)
    except GitHubError as e:
        raise HTTPException(e.status, str(e))


@app.get("/api/advice/{username}")
def advice(username: str):
    try:
        return advisor.build_advice(_validate_username(username))
    except GitHubError as e:
        raise HTTPException(e.status, str(e))


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


@app.post("/api/chat/{username}")
def chat(username: str, body: ChatRequest):
    try:
        return chatbot.reply(_validate_username(username), body.message)
    except GitHubError as e:
        raise HTTPException(e.status, str(e))


# Frontend is presentation only; served as static files by the same app.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
