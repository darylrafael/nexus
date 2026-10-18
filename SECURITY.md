# Security Policy and Key Rotation Guide

## Compromise Notice
If `.env` was previously distributed, archived, or exposed, assume all credentials in that file have been compromised. Every secret must be rotated immediately across all upstream providers and downstream environments.

---

## 1. Secrets to Rotate

| Secret Name | Provider / Source | Where to Rotate | Where to Update |
| :--- | :--- | :--- | :--- |
| `OPENROUTER_API_KEY` | OpenRouter | [openrouter.ai/keys](https://openrouter.ai/keys) | `.env`, GitHub Actions Secrets |
| `GEMINI_API_KEY` | Google AI Studio | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) | `.env`, GitHub Actions Secrets |
| `TAVILY_API_KEY` | Tavily | [app.tavily.com/home](https://app.tavily.com/home) | `.env`, GitHub Actions Secrets |
| `DEEPINFRA_TOKEN` | DeepInfra | [deepinfra.com/dash/api_keys](https://deepinfra.com/dash/api_keys) | `.env` |
| `OBSIDIAN_API_KEY` | Obsidian Local REST API | Obsidian App → Settings → Community Plugins → Local REST API → Regenerate API Key | `.env` (local only) |
| `TELEGRAM_BOT_TOKEN`| Telegram BotFather | Open Telegram → `@BotFather` → `/mybots` → Select Bot → API Token → `/revoke` | `.env`, GitHub Actions Secrets |
| `TELEGRAM_CHAT_ID`  | Telegram | Verify target chat/channel ID, kick unauthorized users if public | `.env`, GitHub Actions Secrets |

---

## 2. Where to Update Rotated Values

1. **Local Development**:
   - Update `c:\Users\Lenovo\nexus\.env`.
   - Never commit `.env` or paste its contents into chat/issues.
2. **GitHub Actions Secrets** (for automated workflows):
   - Navigate to **GitHub Repo** → **Settings** → **Secrets and variables** → **Actions**.
   - Update: `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `TAVILY_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
3. **Vercel Project Settings** (if dashboard API requires access gates):
   - Navigate to **Vercel Dashboard** → Project → **Settings** → **Environment Variables**.

---

## 3. Git History Verification and Purge Procedure

### Verification
To verify if `.env` has ever been committed into Git history:
```bash
git log --all -- .env
```
*(Status: Verified clean. `.env` has not been committed to this repository's Git history).*

### Emergency History Purge Procedure (If Leaked Remotely)
If git history ever contains sensitive files or commit history needs to be sanitized, use `git-filter-repo` (DO NOT run without backup and team coordination):

1. Make a full mirror backup of the repository:
   ```bash
   git clone --mirror <REPO_URL> repo-backup.git
   ```
2. Install `git-filter-repo`:
   ```bash
   pip install git-filter-repo
   ```
3. Purge `.env` from all branches, tags, and commits:
   ```bash
   git filter-repo --invert-paths --path .env
   ```
4. Force push the sanitized history:
   ```bash
   git push origin --force --all
   git push origin --force --tags
   ```
5. Invalidate and rotate all credentials immediately regardless of history rewrite.

---

## 4. Secret Safety Rules in Nexus Codebase
- The codebase enforces strict configuration checks on startup (`config.py`).
- Missing keys fail loudly with variable names only; values are never echoed to stdout, stderr, or log files.
- `.gitignore` and `.dockerignore` strictly exclude `.env`, `*.db`, `*.log`, and temporary directories.

---

## 5. API Rate Limiter Architecture & Serverless Limitation
- **Current Implementation (`dashboard/src/middleware.js`)**: Uses an in-memory sliding-window `Map` (`ipBuckets`) enforcing 60 requests per 60-second window per client IP on `/api/*` routes.
- **Architectural Limitation**: Because `ipBuckets` is held in process memory, rate-limit counters are **per-instance / per-isolate**. In a multi-region or horizontally scaled serverless deployment (e.g., Vercel Edge/Node isolates), state is not shared across instances and resets on cold starts.
- **Production Hardening Recommendation**: For high-traffic multi-instance deployments requiring strict global rate limiting across isolates, back `checkRateLimit()` with a shared atomic store (e.g., Upstash Redis `@upstash/ratelimit` or Cloudflare/Vercel KV) or enforce rate limiting at the upstream WAF/CDN layer.

