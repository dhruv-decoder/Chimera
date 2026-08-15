"""Central configuration and paths.

Everything reproducible is seeded from a single place. Paths resolve relative
to the repository so scripts, the API and tests all read/write the same
artifacts regardless of the working directory.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/chimera/config.py -> repo root is three parents up.
REPO_ROOT = Path(__file__).resolve().parents[2]

# Load backend/.env into the environment before settings are read, so a
# GROQ_API_KEY placed there is picked up (the file is gitignored).
load_dotenv(REPO_ROOT / "backend" / ".env")
DATA_DIR = REPO_ROOT / "data"
ARTIFACTS_DIR = DATA_DIR / "artifacts"
CORPUS_DIR = Path(__file__).resolve().parent / "identify" / "corpus"

for _d in (DATA_DIR, ARTIFACTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """Runtime settings, overridable via environment or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CHIMERA_", extra="ignore")

    # Global reproducibility seed. Every stochastic component derives its RNG
    # from this so a run is bit-for-bit repeatable.
    seed: int = 42

    # --- LLM / agents -----------------------------------------------------
    # Provider is auto-selected: if a Groq key is present we use it, else the
    # deterministic offline planner. This keeps live demos crash-proof.
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    # Groq free-tier open-weight models (the Llama 3.x endpoints were retired on
    # 17 Jun 2026; these are the current recommended replacements).
    groq_model: str = os.getenv("CHIMERA_GROQ_MODEL", "openai/gpt-oss-120b")       # ideation quality
    groq_model_fast: str = os.getenv("CHIMERA_GROQ_MODEL_FAST", "openai/gpt-oss-20b")  # fast/cheap path
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    llm_timeout_s: float = 30.0    # hard per-call timeout; loop never hangs on the LLM

    # --- simulation defaults ---------------------------------------------
    default_population: int = 4000     # number of legitimate accounts
    default_days: int = 30             # simulation horizon
    fraud_base_rate: float = 0.012     # ~1.2% of txns are fraud (realistic-ish)

    @property
    def llm_available(self) -> bool:
        return bool(self.groq_api_key)


settings = Settings()
