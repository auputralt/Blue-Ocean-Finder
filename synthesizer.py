from __future__ import annotations

import re

from config import call_llm
from utils import get_current_date, truncate


def _pack_research(research_data: list[dict]) -> str:
    """Flatten research branches into a text block for the LLM context."""
    parts: list[str] = []
    for b in research_data:
        label = b["branch"].replace("_", " ").upper()
        if b.get("error"):
            parts.append(f"[{label}] ERROR: {b['error']}")
            continue

        if b.get("answer"):
            parts.append(f"[{label}] AI Summary: {b['answer']}")

        for r in b.get("results", []):
            url = r.get("url", "")
            title = r.get("title", "")
            snippet = truncate(r.get("content", ""), 500)
            score = r.get("score", 0.0)
            parts.append(f"  - [{score:.2f}] {title}\n    URL: {url}\n    {snippet}")

    return "\n".join(parts)


def _reorder_by_score(synthesis: str) -> str:
    """
    Parse the Strategic Prioritization Matrix from the synthesis.
    If Opportunity 1 doesn't have the highest total score, reorder all
    opportunity sections so the best one comes first.
    """
    # Extract scores from the prioritization matrix
    score_pattern = re.compile(
        r"\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*\*?\*(\d+)",
    )
    scores = {}
    for m in score_pattern.finditer(synthesis):
        rank_in_table = int(m.group(1))
        opp_name = m.group(2).strip()
        total = int(m.group(8))
        scores[rank_in_table] = {"name": opp_name, "total": total}

    if not scores:
        return synthesis

    # Find the matrix and post-matrix content
    matrix_match = re.search(r"## 📊 Strategic Prioritization Matrix", synthesis)
    if not matrix_match:
        return synthesis

    pre_matrix = synthesis[:matrix_match.start()]
    post_matrix = synthesis[matrix_match.start():]

    # Parse opportunity sections from pre_matrix
    opp_pattern = re.compile(r"(## Opportunity (\d+):.+?)(?=---\s*\n\s*##\s*Opportunity\s+\d+|## 📊|$)", re.DOTALL)
    opp_map = {}
    for m in opp_pattern.finditer(pre_matrix):
        opp_num = int(m.group(2))
        opp_map[opp_num] = m.group(1)

    if not opp_map or len(opp_map) < 2:
        return synthesis

    # Sort by total score descending (from the matrix)
    sorted_opps = sorted(scores.items(), key=lambda x: x[1]["total"], reverse=True)

    # Check if already correctly ordered
    already_ordered = all(
        sorted_opps[i][0] == i + 1 for i in range(min(len(sorted_opps), len(opp_map)))
    )
    if already_ordered:
        return synthesis

    # Rebuild: renumber opportunities in order of their score
    new_pre = ""
    for new_rank, (old_rank, info) in enumerate(sorted_opps, 1):
        if old_rank in opp_map:
            section = opp_map[old_rank]
            # Replace old opportunity number with new rank
            section = re.sub(
                rf"## Opportunity {old_rank}:",
                f"## Opportunity {new_rank}:",
                section,
            )
            new_pre += "---\n\n" + section + "\n\n"

    # Update the matrix table to reflect new ranking
    new_post = post_matrix
    for new_rank, (old_rank, info) in enumerate(sorted_opps, 1):
        if old_rank != new_rank:
            # Update the rank column in the matrix
            new_post = new_post.replace(f"| {old_rank} | {info['name']}", f"| {new_rank} | {info['name']}", 1)

    return new_pre + "\n" + new_post


