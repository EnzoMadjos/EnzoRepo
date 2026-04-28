import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
SECURE_DIR = BASE_DIR / "secure"
SECURE_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

# LLM (Ollama local)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b")

# App
APP_PORT = int(os.getenv("APP_PORT", "8200"))
SESSION_EXPIRE_HOURS = 12  # session expires after this many hours of inactivity

# Remote patch/update URL — set this to a direct-download link (Google Drive, etc.)
# After uploading a new patch.zip, update this URL and she clicks "Apply Update"
UPDATE_URL = os.getenv("UPDATE_URL", "")

# Live relay server — Enzo starts relay/relay_server.py on demand and exposes it via ngrok.
# Paste the public ngrok URL here so Vanessa's app can reach it.
# When this is set it takes priority over UPDATE_URL and LOG_WEBHOOK_URL.
RELAY_URL = os.getenv("RELAY_URL", "").rstrip("/")
RELAY_TOKEN = os.getenv("RELAY_TOKEN", "")  # shared secret — must match relay/.env

# Fallback: static patch URL (Google Drive direct-download) used when RELAY_URL is blank
UPDATE_URL = os.getenv("UPDATE_URL", "")

# Fallback: Discord/Slack webhook used when RELAY_URL is blank
# Discord:  Server Settings → Integrations → Webhooks → New Webhook → Copy Webhook URL
# Slack:    https://api.slack.com/messaging/webhooks
LOG_WEBHOOK_URL = os.getenv("LOG_WEBHOOK_URL", "")
