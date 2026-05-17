import logging
import time

log = logging.getLogger("printer")

try:
    from escpos.printer import Usb
    HAS_ESCPOS = True
except Exception:
    HAS_ESCPOS = False
    log.warning("python-escpos not available — printing will be virtual (logged only)")


def print_mine(
    display_name: str,
    handle: str,
    price: float,
    mined_at: int,
    vid: int = 0x04B8,
    pid: int = 0x0202,
) -> bool:
    """Print a mine label. Returns True on success (or virtual success), False on error."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mined_at))

    if not HAS_ESCPOS:
        log.info("[VIRTUAL PRINT] %s @%s  PHP %.2f  %s", display_name, handle, price, ts)
        return True

    try:
        p = Usb(vid, pid)
        p.set(align="center", bold=True, height=2, width=2)
        p.text(f"{display_name}\n")
        p.set(align="center", bold=False, height=1, width=1)
        p.text(f"@{handle}\n")
        p.set(align="center", bold=True, height=2, width=2)
        p.text(f"PHP {price:,.2f}\n")
        p.set(align="center", bold=False, height=1, width=1)
        p.text(f"{ts}\n")
        p.text("\n\n\n")
        p.cut()
        return True
    except Exception as e:
        log.error("Print failed (VID=0x%04x PID=0x%04x): %s", vid, pid, e)
        return False
