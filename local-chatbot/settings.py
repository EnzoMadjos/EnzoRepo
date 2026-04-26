from pathlib import Path
from typing import List
import os

# Project root — always relative to this file, so it works on any machine.
PROJECT_ROOT = Path(__file__).resolve().parent

# Secure folder lives inside the project — portable and self-contained.
SECURE_DIR = PROJECT_ROOT / "secure"

SECURE_ATLAS_FOLDER_CANDIDATES = [
    SECURE_DIR,
    Path("/mnt/c/ATLAS"),
    Path("C:/ATLAS"),
    Path("/c/ATLAS"),
]

# Set to False to disable web access entirely.
WEB_FETCH_ENABLED = True

# If this list is non-empty, only domains in this allowlist may be fetched.
WEB_ACCESS_ALLOWLIST: List[str] = []

# Maximum amount of text extracted from a webpage for the assistant.
MAX_WEB_TEXT_CHARS = 12000

# API key header and default name for local API authentication.
API_KEY_NAME = "X-API-Key"
API_KEY = os.getenv("ATLAS_API_KEY", "")

# Audit and secure vault filenames.
AUDIT_LOG_NAME = "atlas_web_audit.log"
VAULT_FILE_NAME = "atlas_secrets.bin"
TRAIT_STORE_NAME = "atlas_traits.json"
TRUST_PROFILE_NAME = "atlas_trust.json"
PERSONA_SUMMARY_NAME = "atlas_persona_summary.txt"
NICKNAME_PROFILE_NAME = "atlas_nickname_profile.json"
TRAINING_STORE_NAME = "atlas_training.json"
