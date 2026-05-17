"""
Comment batch collector.
Accumulates raw comment lines from the clipboard queue.
Flushes to the Order Brain when:
  - batch_window_seconds has elapsed, OR
  - batch_max_comments limit is reached
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Coroutine

from config import settings

log = logging.getLogger(__name__)


@dataclass
class RawComment:
    text: str
    received_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))


FlushCallback = Callable[[list[RawComment]], Coroutine]


class BatchCollector:
    """
    Collects RawComment objects and flushes them periodically.
    """

    def __init__(self, flush_callback: FlushCallback) -> None:
        self._flush_callback = flush_callback
        self._buffer: list[RawComment] = []
        self._last_flush = time.monotonic()
        self._running = False

    async def ingest(self, raw_block: str) -> None:
        """
        Parse a raw clipboard block (one comment per line) into RawComment objects
        and add to buffer. Flushes immediately if max_comments reached.
        """
        lines = [l.strip() for l in raw_block.splitlines() if l.strip()]
        for line in lines:
            self._buffer.append(RawComment(text=line))
            if len(self._buffer) >= settings.batch_max_comments:
                await self._flush()
                return

    async def start_timer(self) -> None:
        """Background loop that flushes on time window."""
        self._running = True
        while self._running:
            await asyncio.sleep(1.0)
            elapsed = time.monotonic() - self._last_flush
            if self._buffer and elapsed >= settings.batch_window_seconds:
                await self._flush()

    def stop(self) -> None:
        self._running = False

    async def _flush(self) -> None:
        if not self._buffer:
            return
        batch = list(self._buffer)
        self._buffer.clear()
        self._last_flush = time.monotonic()
        log.info("Batch flush: %d comments", len(batch))
        try:
            await self._flush_callback(batch)
        except Exception as e:
            log.error("Flush callback error: %s", e)
