# Deploying the Dashboard — Free & Dynamic

This turns the dashboard from a static HTML snapshot into a **live web app** that
re-queries your MySQL database on a schedule (and on demand), hosted at **zero cost**
on [Streamlit Community Cloud](https://share.streamlit.io) — the standard free
hosting option for this exact use case (Python + Streamlit apps, public GitHub repos).

## What "dynamic" means here
- The app queries your database, computes every KPI fresh, and renders the charts —
  it isn't a pre-baked snapshot.
- Results are cached for **10 minutes** (`REFRESH_TTL_SECONDS` in `app.py`) so the
  database isn't hit on every single page view — change that number, or click
  **"🔄 Refresh data now"** in the sidebar to force an immediate re-pull.
- If the database is unreachable, the app automatically falls back to the same
  synthetic dataset used earlier, so the dashboard never shows a broken page.

## Files in this folder
| File | Purpose |
|---|---|
| `app.py` | The Streamlit app (UI, layout, charts) |
| `analytics.py` | Cleaning + all KPI calculations (pure functions, reused from the notebook) |
| `data_gen.py` | Synthetic-data fallback generator |
| `db_loader.py` | Live MySQL connection via SQLAlchemy + PyMySQL |
| `requirements.txt` | Dependencies Streamlit Cloud will install |
| `.streamlit/secrets.toml.example` | Template for your DB credentials |

## Step 1 — Put this folder in a GitHub repo
1. Create a free GitHub account if you don't have one: https://github.com/join
2. Create a **new repository** (public is fine and free; private also works on the free tier).
3. Upload all the files in this folder to that repo — keep them at the repo root
   (or note the subfolder path, you'll need it in Step 3).
   - Easiest: drag-and-drop all files via the GitHub web UI ("Add file" → "Upload files").
   - Do **not** upload a real `secrets.toml` — only the `.example` file. Credentials
     go into Streamlit Cloud's own secrets manager (Step 4), not into the repo.

## Step 2 — Sign up for Streamlit Community Cloud
1. Go to https://share.streamlit.io and sign in with your GitHub account (free).
2. Click **"Create app"** → **"From an existing repo"**.
3. Select your repository, branch (`main`), and set **Main file path** to `app.py`
   (or `streamlit_app/app.py` if you kept it in a subfolder).

## Step 3 — Deploy
Click **Deploy**. Streamlit Cloud installs everything from `requirements.txt` and
starts the app. First deploy takes 1–3 minutes. You'll get a public URL like:

```
https://your-app-name.streamlit.app
```

At this point the app is live and working — using the synthetic fallback, since
it doesn't have your DB credentials yet.

## Step 4 — Add your database credentials (to go fully live)
1. In your deployed app, click the **⋮ (kebab menu)** → **Settings** → **Secrets**.
2. Paste in (with your real values):
   ```toml
   DB_HOST = "sql12834948.your-host-provider.com"
   DB_PORT = 3306
   DB_NAME = "sql12834948"
   DB_USER = "your_username"
   DB_PASSWORD = "your_password"
   ```
3. Save. The app restarts automatically and now queries your live MySQL database.

> Find `host`/`port` under your phpMyAdmin "Server" / connection details —
> the exact hostname isn't visible from the phpMyAdmin URL alone.

## Keeping it updated
Any time you push a change to the GitHub repo, Streamlit Cloud **automatically
redeploys** the app — no manual steps needed. The dashboard logic (KPIs, charts)
lives in `analytics.py` / `app.py`, so edits there show up on next push.

## Cost & limits (free tier, as of this writing)
- Streamlit Community Cloud: free for public apps, one active app can sleep after
  inactivity and wake on next visit (a few seconds' delay) — no cost involved.
- Your MySQL host (phpMyAdmin/`sql12834948`) — whatever plan you already have;
  this app just runs `SELECT` queries against it, no extra database cost incurred
  by hosting the dashboard itself.
- If you outgrow the free tier or want guaranteed uptime, the next steps up are a
  paid Streamlit Cloud plan, or self-hosting the same `app.py` on a free-tier VM
  (Render, Railway, Fly.io) — the code doesn't change, only where it runs.

## Alternative: Hugging Face Spaces (also free)
If you'd rather not use GitHub + Streamlit Cloud, [Hugging Face Spaces](https://huggingface.co/spaces)
supports Streamlit apps natively and is also free — see `HUGGINGFACE_DEPLOYMENT.md`
in this same folder for the full walkthrough. `app.py` already works unchanged
on either platform (it checks environment variables first, which is how both
Hugging Face and Streamlit Cloud expose secrets, with a `st.secrets` fallback).
