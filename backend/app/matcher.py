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

# Skills and domains that imply a language even when the JD never names one.
# Only used for languages the JD doesn't mention explicitly.
IMPLIED_PATTERNS = {
    "Python": [r"machine learning", r"deep learning", r"ml", r"ai", r"artificial intelligence",
               r"data scien", r"computer vision", r"natural language processing", r"nlp",
               r"speech recognition", r"generative ai", r"llms?", r"large language model",
               r"neural network", r"regression", r"clustering"],
    "Jupyter Notebook": [r"data analy", r"statistical model", r"exploratory", r"data visuali"],
    "JavaScript": [r"front[- ]?end", r"web develop", r"full[- ]?stack"],
    "SQL": [r"databases?", r"data warehous", r"etl"],
    "Swift": [r"ios develop"],
    "Kotlin": [r"android develop"],
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


def infer_languages(job_description: str, explicit: set[str]) -> dict[str, str]:
    """Languages implied by skills/domains -> the phrase that implied them."""
    inferred = {}
    for lang, pats in IMPLIED_PATTERNS.items():
        if lang in explicit:
            continue
        for p in pats:
            if m := re.search(p, job_description, re.IGNORECASE):
                inferred[lang] = m.group(0).lower()
                break
    return inferred


def compute_match(job_description: str, user_languages: set[str]) -> dict:
    explicit = extract_languages(job_description)
    inferred = infer_languages(job_description, explicit)
    required = explicit | set(inferred)
    matched = sorted(required & user_languages)
    missing = sorted(required - user_languages)
    percent = round(len(matched) * 100 / len(required)) if required else 0
    return {
        "match_percent": percent,
        "required": sorted(required),
        "matched": matched,
        "missing": missing,
        "inferred": inferred,
        "message": None if required else "No programming languages or technical skills found in this job description.",
    }
