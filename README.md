# Nexus — Multi-Agent IHSG Market Intelligence Pipeline

A Python pipeline that autonomously generates pre-market briefs for the Indonesian Stock Exchange (IHSG), delivers them via Telegram, evaluates prediction accuracy after market close, and **learns from its own mistakes** over time.

Built as a portfolio project demonstrating multi-agent orchestration, model routing, RAG/memory patterns, tool use, and multi-API integration.

---

## Architecture

```
                        ┌─────────────────────────────────────────┐
                        │            SCHEDULER (APScheduler)       │
                        │   07:00 Morning Brief  │  19:00 Review   │
                        └────────────┬───────────┴────────┬────────┘
                                     │                    │
                    ┌────────────────▼───────┐   ┌────────▼──────────────┐
                    │     MARKET AGENT        │   │   EVENING REVIEWER    │
                    │  (Morning Brief)        │   │  (Post-Market Eval)   │
                    └──┬──────────┬──────┬───┘   └──┬────────────┬───────┘
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
| Orchestration | OpenRouter (GPT-OSS-120B) | Market brief generation, RCA, reflection |
| Web search | Tavily | News, commodity prices, market movers |
| Market data | yfinance | IHSG, Oil, Gas, Brent, USD/IDR live prices |
| Memory | Obsidian Local REST API | Persistent note storage across sessions |
| Session tracking | SQLite | Run history, success rates, agent usage |
| Delivery | Telegram Bot API | Push reports + evening review to mobile |
| Scheduling | APScheduler | Weekday cron at 07:00 and 19:00 |

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

### 5. Run
```bash
# Test morning brief manually
python -c "from scheduler import daily_brief; daily_brief()"

# Test evening review
python -c "from scheduler import evening_review; evening_review()"

# Start full automated scheduler
python scheduler.py
```

---

## Project Structure

```
nexus/
├── main.py                     # CLI entry point
├── config.py                   # API keys via dotenv
├── scheduler.py                # APScheduler: 07:00 brief, 19:00 review
├── orchestrator/
│   └── gemini.py               # Tool-calling orchestrator
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
└── delivery/
    └── telegram.py             # Telegram delivery
```

---

## API Keys Required

| Key | Source | Free? |
|-----|--------|-------|
| `OPENROUTER_API_KEY` | openrouter.ai | Yes (free models available) |
| `DEEPINFRA_TOKEN` | deepinfra.com | Free credits on signup |
| `TAVILY_API_KEY` | tavily.com | 1,000 calls/month free |
| `TELEGRAM_BOT_TOKEN` | @BotFather | Free |
| `OBSIDIAN_API_KEY` | Local REST API plugin | Free |

---

## Skills Demonstrated

- **Multi-agent orchestration** — specialized agents for web search, commodity data, economic analysis, code generation
- **Deterministic + probabilistic hybrid** — hardcoded economic rules prevent LLM from hallucinating market directions
- **RAG / memory patterns** — Obsidian as persistent memory, context injected into each run
- **Self-improving system** — evening review feeds lessons back into morning prompt
- **Multi-API integration** — 5 external APIs working together in a single pipeline
- **Production scheduling** — fully automated weekday pipeline with no manual triggers

---

*Built with Python 3.11 · OpenRouter · Tavily · yfinance · Obsidian · Telegram*
