"""
config.py — Set your API keys and preferences here.
Supports OpenAI, Anthropic, and Ollama (local, free).

─── CHOOSE YOUR MODEL ────────────────────────────────────────
Pick based on your computer specs. See GUIDE.md Chapter 2 for
the full comparison table with RAM/GPU requirements.

  LOW-END  (8 GB RAM, no GPU)   → llama3.2:3b  or  phi4-mini
  MID-RANGE (16 GB RAM)         → llama3        or  mistral
  HIGH-END  (32 GB RAM / GPU)   → llama3:70b    or  qwen2.5-coder:7b
  CLOUD (OpenAI/Anthropic)      → gpt-4o-mini   or  claude-3-haiku

NOTE: Bigger models produce significantly better output (smarter
reasoning, cleaner code, more natural writing) but require more
RAM and take longer to respond on CPU-only machines.
"""

# ─── LLM Provider ────────────────────────────────────────────
# Options: "openai" | "anthropic" | "ollama"
DEFAULT_PROVIDER = "ollama"

# ─── Model Selection ─────────────────────────────────────────
# Change this to match your machine specs (see table above).
#
# Ollama models (local, free):
#   "llama3.2:3b"        → 8 GB RAM minimum  (fast, lighter quality)
#   "llama3:latest"      → 16 GB RAM minimum (recommended balance)
#   "phi4-mini"          → 8 GB RAM minimum  (Microsoft, punches above size)
#   "mistral"            → 16 GB RAM minimum (great for writing tasks)
#   "qwen2.5-coder:7b"   → 16 GB RAM minimum (best for code generation)
#   "llama3:70b"         → 32 GB RAM + GPU   (near-GPT-4 quality)
#
# Cloud models (paid, fastest, best quality — no GPU needed):
#   "gpt-4o-mini"                   → OpenAI  (cheapest cloud option)
#   "gpt-4o"                        → OpenAI  (best all-round)
#   "claude-3-haiku-20240307"        → Anthropic (fast + cheap)
#   "claude-3-5-sonnet-20241022"     → Anthropic (best for long docs/code)
DEFAULT_MODEL = "llama3:latest"

# ─── API Keys ────────────────────────────────────────────────
# Leave blank if not using that provider.
OPENAI_API_KEY = ""       # https://platform.openai.com/api-keys
ANTHROPIC_API_KEY = ""    # https://console.anthropic.com/

# ─── Ollama ──────────────────────────────────────────────────
# Default: local Ollama on port 11434
# Change if running Ollama on a different machine.
OLLAMA_BASE_URL = "http://localhost:11434"
