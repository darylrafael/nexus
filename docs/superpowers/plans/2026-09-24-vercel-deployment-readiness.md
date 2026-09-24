# Vercel Deployment & Cloud Auto-Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable zero-maintenance, automated Vercel deployment for the Nexus Next.js dashboard so that every cloud morning brief and evening review instantly updates the live website without native C++ compilation errors or missing data.

**Architecture:** 
1. Deterministic telemetry export from SQLite (`memory/session.py`) to JSON artifact (`runs/global/telemetry.json`).
2. Self-contained data bundling inside `dashboard/data/runs` via sync script and GitHub Actions.
3. Decoupling Next.js dashboard from native C++ binaries (`better-sqlite3`), transitioning to pure JSON reader with deterministic fallbacks.
4. Auto-deploy triggers on GitHub Actions by removing `[skip ci]`.

**Tech Stack:** Next.js 14/16 (App Router), Node.js, Python 3.11 (sqlite3 standard library), GitHub Actions, Vercel Serverless.

## Global Constraints
- Preserve existing 3-pillar terminal dashboard design, routes, and styling.
- Zero paid dependencies or external SaaS requirements.
- Backwards compatible with local development (`localhost:3002`) and demo mode.
- All verification steps must be tested and passing before completion.

---

### Task 1: Add Deterministic Telemetry JSON Export in Python

**Files:**
- Modify: `memory/session.py`

**Interfaces:**
- Produces: `export_telemetry_json(output_path=None) -> dict` saving to `runs/global/telemetry.json`.
- Consumes: `sqlite3` connection in `memory/session.py`.

- [ ] **Step 1: Implement `export_telemetry_json` in `memory/session.py`**
Add function that queries `sessions` and `daily_stats`, builds the exact stats object (totalRuns, successfulRuns, failedRuns, successRate, avgDurationMs, runsToday, agentBreakdown, sessions), and writes it to `runs/global/telemetry.json`. Call it inside `log_session`.

- [ ] **Step 2: Test `export_telemetry_json` execution**
Run: `python -c "from memory.session import export_telemetry_json; print(export_telemetry_json())"`
Expected: Output dict with `stats`, `agentBreakdown`, and `sessions`, and file `runs/global/telemetry.json` created.

- [ ] **Step 3: Commit Task 1**
```bash
git add memory/session.py runs/global/telemetry.json
git commit -m "feat(telemetry): export deterministic telemetry json from sqlite for cloud deployment"
```

---

### Task 2: Create Data Resolver & Sync Mechanism in Dashboard

**Files:**
- Create: `dashboard/src/lib/nexusData.js`
- Create: `dashboard/scripts/sync-runs.mjs`
- Modify: `dashboard/package.json`

**Interfaces:**
- Produces: `getRunsDirectory(isDemo?: boolean) -> string`
- Produces: `npm run prebuild` hook running `sync-runs.mjs`

- [ ] **Step 1: Create `dashboard/src/lib/nexusData.js`**
Implement directory locator prioritizing `data/runs` inside `dashboard`, then `runs` at root, then `../runs`.

- [ ] **Step 2: Create `dashboard/scripts/sync-runs.mjs`**
Write script that copies `../runs` to `dashboard/data/runs` and `../demo_data/runs` to `dashboard/data/demo_runs` if parent directory exists.

- [ ] **Step 3: Update `dashboard/package.json`**
Add `"prebuild": "node scripts/sync-runs.mjs"` and remove `"better-sqlite3"` from dependencies.

- [ ] **Step 4: Commit Task 2**
```bash
git add dashboard/src/lib/nexusData.js dashboard/scripts/sync-runs.mjs dashboard/package.json
git commit -m "feat(dashboard): add data resolver and prebuild sync for self-contained packaging"
```

---

### Task 3: Refactor Next.js API Routes to Pure JSON

**Files:**
- Modify: `dashboard/src/app/api/stats/route.js`
- Modify: `dashboard/src/app/api/telemetry/route.js`
- Modify: `dashboard/src/app/api/memory/route.js`
- Modify: `dashboard/src/app/api/brief/[date]/route.js`

**Interfaces:**
- Consumes: `getRunsDirectory` from `dashboard/src/lib/nexusData.js`.
- Produces: Identical JSON responses for `/api/stats`, `/api/telemetry`, `/api/memory`, and `/api/brief/[date]`.

- [ ] **Step 1: Refactor `app/api/stats/route.js`**
Remove `import Database from 'better-sqlite3'`. Use `getRunsDirectory(isDemo)`. Read total runs from `telemetry.json` if available, or fallback to count.

- [ ] **Step 2: Refactor `app/api/telemetry/route.js`**
Remove `import Database from 'better-sqlite3'`. Read `telemetry.json` directly from `runsDir/global/telemetry.json`. Return `isAvailable: true` when file exists.

- [ ] **Step 3: Refactor `app/api/memory/route.js` and `app/api/brief/[date]/route.js`**
Use `getRunsDirectory(isDemo)` for robust path resolution.

- [ ] **Step 4: Commit Task 3**
```bash
git add dashboard/src/app/api/
git commit -m "refactor(api): remove native sqlite dependency and read pure json artifacts"
```

---

### Task 4: Update GitHub Actions Workflows for Auto-Deployment

**Files:**
- Modify: `.github/workflows/morning_brief.yml`
- Modify: `.github/workflows/evening_review.yml`

- [ ] **Step 1: Update `.github/workflows/morning_brief.yml`**
Add sync step to mirror `runs/` into `dashboard/data/runs/`, add both to git stage, and change commit message from `[skip ci]` to normal commit so Vercel triggers.

- [ ] **Step 2: Update `.github/workflows/evening_review.yml`**
Add sync step to mirror `runs/` into `dashboard/data/runs/`, add both to git stage, and change commit message from `[skip ci]` to normal commit so Vercel triggers.

- [ ] **Step 3: Commit Task 4**
```bash
git add .github/workflows/
git commit -m "ci: sync dashboard data and trigger cloud deployment on run archives"
```

---

### Task 5: Vercel Configuration & Full Build Verification

**Files:**
- Create: `vercel.json`

- [ ] **Step 1: Create `vercel.json`**
Provide monorepo build instructions pointing to `dashboard`.

- [ ] **Step 2: Run `npm run build` in `dashboard`**
Run: `npm run build` inside `dashboard/`
Expected: 0 errors, successful compilation of all pages and API routes.

- [ ] **Step 3: Verify API endpoints via curl/Invoke-RestMethod**
Check:
- `http://127.0.0.1:3002/api/stats`
- `http://127.0.0.1:3002/api/telemetry`
- `http://127.0.0.1:3002/api/memory`
Expected: 200 OK with accurate JSON response.

- [ ] **Step 4: Push to origin/main**
Push all commits to GitHub `origin/main`.
