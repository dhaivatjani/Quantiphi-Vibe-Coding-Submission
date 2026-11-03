"""Business logic: all stats are computed here, the frontend only renders them."""
from collections import Counter

from . import github_client


def _repo_card(repo: dict) -> dict:
    return {
        "name": repo["name"],
        "url": repo["html_url"],
        "description": repo["description"] or "",
        "language": repo["language"],
        "stars": repo["stargazers_count"],
        "forks": repo["forks_count"],
        "is_fork": repo["fork"],
        "updated_at": repo["updated_at"],
    }


def language_breakdown(repos: list[dict]) -> list[dict]:
    """Share of repos per primary language, as percentages (most used first)."""
    counts = Counter(r["language"] for r in repos if r["language"])
    total = sum(counts.values())
    return [
        {"language": lang, "repos": n, "percent": round(n * 100 / total, 1)}
        for lang, n in counts.most_common()
    ]


def build_profile(username: str) -> dict:
    user = github_client.get_user(username)
    repos = github_client.get_repos(username)
    cards = sorted((_repo_card(r) for r in repos), key=lambda c: c["stars"], reverse=True)
    return {
        "username": user["login"],
        "name": user["name"] or user["login"],
        "avatar_url": user["avatar_url"],
        "bio": user["bio"] or "",
        "profile_url": user["html_url"],
        "followers": user["followers"],
        "following": user["following"],
        "public_repos": user["public_repos"],
        "total_stars": sum(c["stars"] for c in cards),
        "total_forks": sum(c["forks"] for c in cards),
        "top_languages": language_breakdown(repos),
        "repos": cards,
    }
