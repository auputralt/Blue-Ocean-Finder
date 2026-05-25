from __future__ import annotations

import asyncio
import re
import tempfile
import io
import base64
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

# ── Logo as base64 for reliable inline rendering ──
_logo_path = Path(__file__).parent / "Public" / "Logo.png"
if _logo_path.exists():
    _LOGO_B64 = base64.b64encode(_logo_path.read_bytes()).decode()
else:
    _LOGO_B64 = ""


# ════════════════════════════════════════════════════════════
#  THEME & CSS  —  Deep Ocean Noir
# ════════════════════════════════════════════════════════════

THEME = gr.themes.Soft(
    primary_hue=gr.themes.Color(
        c50="#f0fdfa", c100="#ccfbf1", c200="#99f6e4",
        c300="#5eead4", c400="#2dd4bf", c500="#14b8a6",
        c600="#0d9488", c700="#0f766e", c800="#115e59", c900="#134e4a",
        c950="#042f2e",
    ),
    secondary_hue=gr.themes.Color(
        c50="#fefce8", c100="#fef9c3", c200="#fef08a",
        c300="#fde047", c400="#facc15", c500="#eab308",
        c600="#ca8a04", c700="#a16207", c800="#854d0e", c900="#713f12",
        c950="#422006",
    ),
    neutral_hue="slate",
    font=gr.themes.GoogleFont("Outfit"),
    font_mono=gr.themes.GoogleFont("JetBrains Mono"),
).set(
    body_background_fill_dark="#030712",
    block_background_fill_dark="rgba(8, 14, 28, 0.92)",
    block_border_color_dark="rgba(20, 184, 166, 0.10)",
    block_label_text_color_dark="#64748b",
    block_title_text_color_dark="#e2e8f0",
    input_background_fill_dark="rgba(12, 20, 38, 0.95)",
    input_border_color_dark="rgba(20, 184, 166, 0.18)",
    button_primary_background_fill_dark="linear-gradient(135deg, #0d9488 0%, #0f766e 100%)",
    button_primary_background_fill_hover_dark="linear-gradient(135deg, #14b8a6 0%, #0d9488 100%)",
    button_primary_text_color_dark="#f0fdfa",
    button_secondary_background_fill_dark="rgba(20, 184, 166, 0.08)",
    button_secondary_background_fill_hover_dark="rgba(20, 184, 166, 0.16)",
    button_secondary_text_color_dark="#5eead4",
    checkbox_background_color_dark="rgba(20, 184, 166, 0.12)",
    slider_color_dark="#14b8a6",
)

