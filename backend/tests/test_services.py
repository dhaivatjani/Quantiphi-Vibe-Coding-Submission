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
