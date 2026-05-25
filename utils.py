from __future__ import annotations

import re
from datetime import datetime, timezone


# ── Date helpers ───────────────────────────────────────────

def get_current_date() -> str:
    """Full human-readable date, e.g. 'May 25, 2026'."""
    return datetime.now(timezone.utc).strftime("%B %d, %Y")


def get_current_year() -> int:
    return datetime.now(timezone.utc).year


# ── Text helpers ───────────────────────────────────────────

def clean_text(text: str) -> str:
    """Collapse whitespace and strip."""
    if not text:
        return ""
    return " ".join(text.split()).strip()


def truncate(text: str, max_len: int = 800) -> str:
    if not text or len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + " …"


# ── Research display formatter ─────────────────────────────

_BRANCH_LABELS = {
    "dominant_players": "🏢 Dominant Players & Market Structure",
    "overlooked_customers": "👥 Overlooked Customer Segments",
    "substitute_industries": "🔄 Substitute Industries & Adjacent Markets",
    "trends": "📈 Emerging Trends, Regulation & Technology Shifts",
    "product_gaps": "🧩 Product Gaps & Unmet Needs",
    "dominant_players_deep": "🏢 Deep-Dive: Financials & Valuations",
    "overlooked_customers_deep": "👥 Deep-Dive: Customer Economics",
    "substitute_industries_deep": "🔄 Deep-Dive: Substitution Dynamics",
    "trends_deep": "📈 Deep-Dive: Market Sizing & Forecasts",
    "product_gaps_deep": "🧩 Deep-Dive: Gap Quantification",
}

_BRANCH_ICONS = {
    "dominant_players": "🏢",
    "overlooked_customers": "👥",
    "substitute_industries": "🔄",
    "trends": "📈",
    "product_gaps": "🧩",
}


def _relevance_badge(score: float) -> str:
    """Return a relevance indicator based on Tavily score."""
    if score >= 0.8:
        return "🟢 High"
    elif score >= 0.5:
        return "🟡 Medium"
    else:
        return "🔴 Low"


def format_raw_research(data: list[dict]) -> str:
    """Render research branches as a premium Markdown report."""
    sections: list[str] = []

    # Executive summary line
    total_results = sum(len(b.get("results", [])) for b in data)
    successful = sum(1 for b in data if not b.get("error"))
    sections.append(
        f"### 📋 Research Summary\n\n"
        f"**{total_results} sources** across **{successful}/{len(data)}** branches "
        f"analyzed.\n"
    )

    for branch in data:
        name = branch.get("branch", "unknown")
        # Skip deep-dive branches in display (data already merged)
        if name.endswith("_deep"):
            continue

        label = _BRANCH_LABELS.get(name, name.replace("_", " ").title())
        icon = _BRANCH_ICONS.get(name, "📌")
        lines = [f"\n### {label}\n"]

        if branch.get("error"):
            lines.append(f"> ⚠️ **Error:** {branch['error']}\n")
            sections.append("\n".join(lines))
            continue

        if branch.get("answer"):
            lines.append(f"> 💡 **AI Synthesis:** {branch['answer']}\n")

        results = branch.get("results", [])
        if results:
            lines.append(f"**{len(results)} sources found:**\n")

        for i, r in enumerate(results[:8], 1):
            title = r.get("title", "Untitled")
            url = r.get("url", "#")
            snippet = truncate(r.get("content", ""), 350)
            score = r.get("score", 0.0)
            badge = _relevance_badge(score)

            lines.append(f"{i}. **[{title}]({url})** {badge}")
            if snippet:
                lines.append(f"   > {snippet}\n")

        if not results:
            lines.append("_No results returned._\n")

        sections.append("\n".join(lines))

    return "\n\n---\n\n".join(sections)
