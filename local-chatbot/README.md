# NITRO — Local AI Assistant
### Personal AI. Fully local. No cloud. No subscription.

---

## What is NITRO?

NITRO is your personal offline AI assistant running locally on your machine using Ollama.
It has a custom persona (Bisaya/Tagalog humor, calls you Pre), persistent memory, encrypted secure storage, and a browser-based chat UI.
No internet required after setup. No OpenAI. No Copilot. Just NITRO.

---

## Requirements

Before you copy the folder to a new computer, make sure you have:

| Requirement | How to install |
|---|---|
| **WSL2** (Windows only) | `wsl --install` in PowerShell as Admin, then restart |
| **Ubuntu** in WSL2 | From Microsoft Store, or `wsl --install -d Ubuntu` |
| **Python 3.10+** | `sudo apt install python3 python3-venv python3-pip` |
| **Ollama** | Run inside WSL: `curl -fsSL https://ollama.com/install.sh \| sh` |
| **Git** (optional) | `sudo apt install git` |

---

## First-Time Setup (New Computer)

### Option A — From Windows (double-click)
1. Copy the entire `local-chatbot` folder to the new computer
2. Open the folder in Windows Explorer
3. Go into `windows-launchers/`
4. Double-click **`install_nitro.bat`** — this runs the full installer inside WSL
5. Wait for it to finish (downloads the AI model — ~1GB, takes a few minutes)
6. Double-click **`start_nitro.bat`** to launch NITRO
7. Open your browser and go to: **`http://127.0.0.1:8000/ui/`**
8. Paste your API key from `secure/nitro_api.key` — done!

### Option B — From WSL/Linux terminal
```bash
# 1. Go into the project folder
cd /path/to/local-chatbot

# 2. Run the installer (only needed once per machine)
bash install.sh

# 3. Start NITRO
bash start_nitro.sh
```
Then open **`http://127.0.0.1:8000/ui/`** in your browser.

---

## Daily Use

### Start NITRO
```bash
# From WSL terminal:
cd /home/enzo/ai-lab/local-chatbot
bash start_nitro.sh

# Or from Windows — double-click:
windows-launchers/start_nitro.bat
```

### Open the Chat UI
Go to: **http://127.0.0.1:8000/ui/**

Enter your API key the first time (saved in your browser after that).
Your API key is in `secure/nitro_api.key` or printed in the terminal when you start NITRO.

### Stop NITRO
Press `Ctrl+C` in the terminal where it's running.

---

## Folder Structure

```
local-chatbot/
│
├── app.py                  ← Main FastAPI server (all endpoints)
├── settings.py             ← All file path constants
├── Modelfile               ← Custom NITRO Ollama model definition
├── requirements.txt        ← Python dependencies
├── install.sh              ← First-time setup script
├── start_nitro.sh          ← Daily startup script
│
├── secure/                 ← 🔒 PRIVATE — do NOT share this folder
│   ├── nitro.bin           ← Encrypted NITRO persona
│   ├── nitro.key           ← Encryption key
│   ├── nitro.py.bak        ← Backup of original persona
│   ├── nitro_api.key       ← Your API key
│   ├── nitro_traits.json   ← NITRO personality traits
│   ├── nitro_training.json ← Language/culture training data
│   ├── nitro_trust.json    ← Trust profile
│   └── nitro_persona_summary.txt ← Full persona snapshot
│
├── templates/
│   └── chat.html           ← Browser chat UI
│
├── windows-launchers/      ← Windows .bat shortcut files
│   ├── install_nitro.bat   ← Run ONCE on first setup
│   ├── start_nitro.bat     ← Start NITRO server
│   ├── run_monitor.bat     ← Check file integrity
│   ├── run_monitor_open_log.bat    ← Check + open log
│   ├── run_monitor_history.bat     ← Check + save dated log
│   └── logs/               ← Monitor log outputs
│
├── auth.py                 ← API key authentication
├── audit.py                ← Action audit logging
├── vault.py                ← Encrypted secrets storage
├── trait_memory.py         ← NITRO personality traits
├── training_memory.py      ← Language training data
├── trust_profile.py        ← Trust access profile
├── persona_store.py        ← Persona snapshot
├── nickname_profile.py     ← Pre / Lods nickname settings
├── nitro_loader.py         ← Loads encrypted persona
├── nitro_monitor.py        ← File tamper detection
├── web_fetcher.py          ← Safe web fetch with IP blocking
└── runtime_config.py       ← Web fetch toggle
```

---

## Updating / Training NITRO

NITRO learns from you over time. Training is saved automatically in `secure/nitro_training.json`.

### Add a training entry via the API:
```bash
curl -s -X POST http://127.0.0.1:8000/training \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entry": "Pre always says amigo instead of friend when speaking casually"}'
```

### Update NITRO's persona snapshot:
```bash
curl -s -X POST http://127.0.0.1:8000/persona/summary \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"summary": "Updated persona text here..."}'
```

### Set nickname preference (Pre or Lods):
```bash
curl -s -X POST http://127.0.0.1:8000/nickname \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"preferred": "Pre"}'
```

---

## Integrity Monitor (Windows)

The monitor checks that NITRO's secure files have not been tampered with.

| Launcher | What it does |
|---|---|
| `run_monitor.bat` | Runs check, saves log to `windows-launchers/logs/` |
| `run_monitor_open_log.bat` | Same but opens the log in Notepad |
| `run_monitor_history.bat` | Saves a new dated log file each run |

Or run manually from WSL:
```bash
cd /home/enzo/ai-lab/local-chatbot
python3 nitro_monitor.py

# Reset the baseline after a trusted update:
python3 nitro_monitor.py --init
```

---

## API Key

Your API key is stored in `secure/nitro_api.key`.

To use the API directly (curl / Postman / etc.), include it as a header:
```
X-API-Key: your-key-here
```

---

## Troubleshooting

**NITRO won't start — "model not found"**
```bash
cd /home/enzo/ai-lab/local-chatbot
ollama create nitro -f Modelfile
```

**Ollama not running**
```bash
ollama serve &
```

**Port 8000 already in use**
```bash
# Find and kill what's using port 8000:
lsof -i :8000
kill -9 <PID>
```

**Chat UI says "Could not reach NITRO"**
- Make sure `start_nitro.sh` or `start_nitro.bat` is running
- Check the terminal for errors
- Confirm you're on the right port: `http://127.0.0.1:8000/ui/`

**Wrong API key error in the chat UI**
- Click "Change API key" in the browser
- Re-paste the key from `secure/nitro_api.key`

**Re-run the installer to fix a broken setup**
```bash
bash install.sh
```

---

## Security Notes

- Never share the `secure/` folder — it contains your encryption keys and persona
- The `.gitignore` already excludes `secure/` and `venv/` from git
- If you clone this to a new machine, `install.sh` will generate fresh keys for that machine
- Your old encrypted `nitro.bin` from a different machine will only decrypt with its matching `nitro.key`

---

*NITRO — Built local. Stays local. Always Pre.*
