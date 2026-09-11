# Deploying to Hugging Face Spaces — Full Step-by-Step Guide

Hugging Face Spaces is a free hosting platform for apps like this one. Free tier
gives you **2 vCPU / 16 GB RAM**, a public URL, and automatic rebuilds on every
push — no credit card required.

`app.py` in this project already works on Hugging Face Spaces unchanged (it
reads DB credentials from environment variables, which is how HF exposes
secrets — see Step 5).

---

## Step 1 — Create a Hugging Face account
1. Go to **https://huggingface.co/join**
2. Sign up (email or GitHub/Google login all work). Free, no card needed.
3. Verify your email if prompted.

## Step 2 — Create a new Space
1. Go to **https://huggingface.co/new-space**
2. Fill in:
   - **Space name** — e.g. `food-delivery-analytics`
   - **License** — pick anything (e.g. `mit`) or leave default; not important for a private dashboard.
   - **Select the Space SDK** → choose **Streamlit** (not Gradio, not Docker).
   - **Space hardware** → leave as **CPU basic · 2 vCPU · 16 GB · FREE**.
   - **Visibility** → **Public** (free) or **Private** if you don't want it discoverable — both work on the free tier.
3. Click **Create Space**.

HF will initialize an empty repo for your Space and show you its own quick-start
instructions — you can ignore those and follow the steps below instead, since
this project already has everything Spaces needs.

## Step 3 — Add your files to the Space
You have two options — pick whichever you're more comfortable with.

### Option A — Web UI upload (easiest, no git required)
1. On your new Space's page, click the **Files** tab, then **"+ Add file" → "Upload files"**.
2. Upload every file from this project's `streamlit_app/` folder:
   - `app.py`
   - `analytics.py`
   - `data_gen.py`
   - `db_loader.py`
   - `requirements.txt`
   - `README.md` *(this replaces the placeholder HF auto-generates — it contains
     the required config header, so don't skip it)*
3. No secrets to configure here — the app asks for database credentials
   directly in its sidebar each session (Step 5), so there's nothing to set
   up in Space secrets for the database to work.
4. Click **Commit changes to main** after each upload (or select all files and upload together).

### Option B — Git (better if you'll keep iterating)
```bash
# 1. Install git-lfs if you don't have it (not strictly needed for this small project, but HF recommends it)
git lfs install

# 2. Clone the empty Space repo HF created for you
git clone https://huggingface.co/spaces/YOUR_USERNAME/food-delivery-analytics
cd food-delivery-analytics

# 3. Copy in the project files
cp /path/to/streamlit_app/app.py .
cp /path/to/streamlit_app/analytics.py .
cp /path/to/streamlit_app/data_gen.py .
cp /path/to/streamlit_app/db_loader.py .
cp /path/to/streamlit_app/requirements.txt .
cp /path/to/streamlit_app/README.md .
cp /path/to/streamlit_app/.gitignore .

# 4. Commit and push
git add .
git commit -m "Initial dashboard deploy"
git push
```
You'll be prompted for HF credentials — use your HF username and an
**access token** (create one at https://huggingface.co/settings/tokens with
"Write" permission) instead of your account password.

## Step 4 — Watch the build
1. Go back to your Space's page — it should already show **"Building"**.
2. Click the **Logs** tab to watch the build in real time (installing
   `requirements.txt`, then starting Streamlit).
3. First build typically takes **1–3 minutes**. If it fails, the Logs tab will
   show exactly which line/import errored — almost always a missing package in
   `requirements.txt` (this project's is already complete for what `app.py` imports).
4. Once it says **"Running"**, your app is live at:
   ```
   https://huggingface.co/spaces/YOUR_USERNAME/food-delivery-analytics
   ```
   (or the shorter embed URL `https://YOUR_USERNAME-food-delivery-analytics.hf.space`)

At this point the dashboard is live and working — using **synthetic data
that refreshes automatically once every 24 hours**, since it isn't connected
to your live database yet.

## Step 5 — Connect to your live database (no Space secrets needed)
As of the current version, the app **no longer reads DB credentials from
Space secrets/environment variables** — instead it asks for them directly in
the running app, every session, and never stores them anywhere:

1. Open your deployed Space.
2. In the sidebar, expand **"🔌 Connect to database"**.
3. Enter your `Host`, `Port`, `Database name`, `Username`, `Password`
   (find these in your phpMyAdmin server/connection details).
4. Click **"🔗 Connect"**. On success, the sidebar status chip switches to
   **"Live MySQL · your_database_name"**.
5. If it fails, a specific connection error appears right in the sidebar
   (bad host, wrong password, etc.) instead of silently falling back —
   fix the field it points to and click Connect again.

This is intentionally per-session: reloading the page (including the
automatic 24-hour reload from Step 6) clears the connection and asks again —
nothing is written to disk or Space secrets.

## Step 6 — Confirm it's dynamic
- The sidebar shows either **"Synthetic (auto-refreshes daily)"** or, once
  connected, **"Live MySQL · ..."** with the connection time.
- Click **"🔄 Refresh live data"** (once connected) to re-query immediately,
  or **"🔄 Refresh synthetic data"** when not connected.
- The page also auto-reloads every 24 hours on its own (a `<meta refresh>`
  tag) — this is what drives the daily synthetic-data refresh automatically.
- If a connection attempt fails, the sidebar error message tells you exactly
  what went wrong (auth failure, host unreachable, etc.) — no need to dig
  through Space logs for DB issues specifically (though the Logs tab still
  helps for anything else).

## Updating the dashboard later
- **Web UI:** edit/re-upload any file → commit → Space rebuilds automatically.
- **Git:** `git push` → Space rebuilds automatically.
No separate "deploy" step exists — every push to the Space's repo is a deploy.

## Things worth knowing (free tier)
- **Sleep behavior:** a Space with no visitors for an extended period may go
  idle; the next visitor triggers a **cold start** (roughly 30–60 seconds)
  before the app responds. This is normal on the free tier, not an error.
- **No custom domain** on the free tier — you get `huggingface.co/spaces/...`
  or the `.hf.space` URL. Custom domains are a paid-tier feature.
- **Port:** Streamlit-SDK Spaces are wired up automatically by HF — you don't
  need to set a port anywhere in `app.py`.
- **Public repos by default** — anyone can view your Space's *code* (not your
  secrets, which are never exposed) unless you set the Space to Private in Step 2.

## If something breaks
The **Logs** tab (Settings → or the "Logs" tab near "App"/"Files") shows the
full Python traceback if the app crashes on startup — that's the first place
to look. Common issues:
- Missing package → add it to `requirements.txt`, commit again.
- DB connection error → the sidebar shows the specific error directly
  (wrong host, bad credentials, etc.) when you click Connect — fix the field
  it points to.
- DB connection timeout → check that your MySQL host allows external
  connections from outside its usual network (some free MySQL hosts restrict
  by IP allowlist — check your phpMyAdmin host's connection settings).
