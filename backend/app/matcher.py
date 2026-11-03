"""Tech Stack Compatibility: match job-description keywords against repo languages."""
import re

# GitHub language name -> regex patterns that mean it in a job description.
# Ambiguous short names (C, R, Go) are matched case-sensitively.
LANGUAGE_PATTERNS = {
    "Python": [r"python", r"django", r"flask", r"fastapi", r"pandas", r"pytorch", r"tensorflow"],
    "JavaScript": [r"javascript", r"\bjs\b", r"node(?:\.?js)?", r"react(?:\.?js)?", r"express(?:\.?js)?", r"vue(?:\.?js)?"],
    "TypeScript": [r"typescript", r"\bts\b", r"angular", r"next\.?js", r"nest\.?js"],
    "Java": [r"\bjava\b(?!script)", r"spring(?: boot)?", r"\bj2ee\b"],
    "Kotlin": [r"kotlin"],
    "C++": [r"c\+\+", r"\bcpp\b"],
    "C#": [r"c#", r"\.net\b", r"asp\.net", r"dotnet"],
    "Go": [r"golang"],
    "Rust": [r"\brust\b"],
    "Ruby": [r"\bruby\b", r"\brails\b"],
    "PHP": [r"\bphp\b", r"laravel"],
    "Swift": [r"\bswift\b", r"\bios\b"],
    "Dart": [r"\bdart\b", r"flutter"],
    "Scala": [r"\bscala\b", r"\bspark\b"],
    "Shell": [r"\bbash\b", r"\bshell\b"],
    "HTML": [r"\bhtml5?\b"],
    "CSS": [r"\bcss3?\b", r"tailwind", r"\bsass\b", r"\bscss\b"],
    "Jupyter Notebook": [r"jupyter", r"notebooks?"],
    "SQL": [r"\bsql\b", r"postgres(?:ql)?", r"mysql", r"sqlite"],
    "Dockerfile": [r"docker"],
}
CASE_SENSITIVE_PATTERNS = {
    "C": [r"(?<![\w+#.-])C(?![\w+#])"],
    "R": [r"(?<![\w-])R(?![\w+#&'-])"],
    "Go": [r"(?<![\w-])Go(?![\w-])"],
}

MAX_JD_LENGTH = 20_000


def extract_languages(job_description: str) -> set[str]:
    found = {
        lang for lang, pats in LANGUAGE_PATTERNS.items()
        if any(re.search(p, job_description, re.IGNORECASE) for p in pats)
    }
    found |= {
        lang for lang, pats in CASE_SENSITIVE_PATTERNS.items()
        if any(re.search(p, job_description) for p in pats)
    }
    return found


def compute_match(job_description: str, user_languages: set[str]) -> dict:
    required = extract_languages(job_description)
    matched = sorted(required & user_languages)
    missing = sorted(required - user_languages)
    percent = round(len(matched) * 100 / len(required)) if required else 0
    return {
        "match_percent": percent,
        "required": sorted(required),
        "matched": matched,
        "missing": missing,
        "message": None if required else "No programming languages found in this job description.",
    }
