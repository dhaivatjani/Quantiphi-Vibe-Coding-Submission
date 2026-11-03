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


def _graphql_user(query: str, username: str, feature: str) -> dict:
    """Run a GraphQL query with a $login variable and return data.user."""
    if not GITHUB_TOKEN:
        raise GitHubError(503, f"{feature} needs GITHUB_TOKEN in .env")
    resp = httpx.post(f"{API}/graphql", json={"query": query, "variables": {"login": username}},
                      headers=_headers(), timeout=15)
    resp.raise_for_status()
    user = (resp.json().get("data") or {}).get("user")
    if user is None:
        raise GitHubError(404, "GitHub user not found")
    return user


PINNED_QUERY = """
query($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes { ... on Repository {
        name url description stargazerCount forkCount isFork updatedAt
        primaryLanguage { name }
      } }
    }
  }
}
"""


def get_pinned(username: str) -> list[dict]:
    """Repos the user pinned on their GitHub profile (GraphQL only)."""
    key = f"pinned:{username.lower()}"
    if (data := cache.get(key)) is None:
        data = _graphql_user(PINNED_QUERY, username, "Pinned repos")["pinnedItems"]["nodes"]
        cache.set(key, data)
    return data


LANGUAGES_QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes { languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
    }
  }
}
"""


def get_language_sizes(username: str) -> dict[str, int]:
    """Bytes of code per language across the user's own (non-fork) repos, in one GraphQL call.
    shortcut: only the 100 most recently pushed repos are counted; paginate if users with more matter."""
    key = f"langbytes:{username.lower()}"
    if (data := cache.get(key)) is None:
        data = {}
        for repo in _graphql_user(LANGUAGES_QUERY, username, "Language sizes")["repositories"]["nodes"]:
            for edge in repo["languages"]["edges"]:
                data[edge["node"]["name"]] = data.get(edge["node"]["name"], 0) + edge["size"]
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
    user = _graphql_user(CONTRIBUTIONS_QUERY, username, "Contribution graph")
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
