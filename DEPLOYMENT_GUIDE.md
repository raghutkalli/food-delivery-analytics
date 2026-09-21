# Deploying the Dashboard — Free, Hosted on Streamlit Community Cloud

This turns the dashboard into a **live, hosted web app** at **zero cost** on
[Streamlit Community Cloud](https://share.streamlit.io) — the standard free
hosting option for Python + Streamlit apps backed by a public GitHub repo.

## How the data works
- The app runs entirely on **synthetic data** — no database, no external
  connection, nothing to configure.
- Every KPI and chart is computed fresh from that data on each page load —
  it isn't a pre-baked static snapshot.
- Data **auto-refreshes once every 24 hours** (a date-seeded generator plus
  an automatic page reload) — stable all day, genuinely different the next.
- Click **"🔄 Refresh synthetic data"** in the sidebar any time to force an
  immediate refresh instead of waiting for the daily cycle.

## Files in this folder
| File | Purpose |
|---|---|
| `app.py` | The Streamlit app (UI, layout, charts, filters) |
| `analytics.py` | Cleaning + all KPI calculations (pure functions) |
| `data_gen.py` | Synthetic-data generator |
| `requirements.txt` | Dependencies Streamlit Cloud will install |

## Step 1 — Put this folder in a GitHub repo
1. Create a free GitHub account if you don't have one: https://github.com/join
2. Create a **new repository** (public is fine and free; private also works on the free tier).
3. Upload all the files in this folder to that repo — keep them at the repo root
   (or note the subfolder path, you'll need it in Step 2).
   - Easiest: drag-and-drop all files via the GitHub web UI ("Add file" → "Upload files").
   - No secrets or credentials to worry about anywhere in this setup.

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

The app is immediately live and fully working — synthetic data, all filters,
all tabs, all charts. Nothing further to configure.

## Keeping it updated
Any time you push a change to the GitHub repo, Streamlit Cloud **automatically
redeploys** the app — no manual steps needed. The dashboard logic (KPIs, charts)
lives in `analytics.py` / `app.py`, so edits there show up on next push.

## Cost & limits (free tier, as of this writing)
- Streamlit Community Cloud: free for public apps, one active app can sleep after
  inactivity and wake on next visit (a few seconds' delay) — no cost involved.
- If you outgrow the free tier or want guaranteed uptime, the next steps up are a
  paid Streamlit Cloud plan, or self-hosting the same `app.py` on a free-tier VM
  (Render, Railway, Fly.io) — the code doesn't change, only where it runs.

## Alternative: Hugging Face Spaces (also free)
If you'd rather not use GitHub + Streamlit Cloud, [Hugging Face Spaces](https://huggingface.co/spaces)
supports Streamlit apps natively and is also free — see `HUGGINGFACE_DEPLOYMENT.md`
in this same folder for the full walkthrough. `app.py` works unchanged on
either platform.
