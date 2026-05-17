"""
Clipboard listener daemon.
Polls the system clipboard every N seconds.
If new content looks like a live comment block, pushes it to the shared queue.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time

import pyperclip

from config import settings

log = logging.getLogger(__name__)

# Heuristics — any of these words in clipboard = likely a comment block
_ORDER_KEYWORDS = re.compile(
    r"\b(mine|pa-mine|pamine|order|kuha|bili|penge|isa|dalawa|tatlo|apat|lima|"
    r"plus|\\+[0-9]|bid|bi-bid|bidding|sold|reserve|resibo)\b",
    re.IGNORECASE,
)


class ClipboardListener:
    """
    Background asyncio task that monitors the clipboard.
    Pushes detected comment blocks to `comment_queue` as raw strings.
    """

    def __init__(self, comment_queue: asyncio.Queue[str]) -> None:
        self._queue = comment_queue
        self._last_clip: str = ""
        self._running = False

    async def start(self) -> None:
        self._running = True
        log.info("Clipboard listener started (poll interval: %.1fs)", settings.clipboard_poll_interval)
        while self._running:
            await asyncio.sleep(settings.clipboard_poll_interval)
            try:
                clip = pyperclip.paste()
            except Exception as e:
                log.debug("Clipboard read error: %s", e)
                continue

            if not clip or clip == self._last_clip:
                continue

            if self._looks_like_comments(clip):
                self._last_clip = clip
                log.debug("Clipboard comment block detected (%d chars)", len(clip))
                await self._queue.put(clip)
            else:
                # Still update last so we don't re-check same non-comment content
                self._last_clip = clip

    def stop(self) -> None:
        self._running = False
        log.info("Clipboard listener stopped")

    @staticmethod
    def _looks_like_comments(text: str) -> bool:
        """
        Heuristic: does this clipboard content look like a live comment block?
        Requires: multiple lines AND at least one order keyword.
        """
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if len(lines) < 1:
            return False
        return bool(_ORDER_KEYWORDS.search(text))
