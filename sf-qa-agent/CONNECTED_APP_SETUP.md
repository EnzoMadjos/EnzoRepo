# Salesforce Connected App Setup Guide

You only need to do this **once per org**. It takes about 5 minutes.

> **Why is this needed?**
> Newer Salesforce orgs disable the old username/password login by default. A Connected App provides a Consumer Key and Consumer Secret that the SF QA Agent uses to authenticate via the more secure OAuth 2.0 flow.

---

## Already have a Connected App? Find your Consumer Key & Secret

If the app was already created, go straight to your keys:

**Direct link** (replace the domain with your org's domain):
```
https://<your-org>.my.salesforce.com/lightning/setup/ConnectedApplication/home
```

**Manual path** (if the link above doesn't work):
1. Click the ⚙ gear icon (top right) → **Setup**
2. In the Quick Find box (top left), type **App Manager**
3. Click **App Manager** in the results
4. Find **QA Agent** in the list → click the **▾ dropdown arrow** on the far right → **View**
5. Scroll down to **API (Enable OAuth Settings)**
6. **Consumer Key** is shown directly on the page
7. **Consumer Secret** → click **Click to reveal**

> If you don't see it in App Manager, search **Connected Apps** in Quick Find instead.

---

## Creating a New Connected App

### Step 1 — Open the Connected App Creation Form

**Direct link** (replace the domain with your org's domain):
```
https://<your-org>.my.salesforce.com/app/mgmt/forceconnectedapps/forceAppEdit.apexp
```

**Example:**
```
https://orgfarm-d8cd9f4557-dev-ed.develop.my.salesforce.com/app/mgmt/forceconnectedapps/forceAppEdit.apexp
```

**Manual path** (if the link above doesn't work):
1. Click ⚙ → **Setup**
2. Quick Find → type **App Manager**
3. Click **New Connected App** (top right button)

---

### Step 2 — Fill in Basic Information

| Field | Value |
|---|---|
| Connected App Name | `QA Agent` |
| API Name | `QA_Agent` *(auto-fills)* |
| Contact Email | Your email address |

---

### Step 3 — Enable OAuth Settings

Scroll down to the **API (Enable OAuth Settings)** section:

1. ✅ Check **Enable OAuth Settings**
2. **Callback URL:** `http://localhost:8200/oauth/callback`
3. **Selected OAuth Scopes** — add both of these:
   - `Manage user data via APIs (api)`
   - `Perform requests at any time (refresh_token, offline_access)`
4. ✅ Check **Enable Client Credentials Flow**

---

### Step 4 — Save and Wait

Click **Save** → click **Continue** on the confirmation screen.

> ⏳ **Wait 2–10 minutes.** Salesforce needs time to activate the Connected App. If you try to log in too soon you will get an `invalid_client` error — just wait a bit longer and try again.

---

### Step 5 — Copy Your Consumer Key and Secret

1. After saving, you land on the Connected App detail page
2. Click **Manage Consumer Details** (you may be prompted to verify via email code or authenticator app)
3. Copy the **Consumer Key** and the **Consumer Secret** — paste these into the app's login screen

---

### Step 6 — Allow Username-Password OAuth Flow

This is a one-time org-level setting:

1. In Setup → Quick Find → type `OAuth`
2. Click **OAuth and OpenID Connect Settings**
3. Toggle **ON** → `Allow OAuth Username-Password Flows`
4. Click **Save**

---

### Step 7 — Trusted IP Range (Optional — skips security token)

If you don't want to enter a security token every time, you can whitelist your IP:

1. In Setup → Quick Find → type `Network Access`
2. Click **Network Access**
3. Click **New** → enter your public IP as both Start and End IP
4. Click **Save**

With this in place, you can leave the Security Token field blank in the app.

---

## Logging In to the QA Agent

Open the app at `http://localhost:8200` → click **Add New Org** and fill in:

| Field | Value |
|---|---|
| Username | Your Salesforce login email |
| Password | Your Salesforce password |
| Security Token | From SF Settings → Reset My Security Token (see below) |
| Org Type | Developer / Production (or Sandbox) |
| Consumer Key | Copied from Step 5 (or the "Find your keys" section above) |
| Consumer Secret | Copied from Step 5 (or the "Find your keys" section above) |

Check **"Remember this org"** and give it a profile name so you can log in with one click next time.

Click **Connect to Salesforce**.

---

## How to Get Your Security Token

**Direct link** (replace the domain with your org's domain):
```
https://<your-org>.my.salesforce.com/setup/personal/resetApiToken.jsp
```

**Manual path:**
1. Log in to Salesforce in your browser
2. Click your **profile avatar** (top right) → **Settings**
3. Left sidebar → **My Personal Information** → **Reset My Security Token**
4. Click **Reset Security Token** — Salesforce emails it to you within seconds
5. Copy it from the email and paste it into the app's Security Token field

> The token only changes if you reset your Salesforce password or manually regenerate it. Store it somewhere safe.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `invalid_client` | Wait a few more minutes for the Connected App to activate |
| `invalid_grant` | Wrong password or security token — double-check both |
| `SOAP API login() is disabled` | Consumer Key / Secret are missing or wrong |
| `user is not allowed to use this app` | Setup → App Manager → QA Agent → Manage → Edit Policies → set **Permitted Users** to "All users may self-authorize" |
| Can't find App Manager | Try Quick Find → **Connected Apps** instead |
