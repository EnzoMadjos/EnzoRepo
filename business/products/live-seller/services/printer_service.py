"""
Thermal printer service using python-escpos.
Auto-detects USB ESC/POS printer. Prints order slips asynchronously via a queue.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from config import settings

log = logging.getLogger(__name__)


class PrinterService:
    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._printer = None

    def _get_printer(self):
        """Lazy-initialize ESC/POS printer. Returns None if not available."""
        try:
            from escpos.printer import Usb
            p = Usb(settings.printer_vendor_id, settings.printer_product_id)
            return p
        except Exception as e:
            log.warning("Printer not available: %s", e)
            return None

    async def start(self) -> None:
        if not settings.printer_enabled:
            log.info("Printer disabled in config — print queue will log only")
        self._running = True
        log.info("Printer service started")
        while self._running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await asyncio.get_event_loop().run_in_executor(None, self._print_slip, job)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                log.error("Printer worker error: %s", e)

    def stop(self) -> None:
        self._running = False

    async def enqueue_order(self, order: dict, buyer: dict) -> None:
        await self._queue.put({"type": "order", "order": order, "buyer": buyer})

    async def enqueue_bid_winner(self, bid_session: dict, winner: dict) -> None:
        await self._queue.put({"type": "bid_winner", "bid_session": bid_session, "winner": winner})

    def _print_slip(self, job: dict) -> None:
        if not settings.printer_enabled:
            log.info("PRINT (dry-run): %s", job)
            return

        p = self._get_printer()
        if p is None:
            log.warning("Skipping print — printer not connected")
            return

        try:
            if job["type"] == "order":
                self._print_order_slip(p, job["order"], job["buyer"])
            elif job["type"] == "bid_winner":
                self._print_bid_slip(p, job["bid_session"], job["winner"])
        except Exception as e:
            log.error("Print error: %s", e)
        finally:
            try:
                p.close()
            except Exception:
                pass

    def _print_order_slip(self, p, order: dict, buyer: dict) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        p.set(align="center", bold=True, double_height=True)
        p.text(f"{settings.store_name}\n")
        p.set(align="center", bold=False, double_height=False)
        p.text(f"{settings.store_tagline}\n")
        p.text("-" * 32 + "\n")
        p.set(align="left")
        p.text(f"Date   : {now}\n")
        p.text(f"Order  : #{order['id']}\n")
        p.text("-" * 32 + "\n")
        p.text(f"Buyer  : {buyer.get('display_name', 'Customer')}\n")
        if buyer.get("handle"):
            p.text(f"Handle : @{buyer['handle']}\n")
        p.text("-" * 32 + "\n")
        p.set(bold=True)
        p.text(f"{order.get('product_name', 'Item')}")
        if order.get("variant_label"):
            p.text(f" [{order['variant_label']}]")
        p.text(f"\n")
        p.set(bold=False)
        p.text(f"Qty    : x{order.get('qty', 1)}\n")
        p.text(f"Price  : P{order.get('unit_price', 0):.0f} each\n")
        p.set(bold=True, double_height=True)
        p.text(f"TOTAL  : P{order.get('total_price', 0):.0f}\n")
        p.set(bold=False, double_height=False)
        p.text("-" * 32 + "\n")
        p.text("Payment: COD\n")
        p.cut()

    def _print_bid_slip(self, p, bid_session: dict, winner: dict) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        p.set(align="center", bold=True, double_height=True)
        p.text(f"{settings.store_name}\n")
        p.set(align="center", bold=False, double_height=False)
        p.text("*** BID WINNER ***\n")
        p.text("-" * 32 + "\n")
        p.set(align="left")
        p.text(f"Date   : {now}\n")
        p.text("-" * 32 + "\n")
        p.text(f"Item   : {bid_session.get('product_name', 'Item')}\n")
        if bid_session.get("variant_label"):
            p.text(f"Variant: {bid_session['variant_label']}\n")
        p.text("-" * 32 + "\n")
        p.text(f"Winner : {winner.get('display_name', '?')}\n")
        if winner.get("handle"):
            p.text(f"Handle : @{winner['handle']}\n")
        p.set(bold=True, double_height=True)
        p.text(f"AMOUNT : P{winner.get('amount', 0):.0f}\n")
        p.set(bold=False, double_height=False)
        p.text("-" * 32 + "\n")
        p.text("Payment: COD\n")
        p.cut()
