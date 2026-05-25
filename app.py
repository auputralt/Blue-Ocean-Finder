from __future__ import annotations

import asyncio
import tempfile
import io
from pathlib import Path
from typing import Optional

import gradio as gr

from config import validate_config
from database import init_db, save_report, list_reports, get_report, toggle_favorite, delete_report
from enhancer import enhance_prompt
from researcher import research_all
from synthesizer import synthesize, follow_up
from exporter import generate_markdown, generate_docx, generate_pdf
from utils import format_raw_research

init_db()


# ════════════════════════════════════════════════════════════
#  THEME & CSS
# ════════════════════════════════════════════════════════════

THEME = gr.themes.Soft(
    primary_hue="cyan",
    secondary_hue="sky",
    neutral_hue="slate",
    font=gr.themes.GoogleFont("DM Sans"),
    font_mono=gr.themes.GoogleFont("JetBrains Mono"),
).set(
    body_background_fill_dark="#060c18",
    block_background_fill_dark="rgba(10, 18, 36, 0.85)",
    block_border_color_dark="rgba(56, 189, 248, 0.12)",
    block_label_text_color_dark="#94a3b8",
    block_title_text_color_dark="#e2e8f0",
    input_background_fill_dark="rgba(15, 23, 42, 0.9)",
    input_border_color_dark="rgba(56, 189, 248, 0.2)",
    button_primary_background_fill_dark="linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%)",
    button_primary_background_fill_hover_dark="linear-gradient(135deg, #38bdf8 0%, #22d3ee 100%)",
    button_primary_text_color_dark="#ffffff",
    button_secondary_background_fill_dark="rgba(14, 165, 233, 0.12)",
    button_secondary_background_fill_hover_dark="rgba(14, 165, 233, 0.22)",
    button_secondary_text_color_dark="#7dd3fc",
    checkbox_background_color_dark="rgba(14, 165, 233, 0.15)",
    slider_color_dark="#0ea5e9",
)

