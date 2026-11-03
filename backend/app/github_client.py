"""Thin GitHub REST client. Every call goes through the SQLite cache first."""
import httpx

from . import cache
from .config import GITHUB_TOKEN

API = "https://api.github.com"


class GitHubError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _get(path: str, params: dict | None = None):
    resp = httpx.get(f"{API}{path}", params=params, headers=_headers(), timeout=15)
    if resp.status_code == 404:
        raise GitHubError(404, "GitHub user not found")
    if resp.status_code in (403, 429):
        raise GitHubError(503, "GitHub rate limit reached, try again later")
    resp.raise_for_status()
    return resp.json()


def get_user(username: str) -> dict:
    key = f"user:{username.lower()}"
    if (data := cache.get(key)) is None:
        data = _get(f"/users/{username}")
        cache.set(key, data)
    return data


CONTRIBUTIONS_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def get_contribution_days(username: str) -> list[dict]:
    """Last year of daily contribution counts. GraphQL only, so it needs a token."""
    key = f"contrib:{username.lower()}"
    if (data := cache.get(key)) is not None:
        return data
    if not GITHUB_TOKEN:
        raise GitHubError(503, "Contribution graph needs GITHUB_TOKEN in .env")
    resp = httpx.post(
        f"{API}/graphql",
        json={"query": CONTRIBUTIONS_QUERY, "variables": {"login": username}},
        headers=_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    user = resp.json().get("data", {}).get("user")
    if user is None:
        raise GitHubError(404, "GitHub user not found")
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    data = [day for week in weeks for day in week["contributionDays"]]
    cache.set(key, data)
    return data


def get_repos(username: str) -> list[dict]:
    key = f"repos:{username.lower()}"
    if (data := cache.get(key)) is not None:
        return data
    data, page = [], 1
    while True:
        batch = _get(f"/users/{username}/repos", {"per_page": 100, "page": page, "sort": "updated"})
        data.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    cache.set(key, data)
    return data
