"""JD gap advisor: suggest a small project for each language the JD wants but the repos lack."""
from . import cache, github_client, matcher

PROJECT_IDEAS = {
    "Python": "Build a FastAPI service with tests that wraps a public dataset or ML model.",
    "JavaScript": "Ship a small React app that consumes a public API, deployed on GitHub Pages.",
    "TypeScript": "Rewrite a small JS project in TypeScript with strict mode and typed API clients.",
    "Java": "Create a Spring Boot REST API with JPA persistence and JUnit tests.",
    "Kotlin": "Build a small Android or Ktor app that consumes a REST API.",
    "C++": "Write a real-time OpenCV object-detection demo with a C++ inference path.",
    "C#": "Build an ASP.NET Core Web API with Entity Framework and xUnit tests.",
    "C": "Implement a small CLI tool (e.g. a tiny shell or HTTP parser) in C with a Makefile.",
    "Go": "Write a concurrent Go CLI or REST service using goroutines and channels.",
    "Rust": "Port a small CLI utility to Rust with error handling and cargo tests.",
    "Ruby": "Build a Rails CRUD app with authentication and RSpec tests.",
    "PHP": "Create a Laravel REST API with migrations and feature tests.",
    "Swift": "Build a SwiftUI iOS app that fetches and caches data from an API.",
    "Dart": "Build a cross-platform Flutter app with state management and a REST backend.",
    "Scala": "Write a Spark job in Scala that aggregates a public dataset.",
    "Shell": "Add Bash scripts that automate setup, lint and deploy for one of your projects.",
    "HTML": "Build an accessible, responsive static portfolio page with semantic HTML.",
    "CSS": "Create a responsive UI component library with modern CSS (grid, custom properties).",
    "Jupyter Notebook": "Publish an exploratory data analysis notebook with clear charts and findings.",
    "SQL": "Design a normalized PostgreSQL schema for one of your apps and add query endpoints.",
    "Dockerfile": "Containerize an existing project with a Dockerfile and docker-compose.",
    "R": "Publish an R Markdown statistical analysis of a public dataset.",
}


def build_advice(username: str) -> dict:
    jd = cache.get_setting(f"last_jd:{username.lower()}")
    if not jd:
        return {"has_jd": False, "match_percent": None, "suggestions": [],
                "message": "Check fit for a job first, then come back for advice."}
    repos = github_client.get_repos(username)
    match = matcher.compute_match(jd, {r["language"] for r in repos if r["language"]})
    suggestions = [{"language": lang, "idea": PROJECT_IDEAS.get(lang, f"Build a small project using {lang}.")}
                   for lang in match["missing"]]
    message = ("You already cover every language this job asks for." if match["required"] and not suggestions
               else match["message"])
    return {"has_jd": True, "match_percent": match["match_percent"], "suggestions": suggestions, "message": message}
