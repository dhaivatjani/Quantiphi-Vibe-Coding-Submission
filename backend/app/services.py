"""Business logic: all stats are computed here, the frontend only renders them."""
import math
from collections import Counter
from datetime import date, datetime, timezone

from . import cache, github_client, matcher
from .github_client import GitHubError

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


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
        "topics": repo.get("topics", []),
    }


def _pinned_card(node: dict) -> dict:
    return {
        "name": node["name"],
        "url": node["url"],
        "description": node["description"] or "",
        "language": (node["primaryLanguage"] or {}).get("name"),
        "stars": node["stargazerCount"],
        "forks": node["forkCount"],
        "is_fork": node["isFork"],
        "updated_at": node["updatedAt"],
        "topics": [],
    }


def pinned_cards(username: str) -> list[dict]:
    """Pinned repos are optional: without a token or on error, show none."""
    try:
        return [_pinned_card(n) for n in github_client.get_pinned(username) if n]
    except GitHubError:
        return []


def language_breakdown(repos: list[dict]) -> list[dict]:
    """Share of repos per primary language, as percentages (most used first)."""
    counts = Counter(r["language"] for r in repos if r["language"])
    total = sum(counts.values())
    return [
        {"language": lang, "repos": n, "percent": round(n * 100 / total, 1)}
        for lang, n in counts.most_common()
    ]


def byte_breakdown(sizes: dict[str, int]) -> list[dict]:
    """Share of code bytes per language, as percentages (largest first)."""
    total = sum(sizes.values())
    return [
        {"language": lang, "bytes": n, "percent": round(n * 100 / total, 1)}
        for lang, n in sorted(sizes.items(), key=lambda kv: kv[1], reverse=True) if total
    ]


def languages_with_basis(username: str, repos: list[dict]) -> tuple[list[dict], str]:
    """Prefer exact bytes of code per language; fall back to counting primary languages."""
    try:
        sizes = github_client.get_language_sizes(username)
        if sizes:
            return byte_breakdown(sizes), "bytes"
    except GitHubError:
        pass
    return language_breakdown(repos), "repos"


def user_languages(username: str, repos: list[dict]) -> set[str]:
    """Every language the user has written: primary languages plus any found in the byte breakdown."""
    langs = {r["language"] for r in repos if r["language"]}
    try:
        langs |= set(github_client.get_language_sizes(username))
    except GitHubError:
        pass
    return langs


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
    top_languages, basis = languages_with_basis(username, repos)
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
        "top_languages": top_languages,
        "language_basis": basis,  # "bytes" of code, or share of "repos" without a token
        "pinned": pinned_cards(username),
        "repos": cards,
    }


def build_match(username: str, job_description: str) -> dict:
    """Compare JD keywords with languages from the user's cached repositories."""
    repos = github_client.get_repos(username)
    result = matcher.compute_match(job_description, user_languages(username, repos))
    cache.set_setting(f"last_jd:{username.lower()}", job_description)
    return result


def activity_patterns(days: list[dict]) -> dict:
    """Most active weekday, single best day and busiest month from daily counts."""
    by_weekday, by_month = Counter(), Counter()
    for d in days:
        day = date.fromisoformat(d["date"])
        by_weekday[day.weekday()] += d["contributionCount"]
        by_month[day.strftime("%B %Y")] += d["contributionCount"]
    best = max(days, key=lambda d: d["contributionCount"], default=None)
    if not best or best["contributionCount"] == 0:
        return {"top_weekday": None, "best_day": None, "busiest_month": None}
    weekday, _ = by_weekday.most_common(1)[0]
    month, month_count = by_month.most_common(1)[0]
    return {
        "top_weekday": WEEKDAYS[weekday],
        "best_day": {"date": best["date"], "count": best["contributionCount"]},
        "busiest_month": {"month": month, "count": month_count},
    }


def repo_freshness(repos: list[dict], now: datetime) -> dict:
    """How many repos were updated recently vs left inactive for over a year."""
    ages = [(now - datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00"))).days for r in repos]
    return {"active_30d": sum(a <= 30 for a in ages), "inactive_1y": sum(a > 365 for a in ages)}


def build_insights(username: str) -> dict:
    user = github_client.get_user(username)
    repos = github_client.get_repos(username)
    now = datetime.now(timezone.utc)
    created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    originals = [r for r in repos if not r["fork"]]
    stars = sum(r["stargazers_count"] for r in repos)
    topics = Counter(t for r in repos for t in r.get("topics", []))
    try:
        patterns = activity_patterns(github_client.get_contribution_days(username))
    except GitHubError:
        patterns = {"top_weekday": None, "best_day": None, "busiest_month": None}
    return {
        "member_since": created.year,
        "account_age_years": round((now - created).days / 365.25, 1),
        "original_repos": len(originals),
        "forked_repos": len(repos) - len(originals),
        "avg_stars_per_repo": round(stars / len(repos), 1) if repos else 0,
        "total_forks": sum(r["forks_count"] for r in repos),
        "top_topics": [t for t, _ in topics.most_common(12)],
        **repo_freshness(repos, now),
        **patterns,
    }


def time_ago(iso: str, now: datetime) -> str:
    seconds = int((now - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds())
    for unit, size in (("day", 86400), ("hour", 3600), ("minute", 60)):
        if seconds >= size:
            n = seconds // size
            return f"{n} {unit}{'' if n == 1 else 's'} ago"
    return "just now"


def describe_event(e: dict) -> str | None:
    """One-line summary of a GitHub event; None for event types we don't show."""
    repo, payload, kind = e["repo"]["name"], e.get("payload", {}), e["type"]
    if kind == "PushEvent":
        n = payload.get("size") or len(payload.get("commits", [])) or 1
        return f"Pushed {n} commit{'' if n == 1 else 's'} to {repo}"
    if kind == "CreateEvent":
        ref_type = payload.get("ref_type", "repository")
        return f"Created repository {repo}" if ref_type == "repository" else f"Created {ref_type} {payload.get('ref')} in {repo}"
    if kind == "PullRequestEvent":
        pr = payload.get("pull_request", {})
        return f"{payload.get('action', 'updated').capitalize()} pull request #{pr.get('number', '?')} in {repo}"
    if kind == "IssuesEvent":
        return f"{payload.get('action', 'updated').capitalize()} issue #{payload.get('issue', {}).get('number', '?')} in {repo}"
    if kind == "IssueCommentEvent":
        return f"Commented on #{payload.get('issue', {}).get('number', '?')} in {repo}"
    if kind == "WatchEvent":
        return f"Starred {repo}"
    if kind == "ForkEvent":
        return f"Forked {repo}"
    if kind == "ReleaseEvent":
        return f"Published release {payload.get('release', {}).get('tag_name', '')} of {repo}".replace("  ", " ")
    if kind == "PullRequestReviewEvent":
        return f"Reviewed a pull request in {repo}"
    return None


def build_events(username: str, limit: int = 10) -> list[dict]:
    now = datetime.now(timezone.utc)
    items = []
    for e in github_client.get_events(username):
        if (text := describe_event(e)) is not None:
            items.append({"text": text, "type": e["type"], "repo_url": f"https://github.com/{e['repo']['name']}",
                          "when": time_ago(e["created_at"], now), "created_at": e["created_at"]})
        if len(items) == limit:
            break
    return items
