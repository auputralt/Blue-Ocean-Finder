from __future__ import annotations

import json
import re

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_URL
from utils import get_current_date, get_current_year


async def enhance_prompt(industry: str, location: str) -> dict:
    """
    Ask the LLM to turn raw user input into a structured McKinsey-grade
    research brief + eight targeted search queries covering market structure,
    financials, customer psychographics, and competitive blind spots.

    Returns dict with keys:
        enhanced_query   – human-readable research brief
        search_queries   – {branch_name: query_string, ...}
    """
    year = get_current_year()
    date = get_current_date()

    system_prompt = f"""\
You are a senior partner at a top-tier strategy consulting firm (McKinsey, BCG, Bain).
Today is {date} (year {year}).

TASK: Given an industry and a geographic location, produce a single
valid JSON object (no markdown fences) with exactly two top-level keys:

1. "enhanced_query"  – A 4-6 sentence executive research brief. Write like a
   McKinsey engagement memo: precise, data-oriented, hypothesis-driven. Identify
   the key strategic question, the market context, what makes this space interesting
   NOW, and what specific angles to investigate. Reference {year} dynamics.

2. "search_queries"  – An object with exactly these five keys,
   each holding ONE highly specific, data-dense search query optimized for
   finding financial data, market sizing, and actionable intelligence.
   Include "{year}" and the location name in EVERY query:

   "dominant_players"
       Find: market share data, revenue figures, funding rounds, M&A activity,
       competitive positioning maps. Include specific company names and numbers.
       Target query angle: "[industry] [location] market leaders revenue market share {year}"

   "overlooked_customers"
       Find: underserved demographics, unmet needs, psychographic profiles,
       spending patterns, customer segments competitors ignore.
       Target: specific pain points with willingness-to-pay data.

   "substitute_industries"
       Find: alternative solutions, adjacent markets, cross-industry competition,
       substitution economics, why customers defect to alternatives.
       Include market sizing of substitute markets.

   "trends"
       Find: technology shifts, regulatory changes, consumer behavior data,
       investment trends, CAGR projections, TAM/SAM estimates.
       Focus on data points with specific percentages and dollar figures.

   "product_gaps"
       Find: unmet needs, feature gaps, customer complaints, NPS data,
       product reviews analysis, specific pain points with frequency data.
       Target quantifiable gaps (e.g., "73% of users report X").

CRITICAL QUERY DESIGN RULES:
- Each query must be search-engine-optimized for finding NUMBERS and DATA, not opinions
- Include specific financial terms: "market size", "revenue", "growth rate", "valuation"
- Include the location AND year in every single query
- Target authoritative sources: McKinsey, BCG, Statista, Crunchbase, industry reports
- Each query should be 15-30 words, highly specific

Return ONLY the JSON object, nothing else."""

    user_msg = f"Industry: {industry}\nLocation: {location}"

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.15,
                "max_tokens": 1500,
            },
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        if not raw:
            raise ValueError("LLM returned empty response. Model may be rate-limited or unavailable. Try again in a moment.")

    # ── Parse JSON (handle fenced code blocks gracefully) ──
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[\w]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
        else:
            raise ValueError(f"LLM did not return valid JSON:\n{raw[:500]}")

    # Validate required keys exist
    if "enhanced_query" not in parsed or "search_queries" not in parsed:
        raise ValueError(f"LLM response missing required keys:\n{cleaned[:500]}")

    return parsed
