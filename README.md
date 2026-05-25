---
title: AI Blue Ocean Finder
emoji: "\U0001F30A"
colorFrom: blue
colorTo: blue
sdk: gradio
sdk_version: "5.29.0"
app_file: app.py
pinned: false
---

# 🌊 AI Blue Ocean Finder

Discover uncontested market spaces with AI-powered strategic analysis. This tool produces McKinsey/BCG-grade Blue Ocean Strategy reports — market sizing, unit economics, competitive blind spots, go-to-market roadmaps — all grounded in real-time web research.

**Try it live:** [namaakaisekai-ai-blue-ocean-finder.hf.space](https://namaakaisekai-ai-blue-ocean-finder.hf.space)

## What It Does

1. **Research Brief Enhancement** — Turns your industry + location into a hypothesis-driven consulting brief
2. **10x Parallel Web Search** — Runs 10 simultaneous searches (5 primary + 5 financial deep-dives) via Tavily
3. **Blue Ocean Synthesis** — Generates 5 hidden opportunities with TAM→SAM→SOM sizing, unit economics, ERRC frameworks, risk matrices, and 4-phase GTM roadmaps
4. **Follow-up Q&A** — Ask any strategic question and get partner-level answers grounded in the data
5. **Export** — Download as PDF, Word (.docx), or Markdown

## Sample Output Per Opportunity

- 🔍 **Hidden Insight** — Contrarian data-driven opening (McKinsey partner style)
- 📊 **Market Gap Analysis** — TAM/SAM/SOM with methodology, competitive blind spots
- 🎯 **Target Audience Profile** — Demographics, psychographics, willingness-to-pay
- 🔄 **ERRC Value Innovation Grid** — Eliminate/Reduce/Raise/Create with impact
- 💰 **Financial Architecture** — Startup cost breakdown, unit economics (CAC, LTV, payback), revenue projections
- 🚀 **GTM Roadmap** — 4 phases from MVP validation to market dominance
- ⚠️ **Risk Matrix** — Probability × impact with mitigation strategies
- 📎 **Evidence & Sources** — 5+ sourced claims per opportunity

Plus a **Strategic Prioritization Matrix** ranking all 5 by Feasibility, Market Size, Speed, Moat, and Strategic Fit.

## Architecture

```
app.py          — Gradio UI (dark theme, mobile-responsive)
enhancer.py     — LLM prompt engineering (OpenRouter)
researcher.py   — 10x parallel Tavily searches with enrichment
synthesizer.py  — Blue Ocean synthesis + follow-up Q&A (OpenRouter)
exporter.py     — PDF, Word, Markdown export
database.py     — SQLite storage, history, favorites
config.py       — API keys, endpoints, branches
utils.py        — Date, text, formatting helpers
```

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/auputralt/Blue-Ocean-Finder.git
cd Blue-Ocean-Finder
pip install -r requirements.txt
```

### 2. API Keys

Copy `.env.example` to `.env` and add your keys:

```bash
cp .env.example .env
```

You need two API keys (both have free tiers):

| Key | Get It Free | Used For |
|-----|------------|----------|
| `OPENROUTER_API_KEY` | [openrouter.ai](https://openrouter.ai) | LLM calls (prompt enhancement, synthesis, Q&A) |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | Web search (10 parallel searches per analysis) |

### 3. Run

```bash
python app.py
```

Open `http://localhost:7860` in your browser.

## Usage

1. Enter an **industry** (e.g., "Sustainable Fashion") and **location** (e.g., "Southeast Asia")
2. Click **Find Blue Oceans** — the AI generates a research brief
3. Edit the brief if you want to focus the analysis, then click **Confirm & Launch Research**
4. Wait ~60-90 seconds for 10 parallel searches + synthesis
5. Read the report, ask follow-up questions, export to PDF/Word/Markdown

## Deployment

### Hugging Face Spaces (Free, Always-On)

1. Create a new [Gradio Space](https://huggingface.co/new-space)
2. Push this repo to the Space
3. Add `OPENROUTER_API_KEY` and `TAVILY_API_KEY` as Space Secrets

## Tech Stack

- **Frontend:** Gradio (dark theme, mobile-responsive CSS)
- **LLM:** OpenRouter (any model — default: free tier)
- **Search:** Tavily API (advanced search depth)
- **Storage:** SQLite (local, zero config)
- **Export:** fpdf2 (PDF), python-docx (Word), native Markdown

## Requirements

- Python 3.10+
- ~500MB disk space (dependencies + database)

## License

MIT
