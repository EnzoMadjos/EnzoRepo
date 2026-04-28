"""
SalesforceQA Launcher
---------------------
Compiled to SalesforceQA.exe via PyInstaller (install.bat does this automatically).

What this exe does when the user double-clicks it:
  1. Shows a small status window
  2. Checks Ollama is running, starts it if not
  3. Starts the uvicorn server (using the .venv next to the exe)
  4. Opens http://localhost:8200 in the default browser
  5. Keeps running; closing the window stops the server
"""

import os
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

# ---------------------------------------------------------------------------
#  Tkinter status window
# ---------------------------------------------------------------------------
try:
    import tkinter as tk

    HAS_TK = True
except ImportError:
    HAS_TK = False

# When frozen (compiled .exe), sys.executable is the .exe itself.
# The .exe lives next to the app\ folder, so APP_DIR = BASE_DIR\app
BASE_DIR = os.path.dirname(
    os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
)
APP_DIR = os.path.join(BASE_DIR, "app")

# Fallback: if there's no app\ subfolder, assume we ARE already inside app\
if not os.path.isdir(APP_DIR):
    APP_DIR = BASE_DIR

VENV_PYTHON = os.path.join(APP_DIR, ".venv", "Scripts", "python.exe")
APP_PORT = 8200
APP_URL = f"http://localhost:{APP_PORT}"

_server_proc = None
_ollama_proc = None

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _server_alive():
    try:
        urllib.request.urlopen(APP_URL, timeout=2)
        return True
    except Exception:
        return False


def _ollama_alive():
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except Exception:
        return False


def _start_ollama(log):
    global _ollama_proc
    if _ollama_alive():
        log("Ollama already running.")
        return
    log("Starting Ollama...")
    ollama_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
        r"C:\Program Files\Ollama\ollama.exe",
        "ollama",  # hope it's on PATH
    ]
    exe = next((p for p in ollama_paths if os.path.isfile(p)), None) or "ollama"
    try:
        _ollama_proc = subprocess.Popen(
            [exe, "serve"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for _ in range(20):
            if _ollama_alive():
                log("Ollama is ready.")
                return
            time.sleep(0.5)
        log("WARNING: Ollama did not start in time — continuing anyway.")
    except FileNotFoundError:
        log("WARNING: Ollama not found. AI features require Ollama to be installed.")


def _start_server(log):
    global _server_proc
    if _server_alive():
        log("Server already running.")
        return
    if not os.path.isfile(VENV_PYTHON):
        log(
            f"ERROR: Python venv not found.\nExpected:\n{VENV_PYTHON}\n\nPlease re-run install.bat."
        )
        return
    log("Starting SF QA server...")
    _server_proc = subprocess.Popen(
        [
            VENV_PYTHON,
            "-m",
            "uvicorn",
            "sf_app:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(APP_PORT),
        ],
        cwd=APP_DIR,  # <-- run from the app\ folder where sf_app.py lives
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    for _ in range(30):
        if _server_alive():
            log("Server is ready.")
            return
        time.sleep(0.5)
    log("WARNING: Server slow to respond — opening browser anyway.")


def _stop_all():
    if _server_proc:
        try:
            _server_proc.terminate()
        except Exception:
            pass
    if _ollama_proc:
        try:
            _ollama_proc.terminate()
        except Exception:
            pass


# ---------------------------------------------------------------------------
#  Main with Tk window
# ---------------------------------------------------------------------------


def _run_with_gui():
    root = tk.Tk()
    root.title("SF QA Test Agent")
    root.geometry("460x280")
    root.resizable(False, False)
    root.configure(bg="#0f1117")

    # Icon (if present next to exe)
    icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")
    if os.path.isfile(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass

    title_lbl = tk.Label(
        root,
        text="⚡  SF QA Test Agent",
        font=("Segoe UI", 14, "bold"),
        fg="#58a6ff",
        bg="#0f1117",
    )
    title_lbl.pack(pady=(18, 4))

    status_var = tk.StringVar(value="Initializing…")
    status_lbl = tk.Label(
        root,
        textvariable=status_var,
        font=("Segoe UI", 9),
        fg="#8b949e",
        bg="#0f1117",
        wraplength=420,
        justify="left",
    )
    status_lbl.pack(padx=20, fill="x")

    log_text = tk.Text(
        root,
        height=7,
        bg="#161b22",
        fg="#c9d1d9",
        font=("Consolas", 8),
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground="#30363d",
    )
    log_text.pack(padx=16, pady=(10, 6), fill="x")
    log_text.config(state="disabled")

    open_btn = tk.Button(
        root,
        text="Open in Browser",
        state="disabled",
        command=lambda: webbrowser.open(APP_URL),
        bg="#238636",
        fg="white",
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        cursor="hand2",
        padx=10,
        pady=4,
    )
    open_btn.pack(pady=(0, 10))

    def log(msg):
        log_text.config(state="normal")
        log_text.insert("end", msg + "\n")
        log_text.see("end")
        log_text.config(state="disabled")
        status_var.set(msg)

    def on_close():
        _stop_all()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    def startup():
        _start_ollama(log)
        _start_server(log)
        log(f"Ready — {APP_URL}")
        open_btn.config(state="normal")
        webbrowser.open(APP_URL)

    threading.Thread(target=startup, daemon=True).start()
    root.mainloop()


def _run_headless():
    """Fallback if tkinter is unavailable."""

    def log(msg):
        print(msg)

    _start_ollama(log)
    _start_server(log)
    webbrowser.open(APP_URL)
    if _server_proc:
        _server_proc.wait()


if __name__ == "__main__":
    if HAS_TK:
        _run_with_gui()
    else:
        _run_headless()
