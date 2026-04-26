# SF QA Test Agent

A local AI-powered Salesforce test automation tool. Paste a plain English test script → the AI plans the steps → real records are created on your Salesforce org with live progress and clickable links.

Runs entirely on your machine. No cloud services. No data leaves your network.

---

## How It Works

1. Log in with your Salesforce credentials (securely — never stored to disk)
2. Paste a test script (or upload a `.txt`, `.docx`, or `.pdf` file) describing what records to create
3. The local AI model reads the script and generates an execution plan
4. The app creates the records on your org and streams live progress back
5. The Results table shows each record with a direct link to Salesforce

---

## Requirements

| Tool | Purpose | Download |
|---|---|---|
| **Python 3.10+** | Runs the application | https://www.python.org/downloads/ |
| **Ollama** | Runs the local AI model (offline) | https://ollama.com/download |
| A modern browser | Chrome, Edge, Firefox | — |

---

## Installation

### 1. Get the code

Clone or download this repository into a folder of your choice.

```bash
git clone <repo-url> sf-qa-agent
cd sf-qa-agent
```

### 2. Install Ollama and pull the AI model

After installing Ollama, open a terminal and run:

```bash
ollama pull llama3.2:3b
```

This downloads the AI model (~2 GB). You only need to do this once.

### 3. Create a virtual environment and install dependencies

```bash
# Mac / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

### 4. Set up your environment file

```bash
# Mac / Linux
cp .env.example .env

# Windows
copy .env.example .env
```

Open `.env` — the defaults work out of the box. The only setting you may need to change is `APP_PORT` if port `8200` is already in use.

> **Salesforce credentials are NOT in `.env`.** You enter them on the login screen.

---

## Starting the App

```bash
# Mac / Linux
./start.sh

# Or manually (any platform)
uvicorn sf_app:app --host 0.0.0.0 --port 8200 --reload
```

Then open your browser to **http://localhost:8200**

---

## Salesforce Setup (First-Time Only)

Newer Salesforce orgs disable password-based login by default. You will need to create a **Connected App** to get a Consumer Key and Consumer Secret.

Follow the step-by-step guide in **[CONNECTED_APP_SETUP.md](./CONNECTED_APP_SETUP.md)**.

Once you have those credentials, you only need to fill them in once — the app can save your org profile so future logins are one click.

---

## Logging In

On the login screen you will see two options:

- **Existing Org** — select a previously saved org profile (one-click login)
- **Add New Org** — enter credentials for a new org

### Fields

| Field | Where to get it |
|---|---|
| **Username** | Your Salesforce login email |
| **Password** | Your Salesforce password |
| **Security Token** | Reset from: SF → Avatar → Settings → My Personal Information → Reset My Security Token |
| **Org Type** | Developer/Production or Sandbox |
| **Consumer Key** | From your Connected App (`CONNECTED_APP_SETUP.md`) |
| **Consumer Secret** | From your Connected App |

> Check **"Remember this org"** before connecting to save the profile for future logins.

---

## Writing a Test Script

```
TEST: <Title>

STEP 1: <Salesforce Object API Name>
  - FieldApiName: Value
  - FieldApiName: Value

STEP 2: <Salesforce Object API Name> (linked to Step 1)
  - FieldApiName: Value
  - LookupFieldId: $step1.id
```

### Rules

- Use Salesforce **API names** for both objects and fields (e.g. `Account`, `Contact`, `FirstName`, `AccountId`)
- Reference a record created in a previous step with `$stepN.id` (e.g. `$step1.id`)
- Object type goes in the `STEP N:` line header
- You can paste the script or upload a `.txt`, `.docx`, or `.pdf` file

### Example

```
TEST: Create a Customer Account with a Contact

STEP 1: Account
  - Name: Acme Corporation
  - Type: Customer
  - Industry: Technology

STEP 2: Contact
  - FirstName: John
  - LastName: Smith
  - Email: john@acme.com
  - AccountId: $step1.id
