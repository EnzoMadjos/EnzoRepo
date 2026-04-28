"""
app_logger.py — structured logging for the SF QA Agent.

Writes JSON-lines to secure/app.log (rotating, max 500 KB, 3 backups).
Provides helpers used throughout the app.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import time
import traceback
from pathlib import Path

import config

_LOG_FILE = config.SECURE_DIR / "app.log"
_MAX_BYTES = 512_000  # 500 KB per file
_BACKUP_COUNT = 3  # keep up to 3 rotated files


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            entry["traceback"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            entry.update(record.extra)
        return json.dumps(entry)


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("sfqa")
    if logger.handlers:
        return logger  # already configured (reload-safe)
    logger.setLevel(logging.DEBUG)

    # Rotating file handler
    fh = logging.handlers.RotatingFileHandler(
        _LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    fh.setFormatter(_JsonFormatter())
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    # Console handler (INFO and above)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    return logger


logger = _build_logger()


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def info(msg: str, **kwargs) -> None:
    logger.info(msg, extra={"extra": kwargs} if kwargs else {})


def warn(msg: str, **kwargs) -> None:
    logger.warning(msg, extra={"extra": kwargs} if kwargs else {})


def error(msg: str, exc: BaseException | None = None, **kwargs) -> None:
    if exc:
        logger.error(msg, exc_info=exc, extra={"extra": kwargs} if kwargs else {})
    else:
        logger.error(msg, extra={"extra": kwargs} if kwargs else {})


def get_recent(n: int = 200) -> list[dict]:
    """Return the N most-recent log entries as parsed dicts (newest first)."""
    entries: list[dict] = []
    for log_path in [_LOG_FILE] + [
        Path(str(_LOG_FILE) + f".{i}") for i in range(1, _BACKUP_COUNT + 1)
    ]:
        if log_path.exists():
            with log_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        entries.append({"ts": "?", "level": "RAW", "msg": line})
    # newest first, capped at n
    return list(reversed(entries))[:n]


def clear_logs() -> None:
    """Truncate all log files."""
    for log_path in [_LOG_FILE] + [
        Path(str(_LOG_FILE) + f".{i}") for i in range(1, _BACKUP_COUNT + 1)
    ]:
        if log_path.exists():
            log_path.write_text("", encoding="utf-8")
