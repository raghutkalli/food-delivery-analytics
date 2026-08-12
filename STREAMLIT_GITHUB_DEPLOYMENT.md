# Deploying to GitHub + Streamlit Community Cloud — Browser-Only Guide

Everything below happens in your web browser — no terminal, no git install, no
local Python setup required. Two free accounts (GitHub, Streamlit Community
Cloud) and about 15 minutes.

---

## Part 1 — Put the code on GitHub (browser only)

### Step 1 — Create a GitHub account
1. Go to **https://github.com/signup**
2. Enter your email, create a password, choose a username.
3. Verify your email when prompted. Free — no card needed.

### Step 2 — Create a new repository
1. Once logged in, click the **"+"** icon top-right → **"New repository"**
   (or go directly to **https://github.com/new**).
2. Fill in:
   - **Repository name** — e.g. `food-delivery-analytics`
   - **Description** — optional
   - **Public** or **Private** — both work with Streamlit Community Cloud's free tier.
   - Leave "Add a README file" **unchecked** (we'll upload our own files directly).
3. Click **Create repository**.

### Step 3 — Upload the project files
You'll land on your new (empty) repo page.
1. Click **"uploading an existing file"** (a blue link in the middle of the page —
   or use **Add file → Upload files** from the toolbar if you don't see that link).
2. Drag and drop every file from the `streamlit_app/` folder into the upload box:
   - `app.py`
   - `analytics.py`
   - `data_gen.py`
   - `db_loader.py`
   - `requirements.txt`
   - `README.md`
   - `.gitignore`
   - *(Skip `.streamlit/secrets.toml.example` — optional; it's just a reference
     template, and skipping it changes nothing about deployment. Never upload a
     real `secrets.toml` with actual credentials.)*
3. Scroll down, add a commit message like "Initial dashboard upload," and click
   **"Commit changes"**.
4. Confirm all files now appear in the repo's file listing.

That's it for GitHub — your code is hosted. Now connect it to Streamlit.

---

## Part 2 — Deploy on Streamlit Community Cloud (browser only)

### Step 4 — Sign up for Streamlit Community Cloud
1. Go to **https://share.streamlit.io**
2. Click **"Sign up"** (or "Continue with GitHub" if offered directly).
3. Choose **"Continue with GitHub"** — this is the easiest path since it links
   your GitHub account immediately (no separate password to manage).
4. Authorize the **Streamlit** app when GitHub asks for permission to access
   your repositories. You can scope this to "Only select repositories" and
   pick just `food-delivery-analytics` if you prefer tighter access control.

### Step 5 — Create the app
1. Once inside the Streamlit Community Cloud dashboard, click **"Create app"**
   (top right, or a similar prominent button on an empty workspace).
2. Choose **"Deploy a public app from GitHub"** (or equivalent — wording may vary slightly).
3. Fill in the deploy form:
   - **Repository** — select `your-username/food-delivery-analytics` from the dropdown.
   - **Branch** — `main`
   - **Main file path** — `app.py`
   - **App URL (optional)** — customize the subdomain, e.g. `food-delivery-analytics`
     → your app will live at `food-delivery-analytics.streamlit.app`.
4. Click **"Deploy!"**

### Step 6 — Watch it build
1. You'll be taken to a live-updating log screen ("Your app is in the oven...").
2. It installs everything in `requirements.txt`, then starts the app —
   typically **1–3 minutes** for the first deploy.
3. If something fails, the log will show the exact error (almost always a
   missing package — this project's `requirements.txt` already lists
   everything `app.py` imports, so this should build cleanly).
4. Once it switches to the running app view, you have a **public URL**:
   ```
   https://food-delivery-analytics.streamlit.app
   ```
   (or whatever subdomain you chose, or an auto-generated one).

At this point, the dashboard is live — running on the **synthetic fallback
data**, since it doesn't have your DB credentials yet.

### Step 7 — Add your database credentials
1. From your app's page, click the **"⋮"** menu (top right of your app, or
   accessible from your Streamlit Cloud workspace list) → **"Settings"**.
2. Go to the **"Secrets"** tab.
3. Paste in (with your real values, no quotes needed around the *keys*, but keep them around string values):
   ```toml
   DB_HOST = "sql12834948.your-host-provider.com"
   DB_PORT = 3306
   DB_NAME = "sql12834948"
   DB_USER = "your_username"
   DB_PASSWORD = "your_password"
   ```
4. Click **Save**. The app automatically restarts within a few seconds.
5. Reload the app in your browser — the sidebar should now show
   **"Data source: Live MySQL database (...)"** instead of the fallback message.

### Step 8 — Confirm it's dynamic
- Open the sidebar and note the **"Last refreshed"** timestamp.
- Click **"🔄 Refresh data now"** — this clears the cache and re-queries your
  database immediately, so you can confirm the numbers reflect current DB state.
- Without clicking anything, the cache also expires automatically every
  10 minutes (`REFRESH_TTL_SECONDS` in `app.py`), so any visitor loading the
  page after that window triggers a fresh DB query on their own.

---

## Making changes later (still browser-only)
1. Go to your GitHub repo → click into any file (e.g. `app.py`) → click the
   **pencil icon** ("Edit this file") → make your change → **"Commit changes"**.
2. Streamlit Community Cloud detects the push and **automatically redeploys**
   within roughly a minute — no manual redeploy step, no re-connecting anything.
3. To add a new file the same way: **Add file → Create new file** (or
   **Upload files** for something you already have) directly from the repo page.

## Managing the deployed app
- **View logs:** from the app's Streamlit Cloud page, the **"Manage app"**
  panel (bottom right while viewing the app) shows real-time logs — useful if
  something breaks after a change.
- **Reboot:** the same panel has a **"Reboot app"** option if you ever need a
  clean restart without changing code.
- **Delete:** app settings also let you delete the deployment entirely
  (the GitHub repo itself is unaffected — deleting the Streamlit app just
  un-deploys it).

## Free tier notes
- **Sleep behavior:** an app with no visitors for a while may go idle; the
  next visitor triggers a brief "waking up" screen (a few seconds), then it's
  live again — not an error, just how free compute is kept efficient.
- **Resource limits:** free tier apps get roughly 1 GB of memory — this
  dashboard's data volumes (a few thousand rows) are comfortably within that.
- **Custom domains:** not available on the free tier — you get the
  `*.streamlit.app` subdomain, which is what you'll share.
- **Security:** your GitHub repo can be public without exposing your DB
  password — secrets live only in Streamlit Cloud's Secrets tab, never in the
  repo itself (this is exactly why `app.py` reads credentials from
  environment variables / `st.secrets` instead of having them hardcoded).
