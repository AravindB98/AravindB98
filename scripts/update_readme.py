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

AGENTS = "🤖 LLMs, RAG & Agents"
PHYSICAL = "🦾 Physical AI & Robotics"
CV = "👁️ Computer Vision"
ML = "🧠 Machine Learning & RL"
CLIMATE = "🌡️ Climate AI"
AGRI = "🌾 Agriculture AI"
HEALTH = "🏥 Healthcare AI"
FINTECH = "💳 Fintech AI"
CIVIC = "🏛️ Civic & Policy AI"
SPACE = "🛰️ Space Tech"
SECURITY = "🕵️ Security & Intelligence AI"
QUANTUM = "⚛️ Quantum Computing"
SCI = "🔬 Scientific AI & Simulation"
KNOWLEDGE = "📖 Knowledge & Education AI"
CLOUD = "☁️ Cloud, Data & Backend Engineering"
GAMES = "🎮 Games & Creative"
WEB = "🌐 Websites & Portfolio"
TOOLS = "🛠️ Tools & Other"

CATEGORY_ORDER = [AGENTS, PHYSICAL, CV, ML, CLIMATE, AGRI, HEALTH, FINTECH,
                  CIVIC, SPACE, SECURITY, QUANTUM, SCI, KNOWLEDGE, CLOUD,
                  GAMES, WEB, TOOLS]

# Keyword rules — a repo picks up EVERY category whose keywords match.
KEYWORDS = {
    AGENTS: ["agent", "multi-agent", "crewai", "langgraph", "llm", "rag",
             "knowledge-graph", "knowledge graph", "copilot", "gpt",
             "research assistant", "fact-check", "citation", "hallucination",
             "prompt", "retrieval"],
    PHYSICAL: ["robot", "embodied", "raspberry pi", "edge-ai", "edge ai",
               "iot", "sensor", "drone"],
    CV: ["vision", "cnn", "pose", "densepose", "camera", "recognition",
         "image", "opencv", "yolo", "detection", "segmentation"],
    ML: ["reinforcement", "fine-tun", "qlora", "machine-learning",
         "machine learning", "deep-learning", "pytorch", "neural",
         "forecasting", "generative", "surrogate", "benchmark"],
    CLIMATE: ["climate", "ghg", "carbon", "emission", "grid carbon"],
    AGRI: ["agriculture", "agro", "crop", "plant-disease", "farm"],
    HEALTH: ["health", "clinical", "fhir", "hl7", "medical", "prior auth",
             "patient", "hospital"],
    FINTECH: ["banking", "atm", "iso 8583", "fintech", "payment", "fraud",
              "trading", "cobol"],
    CIVIC: ["political", "legislative", "election", "civic", "policy",
            "government"],
    SPACE: ["space", "orbit", "satellite", "sgp4", "conjunction",
            "spacecraft"],
    SECURITY: ["vulnerability", "security", "osint", "intelligence fusion",
               "threat", "ads-b", "surveillance", "quantum-safe"],
    QUANTUM: ["quantum", "qema", "pennylane", "qiskit"],
    SCI: ["physics", "simulation", "differentiable", "molecular", "chemical",
          "chemistry", "rdkit", "lean 4", "math", "pde", "propagation",
          "scientific"],
    KNOWLEDGE: ["book", "education", "corpus", "sacred", "learning platform",
                "course", "chapter"],
    CLOUD: ["gcp", "aws", "azure", "cloud run", "pipeline", "ingestion",
            "kubernetes", "docker", "backend", "api platform", "pub/sub"],
    GAMES: ["game", "arcade", "puzzle"],
    WEB: ["website", "portfolio", "profile page", "landing"],
}

TOPIC_MAP = {
    "computer-vision": CV, "robotics": PHYSICAL,
    "quantum": QUANTUM, "quantum-computing": QUANTUM,
    "reinforcement-learning": ML, "machine-learning": ML, "deep-learning": ML,
    "ai": AGENTS, "agents": AGENTS, "llm": AGENTS, "rag": AGENTS,
    "simulation": SCI, "physics": SCI, "chemistry": SCI,
    "space": SPACE, "healthcare": HEALTH, "fintech": FINTECH,
    "climate": CLIMATE, "agriculture": AGRI, "security": SECURITY,
    "game": GAMES, "website": WEB, "cloud": CLOUD,
}

# Manual overrides where keywords would guess wrong: repo -> list of categories
OVERRIDES = {
    "Cerebro": [AGENTS],
    "CodeSentinel-v1": [AGENTS, SECURITY],
    "CodeSentinel-v2": [AGENTS, SECURITY],
    "QueryCraft": [AGENTS, ML],
    "LLM-Agents-Deep-Q-Learning-Atari": [AGENTS, ML],
    "MediGraphAI": [AGENTS, HEALTH],
    "CareHub": [HEALTH],
    "ServiQue": [CLOUD, WEB],
    "RL_Codesentinel": [AGENTS, ML, SECURITY],
    "ch09-grounding-agents-in-evidence": [AGENTS, KNOWLEDGE],
    "medigraph-ai": [AGENTS, HEALTH],
    "civisynth": [AGENTS, CIVIC],
    "omnicanon": [AGENTS, KNOWLEDGE],
    "Foglight": [AGENTS, SECURITY],
    "WardSight": [AGENTS, SECURITY],
    "agrocortex": [AGENTS, CV, AGRI],
    "verimathix": [AGENTS, SCI],
    "everycam": [PHYSICAL, CV],
    "RuView": [PHYSICAL, CV],
    "Smart-Trolley": [PHYSICAL, CV],
    "Projects": [ML],
    "physweave": [ML, SCI],
    "alchemind": [ML, SCI],
    "carbonoscope": [ML, CLIMATE],
    "ClearAuth": [HEALTH, FINTECH],
    "quantumteller": [FINTECH, QUANTUM, CLOUD],
    "orbistra": [SPACE, SCI],
    "qemag-validation": [QUANTUM],
    "robust-data-processor": [CLOUD],
    "servique-v2": [CLOUD, WEB],
    "cheese-chase-arcade": [GAMES],
    "ideas-you-can-picture": [WEB, KNOWLEDGE],
    "aravindb98.github.io": [WEB],
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
