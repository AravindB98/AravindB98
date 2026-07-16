#!/usr/bin/env python3
"""Regenerate the categorized project list in README.md from live GitHub data.

Fetches all PUBLIC, non-fork repos for the user and rewrites the section
between <!--PROJECTS:START--> and <!--PROJECTS:END-->. Any repo flipped from
private to public appears automatically on the next run.

A repo can appear under MULTIPLE categories. Categorization order:
1. OVERRIDES (explicit repo -> [categories]) wins entirely.
2. GitHub repo topics add categories via TOPIC_MAP.
3. Keyword rules on name+description add categories.
4. No match -> fallback "Tools & Other".
"""
import json
import re
import sys
import urllib.request

USER = "AravindB98"
README = sys.argv[1] if len(sys.argv) > 1 else "README.md"

AI = "🤖 AI & Agentic Systems"
CV = "👁️ Computer Vision & Robotics"
ML = "🧠 Machine Learning & RL"
SCI = "🔬 Science & Simulation"
QUANTUM = "⚛️ Quantum"
DOMAIN = "🌍 Domain Platforms (Health · Climate · Fintech · Civic · Space)"
TOOLS = "🛠️ Tools & Other"

CATEGORY_ORDER = [AI, CV, ML, SCI, QUANTUM, DOMAIN, TOOLS]

# Keyword rules — a repo picks up EVERY category whose keywords match.
KEYWORDS = {
    AI: ["agent", "multi-agent", "crewai", "langgraph", "llm", "rag",
         "knowledge-graph", "knowledge graph", "code review", "copilot",
         "research assistant", "fact-check", "citation", "hallucination",
         "benchmark", "ai "],
    CV: ["vision", "cnn", "pose", "densepose", "camera", "recognition",
         "image", "opencv", "yolo", "detection", "robot", "embodied"],
    ML: ["reinforcement", "fine-tun", "qlora", "machine-learning",
         "machine learning", "deep-learning", "pytorch", "neural",
         "forecasting", "generative", "surrogate"],
    SCI: ["physics", "simulation", "differentiable", "molecular", "chemical",
          "chemistry", "rdkit", "lean 4", "math", "pde", "orbit", "sgp4",
          "propagation", "conjunction", "satellite"],
    QUANTUM: ["quantum", "qema", "pennylane"],
    DOMAIN: ["fhir", "clinical", "healthcare", "prior authorization",
             "banking", "atm", "iso 8583", "fintech", "climate", "ghg",
             "carbon", "political", "legislative", "election", "agriculture",
             "osint", "intelligence platform", "ads-b", "ais", "space operations"],
}

TOPIC_MAP = {
    "computer-vision": CV, "robotics": CV,
    "quantum": QUANTUM, "quantum-computing": QUANTUM,
    "reinforcement-learning": ML, "machine-learning": ML, "deep-learning": ML,
    "ai": AI, "agents": AI, "llm": AI, "rag": AI,
    "simulation": SCI, "physics": SCI, "chemistry": SCI, "space": SCI,
    "healthcare": DOMAIN, "fintech": DOMAIN, "climate": DOMAIN,
}

# Manual overrides where keywords would guess wrong: repo -> list of categories
OVERRIDES = {
    "civisynth": [AI, DOMAIN],
    "omnicanon": [AI],
    "verimathix": [AI, SCI],
    "physweave": [ML, SCI],
    "carbonoscope": [ML, DOMAIN],
    "quantumteller": [QUANTUM, DOMAIN],
    "orbistra": [SCI, DOMAIN],
    "ClearAuth": [DOMAIN],
    "alchemind": [ML, SCI],
    "agrocortex": [AI, CV, DOMAIN],
    "WardSight": [AI, DOMAIN],
    "Foglight": [AI],
    "everycam": [CV],
    "Smart-Trolley": [CV],
    "RuView": [CV],
    "RL_Codesentinel": [ML],
    "Projects": [ML],
    "qemag-validation": [QUANTUM],
    "CodeSentinel": [AI],
    "Cerebro": [AI],
    "medigraph-ai": [AI, DOMAIN],
    "ch09-grounding-agents-in-evidence": [AI],
    "cheese-chase-arcade": [TOOLS],
    "servique-v2": [TOOLS],
    "robust-data-processor": [TOOLS],
    "ideas-you-can-picture": [TOOLS],
    "aravindb98.github.io": [TOOLS],
}

SKIP = {USER, "websiteab"}  # profile repo itself + site repo


def fetch(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": USER})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def categorize(repo):
    """Return the ordered list of categories this repo belongs to."""
    if repo["name"] in OVERRIDES:
        return OVERRIDES[repo["name"]]
    cats = set()
    for t in repo.get("topics") or []:
        if t in TOPIC_MAP:
            cats.add(TOPIC_MAP[t])
    text = (repo["name"] + " " + (repo["description"] or "")).lower()
    for cat, keys in KEYWORDS.items():
        if any(k in text for k in keys):
            cats.add(cat)
    if not cats:
        cats.add(TOOLS)
    return [c for c in CATEGORY_ORDER if c in cats]


def main():
    repos = fetch(f"https://api.github.com/users/{USER}/repos?per_page=100&sort=updated")
    repos = [r for r in repos if not r["fork"] and not r["private"] and r["name"] not in SKIP]

    buckets = {cat: [] for cat in CATEGORY_ORDER}
    for r in repos:
        for cat in categorize(r):
            buckets[cat].append(r)

    lines = []
    for cat in CATEGORY_ORDER:
        if not buckets[cat]:
            continue
        lines.append(f"### {cat}\n")
        lines.append("| Project | Description | Tech |")
        lines.append("|---|---|---|")
        for r in sorted(buckets[cat], key=lambda x: x["name"].lower()):
            desc = (r["description"] or "—").replace("|", "\\|")
            lang = r["language"] or "—"
            lines.append(f"| **[{r['name']}]({r['html_url']})** | {desc} | {lang} |")
        lines.append("")
    block = "\n".join(lines).strip()

    with open(README, encoding="utf-8") as f:
        content = f.read()
    new = re.sub(r"(<!--PROJECTS:START-->)(.*?)(<!--PROJECTS:END-->)",
                 lambda m: f"{m.group(1)}\n{block}\n{m.group(3)}",
                 content, flags=re.S)
    with open(README, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"Updated {README} with {len(repos)} public repos.")


if __name__ == "__main__":
    main()
