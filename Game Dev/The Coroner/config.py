import os
from dotenv import load_dotenv

load_dotenv()

# ── App ───────────────────────────────────────────────────────────────────
APP_PORT = int(os.getenv("APP_PORT", 8400))
SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())
DB_PATH = os.getenv("DB_PATH", "secure/coroner.db")

# ── GitHub Models API (all LLM calls — auto-rotates via model_router.py) ──
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_BASE_URL = "https://models.inference.ai.azure.com"
GITHUB_TIMEOUT = int(os.getenv("GITHUB_TIMEOUT", 90))

# Legacy single-model vars — kept only for backward compat, not used in rotation.
# The active chains are defined in llm/model_router.py.
GITHUB_MODEL = os.getenv("GITHUB_MODEL", "gpt-4.1")
INTERACTIVE_MODEL = os.getenv("INTERACTIVE_MODEL", "gpt-4.1-mini")

# ── Ollama (DEPRECATED — no longer used) ─────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi4-mini")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", 60))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", 8192))

# ── Generation settings ───────────────────────────────────────────────────
MAX_GENERATION_RETRIES = 3
ANTI_REPEAT_WINDOW = 2        # block same motive type for last N sessions
MAX_WORLD_SKELETON_BYTES = 50_000
