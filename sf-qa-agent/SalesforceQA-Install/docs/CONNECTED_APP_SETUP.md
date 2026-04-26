# Salesforce Connected App Setup Guide

You only need to do this **once per org**. It takes about 5 minutes.

> **Why is this needed?**
> Newer Salesforce orgs disable the old username/password login by default. A Connected App provides a Consumer Key and Consumer Secret that the SF QA Agent uses to authenticate via the more secure OAuth 2.0 flow.

---

## Step 1 — Open the Connected App Creation Form

In your browser, navigate to this URL (replace the domain with your org's domain):

```
https://<your-org>.my.salesforce.com/app/mgmt/forceconnectedapps/forceAppEdit.apexp
```

**Example:**
```
https://orgfarm-d8cd9f4557-dev-ed.develop.my.salesforce.com/app/mgmt/forceconnectedapps/forceAppEdit.apexp
```

> **Can't find Setup?** Go to Salesforce → click the gear icon (⚙) top right → **Setup**, then paste the URL above directly into your browser address bar replacing only the domain part.

---

## Step 2 — Fill in Basic Information

| Field | Value |
|---|---|
| Connected App Name | `QA Agent` |
| API Name | `QA_Agent` *(auto-fills)* |
| Contact Email | Your email address |

---

## Step 3 — Enable OAuth Settings

Scroll down to the **API (Enable OAuth Settings)** section:

1. ✅ Check **Enable OAuth Settings**
2. **Callback URL:** `http://localhost:8200/oauth/callback`
3. **Selected OAuth Scopes** — add both of these:
   - `Manage user data via APIs (api)`
   - `Perform requests at any time (refresh_token, offline_access)`
4. ✅ Check **Enable Client Credentials Flow**

---

## Step 4 — Save and Wait

Click **Save** → click **Continue** on the confirmation screen.

> ⏳ **Wait 2–10 minutes.** Salesforce needs time to activate the Connected App before it will work. If you try to log in too soon you'll get an `invalid_client` error — just wait a bit longer.

---

## Step 5 — Copy Your Consumer Key and Secret

1. After saving, you land on the Connected App detail page
2. Click **Manage Consumer Details** (you may be prompted to verify via email code or authenticator app)
3. Copy the **Consumer Key** and the **Consumer Secret** — you will paste these into the app's login screen

---

## Step 6 — Allow Username-Password OAuth Flow

This is a one-time org setting you need to enable:

1. In Salesforce **Setup**, type `OAuth` in the Quick Find box (top left)
2. Click **OAuth and OpenID Connect Settings**
3. Toggle **ON** → `Allow OAuth Username-Password Flows`
4. Click **Save**

---

## Step 7 — Set Up a Trusted IP Range (Optional but Recommended)

If you don't want to use a security token, you can whitelist your IP address:

1. In Setup → type `Network Access` in Quick Find
2. Click **Network Access**
3. Click **New** → add your public IP address as both Start and End
4. Click **Save**

With this in place, you can leave the Security Token field blank in the app.

---

## Step 8 — Log In to the QA Agent

Open the app at `http://localhost:8200` → click **Add New Org** and fill in:

| Field | Value |
|---|---|
| Username | Your Salesforce login email |
| Password | Your Salesforce password |
| Security Token | From SF Settings → Reset My Security Token (see below) |
| Org Type | Developer / Production (or Sandbox) |
| Consumer Key | Copied from Step 5 |
| Consumer Secret | Copied from Step 5 |

Check **"Remember this org"** and give it a profile name so you can log in with one click next time.

Click **Connect to Salesforce**.

---

## How to Get Your Security Token

1. Log in to Salesforce in your browser
2. Click your **profile avatar** (top right) → **Settings**
3. Left sidebar → **My Personal Information** → **Reset My Security Token**
4. Click the button — Salesforce emails it to you within seconds
5. Copy it from the email and paste it into the app's Security Token field

> The token only changes if you reset your Salesforce password or manually regenerate it. Store it somewhere safe.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `invalid_client` | Wait a few more minutes for the Connected App to activate |
| `invalid_grant` | Wrong password or security token. Double-check both |
| `SOAP API login() is disabled` | Consumer Key/Secret are missing or wrong |
| `user is not allowed to use this app` | In Setup → Connected App → Manage → edit policies → set "Permitted Users" to "All users may self-authorize" |


---

## Step 1 — Open the New Connected App Form

In your browser, go to this URL (replace the domain with your own org's domain):

```
https://<your-org-domain>.my.salesforce.com/app/mgmt/forceconnectedapps/forceAppEdit.apexp
```

**Example:**
```
https://orgfarm-d8cd9f4557-dev-ed.develop.my.salesforce.com/app/mgmt/forceconnectedapps/forceAppEdit.apexp
```

---

## Step 2 — Fill in Basic Information

| Field | Value |
|---|---|
| Connected App Name | `QA Agent` |
| API Name | `QA_Agent` *(auto-fills)* |
| Contact Email | Your email address |

---

## Step 3 — Enable OAuth Settings

Scroll down to the **API (Enable OAuth Settings)** section:

1. ✅ Check **Enable OAuth Settings**
2. **Callback URL:** `http://localhost:8200/oauth/callback`
3. **Selected OAuth Scopes** — add both:
   - `Manage user data via APIs (api)`
   - `Perform requests at any time (refresh_token, offline_access)`
4. ✅ Check **Enable Client Credentials Flow**
5. ✅ Check **Enable Authorization Code and Credentials Flow** *(if visible)*

---

## Step 4 — Save

Click **Save** at the bottom → click **Continue** on the confirmation screen.

> ⏳ Wait **2–5 minutes** before proceeding. Salesforce needs time to activate the Connected App.

---

## Step 5 — Get Your Consumer Key and Secret

1. After saving, you land on the Connected App detail page
2. Click **Manage Consumer Details** (you may be asked to verify via email/authenticator)
3. Copy the **Consumer Key** and **Consumer Secret** — you will paste these into the app's login screen

---

## Step 6 — Allow OAuth Username-Password Flow (if not already done)

1. Go to **Setup** → search `OAuth` in Quick Find
2. Click **OAuth and OpenID Connect Settings**
3. Turn **ON** → `Allow OAuth Username-Password Flows`
4. Click **Save**

---

## Step 7 — Log In to the QA Agent

Open the app at `http://localhost:8200` and fill in the login form:

| Field | Value |
|---|---|
| Username | Your Salesforce login email |
| Password | Your Salesforce password |
| Security Token | From SF Settings → My Personal Information → Reset My Security Token |
| Org Type | Developer / Production (or Sandbox) |
| Consumer Key | Copied from Step 5 |
| Consumer Secret | Copied from Step 5 |

Click **Connect to Salesforce**.

---

## How to Get Your Security Token

1. Log in to Salesforce in your browser
2. Click your **profile avatar** (top right) → **Settings**
3. Left sidebar → **My Personal Information** → **Reset My Security Token**
4. Click the button — Salesforce emails it to you instantly
5. Copy it from the email and paste into the app

> The security token changes only if you reset your Salesforce password or manually regenerate it.
