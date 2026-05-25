import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ───────────────────────────────────────────────
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openrouter/free")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# ── Endpoints ──────────────────────────────────────────────
OPENROUTER_URL: str = "https://openrouter.ai/api/v1/chat/completions"
TAVILY_URL: str = "https://api.tavily.com/search"

# ── Search branch names (order matters) ────────────────────
BRANCHES: list[str] = [
    "dominant_players",
    "overlooked_customers",
    "substitute_industries",
    "trends",
    "product_gaps",
]


def validate_config() -> tuple[bool, str]:
    """Return (ok, message). Warn about missing keys."""
    missing: list[str] = []
    if not OPENROUTER_API_KEY:
        missing.append("OPENROUTER_API_KEY")
    if not TAVILY_API_KEY:
        missing.append("TAVILY_API_KEY")
    if missing:
        msg = (
            f"⚠️  Missing API key(s): **{', '.join(missing)}**. "
            f"Create a `.env` file based on `.env.example` and restart."
        )
        print(msg)
        return False, msg
    return True, "All API keys loaded successfully."
