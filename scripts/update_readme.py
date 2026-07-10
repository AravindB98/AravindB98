#!/usr/bin/env python3
"""Regenerate the categorized project list in README.md from live GitHub data.

Fetches all PUBLIC, non-fork repos for the user and rewrites the section
between <!--PROJECTS:START--> and <!--PROJECTS:END-->. Any repo flipped from
private to public appears automatically on the next run.

Categorization: GitHub repo topics win (ai, machine-learning, computer-vision,
quantum, reinforcement-learning); otherwise keyword rules on name+description.
"""
import json
import re
import sys
import urllib.request

USER = "AravindB98"
README = sys.argv[1] if len(sys.argv) > 1 else "README.md"

CATEGORIES = [
    ("🤖 AI & Agentic Systems", ["agent", "multi-agent", "crewai", "langgraph",
     "llm", "rag", "knowledge-graph", "knowledge graph", "code review",
     "research assistant", "ai "]),
    ("👁️ Computer Vision", ["vision", "cnn", "pose", "densepose", "camera",
     "recognition", "image", "opencv", "yolo", "detection"]),
    ("🧠 Machine Learning & RL", ["reinforcement", "fine-tun", "qlora",
     "machine-learning", "machine learning", "deep-learning",
     "pytorch", "neural"]),
    ("⚛️ Quantum AI", ["quantum", "qema", "pennylane"]),
    ("🛠️ Tools & Other", []),  # fallback
]

TOPIC_MAP = {
    "computer-vision": "👁️ Computer Vision",
    "quantum": "⚛️ Quantum AI",
    "quantum-computing": "⚛️ Quantum AI",
    "reinforcement-learning": "🧠 Machine Learning & RL",
    "machine-learning": "🧠 Machine Learning & RL",
    "ai": "🤖 AI & Agentic Systems",
    "agents": "🤖 AI & Agentic Systems",
    "llm": "🤖 AI & Agentic Systems",
}

# Manual overrides where keywords would guess wrong
OVERRIDES = {
    "Smart-Trolley": "👁️ Computer Vision",
    "RuView": "👁️ Computer Vision",
    "RL_Codesentinel": "🧠 Machine Learning & RL",
    "Projects": "🧠 Machine Learning & RL",
    "qemag-validation": "⚛️ Quantum AI",
    "CodeSentinel": "🤖 AI & Agentic Systems",
    "Cerebro": "🤖 AI & Agentic Systems",
    "medigraph-ai": "🤖 AI & Agentic Systems",
    "ch09-grounding-agents-in-evidence": "🤖 AI & Agentic Systems",
    "cheese-chase-arcade": "🛠️ Tools & Other",
}

SKIP = {USER, "websiteab"}  # profile repo itself + site repo


def fetch(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": USER})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def categorize(repo):
    if repo["name"] in OVERRIDES:
        return OVERRIDES[repo["name"]]
    for t in repo.get("topics") or []:
        if t in TOPIC_MAP:
            return TOPIC_MAP[t]
    text = (repo["name"] + " " + (repo["description"] or "")).lower()
    for cat, keys in CATEGORIES:
        if any(k in text for k in keys):
            return cat
    return "🛠️ Tools & Other"


def main():
    repos = fetch(f"https://api.github.com/users/{USER}/repos?per_page=100&sort=updated")
    repos = [r for r in repos if not r["fork"] and not r["private"] and r["name"] not in SKIP]

    buckets = {cat: [] for cat, _ in CATEGORIES}
    for r in repos:
        buckets[categorize(r)].append(r)

    lines = []
    for cat, _ in CATEGORIES:
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
