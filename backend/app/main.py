from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="GitHub Developer Portfolio")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Frontend is presentation only; served as static files by the same app.
app.mount("/", StaticFiles(directory=Path(__file__).parents[2] / "frontend", html=True), name="frontend")