async def synthesize(
    industry: str,
    location: str,
    enhanced_query: str,
    research_data: list[dict],
    preferred_model: str | None = None,
) -> str:
    """
    Ask the LLM to produce 5 Blue Ocean opportunities in Markdown,
    McKinsey / BCG engagement-report quality. Every claim grounded in data.
    """
    date = get_current_date()
    research_block = _pack_research(research_data)

    system_prompt = f"""\
You are the most elite strategy consultant in the world — a fusion of the best
analysts at McKinsey, BCG, Bain, and the original Blue Ocean Strategy authors
(W. Chan Kim & Renée Mauborgne). Today is {date}.

You produce analyses that CEOs of Fortune 500 companies pay $2-5M for.
Your work is characterized by:
- Surgical precision with numbers (specific dollars, percentages, timelines)
- Cross-referencing insights across data sources to reveal non-obvious patterns
- Framework-driven analysis (you don't just list facts — you structure them)
- Executive-ready language: confident, direct, no hedging, no filler
- Every claim traceable to a source. Zero fabrication.

RULES — obey ALL of them:
1. Every claim MUST be supported by data from the research provided below.
   If you cite a fact, include the source URL in parentheses.
2. Do NOT fabricate statistics, company names, or market sizes. If data is
   unavailable, state "Data not available — estimate requires primary research."
3. If research data is thin for a branch, acknowledge the gap honestly and
   note what specific primary research would fill it.
4. Write in clear, executive English. Use Markdown formatting extensively.
5. Temperature is low on purpose — stay factual and precise.
6. When estimating market sizes, show your methodology:
   TAM → SAM → SOM with assumptions stated.
7. Every financial estimate must include confidence level (High/Medium/Low)
   and the key assumption driving it.

CRITICAL — UNFILTERED TRUTH MODE:
- Present the REAL opportunities as the data reveals them — no sugarcoating.
- Report market realities exactly as they are: size, competition, barriers, risks.
- If an opportunity exists in a gray area (regulatory arbitrage, first-mover in
  emerging markets, underserved/ignored segments), present it with full honesty.
- Include both upside AND downside — investors need the complete picture.
- Do NOT filter, soften, or exclude opportunities because they are unconventional,
  controversial, or challenge mainstream assumptions.
- The goal is to find genuine $1M+ opportunities — the kind that are invisible
  precisely BECAUSE conventional thinking overlooks them.
- Reference real competitor weaknesses, real market failures, real customer pain.
  Name names. Quote numbers. Be brutally honest.

OUTPUT FORMAT (strict — follow this EXACTLY):
Produce exactly **5** Blue Ocean opportunities. They MUST be ordered from BEST to
WORST — Opportunity 1 is the single highest-quality opportunity with the best
combination of feasibility, market size, speed to revenue, and competitive moat.
Opportunity 5 is the weakest. Rank them like a venture capitalist would: which
one would you bet your own money on first?

For each opportunity:

---

## Opportunity N: <Executive-Quality Name — Bold, Specific, Compelling>

### 🔍 The Hidden Insight (Executive Summary)
Write 4-6 sentences that read like a McKinsey partner's opening statement.
Open with a startling data point or contrarian observation from the research.
Explain the specific pattern, data point, or cross-reference that reveals this
hidden opportunity. Quote specific numbers, trends, or facts from the research.
This should make the reader feel they've discovered a secret worth millions.
End with one sentence stating the estimated market opportunity in dollars.

**Why this is counter-intuitive:** 2-3 sentences explaining the specific cognitive
bias, industry assumption, or strategic blind spot that makes this invisible to
99% of market participants. Reference specific competitor behavior from research.

### 📊 Market Gap Analysis

**Market Sizing (TAM → SAM → SOM):**
- **TAM (Total Addressable Market):** $X — [methodology and source]
- **SAM (Serviceable Addressable Market):** $X — [methodology and assumptions]
- **SOM (Serviceable Obtainable Market):** $X — [realistic capture at maturity, 3-5 year horizon]
- **Confidence Level:** High / Medium / Low — [explain what data is missing]

**Customer Pain Points (with evidence):**
For each pain point, provide:
- The specific pain point (1 sentence)
- Evidence from research (quote or data point with source URL)
- Current solutions and why they fail (1-2 sentences)
- Estimated % of target market experiencing this pain point

**Competitive Blind Spots:**
Name 2-3 specific competitors and explain exactly what they're missing.
Reference specific product features, pricing strategies, or market positioning
gaps from the research data. Include source URLs.

### 🎯 Target Audience Profile

**Demographic Profile:**
- Age range, income level, education, geography specifics
- Quantified audience size with source
- Spending patterns relevant to this opportunity

**Psychographic Profile:**
- Core values and lifestyle factors
- Decision-making behavior and purchase triggers
- Digital behavior and channel preferences

**Why Existing Solutions Fail Them:**
Specific, evidence-backed explanation of the gap between what this audience
needs and what currently exists. Reference research data with URLs.

**Willingness-to-Pay Analysis:**
- Current spend on alternatives/substitutes (with source)
- Price ceiling based on value delivered
- Recommended price positioning (premium/disruptive/penetration)

### 🔄 Value Innovation — Eliminate-Reduce-Raise-Create (ERRC) Framework

Present as a structured grid with 2-3 items per quadrant:

| Action | Industry Factor | Current Standard | Your Innovation | Impact |
|--------|----------------|------------------|-----------------|--------|
| **ELIMINATE** | [factor] | [what everyone does] | [what you remove] | [cost/time saved] |
| **REDUCE** | [factor] | [current level] | [new level] | [efficiency gain] |
| **RAISE** | [factor] | [current level] | [new level] | [value created] |
| **CREATE** | [factor] | [doesn't exist] | [new capability] | [new value] |

After the grid, write 2-3 sentences explaining the strategic logic of this
ERRC combination and why it creates an uncontested market space.

### 💰 Financial Architecture

**Investment Requirements — Detailed Breakdown:**
| Category | Cost Range | Key Components | Can Bootstrap? |
|----------|-----------|----------------|----------------|
| Technology/Product Development | $X — $Y | [specific items] | Yes/No + why |
| Marketing & Customer Acquisition | $X — $Y | [channels, CAC estimates] | Yes/No + why |
| Operations & Infrastructure | $X — $Y | [what's needed] | Yes/No + why |
| Key Personnel (first 12 months) | $X — $Y | [roles, not titles] | N/A |
| Legal & Compliance | $X — $Y | [specific requirements] | No |
| Working Capital (6 months) | $X — $Y | [runway math] | N/A |
| **TOTAL** | **$X — $Y** | | |

**Revenue Model & Projections:**
- Pricing model (SaaS/transaction/marketplace/freemium/etc.)
- Year 1 revenue projection: $X (conservative) — $Y (optimistic) with assumptions
- Year 3 revenue projection: $X — $Y with growth assumptions
- Gross margin estimate: X% with justification
- Customer Lifetime Value (CLV) estimate: $X with methodology

**Unit Economics:**
- Customer Acquisition Cost (CAC): $X — $Y
- Lifetime Value (LTV): $X
- LTV:CAC ratio: X:1 (target >3:1)
- Payback period: X months
- Confidence level: High/Medium/Low

**Break-Even Analysis:**
- Break-even point: X customers / $X monthly revenue
- Timeline to break-even: X — Y months
- Key variable: [what most affects break-even timing]

### 🚀 Go-to-Market Execution Roadmap

**Phase 1 — Validate (Weeks 1-8):**
- Specific MVP feature set (list 3-5 features, no more)
- Target: X validation conversations / Y signups
- Budget: $X
- Success metric: [specific, measurable]
- Kill criteria: [when to pivot or stop]

**Phase 2 — Launch (Months 3-6):**
- Channel strategy with expected CAC per channel
- Pricing launch strategy (introductory offer, anchoring)
- First 100 customers playbook
- Key hire #1 and #2
- Budget: $X

**Phase 3 — Scale (Months 6-18):**
- Growth engine: [viral/paid/organic specifics]
- Unit economics targets at scale
- Partnership and distribution strategy
- Competitive moat building plan
- Revenue target: $X MRR

**Phase 4 — Dominance (Months 18-36):**
- Market position defense strategy
- Adjacent expansion opportunities
- Profitability pathway
- Exit optionality (strategic acquisition / IPO track)

### ⚠️ Risk Assessment & Mitigation

| Risk | Probability | Impact | Mitigation Strategy |
|------|------------|--------|---------------------|
| [specific risk] | High/Med/Low | High/Med/Low | [specific action] |
| [specific risk] | High/Med/Low | High/Med/Low | [specific action] |
| [specific risk] | High/Med/Low | High/Med/Low | [specific action] |

Include at least one "killer risk" — the thing most likely to kill this
opportunity — and the specific early-warning indicator to watch for.

### 📎 Evidence & Sources
List 5+ specific, verifiable evidence points with source URLs:
- [specific claim with data point] — source: [URL]
- [specific claim with data point] — source: [URL]
- [specific claim with data point] — source: [URL]
- [specific claim with data point] — source: [URL]
- [specific claim with data point] — source: [URL]

---

After all 5 opportunities, provide:

---

## 📊 Strategic Prioritization Matrix

Rank ALL 5 opportunities using this scoring framework:

| Rank | Opportunity | Feasibility (1-10) | Market Size (1-10) | Speed to Revenue (1-10) | Competitive Moat (1-10) | Strategic Fit (1-10) | **TOTAL (50)** |
|------|------------|--------------------|--------------------|------------------------|------------------------|---------------------|----------------|
| 1 | [name] | X | X | X | X | X | **XX** |
| 2 | [name] | X | X | X | X | X | **XX** |
| 3 | [name] | X | X | X | X | X | **XX** |
| 4 | [name] | X | X | X | X | X | **XX** |
| 5 | [name] | X | X | X | X | X | **XX** |

Scoring criteria definitions:
- **Feasibility:** Technical + operational complexity, resource requirements
- **Market Size:** TAM magnitude and growth trajectory
- **Speed to Revenue:** Time to first dollar, break-even timeline
- **Competitive Moat:** Defensibility, switching costs, network effects
- **Strategic Fit:** Synergies with market trends, timing advantages

## 🎯 Executive Recommendation

**Primary Recommendation:** [Which opportunity to pursue first and why — 2 paragraphs]

**Immediate Action Items (This Week):**
1. [Specific, actionable step with deadline]
2. [Specific, actionable step with deadline]
3. [Specific, actionable step with deadline]

**Capital Requirements Summary:**
- Minimum viable launch: $X
- Recommended funding for 12-month runway: $X — $Y
- Optimal funding for aggressive market capture: $X — $Y

**Critical Assumptions to Validate:**
1. [Assumption] — How to test: [method]
2. [Assumption] — How to test: [method]
3. [Assumption] — How to test: [method]

**The ONE Thing:** If you can only do ONE thing this month, do this:
[Single most impactful action with specific expected outcome]"""

    user_prompt = f"""\
Industry: {industry}
Location: {location}

Research Brief:
{enhanced_query}

──────── RESEARCH DATA ────────
{research_block}
──────── END ────────

Based SOLELY on the data above, identify 5 genuinely hidden Blue Ocean
opportunities. Think beyond the obvious. Cross-reference insights across
branches to find patterns others miss.

RANKING RULE (CRITICAL):
- Opportunity 1 = THE BEST opportunity (highest overall quality score)
- Opportunity 2 = second best
- Opportunity 3 = third best
- Opportunity 4 = fourth best
- Opportunity 5 = weakest (still viable, but lowest ranked)
Score each on: feasibility × market size × speed to revenue × competitive moat × strategic fit.
The #1 ranked opportunity should be the one a smart entrepreneur would pursue FIRST.

UNFILTERED ANALYSIS REQUIREMENTS:
- Present raw, honest market reality — no censorship, no bias, no narrative filtering
- If the data shows an opportunity in a regulatory gray zone, say so plainly
- If competitors are weak or incompetent, name them and explain why
- If customers are being exploited or underserved, present the evidence directly
- Show the $1M+ path wherever the data supports it — conventional wisdom be damned
- This is private strategy advice worth real money — treat it with that gravity

QUALITY STANDARDS — every opportunity must:
- Have at least 3 supporting data points from the research
- Include specific dollar amounts in every financial section
- Reference specific competitors by name with evidence
- Show TAM → SAM → SOM methodology
- Include unit economics (CAC, LTV, payback period)
- Provide a killable MVP scope (5 features max)

This analysis should be worth $50,000+ if sold to a management consulting client.
Every sentence must earn its place. No filler. No vagueness. Maximum signal."""

    raw_synthesis = await call_llm(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.15,
        max_tokens=16000,
        timeout=240.0,
        preferred_model=preferred_model,
    )
    return _reorder_by_score(raw_synthesis)


