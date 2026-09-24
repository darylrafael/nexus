# Nexus — Multi-Agent IHSG Market Intelligence Pipeline

A Python pipeline that autonomously generates pre-market briefs for the Indonesian Stock Exchange (IHSG), delivers them via Telegram, evaluates prediction accuracy after market close, and **learns from its own mistakes** over time.

Built as a portfolio project demonstrating multi-agent orchestration, model routing, RAG/memory patterns, tool use, and multi-API integration.

---

## Architecture

```
                  ┌────────────────────────────────────────────────────────┐
                  │          SCHEDULING & EXECUTION LAYER                  │
                  │  GitHub Actions (Cloud Cron)  │  APScheduler (Local)   │
                  │  06:55 WIB Morning Brief      │  18:55 WIB Review      │
                  └────────────┬───────────────────────────┬───────────────┘
                               │                           │
              ┌────────────────▼───────┐          ┌────────▼──────────────┐
              │     MARKET AGENT        │          │   EVENING REVIEWER    │
              │  (Morning Brief)        │          │  (Post-Market Eval)   │
              └──┬──────────┬──────┬───┘          └──┬────────────┬───────┘
                       │          │      │           │            │
              ┌────────▼─┐ ┌──────▼─┐ ┌─▼────────┐ │     ┌──────▼──────┐
              │ WEB AGENT │ │COMMODITY│ │ECONOMICS │ │     │  PREDICTION │
              │ (Tavily)  │ │ AGENT   │ │ ENGINE   │ │     │  EXTRACTOR  │
              └────────┬──┘ │(yfinance│ │(rules)   │ │     └─────────────┘
                       │    └────────┘ └──────────┘ │
                       │                            │
              ┌────────▼────────────────────────────▼────┐
              │                  LLM                      │
              │         OpenRouter (GPT-OSS-120B)         │
              └────────────────────┬──────────────────────┘
                                   │
              ┌────────────────────▼──────────────────────┐
              │              VALIDATOR                     │
              │  Direction language fixer + ticker check  │
              └────────────────────┬──────────────────────┘
                                   │
              ┌─────────────┬──────▼──────┬───────────────┐
              │             │             │               │
     ┌────────▼──────┐ ┌────▼────┐ ┌─────▼──────┐ ┌──────▼──────┐
     │   OBSIDIAN    │ │ TELEGRAM│ │  LEARNING  │ │   SESSION   │
     │ (Memory/Notes)│ │(Delivery│ │   STORE    │ │  (SQLite)   │
     └───────────────┘ └─────────┘ └────────────┘ └─────────────┘
```

---

## How It Works

### Morning (07:00 WIB, weekdays)
1. Fetches real commodity prices — Oil, Gas via yfinance; Coal, CPO, Nickel via Tavily
2. Injects **deterministic economic logic** (commodity price → sector impact) to prevent LLM hallucination
3. Searches macro news: Indonesian economy, global macro, geopolitics
4. Loads **past prediction accuracy + lessons** from memory to calibrate the LLM
5. Generates structured 7-section market brief via LLM
6. Validates output (direction language, ticker consistency)
7. Saves to Obsidian vault + sends via Telegram

### Evening (19:00 WIB, weekdays)
1. Reads morning brief from Obsidian — if not found, stops
2. Fetches actual IHSG close, USD/IDR, commodity prices, top movers, foreign flow
3. Searches for unexpected news that may have moved the market
4. LLM performs quantitative evaluation: was IHSG direction correct? Sectors? Foreign flow?
5. Root Cause Analysis: unanticipated factors, overestimated factors, info delays, inverse correlations
6. Generates specific lessons: *"Ketika [morning condition], tetapi [unexpected factor], maka [actual impact]"*
7. Saves learning entry + updates rolling performance stats in Obsidian

### Next Morning
The morning brief LLM receives a **calibration block** containing:
- Rolling accuracy stats
- Recent session results (predicted vs actual)
- Recurring blind spots
- Latest lessons learned

---

## Tech Stack

| Component | Tool | Role |
|-----------|------|------|
| Orchestration | OpenRouter + Gemini fallback | Market brief generation, RCA, reflection |
| Web search | Tavily | News, commodity prices, market movers |
| Market data | yfinance | IHSG, Oil, Gas, Brent, USD/IDR live prices |
| Memory | Obsidian Local REST API | Persistent note storage across sessions |
| Session tracking | SQLite | Run history, success rates, agent usage |
| Delivery | Telegram Bot API | Push reports + evening review to mobile |
| Cloud Automation | GitHub Actions | Scheduled cloud cron (06:55 & 18:55 WIB) + artifact sync |
| Local Scheduling | APScheduler / Windows Tasks | Local cron at 07:00 and 19:00 WIB |

---

## Self-Learning Loop

```
Day 1 Morning → Predict IHSG Bullish (70%)
Day 1 Evening → Actual: Bearish (-1.2%)
               → RCA: "BI rate surprise announced at 10:00, after brief was generated"
               → Lesson saved to Obsidian

Day 2 Morning → LLM sees: "Yesterday predicted Bullish → actual Bearish ❌"
               → "Recurring blind spot: BI policy surprise"
               → Applies extra scrutiny to BI rate signals today
```

---

## Setup

### 1. Clone and install
```bash
git clone https://github.com/yourusername/nexus.git
cd nexus
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Fill in your API keys
```

