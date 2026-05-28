import os

import httpx
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ───────────────────────────────────────────────
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openrouter/free")
DEFAULT_MODEL: str = "openrouter/free"
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# ── Free model fallback chain (tried in order until one works) ──
FREE_MODEL_CHAIN: list[str] = [
    "openrouter/free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "google/gemini-2.5-flash:free",
    "deepseek/deepseek-r1-0528:free",
    "deepseek/deepseek-chat-v3-5:free",
    "mistralai/mistral-small-3.2-24b-instruct:free",
    "qwen/qwen3-235b-a22b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "microsoft/phi-4-reasoning-plus:free",
    "google/gemma-3-27b-it:free",
]

# All selectable models for UI dropdown
MODEL_OPTIONS: list[str] = ["Auto (fallback chain)"] + FREE_MODEL_CHAIN

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


def _resolve_models(preferred_model: str | None = None) -> list[str]:
    """Return ordered list of models to try."""
    if preferred_model and preferred_model != "Auto (fallback chain)":
        return [preferred_model]
    return FREE_MODEL_CHAIN


async def call_llm(
    messages: list[dict],
    *,
    temperature: float = 0.15,
    max_tokens: int = 1500,
    timeout: float = 45.0,
    preferred_model: str | None = None,
) -> str:
    """
    Call OpenRouter with model fallback chain.
    Tries models in order until one succeeds.
    Retries each model up to 2 times on transient failures before moving to next.
    """
    models = _resolve_models(preferred_model)
    last_err = None

    for model in models:
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(
                        OPENROUTER_URL,
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        },
                    )
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"]
                    if content:
                        return content
                    last_err = ValueError(f"[{model}] Empty response (attempt {attempt+1}/2)")
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                last_err = ValueError(f"[{model}] API error {status} (attempt {attempt+1}/2): {exc.response.text[:200]}")
                # 404/403 = model unavailable, skip to next immediately
                if status in (404, 403, 503):
                    break
            except Exception as exc:
                last_err = ValueError(f"[{model}] Error (attempt {attempt+1}/2): {exc}")

    raise last_err or ValueError("All models in fallback chain failed.")
