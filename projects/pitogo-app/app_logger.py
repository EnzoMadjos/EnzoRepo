"""
app_logger.py — structured rotating JSON logger for PITOGO Barangay App.
Reused directly from sf-qa-agent pattern.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import time
import traceback
from pathlib import Path

import config

_LOG_FILE     = config.SECURE_DIR / "app.log"
_MAX_BYTES    = 512_000   # 500 KB per file
_BACKUP_COUNT = 3


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "ts":    time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "msg":   record.getMessage(),
        }
        extra = getattr(record, "extra", None)
        if extra:
            entry.update(extra)
        if record.exc_info:
            entry["traceback"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("pitogo")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fh = logging.handlers.RotatingFileHandler(
        _LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    fh.setFormatter(_JsonFormatter())
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    return logger


logger = _build_logger()


def info(msg: str, **kwargs) -> None:
    logger.info(msg, extra={"extra": kwargs} if kwargs else {})


def warn(msg: str, **kwargs) -> None:
    logger.warning(msg, extra={"extra": kwargs} if kwargs else {})


def error(msg: str, exc: BaseException | None = None, **kwargs) -> None:
    if exc:
        kwargs["error"] = str(exc)
        kwargs["traceback"] = traceback.format_exc()
    logger.error(msg, extra={"extra": kwargs} if kwargs else {})


def get_recent(n: int = 200) -> list[dict]:
    entries: list[dict] = []
    for log_path in [_LOG_FILE] + [
        Path(str(_LOG_FILE) + f".{i}") for i in range(1, _BACKUP_COUNT + 1)
    ]:
        if log_path.exists():
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    entries.append({"ts": "?", "level": "RAW", "msg": line})
    return list(reversed(entries))[:n]


def clear_logs() -> None:
    if _LOG_FILE.exists():
        _LOG_FILE.write_text("", encoding="utf-8")
