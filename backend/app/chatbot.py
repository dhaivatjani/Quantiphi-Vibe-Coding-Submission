"""Rule-based portfolio chatbot: detect the question's intent, answer from cached data."""
import re

from . import advisor, services
from .github_client import GitHubError

INTENTS = {
    "advice": r"improve|advice|suggest|gap|missing|learn|what should",
    "match": r"\bmatch|\bfit\b|\bjob\b|\bjd\b|hire",
    "languages": r"language|tech|stack|skill|code in|write in",
    "best_repo": r"best|popular|top repo|most star|famous|favo",
    "activity": r"streak|active|activity|contribut|commit|consistent",
    "stats": r"follower|stat|summary|overview|star|about|who",
}
SUGGESTIONS = ["Which languages are used most?", "Which repo is the most popular?",
               "How active is this developer?", "How can the job match improve?"]


def detect_intent(message: str, repo_names: list[str]) -> tuple[str, str | None]:
    """Return (intent, repo_name). A mentioned repo name wins over keyword intents."""
    text = message.lower()
    for name in repo_names:
        if re.search(rf"(?<![\w-]){re.escape(name.lower())}(?![\w-])", text):
            return "repo", name
    for intent, pattern in INTENTS.items():
        if re.search(pattern, text):
            return intent, None
    return "fallback", None


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def reply(username: str, message: str) -> dict:
    profile = services.build_profile(username)
    repos = profile["repos"]
    intent, repo_name = detect_intent(message, [r["name"] for r in repos])
    name = profile["name"]

    if intent == "repo":
        r = next(r for r in repos if r["name"] == repo_name)
        text = (f"{r['name']}: {r['description'] or 'no description'}. "
                f"Written mainly in {r['language'] or 'an unknown language'}, "
                f"with {r['stars']} stars and {r['forks']} forks.")
    elif intent == "languages":
        langs = profile["top_languages"][:3]
        text = (f"{name} mostly works in " + _join([f"{l['language']} ({l['percent']}% of repos)" for l in langs]) + "."
                if langs else f"{name}'s repositories don't report a language yet.")
    elif intent == "best_repo":
        text = (f"The most starred repo is {repos[0]['name']} with {repos[0]['stars']} stars"
                f" — {repos[0]['description'] or 'no description'}." if repos else f"{name} has no public repos yet.")
    elif intent == "activity":
        try:
            c = services.build_contributions(username)
            text = (f"{c['total']} contributions in the last year across {c['active_days']} active days. "
                    f"Current streak: {c['current_streak']} days, longest: {c['longest_streak']} days.")
        except GitHubError:
            text = "Contribution data isn't available right now."
    elif intent == "match":
        a = advisor.build_advice(username)
        text = (f"The last checked job is a {a['match_percent']}% tech stack match."
                if a["has_jd"] else a["message"])
    elif intent == "advice":
        a = advisor.build_advice(username)
        if a["suggestions"]:
            text = "To close the gap: " + " ".join(f"{s['language']}: {s['idea']}" for s in a["suggestions"])
        else:
            text = a["message"]
    elif intent == "stats":
        text = (f"{name} has {profile['followers']} followers, {profile['public_repos']} public repos "
                f"and {profile['total_stars']} stars in total.")
    else:
        text = "I can answer questions about languages, repositories, activity, stats and job fit. Try one below."

    return {"intent": intent, "reply": text, "suggestions": SUGGESTIONS}
