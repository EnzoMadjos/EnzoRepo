"""
ATLAS Desktop App
Starts the FastAPI server in the background and opens the chat UI in a native window.
"""

import os
import signal
import sys
import threading
import time
from pathlib import Path

# ── Resolve project root (works whether run from local-chatbot/ or C:\ATLAS V1\) ──
ROOT = Path(__file__).parent.resolve()
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))


# ── Load API key from secure folder ──
def _load_api_key() -> str:
    candidates = [
        ROOT / "secure" / "atlas_api.key",
        Path("/mnt/c/ATLAS V1/secure/atlas_api.key"),
        Path("C:/ATLAS V1/secure/atlas_api.key"),
    ]
    for p in candidates:
        if p.exists():
            return p.read_text().strip()
    raise FileNotFoundError("atlas_api.key not found. Run install.sh first.")


API_KEY = _load_api_key()
HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}/ui/"

# ── Server thread ──
_server = None


def _start_server():
    import uvicorn

    os.environ["ATLAS_API_KEY"] = API_KEY
    config = uvicorn.Config(
        "app:app",
        host=HOST,
        port=PORT,
        log_level="warning",  # quiet in desktop mode
        reload=False,
    )
    global _server
    _server = uvicorn.Server(config)
    _server.run()


def _stop_server():
    global _server
    if _server:
        _server.should_exit = True


def _wait_for_server(timeout: int = 15) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://{HOST}:{PORT}/auth/status", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


# ── Main ──
def main():
    try:
        import webview
    except ImportError:
        print("pywebview is not installed. Run:  pip install pywebview")
        sys.exit(1)

    # Start server in background thread
    t = threading.Thread(target=_start_server, daemon=True)
    t.start()

    # Wait for it to be ready
    print("Starting ATLAS...")
    ready = _wait_for_server(timeout=20)
    if not ready:
        print("ERROR: Server did not start in time.")
        _stop_server()
        sys.exit(1)

    # Open native window with the chat UI
    window = webview.create_window(
        title="ATLAS",
        url=URL,
        width=1050,
        height=760,
        min_size=(700, 500),
        resizable=True,
        text_select=True,
    )

    def on_closed():
        _stop_server()

    window.events.closed += on_closed

    webview.start(debug=False)


if __name__ == "__main__":
    # Handle Ctrl+C cleanly
    signal.signal(signal.SIGINT, lambda *_: (_stop_server(), sys.exit(0)))
    main()
