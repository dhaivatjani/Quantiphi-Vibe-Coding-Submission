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
