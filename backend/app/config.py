import os
from pathlib import Path

ROOT = Path(__file__).parents[2]


def _load_env_file(path: Path) -> None:
    """Minimal .env loader so we don't need python-dotenv."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(ROOT / ".env")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
DB_PATH = ROOT / "backend" / "cache.db"
CACHE_TTL_SECONDS = 60 * 60  # 1 hour
FRONTEND_DIR = ROOT / "frontend"
