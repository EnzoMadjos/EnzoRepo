from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    port: int = 8500
    db_path: str = "secure/minetracker.db"
    printer_usb_vid: int = 0x04B8  # Epson default
    printer_usb_pid: int = 0x0202
    new_buyer_mine_limit: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
BASE_DIR = Path(__file__).parent
