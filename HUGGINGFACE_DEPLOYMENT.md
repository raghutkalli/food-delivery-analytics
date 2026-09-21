# Deploying to Hugging Face Spaces — Full Step-by-Step Guide

Hugging Face Spaces is a free hosting platform for apps like this one. Free tier
gives you **2 vCPU / 16 GB RAM**, a public URL, and automatic rebuilds on every
push — no credit card required.

`app.py` in this project already works on Hugging Face Spaces unchanged —
it needs no credentials, secrets, or configuration of any kind. It runs
entirely on synthetic data generated on the fly.

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
   - `requirements.txt`
   - `README.md` *(this replaces the placeholder HF auto-generates — it contains
     the required config header, so don't skip it)*
3. No secrets to configure — the app needs no credentials of any kind, it
   runs entirely on synthetic data.
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

At this point the dashboard is fully live and working — synthetic data,
all filters, all tabs. Nothing further to configure.

## Step 5 — Confirm it's working
- The sidebar shows **"Synthetic (auto-refreshes daily)"** with a timestamp (in IST).
- Data auto-refreshes once every 24 hours on its own (date-seeded generator +
  automatic page reload) — no clicking required.
- Click **"🔄 Refresh synthetic data"** any time to force an immediate
  refresh instead of waiting for the daily cycle.

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
- **Public repos by default** — anyone can view your Space's *code* unless
  you set the Space to Private in Step 2. There are no secrets to expose
  either way, since the app needs none.

## If something breaks
The **Logs** tab (Settings → or the "Logs" tab near "App"/"Files") shows the
full Python traceback if the app crashes on startup — that's the first place
to look. Most common issue: a missing package → add it to `requirements.txt`,
commit again.
