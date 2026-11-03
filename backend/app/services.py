"""Business logic: all stats are computed here, the frontend only renders them."""
import math
from collections import Counter

from . import cache, github_client, matcher


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


def intensity_level(count: int, max_count: int) -> int:
    """Bucket a day's count into 0-4 relative to the busiest day."""
    if count == 0 or max_count == 0:
        return 0
    return min(4, math.ceil(4 * count / max_count))


def streaks(counts: list[int]) -> tuple[int, int]:
    """(current, longest) runs of days with contributions; counts are oldest -> newest.
    Today with zero contributions doesn't break the current streak yet."""
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    days = counts[:-1] if counts and counts[-1] == 0 else counts
    current = 0
    for c in reversed(days):
        if c == 0:
            break
        current += 1
    return current, longest


def build_contributions(username: str) -> dict:
    days = github_client.get_contribution_days(username)
    counts = [d["contributionCount"] for d in days]
    max_count = max(counts, default=0)
    current, longest = streaks(counts)
    return {
        "total": sum(counts),
        "current_streak": current,
        "longest_streak": longest,
        "active_days": sum(1 for c in counts if c > 0),
        "days": [
            {"date": d["date"], "count": c, "level": intensity_level(c, max_count)}
            for d, c in zip(days, counts)
        ],
    }


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


def build_match(username: str, job_description: str) -> dict:
    """Compare JD keywords with languages from the user's cached repositories."""
    repos = github_client.get_repos(username)
    user_languages = {r["language"] for r in repos if r["language"]}
    result = matcher.compute_match(job_description, user_languages)
    cache.set_setting(f"last_jd:{username.lower()}", job_description)
    return result
