# PITOGO Barangay App — Windows Installation Guide

## Requirements

| Requirement | Version | Download |
|-------------|---------|----------|
| Python | 3.10 or newer | https://python.org/downloads |
| WeasyPrint GTK runtime | — | See note below |

> **WeasyPrint note:** PDF generation requires GTK3 runtime libraries on Windows.
> Download the GTK3 runtime installer from https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
> and install it **before** running `install.bat`.

---

## First-time installation

1. Install **Python 3.10+** — tick **"Add Python to PATH"** during setup.
2. Install the **GTK3 runtime** (link above) — required for PDF generation.
3. Open a File Explorer window, navigate to the `windows-dist\` folder.
4. Double-click **`install.bat`**.
   - This creates a Python virtual environment in `.venv\`
   - Installs all dependencies from `requirements.txt`
   - Applies database migrations
   - Writes `start_pitogo.bat`

---

## Starting the app

Double-click **`windows-dist\start_pitogo.bat`**.

The app starts silently (no console window) and opens your browser at:

```
http://localhost:8300
```

Default admin credentials are printed to the app log on first boot.
Look in `secure\pitogo.log` if you need to recover them.

---

## Stopping the app

Double-click **`windows-dist\stop_pitogo.bat`** to kill the server and free port 8300.

---

## Updating

1. Pull or copy the latest files into the project folder.
2. Re-run `install.bat` — it skips venv creation if it already exists and only
   updates packages/migrations.

---

## Folder structure (after install)

```
pitogo-app\
├── app.py              Main application
├── requirements.txt
├── start.py            Cross-platform launcher
├── secure\             Database, logs, keys (do NOT delete)
│   ├── pitogo.db
│   ├── users.json
│   └── pitogo.log
├── .venv\              Python virtual environment (auto-created)
└── windows-dist\
    ├── install.bat         ← Run once to install
    ├── start_pitogo.bat    ← Run to start app
    ├── stop_pitogo.bat     ← Run to stop app
    └── INSTALL.md          ← This file
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Python not found` | Re-install Python with "Add to PATH" checked |
| PDF generation fails | Install GTK3 runtime (see Requirements above) |
| Port 8300 in use | Run `stop_pitogo.bat` or change `APP_PORT` in `.env` |
| App won't start | Check `secure\pitogo.log` for error details |
| Blank login page | Clear browser cache and try http://localhost:8300 again |
