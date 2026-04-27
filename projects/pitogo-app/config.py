"""
config.py — PITOGO Barangay App configuration.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR   = Path(__file__).parent
SECURE_DIR = BASE_DIR / "secure"
SECURE_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

# ── App ────────────────────────────────────────────────────────────────────────
APP_NAME              = os.getenv("APP_NAME", "PITOGO Barangay App")
APP_PORT              = int(os.getenv("APP_PORT", "8300"))
SESSION_EXPIRE_HOURS  = int(os.getenv("SESSION_EXPIRE_HOURS", "12"))

# ── Peer discovery & auto-election ────────────────────────────────────────────
# Port used for UDP broadcast discovery messages
DISCOVERY_PORT        = int(os.getenv("DISCOVERY_PORT", "50300"))
# Seconds to wait for an existing server before self-electing
DISCOVERY_TIMEOUT_SEC = float(os.getenv("DISCOVERY_TIMEOUT_SEC", "2.0"))
# Heartbeat interval in seconds
HEARTBEAT_INTERVAL    = float(os.getenv("HEARTBEAT_INTERVAL", "5.0"))
# Miss this many heartbeats before triggering re-election
HEARTBEAT_MISSES      = int(os.getenv("HEARTBEAT_MISSES", "3"))

# ── Support relay ─────────────────────────────────────────────────────────────
RELAY_URL   = os.getenv("RELAY_URL",   "").rstrip("/")
RELAY_TOKEN = os.getenv("RELAY_TOKEN", "")

# Fallback webhook (Discord / Slack) when relay is offline
LOG_WEBHOOK_URL = os.getenv("LOG_WEBHOOK_URL", "")

# ── Update ────────────────────────────────────────────────────────────────────
UPDATE_URL = os.getenv("UPDATE_URL", "")
