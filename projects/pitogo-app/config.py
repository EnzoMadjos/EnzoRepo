"""
config.py — PITOGO Barangay App configuration.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
SECURE_DIR = BASE_DIR / "secure"
SECURE_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

# ── App ────────────────────────────────────────────────────────────────────────
APP_NAME = os.getenv("APP_NAME", "PITOGO Barangay App")
APP_PORT = int(os.getenv("APP_PORT", "8300"))
SESSION_EXPIRE_HOURS = int(os.getenv("SESSION_EXPIRE_HOURS", "12"))
BRGY_CODE = os.getenv("BRGY_CODE", "PITOGO")

# ── Peer discovery & auto-election ────────────────────────────────────────────
# Port used for UDP broadcast discovery messages
DISCOVERY_PORT = int(os.getenv("DISCOVERY_PORT", "50300"))
# Seconds to wait for an existing server before self-electing
DISCOVERY_TIMEOUT_SEC = float(os.getenv("DISCOVERY_TIMEOUT_SEC", "2.0"))
# Heartbeat interval in seconds
HEARTBEAT_INTERVAL = float(os.getenv("HEARTBEAT_INTERVAL", "5.0"))
# Miss this many heartbeats before triggering re-election
HEARTBEAT_MISSES = int(os.getenv("HEARTBEAT_MISSES", "3"))

# ── Support relay ─────────────────────────────────────────────────────────────
RELAY_URL = os.getenv("RELAY_URL", "").rstrip("/")
RELAY_TOKEN = os.getenv("RELAY_TOKEN", "")

# Fallback webhook (Discord / Slack) when relay is offline
LOG_WEBHOOK_URL = os.getenv("LOG_WEBHOOK_URL", "")

# ── Update ────────────────────────────────────────────────────────────────────
UPDATE_URL = os.getenv("UPDATE_URL", "")
# Patch signing
PATCH_PUBLIC_KEY_PATH = os.getenv(
    "PATCH_PUBLIC_KEY_PATH", str(SECURE_DIR / "patch_public.pem")
)
# Secret used to sign short-lived download URLs. Set this in your .env for stable behavior.
DOWNLOAD_SECRET = os.getenv("DOWNLOAD_SECRET", "")

# Directory to store archived logs/exports
LOG_ARCHIVE_DIR = SECURE_DIR / "log_archives"
LOG_ARCHIVE_DIR.mkdir(exist_ok=True)

# ── Database ───────────────────────────────────────────────────────────────────
# DB_BACKEND: "postgres" (default) | "sqlite" (emergency fallback)
DB_BACKEND = os.getenv("DB_BACKEND", "sqlite").lower()  # default sqlite for dev safety

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "pitogo")
DB_USER = os.getenv("DB_USER", "pitogo")
DB_PASS = os.getenv("DB_PASS", "")

# Node role: "leader" (runs postgres) | "client" (connects to leader)
NODE_ROLE = os.getenv("NODE_ROLE", "leader")

def get_database_url() -> str:
    """Return the SQLAlchemy database URL based on DB_BACKEND."""
    if DB_BACKEND == "postgres":
        return f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    # sqlite fallback
    db_path = SECURE_DIR / "pitogo.db"
    return f"sqlite:///{db_path}"
