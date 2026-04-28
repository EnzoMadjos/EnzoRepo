import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
SECURE_DIR = BASE_DIR / "secure"
SECURE_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

# LLM (Ollama local)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# App
APP_PORT = int(os.getenv("APP_PORT", "8200"))
SESSION_EXPIRE_HOURS = 12  # session expires after this many hours of inactivity