```

---

## Supported File Formats

| Format | Notes |
|---|---|
| Paste | Directly in the text area |
| `.txt` | Plain text file |
| `.docx` | Microsoft Word document |
| `.pdf` | PDF document |

---

## Admin Panel

Click the **⚙ Admin** button in the header (visible after login) to open the admin panel.

### Error Log

- Shows all errors, warnings, and info events from the app in real time
- **Refresh** to reload — **Clear Logs** to wipe the log file
- Errors include full stack traces to help diagnose issues

### AI System Prompt — Live Patch

The "patch" feature lets you edit the instructions the AI uses to parse test scripts — **without restarting the server**. Use this when:

- The AI misreads a field name or object type
- You want to add specific instructions for your org's custom objects
- A test is producing incorrect plans and you want to fine-tune the AI's behavior

**How to use:**
1. Click **Load Current** to see the active prompt
2. Edit it — add clearer instructions, add examples, fix any patterns that aren't working
3. Click **Apply Patch** — the change takes effect on the very next test run
4. Changes are in-memory only — they reset when the server restarts. To make permanent, edit `llm_planner.py` → `_SYSTEM_PROMPT`.

---

## Sharing with Someone on the Same Network

When the app is running, the login page shows two URLs:

- **This machine:** `http://localhost:8200`
- **From another device on the same network:** `http://192.168.x.x:8200`

Anyone on the same WiFi can use the network URL.

---

## Stopping the App

Press `Ctrl + C` in the terminal where the app is running.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `SOAP API login() is disabled` | You need a Connected App — follow `CONNECTED_APP_SETUP.md` |
| `Planning failed: 404` | Ollama isn't running or wrong model name. Run `ollama serve` and check `.env` has `OLLAMA_MODEL=llama3.2:3b` |
| `Could not connect to Salesforce` | Wrong credentials or org type. Check username, password, security token |
| `Port already in use` | Change `APP_PORT=8200` to another port in `.env` |
| App slow on first run | The AI model takes a few seconds to warm up — normal |
| Plan is wrong / missing fields | Use the **Admin → AI System Prompt Patch** to refine the AI's instructions |

---

## Security Notes

- Salesforce credentials are held **in memory only** — never written to disk (except encrypted org profiles if you choose to save them)
- Saved org profiles are encrypted with a machine-specific key stored in `secure/profiles.key`
- Sessions expire automatically after 12 hours
- The app runs **entirely locally** — no data is sent to any external service except Salesforce itself
- Ollama runs completely offline — the AI model runs on your machine


---

## What It Does

1. You paste a test script (or upload a `.docx` / `.pdf` file) describing what records to create
2. The AI reads the script and figures out the sequence of Salesforce operations
3. The app creates the records on your org and shows you live progress with clickable links to each record

---

## Requirements

Before installing, make sure the following are on your machine:

| Tool | Purpose | Download |
|---|---|---|
| **Python 3.10+** | Runs the app | https://www.python.org/downloads/ |
| **Ollama** | Runs the local AI model | https://ollama.com/download |
| A modern browser | Chrome, Edge, Firefox | — |

---

## Installation

### 1. Download the app

Either clone the repository or download and extract the zip file into a folder of your choice, e.g. `C:\sf-qa-agent\` (Windows) or `~/sf-qa-agent/` (Mac/Linux).

### 2. Install Ollama and pull the AI model

After installing Ollama, open a terminal and run:

```bash
ollama pull llama3.2
```

This downloads the AI model (~2GB). You only need to do this once.

### 3. Install Python dependencies

Open a terminal in the `sf-qa-agent` folder and run:

```bash
pip install -r requirements.txt
```

On Windows you may need:
```bash
pip install -r requirements.txt --break-system-packages
```

### 4. Create your environment file

Copy the example file:

```bash
# Mac/Linux
cp .env.example .env

