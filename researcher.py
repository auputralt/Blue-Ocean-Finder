from __future__ import annotations

import asyncio
import httpx

from config import TAVILY_API_KEY, TAVILY_URL, BRANCHES


# ── Single search call ─────────────────────────────────────

async def _search_tavily(query: str, branch: str) -> dict:
    """Execute one Tavily search and return a normalised result dict."""
    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            resp = await client.post(
                TAVILY_URL,
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "advanced",
                    "include_answer": True,
                    "include_raw_content": False,
                    "max_results": 8,
                    "include_domains": [],
                    "exclude_domains": [],
                },
            )
            resp.raise_for_status()
            body = resp.json()

        results = []
        for item in body.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0.0),
                    "published_date": item.get("published_date", ""),
                }
            )

        # Sort by relevance score descending
        results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        return {
            "branch": branch,
            "query": query,
            "answer": body.get("answer", ""),
            "results": results,
            "error": None,
        }
    except Exception as exc:
        return {
            "branch": branch,
            "query": query,
            "answer": "",
            "results": [],
            "error": f"{type(exc).__name__}: {exc}",
        }


# ── Secondary deep-dive search for cross-referencing ───────

async def _search_secondary(query: str, branch: str) -> dict:
    """Run a follow-up search angled toward financials and market sizing."""
    financial_query = f"{query} market size revenue growth forecast valuation"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                TAVILY_URL,
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": financial_query,
                    "search_depth": "advanced",
                    "include_answer": True,
                    "max_results": 5,
                },
            )
            resp.raise_for_status()
            body = resp.json()

        results = []
        for item in body.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0.0),
                    "published_date": item.get("published_date", ""),
                }
            )

        return {
            "branch": f"{branch}_deep",
            "query": financial_query,
            "answer": body.get("answer", ""),
            "results": results,
            "error": None,
        }
    except Exception:
        return {
            "branch": f"{branch}_deep",
            "query": financial_query,
            "answer": "",
            "results": [],
            "error": "Secondary search unavailable",
        }


# ── Empty placeholder for missing queries ──────────────────

def _empty(branch: str) -> dict:
    return {
        "branch": branch,
        "query": "",
        "answer": "",
        "results": [],
        "error": "No search query was provided for this branch.",
    }


# ── Merge primary + secondary into one enriched branch ─────

def _merge(primary: dict, secondary: dict) -> dict:
    """Merge primary and secondary search into single enriched branch."""
    if primary.get("error"):
        return primary

    merged_results = primary.get("results", [])
    seen_urls = {r["url"] for r in merged_results}

    for r in secondary.get("results", []):
        if r["url"] not in seen_urls:
            merged_results.append(r)
            seen_urls.add(r["url"])

    merged_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

    combined_answer_parts = []
    if primary.get("answer"):
        combined_answer_parts.append(primary["answer"])
    if secondary.get("answer"):
        combined_answer_parts.append(f"[Financial context] {secondary['answer']}")

    return {
        "branch": primary["branch"],
        "query": primary.get("query", ""),
        "answer": " | ".join(combined_answer_parts) if combined_answer_parts else "",
        "results": merged_results[:12],
        "error": None,
    }


# ── Public API ─────────────────────────────────────────────

async def research_all(search_queries: dict[str, str]) -> list[dict]:
    """
    Fire all five Tavily searches in parallel, plus secondary deep-dives
    for financial and market-sizing data. Returns enriched results per branch.
    """
    primary_tasks = []
    secondary_tasks: list = []

    for branch in BRANCHES:
        q = ((search_queries or {}).get(branch) or "").strip()
        if q:
            primary_tasks.append(_search_tavily(q, branch))
            secondary_tasks.append(_search_secondary(q, branch))
        else:
            async def _placeholder(b=branch):
                return _empty(b)
            primary_tasks.append(_placeholder())
            secondary_tasks.append(None)

    raw_primary = await asyncio.gather(*primary_tasks, return_exceptions=True)

    # Only gather secondary tasks that aren't None
    sec_coros = [t for t in secondary_tasks if t is not None]
    raw_secondary_list = await asyncio.gather(*sec_coros, return_exceptions=True) if sec_coros else []

    # Build a map: branch index -> secondary result
    sec_map: dict[int, dict] = {}
    sec_idx = 0
    for i, t in enumerate(secondary_tasks):
        if t is not None:
            r = raw_secondary_list[sec_idx] if sec_idx < len(raw_secondary_list) else None
            if isinstance(r, dict):
                sec_map[i] = r
            sec_idx += 1

    final: list[dict] = []
    for i, r in enumerate(raw_primary):
        if isinstance(r, BaseException):
            final.append(
                {
                    "branch": BRANCHES[i],
                    "query": "",
                    "answer": "",
                    "results": [],
                    "error": f"{type(r).__name__}: {r}",
                }
            )
        else:
            sec = sec_map.get(i)
            if sec and not sec.get("error"):
                final.append(_merge(r, sec))
            else:
                final.append(r)

    return final