CUSTOM_CSS = """
/* ── Global mobile reset ──────────────────────────────── */
*, *::before, *::after { box-sizing:border-box; }
html { -webkit-text-size-adjust:100%; }
body { overflow-x:hidden; }

/* ── Hero ──────────────────────────────────────────────── */
.hero  { text-align:center; padding:1.8rem 0 0.4rem; }
.hero h1 {
    font-size:2.6rem; font-weight:800; letter-spacing:-0.03em;
    background:linear-gradient(135deg,#38bdf8 0%,#0ea5e9 35%,#06b6d4 70%,#14b8a6 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text; margin:0;
}
.hero p { color:#64748b; font-size:1.05rem; margin-top:0.25rem; }

/* ── Animated accent bar ─────────────────────────────── */
.wave-bar {
    height:3px; border-radius:2px; margin:0 auto 1.2rem;
    max-width:280px;
    background:linear-gradient(90deg,#0ea5e9,#06b6d4,#14b8a6,#0ea5e9);
    background-size:200% 100%;
    animation:waveSlide 3s linear infinite;
}
@keyframes waveSlide {
    0%  { background-position:0% 50%; }
    100%{ background-position:200% 50%; }
}

/* ── Status box ──────────────────────────────────────── */
.status-box {
    padding:0.85rem 1.25rem; border-radius:10px;
    background:rgba(14,165,233,0.08);
    border:1px solid rgba(14,165,233,0.18);
    font-weight:500; color:#7dd3fc; font-size:0.95rem;
    word-break:break-word;
}
.status-box.working {
    animation:pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.6} }

/* ── Results card ────────────────────────────────────── */
.results-card {
    background:rgba(8,15,30,0.7);
    backdrop-filter:blur(12px);
    border:1px solid rgba(56,189,248,0.1);
    border-radius:14px; padding:1.8rem;
    overflow-wrap:break-word;
    word-break:break-word;
}

/* ── Primary CTA glow ───────────────────────────────── */
.glow-btn {
    box-shadow:0 4px 18px rgba(14,165,233,0.35) !important;
    transition:all 0.25s ease !important;
    min-height:48px !important;
}
.glow-btn:hover {
    transform:translateY(-2px) !important;
    box-shadow:0 8px 28px rgba(14,165,233,0.5) !important;
}
@media (hover:none) {
    .glow-btn:hover { transform:none !important; }
}

/* ── Markdown inside results ─────────────────────────── */
.results-card h1, .results-card h2, .results-card h3 {
    color:#38bdf8 !important;
}
.results-card a { color:#22d3ee !important; }
.results-card strong { color:#e2e8f0 !important; }
.results-card p { color:#cbd5e1 !important; line-height:1.7 !important; }
.results-card ul, .results-card ol { color:#cbd5e1 !important; }
.results-card hr { border-color:rgba(56,189,248,0.15) !important; }

/* ── Section separator ───────────────────────────────── */
.section-sep {
    border:0; height:1px;
    background:linear-gradient(90deg,transparent,rgba(56,189,248,0.2),transparent);
    margin:1.2rem 0;
}

/* ── Editable brief textarea ──────────────────────────── */
.brief-area textarea {
    background:rgba(15,23,42,0.95) !important;
    border:1px solid rgba(56,189,248,0.25) !important;
    border-radius:10px !important;
    color:#e2e8f0 !important;
    font-size:16px !important;
    line-height:1.6 !important;
    padding:1rem !important;
}
.brief-area textarea:focus {
    border-color:rgba(56,189,248,0.5) !important;
    box-shadow:0 0 0 2px rgba(14,165,233,0.15) !important;
}

/* ── Q&A Chat ─────────────────────────────────────────── */
.chat-area {
    background:rgba(8,15,30,0.6) !important;
    border-radius:12px !important;
    border:1px solid rgba(56,189,248,0.1) !important;
}
.chat-input textarea {
    background:rgba(15,23,42,0.9) !important;
    border:1px solid rgba(56,189,248,0.2) !important;
    border-radius:10px !important;
    color:#e2e8f0 !important;
    font-size:16px !important;
}

/* ── Export buttons ───────────────────────────────────── */
.export-btn {
    min-width:140px !important;
    min-height:44px !important;
}

/* ── Footer ──────────────────────────────────────────── */
.footer-text { text-align:center; color:#334155; font-size:0.8rem; padding:1rem 0 2rem; }

/* ── Input fields — prevent zoom on iOS ──────────────── */
input[type="text"], textarea, select {
    font-size:16px !important;
}

/* ══════════════════════════════════════════════════════════
   TABLET — max 768px
   ══════════════════════════════════════════════════════════ */
@media (max-width:768px) {
    .hero { padding:1.2rem 0.5rem 0.3rem; }
    .hero h1 { font-size:1.9rem; }
    .hero p { font-size:0.92rem; }
    .wave-bar { max-width:200px; }

    .results-card {
        padding:1.2rem 0.9rem;
        border-radius:10px;
    }

    .status-box {
        padding:0.7rem 0.9rem;
        font-size:0.88rem;
    }

    .brief-area textarea { padding:0.8rem !important; }

    .chat-area { border-radius:8px !important; }

    .section-sep { margin:0.8rem 0; }
}

/* ══════════════════════════════════════════════════════════
   MOBILE — max 480px
   ══════════════════════════════════════════════════════════ */
@media (max-width:480px) {
    .hero { padding:0.8rem 0.25rem 0.2rem; }
    .hero h1 { font-size:1.45rem; letter-spacing:-0.02em; }
    .hero p { font-size:0.82rem; }
    .wave-bar { max-width:150px; height:2px; margin-bottom:0.8rem; }

    .results-card {
        padding:0.9rem 0.7rem;
        border-radius:8px;
    }

    .status-box {
        padding:0.6rem 0.75rem;
        font-size:0.82rem;
        border-radius:8px;
    }

    .brief-area textarea {
        padding:0.6rem !important;
        line-height:1.5 !important;
    }

    .section-sep { margin:0.6rem 0; }

    /* Force Gradio rows to stack on mobile */
    [data-testid="row"] {
        flex-direction:column !important;
        gap:0.5rem !important;
    }

    /* Chat input row stays horizontal — ask button beside input */
    .chat-input-row {
        flex-direction:row !important;
    }
    .chat-input-row input, .chat-input-row textarea {
        flex:1 !important;
    }

    /* Export buttons full-width stacked */
    .export-btn {
        min-width:100% !important;
        margin-bottom:0.4rem;
    }

    /* Touch-friendly tap targets */
    button { min-height:44px !important; }

    /* Dataframe horizontal scroll */
    .table-wrap {
        overflow-x:auto !important;
        -webkit-overflow-scrolling:touch;
    }

    /* Prevent horizontal overflow */
    .gradio-container { overflow-x:hidden !important; max-width:100vw !important; }
    .contain {
        padding-left:0.4rem !important;
        padding-right:0.4rem !important;
        max-width:100% !important;
    }

    /* Chatbot compact height */
    .chat-area { min-height:200px !important; }

    .footer-text { font-size:0.7rem; padding:0.8rem 0 1.5rem; }
}

/* ── Safe area inset (notch phones iPhone X+) ─────────── */
@supports (padding:max(0px)) {
    .gradio-container {
        padding-left:max(0.5rem, env(safe-area-inset-left)) !important;
        padding-right:max(0.5rem, env(safe-area-inset-right)) !important;
    }
    .footer-text {
        padding-bottom:max(2rem, calc(env(safe-area-inset-bottom) + 1rem));
    }
}
"""