# Windows
copy .env.example .env
```

Open `.env` in any text editor. The defaults are fine — you only need to change `APP_PORT` if port `8200` is already in use on your machine.

> **Salesforce credentials are NOT stored in `.env`** — you enter them on the login screen every time.

---

## Starting the App

### Mac / Linux

```bash
./start.sh
```

### Windows

```batch
start_app.bat
```

*(The `.bat` launcher is included in the Windows installer package)*

Then open your browser and go to:

```
http://localhost:8200
```

---

## Logging In

The login screen asks for your Salesforce credentials:

| Field | Where to get it |
|---|---|
| **Username** | Your Salesforce login email |
| **Password** | Your Salesforce password |
| **Security Token** | Email from Salesforce — see below |
| **Org Type** | Developer/Production or Sandbox |
| **Consumer Key / Secret** | From your Connected App — see `CONNECTED_APP_SETUP.md` |

### Getting your Security Token

1. Log in to Salesforce → click your **avatar** (top right) → **Settings**
2. Left sidebar → **My Personal Information** → **Reset My Security Token**
3. Click the button — Salesforce emails the token immediately
4. Copy it from the email and paste it into the login field

> The token only changes if you reset your SF password or manually regenerate it. Keep it somewhere safe.

### Connected App Setup

The first time you log in you will need a **Consumer Key** and **Consumer Secret** from a Salesforce Connected App. Follow the step-by-step guide in **`CONNECTED_APP_SETUP.md`** (included in this folder).

---

## Writing a Test Script

The app accepts plain English test scripts in the following format:

```
TEST: <Title of your test>

STEP 1: <Salesforce Object Type>
  - Field Name: Value
  - Field Name: Value

STEP 2: <Salesforce Object Type> (linked to Step 1 <Object>)
  - Field Name: Value
  - Field Name: $step1.id
```

### Example

```
TEST: Create a Customer Account with a Contact

STEP 1: Create Account
  - Name: Acme Corporation
  - Type: Customer
  - Industry: Technology

STEP 2: Create Contact (linked to Step 1 Account)
  - First Name: John
  - Last Name: Smith
  - Email: john@acme.com
```

### Rules

- Each `STEP` header must include the Salesforce **object type** (e.g. Account, Contact, Opportunity, Case)
- Field names should match Salesforce API names (e.g. `FirstName`, `LastName`, `AccountId`)
- To reference a record created in a previous step, use `$step1.id`, `$step2.id`, etc.
- You can paste the script directly or upload a `.txt`, `.docx`, or `.pdf` file

---

## Supported File Formats

| Format | Notes |
|---|---|
| Paste (plain text) | Directly in the text area |
| `.txt` | Plain text file |
| `.docx` | Microsoft Word document |
| `.pdf` | PDF document |

---

## Sharing the App with Someone Else

When the app is running, the login page shows two URLs at the bottom:

- **This machine:** `http://localhost:8200` — use this on the machine running the app
- **From another device (same network):** `http://192.168.x.x:8200` — share this with anyone on the same WiFi

> For full standalone use, the other person should run their own installation of this app on their own machine.

---

## Stopping the App

Press `Ctrl + C` in the terminal where the app is running.

---

## Troubleshooting

**"Salesforce authentication failed: SOAP API login() is disabled"**
→ You need a Connected App. Follow `CONNECTED_APP_SETUP.md`.

**"Could not connect to Salesforce"**
→ Check your username, password, and security token. Make sure Org Type is correct (Developer/Production vs Sandbox).

**"Planning failed"**
→ Make sure Ollama is running (`ollama serve`) and the model is installed (`ollama pull llama3.2`).

**Port already in use**
→ Change `APP_PORT=8200` to another port (e.g. `8201`) in your `.env` file.

**App is slow to respond on first run**
→ The AI model takes a few seconds to load on the first request. Subsequent runs are faster.

---

## Security Notes

- Your Salesforce credentials are **never stored to disk** — they are held in memory only for the duration of your session (12 hours)
- Sessions expire automatically — you will be asked to log in again after 12 hours of inactivity
- The app runs entirely on your local machine — no data is sent to any external service
- After sharing credentials for testing, **reset your Salesforce password and security token**