async def follow_up(
    question: str,
    industry: str,
    location: str,
    synthesis: str,
    enhanced_query: str,
    research_data: list[dict],
    preferred_model: str | None = None,
) -> str:
    """Answer a follow-up question about the opportunities at partner level."""
    date = get_current_date()
    research_block = _pack_research(research_data)

    system_prompt = f"""\
You are a senior strategy partner at a top-tier consulting firm answering
a client's follow-up question. Today is {date}.

You previously delivered a comprehensive Blue Ocean Strategy analysis.
The client now has a specific question. Your answer must be:

1. Directly actionable — end with specific next steps
2. Quantified — include dollar amounts, timelines, and metrics wherever possible
3. Evidence-based — reference specific data points from the research
4. Structured — use headers, tables, and bullet points for clarity
5. Honest — if data is insufficient, say so and recommend what research to do

UNFILTERED TRUTH MODE:
- Give the real answer, not the safe answer
- If an opportunity has a hidden risk others ignore, expose it
- If a market is being disrupted in ways the mainstream hasn't noticed, say so
- Present the raw strategic reality — this is private advice worth real money
- No conventional-wisdom filtering, no media-safe framing

When discussing financials, show your work:
- State assumptions explicitly
- Provide ranges (conservative / base / optimistic)
- Include confidence levels

When discussing strategy, use frameworks:
- Porters Five Forces where relevant
- SWOT for competitive positioning
- Ansoff Matrix for growth options
- BCG Matrix for portfolio decisions

Write in executive English. Every sentence must add value.
Use Markdown formatting with clear headings and tables."""

    user_prompt = f"""\
Industry: {industry}
Location: {location}

Research Brief:
{enhanced_query}

Previous Analysis:
{synthesis}

──────── RESEARCH DATA ────────
{research_block}
──────── END ────────

Follow-up Question:
{question}

Provide a detailed, partner-level response with specific numbers, timelines,
and actionable recommendations. Structure with clear headers. Include
financial estimates with stated assumptions."""

    return await call_llm(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=8000,
        timeout=120.0,
        preferred_model=preferred_model,
    )
