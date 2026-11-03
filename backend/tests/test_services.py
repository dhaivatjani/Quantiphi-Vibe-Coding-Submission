"""Run from backend/: python -m tests.test_services"""
from app.services import intensity_level, streaks

assert streaks([]) == (0, 0)
assert streaks([1, 1, 0, 1, 1, 1]) == (3, 3)
assert streaks([1, 1, 1, 0, 1, 0]) == (1, 3)  # zero today doesn't break the streak
assert streaks([1, 0, 0]) == (0, 1)
assert intensity_level(0, 10) == 0
assert intensity_level(1, 10) == 1
assert intensity_level(10, 10) == 4
print("ok")

from app.matcher import compute_match, extract_languages

assert extract_languages("We need Python, React and Golang. Experience with C++ a plus.") == {"Python", "JavaScript", "Go", "C++"}
assert extract_languages("Strong Java skills, not JavaScript") >= {"Java"}
assert "C" not in extract_languages("C# and C++ developers")
assert "Go" not in extract_languages("ready to go live")
m = compute_match("Python and Rust engineer", {"Python", "C"})
assert m["match_percent"] == 50 and m["matched"] == ["Python"] and m["missing"] == ["Rust"]
assert compute_match("great communicator", {"Python"})["match_percent"] == 0
print("matcher ok")

from app.chatbot import SUGGESTIONS, detect_intent

repos = ["linux", "test-tlb"]
assert detect_intent("tell me about linux", repos) == ("repo", "linux")
assert detect_intent("Which languages are used most?", repos)[0] == "languages"
assert detect_intent("What's the longest streak?", repos)[0] == "activity"
assert detect_intent("How can the job match improve?", repos)[0] == "advice"
assert detect_intent("is this a good fit for the job", repos)[0] == "match"
assert detect_intent("hello there", repos)[0] == "fallback"
assert all(detect_intent(s, repos)[0] != "fallback" for s in SUGGESTIONS)
print("chatbot ok")

from app.chatbot import _plural

assert _plural(1, "day") == "1 day" and _plural(3, "day") == "3 days" and _plural(0, "day") == "0 days"
print("plural ok")

from app.documents import DocumentError, extract_text

assert extract_text("jd.txt", b"Python developer") == "Python developer"
for name, data in [("jd.docx", b"x"), ("empty.txt", b"   "), ("broken.pdf", b"%PDF-garbage")]:
    try:
        extract_text(name, data)
        raise AssertionError(f"{name} should be rejected")
    except DocumentError:
        pass
print("documents ok")

m = compute_match("Intern ML engineer: machine learning, computer vision and statistical modeling.", {"Python"})
assert m["required"] == ["Jupyter Notebook", "Python"] and m["match_percent"] == 50
assert m["inferred"] == {"Python": "machine learning", "Jupyter Notebook": "statistical model"}
assert compute_match("Python and machine learning", set())["inferred"] == {}  # explicit wins
assert compute_match("great communicator", {"Python"})["match_percent"] == 0
print("inference ok")

from datetime import datetime, timezone

from app.services import activity_patterns, repo_freshness

days = [{"date": "2026-03-02", "contributionCount": 5},   # Monday
        {"date": "2026-03-03", "contributionCount": 9},   # Tuesday
        {"date": "2026-04-07", "contributionCount": 1}]   # Tuesday
p = activity_patterns(days)
assert p["top_weekday"] == "Tuesday" and p["best_day"] == {"date": "2026-03-03", "count": 9}
assert p["busiest_month"] == {"month": "March 2026", "count": 14}
assert activity_patterns([{"date": "2026-03-02", "contributionCount": 0}])["top_weekday"] is None
now = datetime(2026, 11, 3, tzinfo=timezone.utc)
f = repo_freshness([{"updated_at": "2026-10-20T00:00:00Z"}, {"updated_at": "2024-01-01T00:00:00Z"}], now)
assert f == {"active_30d": 1, "inactive_1y": 1}
print("insights ok")

from app.services import byte_breakdown

b = byte_breakdown({"Python": 300, "Shell": 100})
assert b[0] == {"language": "Python", "bytes": 300, "percent": 75.0} and b[1]["percent"] == 25.0
assert byte_breakdown({}) == []
print("bytes ok")

from app.services import describe_event, time_ago

now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
assert time_ago("2026-11-03T11:00:00Z", now) == "1 hour ago"
assert time_ago("2026-11-01T12:00:00Z", now) == "2 days ago"
assert time_ago("2026-11-03T11:59:50Z", now) == "just now"
assert describe_event({"type": "PushEvent", "repo": {"name": "a/b"}, "payload": {"size": 3}}) == "Pushed 3 commits to a/b"
assert describe_event({"type": "WatchEvent", "repo": {"name": "a/b"}, "payload": {}}) == "Starred a/b"
assert describe_event({"type": "GollumEvent", "repo": {"name": "a/b"}, "payload": {}}) is None
print("events ok")

from app.services import compare_rows

r = compare_rows({"Stars": 5, "Repos": 2, "Streak": None}, {"Stars": 3, "Repos": 2, "Streak": 4})
assert [x["leader"] for x in r] == ["a", "tie", None]
print("compare ok")
