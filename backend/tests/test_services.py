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