CUSTOM_CSS = """
/* ── Fonts ──────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&display=swap');

/* ── Global reset ───────────────────────────────────────── */
*, *::before, *::after { box-sizing:border-box; }
html { -webkit-text-size-adjust:100%; }
body {
    overflow-x:hidden;
    background:#030712;
    font-family:'Outfit', sans-serif;
}

/* ── Subtle background grid ─────────────────────────────── */
.gradio-container {
    position:relative;
}
.gradio-container::before {
    content:'';
    position:fixed;
    inset:0;
    background-image:
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(20,184,166,0.06) 0%, transparent 60%),
        linear-gradient(rgba(20,184,166,0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(20,184,166,0.02) 1px, transparent 1px);
    background-size:100% 100%, 60px 60px, 60px 60px;
    pointer-events:none;
    z-index:0;
}
.gradio-container > * { position:relative; z-index:1; }

/* ── Hero ───────────────────────────────────────────────── */
.hero-wrap {
    text-align:center;
    padding:2.4rem 1rem 0.6rem;
    position:relative;
}
.hero-logo {
    width:120px; height:120px;
    border-radius:24px;
    object-fit:contain;
    margin:0 auto 1rem;
    display:block;
    filter:drop-shadow(0 8px 24px rgba(20,184,166,0.25));
    animation:logoFloat 6s ease-in-out infinite;
}
@keyframes logoFloat {
    0%,100% { transform:translateY(0); }
    50% { transform:translateY(-6px); }
}
.hero-wrap h1 {
    font-family:'Outfit', sans-serif;
    font-size:2.8rem; font-weight:800;
    letter-spacing:-0.04em;
    background:linear-gradient(135deg, #5eead4 0%, #2dd4bf 30%, #14b8a6 60%, #eab308 100%);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
    background-clip:text;
    margin:0;
    line-height:1.1;
}
.hero-wrap p {
    font-family:'Source Serif 4', serif;
    color:#64748b;
    font-size:1.1rem;
    margin-top:0.5rem;
    font-style:italic;
    letter-spacing:0.01em;
}

/* ── Accent line ────────────────────────────────────────── */
.accent-line {
    width:60px; height:2px;
    margin:0.8rem auto 1.5rem;
    background:linear-gradient(90deg, #14b8a6, #eab308);
    border-radius:2px;
    position:relative;
}
.accent-line::after {
    content:'';
    position:absolute;
    inset:-4px -20px;
    background:linear-gradient(90deg, transparent, rgba(20,184,166,0.15), rgba(234,179,8,0.15), transparent);
    border-radius:4px;
    filter:blur(4px);
}

/* ── Status box ─────────────────────────────────────────── */
.status-box {
    padding:0.9rem 1.3rem;
    border-radius:10px;
    background:rgba(20,184,166,0.06);
    border:1px solid rgba(20,184,166,0.14);
    font-weight:500;
    color:#5eead4;
    font-size:0.95rem;
    word-break:break-word;
    font-family:'Outfit', sans-serif;
}
.status-box.working {
    animation:statusPulse 2.5s ease-in-out infinite;
    border-color:rgba(20,184,166,0.3);
}
@keyframes statusPulse {
    0%,100% { opacity:1; border-color:rgba(20,184,166,0.14); }
    50% { opacity:0.7; border-color:rgba(20,184,166,0.3); }
}

/* ── Results card ────────────────────────────────────────── */
.results-card {
    background:rgba(6,12,24,0.85);
    backdrop-filter:blur(16px);
    border:1px solid rgba(20,184,166,0.08);
    border-radius:16px;
    padding:2rem;
    overflow-wrap:break-word;
    word-break:break-word;
    position:relative;
}
.results-card::before {
    content:'';
    position:absolute;
    top:0; left:20px; right:20px;
    height:1px;
    background:linear-gradient(90deg, transparent, rgba(20,184,166,0.3), transparent);
}

/* ── Primary CTA ────────────────────────────────────────── */
.glow-btn {
    box-shadow:0 4px 20px rgba(20,184,166,0.25) !important;
    transition:all 0.3s cubic-bezier(0.4,0,0.2,1) !important;
    min-height:50px !important;
    font-family:'Outfit', sans-serif !important;
    font-weight:600 !important;
    letter-spacing:0.02em !important;
    text-transform:none !important;
}
.glow-btn:hover {
    transform:translateY(-2px) !important;
    box-shadow:0 8px 32px rgba(20,184,166,0.4) !important;
}
@media (hover:none) {
    .glow-btn:hover { transform:none !important; }
}

/* ── Markdown inside results ────────────────────────────── */
.results-card h1, .results-card h2, .results-card h3 {
    color:#2dd4bf !important;
    font-family:'Outfit', sans-serif !important;
}
.results-card h2 {
    border-bottom:1px solid rgba(20,184,166,0.12) !important;
    padding-bottom:0.4rem !important;
}
.results-card a { color:#eab308 !important; text-decoration:underline !important; }
.results-card strong { color:#f1f5f9 !important; }
.results-card p {
    color:#94a3b8 !important;
    line-height:1.75 !important;
    font-family:'Source Serif 4', serif !important;
}
.results-card ul, .results-card ol { color:#94a3b8 !important; }
.results-card hr { border-color:rgba(20,184,166,0.1) !important; }
.results-card table {
    border-collapse:collapse !important;
    width:100% !important;
}
.results-card th {
    background:rgba(20,184,166,0.08) !important;
    color:#5eead4 !important;
    font-family:'Outfit', sans-serif !important;
    font-weight:600 !important;
    padding:0.5rem 0.75rem !important;
    border:1px solid rgba(20,184,166,0.12) !important;
}
.results-card td {
    padding:0.5rem 0.75rem !important;
    border:1px solid rgba(20,184,166,0.08) !important;
    color:#cbd5e1 !important;
}

/* ── Section separator ──────────────────────────────────── */
.section-sep {
    border:0; height:1px;
    background:linear-gradient(90deg, transparent, rgba(20,184,166,0.15), rgba(234,179,8,0.1), transparent);
    margin:1.5rem 0;
}

/* ── Editable brief textarea ────────────────────────────── */
.brief-area textarea {
    background:rgba(8,14,28,0.95) !important;
    border:1px solid rgba(20,184,166,0.18) !important;
    border-radius:12px !important;
    color:#e2e8f0 !important;
    font-size:16px !important;
    line-height:1.65 !important;
    padding:1.1rem !important;
    font-family:'Source Serif 4', serif !important;
    transition:border-color 0.25s ease, box-shadow 0.25s ease !important;
}
.brief-area textarea:focus {
    border-color:rgba(20,184,166,0.4) !important;
    box-shadow:0 0 0 3px rgba(20,184,166,0.08) !important;
}

/* ── Input row styling ──────────────────────────────────── */
.input-row input[type="text"] {
    background:rgba(8,14,28,0.95) !important;
    border:1px solid rgba(20,184,166,0.15) !important;
    border-radius:12px !important;
    color:#e2e8f0 !important;
    font-family:'Outfit', sans-serif !important;
    transition:border-color 0.25s ease !important;
}
.input-row input[type="text"]:focus {
    border-color:rgba(20,184,166,0.4) !important;
}

/* ── Q&A Chat ───────────────────────────────────────────── */
.chat-area {
    background:rgba(6,12,24,0.7) !important;
    border-radius:14px !important;
    border:1px solid rgba(20,184,166,0.08) !important;
}
.chat-input textarea {
    background:rgba(8,14,28,0.9) !important;
    border:1px solid rgba(20,184,166,0.15) !important;
    border-radius:12px !important;
    color:#e2e8f0 !important;
    font-size:16px !important;
    font-family:'Outfit', sans-serif !important;
}
.typing-indicator {
    display:flex; align-items:center; gap:6px;
    padding:8px 14px; color:#5eead4; font-size:0.9rem;
    font-family:'Outfit', sans-serif;
}
.typing-indicator .dot {
    width:6px; height:6px; border-radius:50%; background:#14b8a6;
    animation:typingBounce 1.4s infinite ease-in-out;
}
.typing-indicator .dot:nth-child(2) { animation-delay:0.2s; }
.typing-indicator .dot:nth-child(3) { animation-delay:0.4s; }
@keyframes typingBounce {
    0%,80%,100% { opacity:0.2; transform:scale(0.7); }
    40% { opacity:1; transform:scale(1.15); }
}

/* ── Export buttons ──────────────────────────────────────── */
.export-btn {
    min-width:160px !important;
    min-height:46px !important;
    border-radius:12px !important;
    font-family:'Outfit', sans-serif !important;
}

/* ── Footer ─────────────────────────────────────────────── */
.footer-text {
    text-align:center;
    color:#1e293b;
    font-size:0.78rem;
    padding:1.2rem 0 2.5rem;
    font-family:'Outfit', sans-serif;
    letter-spacing:0.04em;
    text-transform:uppercase;
}

/* ── Input fields — prevent zoom on iOS ──────────────────── */
input[type="text"], textarea, select {
    font-size:16px !important;
}

/* ── Gradio label styling ───────────────────────────────── */
label span, .svelte-1gfkn6j {
    font-family:'Outfit', sans-serif !important;
    font-weight:500 !important;
    letter-spacing:0.01em !important;
}

/* ── Accordion styling ──────────────────────────────────── */
details summary {
    font-family:'Outfit', sans-serif !important;
    font-weight:600 !important;
}

/* ── Dataframe styling ──────────────────────────────────── */
.table-wrap table {
    font-family:'Outfit', sans-serif !important;
}
.table-wrap th {
    background:rgba(20,184,166,0.06) !important;
    color:#5eead4 !important;
}

/* ══════════════════════════════════════════════════════════
   TABLET — max 768px
   ══════════════════════════════════════════════════════════ */
@media (max-width:768px) {
    .hero-wrap { padding:1.5rem 0.75rem 0.4rem; }
    .hero-logo { width:90px; height:90px; border-radius:18px; }
    .hero-wrap h1 { font-size:2rem; }
    .hero-wrap p { font-size:0.95rem; }
    .accent-line { margin:0.6rem auto 1.2rem; }

    .results-card {
        padding:1.3rem 1rem;
        border-radius:12px;
    }
    .status-box {
        padding:0.7rem 1rem;
        font-size:0.88rem;
    }
    .brief-area textarea { padding:0.9rem !important; }
    .chat-area { border-radius:10px !important; }
    .section-sep { margin:1rem 0; }
}

/* ══════════════════════════════════════════════════════════
   MOBILE — max 480px
   ══════════════════════════════════════════════════════════ */
@media (max-width:480px) {
    .hero-wrap { padding:1rem 0.5rem 0.2rem; }
    .hero-logo { width:72px; height:72px; border-radius:14px; margin-bottom:0.7rem; }
    .hero-wrap h1 { font-size:1.55rem; letter-spacing:-0.03em; }
    .hero-wrap p { font-size:0.82rem; }
    .accent-line { width:40px; margin:0.5rem auto 1rem; }

    .results-card {
        padding:1rem 0.75rem;
        border-radius:10px;
    }
    .status-box {
        padding:0.6rem 0.8rem;
        font-size:0.82rem;
        border-radius:8px;
    }
    .brief-area textarea {
        padding:0.7rem !important;
        line-height:1.5 !important;
    }
    .section-sep { margin:0.7rem 0; }

    /* Force Gradio rows to stack on mobile */
    [data-testid="row"] {
        flex-direction:column !important;
        gap:0.5rem !important;
    }
    .chat-input-row {
        flex-direction:row !important;
    }
    .chat-input-row input, .chat-input-row textarea {
        flex:1 !important;
    }
    .export-btn {
        min-width:100% !important;
        margin-bottom:0.5rem;
    }
    button { min-height:44px !important; }
    .table-wrap {
        overflow-x:auto !important;
        -webkit-overflow-scrolling:touch;
    }
    .gradio-container { overflow-x:hidden !important; max-width:100vw !important; }
    .contain {
        padding-left:0.4rem !important;
        padding-right:0.4rem !important;
        max-width:100% !important;
    }
    .chat-area { min-height:200px !important; }
    .footer-text { font-size:0.65rem; padding:0.8rem 0 1.5rem; }
}

/* ── Safe area inset (notch phones iPhone X+) ──────────── */
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
        theme=THEME,
        css=CUSTOM_CSS,
        head=VIEWPORT_META,
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
        _logo_img = f'<img src="data:image/png;base64,{_LOGO_B64}" alt="Blue Ocean Finder" class="hero-logo">' if _LOGO_B64 else ""
        gr.HTML(
            '<div class="hero-wrap">'
            f'{_logo_img}'
            "<h1>Blue Ocean Finder</h1>"
            '<p>Discover uncontested market spaces &mdash; powered by real-time AI research</p>'
            "</div>"
            '<div class="accent-line"></div>'
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
                type="messages",
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
            gr.Markdown("*Click a format button below to generate and download your report.*")
            with gr.Row(elem_classes="export-row"):
                btn_pdf  = gr.Button("📄  Download PDF", variant="primary", elem_classes="export-btn glow-btn")
                btn_docx = gr.Button("📝  Download Word", elem_classes="export-btn")
                btn_md   = gr.Button("📋  Download Markdown", elem_classes="export-btn")
            file_out = gr.File(label="⬇️  Your download will appear here", visible=True, interactive=False)

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
        TYPING_MSG = (
            '<div class="typing-indicator">'
            '<span>Agent is thinking</span>'
            '<span class="dot"></span>'
            '<span class="dot"></span>'
            '<span class="dot"></span>'
            '</div>'
        )

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
            # Show user message + typing indicator
            chat_history.append(
                {"role": "assistant", "content": TYPING_MSG}
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
                answer = f"Error generating response: {exc}"

            # Replace typing indicator with real answer
            chat_history[-1] = {"role": "assistant", "content": answer}
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
                return gr.update(value=None, visible=True)
            buf = generate_pdf(industry, location, synthesis, research)
            safe_name = re.sub(r'[^\w\s-]', '', industry)[:30].strip().replace(' ', '_') or "report"
            path = _save_temp(buf, ".pdf", f"blue_ocean_{safe_name}")
            return gr.update(value=path, visible=True)

        def dl_docx(industry, location, synthesis, research):
            if not synthesis:
                return gr.update(value=None, visible=True)
            buf = generate_docx(industry, location, synthesis, research)
            safe_name = re.sub(r'[^\w\s-]', '', industry)[:30].strip().replace(' ', '_') or "report"
            path = _save_temp(buf, ".docx", f"blue_ocean_{safe_name}")
            return gr.update(value=path, visible=True)

        def dl_md(industry, location, synthesis, research):
            if not synthesis:
                return gr.update(value=None, visible=True)
            text = generate_markdown(industry, location, synthesis, research)
            safe_name = re.sub(r'[^\w\s-]', '', industry)[:30].strip().replace(' ', '_') or "report"
            p = Path(tempfile.gettempdir()) / f"blue_ocean_{safe_name}.md"
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
    )