# ════════════════════════════════════════════════════════════
#  HISTORY HELPERS
# ════════════════════════════════════════════════════════════

def _history_rows(favorites_only: bool = False) -> list[list]:
    rows = list_reports(favorites_only=favorites_only)
    return [
        [r["id"], r["created_at"], r["industry"], r["location"], "⭐" if r["favorite"] else ""]
        for r in rows
    ]


# ════════════════════════════════════════════════════════════
#  BUILD APPLICATION
# ════════════════════════════════════════════════════════════

def create_app() -> gr.Blocks:

    config_ok, config_msg = validate_config()

    with gr.Blocks(
        title="AI Blue Ocean Finder",
    ) as app:

        # ── State (session-scoped, no globals) ───────────
        s_enhanced   = gr.State({})     # enhanced prompt + queries
        s_research   = gr.State([])     # raw branch results
        s_synthesis  = gr.State("")     # LLM markdown output
        s_industry   = gr.State("")     # cached input
        s_location   = gr.State("")     # cached input
        s_report_id  = gr.State(None)   # DB row id for current report
        s_selected_row = gr.State(None) # selected history row data

        # ── Hero ─────────────────────────────────────────
        gr.HTML(
            '<div class="hero">'
            "<h1>🌊 AI Blue Ocean Finder</h1>"
            "<p>Discover uncontested market spaces — powered by real-time AI research</p>"
            "</div>"
            '<div class="wave-bar"></div>'
        )

        if not config_ok:
            gr.Markdown(f"### 🚫 Startup Warning\n{config_msg}")

        # ── Phase 1: Input ───────────────────────────────
        with gr.Row(equal_height=True, elem_classes="input-row"):
            inp_industry = gr.Textbox(
                label="Industry",
                placeholder="e.g., Sustainable Fashion, Pet Tech, EdTech …",
                scale=3,
            )
            inp_location = gr.Textbox(
                label="Location / Market",
                placeholder="e.g., Southeast Asia, Brazil, Germany …",
                scale=3,
            )
        btn_find = gr.Button(
            "🌊  Find Blue Oceans",
            variant="primary",
            size="lg",
            elem_classes="glow-btn",
        )

        # ── Status (visible throughout) ──────────────────
        status = gr.Markdown(
            "",
            elem_classes="status-box",
            visible=False,
        )

        # ── Phase 3: Enhanced prompt review (EDITABLE) ───
        with gr.Column(visible=False) as col_enhanced:
            gr.HTML('<hr class="section-sep">')
            gr.Markdown("### 📋 Research Brief (editable)")
            gr.Markdown(
                "*Review and edit the research brief below. "
                "You can modify it to focus the analysis on specific aspects.*"
            )
            txt_enhanced = gr.Textbox(
                value="",
                lines=6,
                show_label=False,
                elem_classes="brief-area",
                interactive=True,
            )
            btn_confirm = gr.Button(
                "✅  Confirm & Launch Research",
                variant="primary",
                size="lg",
                elem_classes="glow-btn",
            )

        # ── Phase 6: Results ─────────────────────────────
        with gr.Column(visible=False) as col_results:
            gr.HTML('<hr class="section-sep">')
            gr.Markdown("### 🎯 Blue Ocean Opportunities")
            with gr.Group(elem_classes="results-card"):
                md_results = gr.Markdown("")

        # ── Follow-up Q&A ────────────────────────────────
        with gr.Column(visible=False) as col_qa:
            gr.HTML('<hr class="section-sep">')
            gr.Markdown("### 💬 Follow-up Questions")
            gr.Markdown(
                "*Ask about positioning, pricing, go-to-market strategy, "
                "or dig deeper into any opportunity.*"
            )
            chatbot = gr.Chatbot(
                label="",
                elem_classes="chat-area",
                height=350,
            )
            with gr.Row(elem_classes="chat-input-row"):
                inp_question = gr.Textbox(
                    placeholder="e.g., How should I position Opportunity 3 for investors?",
                    show_label=False,
                    scale=5,
                    elem_classes="chat-input",
                )
                btn_ask = gr.Button(
                    "Ask",
                    variant="primary",
                    scale=1,
                    elem_classes="glow-btn",
                )

        # ── Raw data accordion ───────────────────────────
        with gr.Column(visible=False) as col_raw:
            with gr.Accordion("📊  Raw Research Data (5 branches)", open=False):
                md_raw = gr.Markdown("")

        # ── Phase 7: Export ──────────────────────────────
        with gr.Column(visible=False) as col_download:
            gr.HTML('<hr class="section-sep">')
            gr.Markdown("### 📥  Export Report")
            with gr.Row(elem_classes="export-row"):
                btn_pdf  = gr.Button("📄  PDF", elem_classes="export-btn")
                btn_docx = gr.Button("📝  Word (.docx)", elem_classes="export-btn")
                btn_md   = gr.Button("📋  Markdown", elem_classes="export-btn")
            file_out = gr.File(label="Download", visible=False, interactive=False)

        # ── History Tab ──────────────────────────────────
        with gr.Accordion("📚  Report History", open=False):
            with gr.Row():
                chk_fav_only = gr.Checkbox(
                    label="Favorites only", value=False
                )
                btn_refresh_hist = gr.Button("🔄 Refresh", size="sm")
            df_history = gr.DataFrame(
                headers=["ID", "Date", "Industry", "Location", "⭐"],
                datatype=["number", "str", "str", "str", "str"],
                interactive=False,
                wrap=True,
                value=_history_rows(),
            )
            with gr.Row(elem_classes="history-actions-row"):
                btn_load_report = gr.Button("📂  Load Selected", variant="primary")
                btn_toggle_fav = gr.Button("⭐  Toggle Favorite")
                btn_del_report = gr.Button("🗑️  Delete Selected")

        # ── Footer ───────────────────────────────────────
        gr.HTML(
            '<div class="footer-text">'
            "AI Blue Ocean Finder &mdash; Open-source, free, data-driven."
            "</div>"
        )

        # ==================================================
        #  EVENT HANDLERS
        # ==================================================

        # ── STEP 1: Enhance prompt ───────────────────────
        async def step1_enhance(industry: str, location: str):
            if not industry or not location or not industry.strip() or not location.strip():
                yield {
                    status: gr.update(
                        value="⚠️  Please fill in **both** the Industry and Location fields.",
                        visible=True,
                        elem_classes="status-box",
                    ),
                    col_enhanced: gr.update(visible=False),
                    s_enhanced: {},
                    s_industry: "",
                    s_location: "",
                }
                return

            yield {
                status: gr.update(
                    value="🔍  **Phase 2/7** — Enhancing research prompt with AI …",
                    visible=True,
                    elem_classes="status-box working",
                ),
                col_enhanced: gr.update(visible=False),
            }

            try:
                enhanced = await enhance_prompt(industry.strip(), location.strip())
            except Exception as exc:
                yield {
                    status: gr.update(
                        value=f"❌  Prompt enhancement failed: `{exc}`",
                        visible=True,
                        elem_classes="status-box",
                    ),
                    col_enhanced: gr.update(visible=False),
                    s_enhanced: {},
                }
                return

            brief = enhanced.get("enhanced_query", "_No brief generated._")

            yield {
                status: gr.update(
                    value="✅  **Phase 3/7** — Edit the research brief below if needed, then confirm.",
                    visible=True,
                    elem_classes="status-box",
                ),
                col_enhanced: gr.update(visible=True),
                txt_enhanced: gr.update(value=brief),
                s_enhanced: enhanced,
                s_industry: industry.strip(),
                s_location: location.strip(),
            }

        btn_find.click(
            fn=step1_enhance,
            inputs=[inp_industry, inp_location],
            outputs=[
                status,
                col_enhanced,
                txt_enhanced,
                s_enhanced,
                s_industry,
                s_location,
            ],
        )

        # ── STEP 2: Parallel research + synthesis ────────
        async def step2_research(
            industry: str, location: str, enhanced: dict, edited_brief: str
        ):
            if not enhanced:
                yield {status: gr.update(
                    value="⚠️  No enhanced data found. Please start over.",
                    visible=True,
                )}
                return

            # Use edited brief if user changed it
            if edited_brief and isinstance(edited_brief, str) and edited_brief.strip():
                enhanced["enhanced_query"] = edited_brief.strip()

            queries = enhanced.get("search_queries", {})

            # Phase 4 — parallel search
            yield {
                status: gr.update(
                    value="🔍  **Phase 4/7** — Running 5 parallel web searches …",
                    visible=True,
                    elem_classes="status-box working",
                ),
                col_results: gr.update(visible=False),
                col_qa: gr.update(visible=False),
                col_raw: gr.update(visible=False),
                col_download: gr.update(visible=False),
            }

            try:
                research = await research_all(queries)
            except Exception as exc:
                yield {
                    status: gr.update(
                        value=f"❌  Research pipeline failed: `{exc}`",
                        visible=True,
                        elem_classes="status-box",
                    ),
                }
                return

            # Phase 5 — synthesis
            yield {
                status: gr.update(
                    value="🧠  **Phase 5/7** — AI synthesizing Blue Ocean opportunities …",
                    visible=True,
                    elem_classes="status-box working",
                ),
            }

            enhanced_query = enhanced.get("enhanced_query", "")

            try:
                synthesis = await synthesize(
                    industry, location, enhanced_query, research
                )
            except Exception as exc:
                yield {
                    status: gr.update(
                        value=f"❌  Synthesis failed: `{exc}`",
                        visible=True,
                        elem_classes="status-box",
                    ),
                }
                return

            # Phase 6 — display + save to DB
            raw_md = format_raw_research(research)
            report_id = save_report(
                industry, location, enhanced, research, synthesis
            )

            yield {
                status: gr.update(
                    value="✅  **Done!** Scroll down for opportunities. Ask follow-up questions below.",
                    visible=True,
                    elem_classes="status-box",
                ),
                col_results: gr.update(visible=True),
                md_results: gr.update(value=synthesis),
                col_qa: gr.update(visible=True),
                chatbot: gr.update(value=[]),
                col_raw: gr.update(visible=True),
                md_raw: gr.update(value=raw_md),
                col_download: gr.update(visible=True),
                s_research: research,
                s_synthesis: synthesis,
                s_enhanced: enhanced,
                s_report_id: report_id,
                df_history: gr.update(value=_history_rows()),
            }

        btn_confirm.click(
            fn=step2_research,
            inputs=[s_industry, s_location, s_enhanced, txt_enhanced],
            outputs=[
                status,
                col_results,
                md_results,
                col_qa,
                chatbot,
                col_raw,
                md_raw,
                col_download,
                s_research,
                s_synthesis,
                s_enhanced,
                s_report_id,
                df_history,
            ],
        )

        # ── FOLLOW-UP Q&A ───────────────────────────────
        async def ask_followup(
            question: str,
            chat_history: list,
            industry: str,
            location: str,
            synthesis: str,
            enhanced: dict,
            research: list,
        ):
            if not question.strip():
                yield {chatbot: chat_history, inp_question: ""}
                return

            chat_history.append(
                {"role": "user", "content": question.strip()}
            )
            yield {chatbot: chat_history, inp_question: ""}

            enhanced_query = enhanced.get("enhanced_query", "") if enhanced else ""
            try:
                answer = await follow_up(
                    question.strip(),
                    industry,
                    location,
                    synthesis,
                    enhanced_query,
                    research or [],
                )
            except Exception as exc:
                answer = f"Error: {exc}"

            chat_history.append(
                {"role": "assistant", "content": answer}
            )
            yield {chatbot: chat_history}

        btn_ask.click(
            fn=ask_followup,
            inputs=[
                inp_question,
                chatbot,
                s_industry,
                s_location,
                s_synthesis,
                s_enhanced,
                s_research,
            ],
            outputs=[chatbot, inp_question],
        )

        inp_question.submit(
            fn=ask_followup,
            inputs=[
                inp_question,
                chatbot,
                s_industry,
                s_location,
                s_synthesis,
                s_enhanced,
                s_research,
            ],
            outputs=[chatbot, inp_question],
        )

        # ── DOWNLOAD HANDLERS ────────────────────────────

        def _save_temp(buf: io.BytesIO, suffix: str, stem: str) -> str:
            p = Path(tempfile.gettempdir()) / f"{stem}{suffix}"
            p.write_bytes(buf.getvalue())
            return str(p)

        def dl_pdf(industry, location, synthesis, research):
            if not synthesis:
                return gr.update(visible=False)
            buf = generate_pdf(industry, location, synthesis, research)
            path = _save_temp(buf, ".pdf", "blue_ocean_report")
            return gr.update(value=path, visible=True)

        def dl_docx(industry, location, synthesis, research):
            if not synthesis:
                return gr.update(visible=False)
            buf = generate_docx(industry, location, synthesis, research)
            path = _save_temp(buf, ".docx", "blue_ocean_report")
            return gr.update(value=path, visible=True)

        def dl_md(industry, location, synthesis, research):
            if not synthesis:
                return gr.update(visible=False)
            text = generate_markdown(industry, location, synthesis, research)
            p = Path(tempfile.gettempdir()) / "blue_ocean_report.md"
            p.write_text(text, encoding="utf-8")
            return gr.update(value=str(p), visible=True)

        btn_pdf.click(
            fn=dl_pdf,
            inputs=[s_industry, s_location, s_synthesis, s_research],
            outputs=[file_out],
        )
        btn_docx.click(
            fn=dl_docx,
            inputs=[s_industry, s_location, s_synthesis, s_research],
            outputs=[file_out],
        )
        btn_md.click(
            fn=dl_md,
            inputs=[s_industry, s_location, s_synthesis, s_research],
            outputs=[file_out],
        )

        # ── HISTORY HANDLERS ─────────────────────────────

        def refresh_history(fav_only):
            return _history_rows(favorites_only=fav_only)

        btn_refresh_hist.click(
            fn=refresh_history,
            inputs=[chk_fav_only],
            outputs=[df_history],
        )

        chk_fav_only.change(
            fn=refresh_history,
            inputs=[chk_fav_only],
            outputs=[df_history],
        )

        def on_history_select(evt: gr.SelectData):
            """Store selected row data in state when user clicks a row."""
            try:
                if not evt.row_value:
                    return {s_selected_row: None}
                return {s_selected_row: evt.row_value}
            except TypeError:
                return {s_selected_row: None}

        df_history.select(
            fn=on_history_select,
            outputs=[s_selected_row],
        )

        def load_selected_report(selected_row):
            if not selected_row:
                return {
                    status: gr.update(value="⚠️  Click a row first, then load.", visible=True),
                }
            rid = int(selected_row[0])
            report = get_report(rid)
            if not report:
                return {
                    status: gr.update(value="⚠️  Report not found.", visible=True),
                }
            raw_md = format_raw_research(report["research_data"])
            return {
                status: gr.update(
                    value=f"📂  Loaded report #{rid} — {report['industry']} / {report['location']}. Ask follow-up questions below!",
                    visible=True,
                    elem_classes="status-box",
                ),
                col_results: gr.update(visible=True),
                md_results: gr.update(value=report["synthesis"]),
                col_qa: gr.update(visible=True),
                chatbot: gr.update(value=[]),
                col_raw: gr.update(visible=True),
                md_raw: gr.update(value=raw_md),
                col_download: gr.update(visible=True),
                s_industry: report["industry"],
                s_location: report["location"],
                s_synthesis: report["synthesis"],
                s_research: report["research_data"],
                s_enhanced: {
                    "enhanced_query": report.get("enhanced_query", ""),
                    "search_queries": report.get("search_queries", {}),
                },
                s_report_id: rid,
            }

        btn_load_report.click(
            fn=load_selected_report,
            inputs=[s_selected_row],
            outputs=[
                status,
                col_results,
                md_results,
                col_qa,
                chatbot,
                col_raw,
                md_raw,
                col_download,
                s_industry,
                s_location,
                s_synthesis,
                s_research,
                s_enhanced,
                s_report_id,
            ],
        )

        def do_toggle_fav(selected_row, fav_only):
            if not selected_row:
                return _history_rows(favorites_only=fav_only)
            rid = int(selected_row[0])
            toggle_favorite(rid)
            return _history_rows(favorites_only=fav_only)

        btn_toggle_fav.click(
            fn=do_toggle_fav,
            inputs=[s_selected_row, chk_fav_only],
            outputs=[df_history],
        )

        def do_delete_report(selected_row, fav_only):
            if not selected_row:
                return _history_rows(favorites_only=fav_only)
            rid = int(selected_row[0])
            delete_report(rid)
            return _history_rows(favorites_only=fav_only)

        btn_del_report.click(
            fn=do_delete_report,
            inputs=[s_selected_row, chk_fav_only],
            outputs=[df_history],
        )


    return app


# ════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════

VIEWPORT_META = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, viewport-fit=cover">'

if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        theme=THEME,
        css=CUSTOM_CSS,
        head=VIEWPORT_META,
    )
