# Updating Your Existing GitHub Repo — Version Control Guide

You already have an older version of these files in your repo. Here's how to
update it properly so you keep full history and can roll back if anything
breaks — still entirely browser-based, no terminal needed.

## The key thing to understand
Git/GitHub never deletes anything just because you upload a new version of a
file. Every commit is a snapshot. Uploading `app.py` again with new content
doesn't erase the old one — it creates a new commit, and the old version
stays viewable forever in that file's history. So even the "quick and simple"
option below is safe.

There are two ways to do this — pick based on how cautious you want to be.

---

## Option A — Quick: commit straight to `main`
Best if you're the only one working on this and you're comfortable deploying
the new version immediately.

1. Go to your repo on GitHub.
2. Click **"Add file" → "Upload files"**.
3. Drag in all the files from the new `streamlit_app/` folder — `app.py`,
   `analytics.py`, `data_gen.py`, `db_loader.py`, `requirements.txt`,
   `README.md`, `.gitignore`.
   - GitHub automatically detects that files with these names already exist
     and will show them as **modified** (not duplicated) in the commit preview.
4. New files that didn't exist before (`HUGGINGFACE_DEPLOYMENT.md`,
   `STREAMLIT_GITHUB_DEPLOYMENT.md`, `VERSION_CONTROL_GUIDE.md`) will
   show as **added**.
5. Scroll down to the commit box. Write a clear, specific message — this is
   your version history, so make it useful later:
   ```
   v3: fix reset-filters bug, daily auto-refresh, always-ask DB credentials
   ```
6. Click **"Commit changes directly to the main branch"** → **Commit changes**.
7. Streamlit Community Cloud detects the push and redeploys automatically
   within about a minute.

If something in the new version breaks, jump to **"Rolling back"** below —
nothing is lost.

---

## Option B — Recommended: branch + Pull Request
Best practice even for solo projects, because you get a clean before/after
diff to review before it goes live, and your `main` branch always stays in a
known-good state.

### Step 1 — Create a new branch
1. On your repo's main page, click the branch dropdown (usually shows "main").
2. Type a new branch name, e.g. `v2-modern-dashboard`.
3. Click **"Create branch: v2-modern-dashboard from main"**.
   You're now on the new branch — uploads here won't touch `main` yet.

### Step 2 — Upload the new files to that branch
1. Make sure the branch dropdown still shows `v2-modern-dashboard`.
2. **Add file → Upload files** → drag in all the updated files (same list as Option A).
3. Commit with a message like `Modern UI + filters + robustness fixes`.

### Step 3 — Open a Pull Request
1. GitHub will show a banner: **"v2-modern-dashboard had recent pushes"** →
   click **"Compare & pull request"**.
2. Review the **diff** it shows you — every line added/removed/changed
   across every file, side by side. This is the main benefit over Option A:
   you can actually see what's changing before it's live.
3. Add a description if you want (optional), then click **"Create pull request"**.

### Step 4 — Merge
1. On the Pull Request page, click **"Merge pull request"** → **"Confirm merge"**.
2. This merges `v2-modern-dashboard` into `main` as a single merge commit —
   `main` now has the new version, and Streamlit Cloud redeploys automatically.
3. Optionally click **"Delete branch"** afterward to tidy up (the commits
   remain in history either way).

---

## Tagging a version (optional, but useful for milestones)
If you want a clear marker like "this is v2" that's easy to find later:
1. Go to your repo → **Releases** (right sidebar, or `github.com/USERNAME/REPO/releases`).
2. Click **"Create a new release"**.
3. **Tag**: type something like `v2.0` → **"Create new tag on publish"**.
4. **Release title**: `v2.0 — Modern UI, filters, tabbed dashboard`.
5. **Description**: bullet the key changes (custom CSS design system, sidebar
   filters with real drill-down, Plotly interactivity, robustness fixes).
6. Click **"Publish release"**.

This doesn't affect deployment — it's purely a bookmark in history so you (or
anyone else) can always find "the version before the redesign" vs. "the
current one" without digging through individual commits.

## Rolling back, if you ever need to
Every one of these paths is fully reversible:
- **Single file:** open the file on GitHub → click **"History"** → click any
  older commit → **"..."** menu → you can view or restore that version.
- **Whole commit:** go to the repo's **"Commits"** list → find the commit →
  click **"Revert"** (creates a new commit that undoes it — doesn't rewrite history).
- **Whole release:** check out the tagged release (e.g. `v1.0`) and re-upload
  those files the same way if you want to fully go back to the old dashboard.

## Streamlit Cloud specifics
- Streamlit Community Cloud deploys from a **specific branch** (usually
  `main`) — check your app's Settings if you're unsure which one. Option B's
  branch/PR workflow only triggers a redeploy once you **merge to that branch**,
  so you can safely experiment on `v2-modern-dashboard` without affecting the
  live app until you're ready.
- If you used Option A and want a safety net next time, you can always create
  a branch retroactively from any past commit to preserve it before overwriting.