### 3. Set up Obsidian
- Install [Obsidian](https://obsidian.md) (free)
- Enable **Local REST API** plugin → port 27124
- Copy the API key to `.env`

### 4. Set up Telegram bot
- Message `@BotFather` on Telegram → `/newbot`
- Copy token to `.env`
- Get your chat ID and add to `.env`

### 5. Automated Execution Modes

#### Option A: Cloud Scheduled Pipelines (GitHub Actions — Zero Local Hardware Dependency)
Nexus includes production GitHub Actions workflows for 100% headless, cloud-hosted execution. Your computer does **not** need to be powered on:
- **Nexus Morning Brief** (`.github/workflows/morning_brief.yml`): Runs Monday–Friday at 06:55 WIB (`23:55 UTC Sun-Thu`).
- **Nexus Evening Review** (`.github/workflows/evening_review.yml`): Runs Monday–Friday at 18:55 WIB (`11:55 UTC Mon-Fri`).
- **Artifact Auto-Archiving**: Every cloud run commits generated reports and predictions in `runs/` back to GitHub (`[skip ci]`). Run `git pull` locally to view them in your local dashboard.
- **Manual Trigger**: Run either pipeline on-demand from the GitHub web UI or the GitHub mobile app via `workflow_dispatch`.

**Cloud Setup:**
1. In your GitHub repo, go to **Settings** > **Secrets and variables** > **Actions**.
2. Add the repository secrets: `OPENROUTER_API_KEY`, `TAVILY_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `GEMINI_API_KEY`.
3. Under **Settings** > **Actions** > **General** > **Workflow permissions**, choose **Read and write permissions** (required for saving artifacts back to `runs/`).

#### Option B: Local Scheduled Execution
If you prefer running locally on your own machine:
- **Windows Task Scheduler**: Register background tasks via PowerShell:
  ```powershell
  .\register_tasks.ps1
  ```
- **APScheduler Service**: Run the blocking foreground scheduler:
  ```bash
  python scheduler.py
  ```
- **Manual One-Off Test**:
  ```bash
  # Test morning brief manually
  python -c "from scheduler import daily_brief; daily_brief()"

  # Test evening review
  python -c "from scheduler import evening_review; evening_review()"
  ```

### Dashboard demo

The local dashboard reads generated artifacts and session counts directly from the project folder. Run it after at least one evening review:

```bash
cd dashboard
npm install
npm run dev
```

Open [http://127.0.0.1:3001](http://127.0.0.1:3001). For a production-mode demo, use `npm run build` followed by `npm run start`.

### Verification

```bash
python -m unittest discover -s tests -v
cd dashboard && npm run lint && npm run build
```

---

## Project Structure

```
nexus/
├── .github/
│   └── workflows/
│       ├── morning_brief.yml   # 06:55 WIB cloud scheduled morning brief
│       └── evening_review.yml   # 18:55 WIB cloud scheduled evening review
├── main.py                     # CLI entry point
├── config.py                   # API keys via dotenv
├── scheduler.py                # APScheduler / local cron
├── orchestrator/
│   └── gemini.py               # Tool-calling orchestrator (OpenRouter + fallback)
├── agents/
│   ├── web_agent.py            # Tavily search wrapper
│   ├── code_agent.py           # Code generation agent
│   ├── commodity_agent.py      # Commodity price fetcher
│   ├── market_agent.py         # Morning brief orchestrator
│   ├── economics_engine.py     # Deterministic economic logic
│   ├── validator.py            # Output validation
│   ├── prediction_extractor.py # Parse brief → structured predictions
│   └── evening_reviewer.py     # Post-market evaluation pipeline
├── memory/
│   ├── obsidian.py             # Obsidian REST API wrapper
│   ├── learning_store.py       # Learning persistence + performance stats
│   └── session.py              # SQLite session tracking
├── delivery/
│   └── telegram.py             # Telegram delivery
└── dashboard/                  # Next.js 14 telemetry & performance dashboard
```

---

## API Keys Required

| Key | Source | Free? | Role |
|-----|--------|-------|------|
| `OPENROUTER_API_KEY` | openrouter.ai | Yes | Primary LLM inference (gemini-2.0-flash-lite / deepseek) |
| `GEMINI_API_KEY` | aistudio.google.com | Yes | Tier-2 high availability fallback LLM |
| `TAVILY_API_KEY` | tavily.com | 1,000 calls/mo | Macro & domestic market news search |
| `TELEGRAM_BOT_TOKEN` | @BotFather | Free | Push delivery to mobile channel/chat |
| `TELEGRAM_CHAT_ID` | Telegram | Free | Target chat ID for automated delivery |
| `OBSIDIAN_API_KEY` | Local REST API plugin | Free | Optional local long-term knowledge base |

---

## Skills Demonstrated

- **Multi-agent orchestration** — specialized agents for web search, commodity data, economic analysis, code generation
- **Deterministic + probabilistic hybrid** — hardcoded economic rules prevent LLM from hallucinating market directions
- **RAG / memory patterns** — Obsidian as persistent memory, context injected into each run
- **Self-improving system** — evening review feeds lessons back into morning prompt
- **Multi-API integration** — 5 external APIs working together in a single pipeline
- **Cloud CI/CD scheduling** — headless GitHub Actions cron workflows with automated artifact commits and zero hardware dependency

---

## Notes for reviewers

- This is an educational portfolio project, not investment advice. Market outputs are hypotheses generated from public data and may be wrong.
- Credentials stay in `.env`, which is ignored by Git. Start from `.env.example`; never commit a populated `.env` file.
- LLM model IDs can be overridden in `.env`, so provider changes do not require source-code edits.
- Obsidian and Telegram are optional delivery integrations. Local artifacts in `runs/` keep the evening-review and dashboard demo usable when Obsidian is offline.
- If a virtual environment was copied or moved, recreate it with the setup commands above; virtual environments embed the path to the Python installation that created them.

*Built with Python 3.11 · OpenRouter · Tavily · yfinance · Obsidian · Telegram · Next.js*
