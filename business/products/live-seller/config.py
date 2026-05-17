from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).parent
SECURE_DIR = BASE_DIR / "secure"
DB_PATH = SECURE_DIR / "liveseller.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    # Server
    host: str = "0.0.0.0"
    port: int = 8500
    debug: bool = False

    # LLM — primary (local Ollama)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "phi4-mini"
    ollama_timeout: int = 10  # seconds per attempt
    ollama_max_retries: int = 3

    # LLM — fallback (GitHub Models API)
    github_models_token: str = ""
    github_models_model: str = "meta/Llama-3.3-70B-Instruct"
    github_models_endpoint: str = "https://models.inference.ai.azure.com"

    # Comment pipeline
    batch_window_seconds: int = 30
    batch_max_comments: int = 20
    clipboard_poll_interval: float = 3.0  # seconds between clipboard checks

    # Order Brain confidence thresholds
    confidence_auto_confirm: float = 0.85
    confidence_review_threshold: float = 0.60

    # Thermal printer (USB)
    printer_vendor_id: int = 0x0416   # Xprinter default — override in .env
    printer_product_id: int = 0x5011  # Xprinter default — override in .env
    printer_enabled: bool = True

    # Bidding defaults
    bid_countdown_default_seconds: int = 60
    bid_min_increment_default: float = 10.0

    # Store info (printed on slips)
    store_name: str = "My Live Store"
    store_tagline: str = "Salamat sa inyong suporta! 🙏"


settings = Settings()
