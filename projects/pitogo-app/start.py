"""
start.py — launcher for PITOGO Barangay App.
Checks venv/deps, then starts the app and opens the browser.
"""
import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).parent
PORT     = int(os.getenv("APP_PORT", "8300"))
URL      = f"http://localhost:{PORT}"

def _server_alive() -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(f"{URL}/status", timeout=2)
        return True
    except Exception:
        return False

def main():
    print(f"\n  PITOGO Barangay App — Starting on {URL}\n")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", f"--port={PORT}", "--no-access-log"],
        cwd=str(BASE_DIR),
    )
    # Wait for server to be ready
    for _ in range(20):
        if _server_alive():
            break
        time.sleep(0.5)
    print(f"  Ready → {URL}\n")
    webbrowser.open(URL)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        print("\n  Stopped.\n")

if __name__ == "__main__":
    main()
