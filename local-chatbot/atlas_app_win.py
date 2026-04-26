"""
ATLAS Desktop App — Windows Native
Starts the ATLAS server inside WSL, then opens the chat UI in a native Windows window.
Package with:  pyinstaller --onefile --windowed --icon=atlas.ico atlas_app_win.py
"""

import os
import sys
import time
import signal
import subprocess
import threading
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import messagebox

HOST = "127.0.0.1"
PORT = 8200
URL  = f"http://{HOST}:{PORT}/"

WSL_CMD = (
    "cd /home/enzo/ai-lab/local-chatbot && "
    "venv/bin/uvicorn app:app --host 127.0.0.1 --port 8200 --log-level warning"
)

_wsl_proc = None


def _start_wsl_server():
    global _wsl_proc
    _wsl_proc = subprocess.Popen(
        ["wsl.exe", "-e", "bash", "-lc", WSL_CMD],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
    )


def _stop_wsl_server():
    global _wsl_proc
    # Kill the uvicorn process inside WSL
    subprocess.run(
        ["wsl.exe", "-e", "bash", "-lc", "pkill -f uvicorn 2>/dev/null; exit 0"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if _wsl_proc:
        try:
            _wsl_proc.terminate()
        except Exception:
            pass


def _wait_for_server(timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://{HOST}:{PORT}/auth/status", timeout=1)
            return True
        except Exception:
            time.sleep(0.4)
    return False


def _show_loading_window():
    """Small splash window while server starts."""
    root = tk.Tk()
    root.title("ATLAS")
    root.geometry("320x110")
    root.resizable(False, False)
    root.configure(bg="#1a1a2e")
    root.eval("tk::PlaceWindow . center")

    tk.Label(root, text="ATLAS", font=("Segoe UI", 22, "bold"),
             bg="#1a1a2e", fg="#e94560").pack(pady=(18, 4))
    tk.Label(root, text="Starting up...", font=("Segoe UI", 10),
             bg="#1a1a2e", fg="#aaaaaa").pack()

    root.update()
    return root


def main():
    # Check WSL is available
    if not os.path.exists(r"C:\Windows\System32\wsl.exe") and \
       subprocess.run(["wsl.exe", "--status"], capture_output=True).returncode != 0:
        messagebox.showerror("ATLAS", "WSL2 is not installed.\n\nInstall it from: https://aka.ms/wsl2")
        sys.exit(1)

    # Check if server is already running (e.g. from a previous session)
    already_up = _wait_for_server(timeout=1)

    if not already_up:
        splash = _show_loading_window()
        splash.update()

        t = threading.Thread(target=_start_wsl_server, daemon=True)
        t.start()

        ready = _wait_for_server(timeout=35)
        splash.destroy()

        if not ready:
            messagebox.showerror(
                "ATLAS — Startup Failed",
                "The ATLAS server did not start in time.\n\n"
                "Make sure WSL2 is running and your install is complete.\n"
                "Try running start_atlas.bat first to diagnose."
            )
            _stop_wsl_server()
            sys.exit(1)

    # Open the chat UI in a native window
    try:
        import webview
    except ImportError:
        messagebox.showerror("ATLAS", "pywebview is not installed.\nRun build_exe.bat to set up dependencies.")
        sys.exit(1)

    window = webview.create_window(
        title="ATLAS",
        url=URL,
        width=1080,
        height=780,
        min_size=(720, 520),
        resizable=True,
        text_select=True,
    )

    def on_closed():
        _stop_wsl_server()

    window.events.closed += on_closed

    webview.start(debug=False, gui="edgechromium")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: (_stop_wsl_server(), sys.exit(0)))
    main()
