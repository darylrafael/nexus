# Nexus — Codex Project Context

## What This Is
A Python multi-agent AI pipeline for IHSG (Indonesian Stock Exchange) market intelligence.
Runs automatically every weekday: morning brief at 07:00, evening review at 19:00.

## Project Structure
```
nexus/
├── .github/
│   └── workflows/
│       ├── morning_brief.yml      # 06:55 WIB cloud scheduled morning brief
│       └── evening_review.yml     # 18:55 WIB cloud scheduled evening review
├── main.py                        # CLI entry point
├── config.py                      # API keys via dotenv
├── scheduler.py                   # APScheduler / local cron
├── orchestrator/
│   └── gemini.py                  # Tool-calling orchestrator (OpenRouter + Gemini fallback)
├── agents/
│   ├── web_agent.py               # Tavily search wrapper
│   ├── code_agent.py              # Code generation (OpenRouter)
│   ├── commodity_agent.py         # yfinance + web for commodity prices
│   ├── market_agent.py            # Main IHSG daily brief orchestrator
│   ├── economics_engine.py        # Deterministic commodity→sector impact logic
│   ├── validator.py               # Post-LLM output fixer
│   ├── prediction_extractor.py    # Parse morning brief → structured predictions
│   └── evening_reviewer.py        # Post-market evaluation + RCA + lessons
├── memory/
│   ├── obsidian.py                # Obsidian Local REST API (read/write notes)
│   ├── learning_store.py          # Save/load learning entries + performance stats
│   └── session.py                 # SQLite session tracking
├── delivery/
│   └── telegram.py                # Telegram bot delivery
└── dashboard/                     # Next.js 14 telemetry & performance dashboard
```

## How to Run
```bash
# Cloud automated:
# GitHub Actions runs morning brief at 06:55 WIB and evening review at 18:55 WIB.
# Manual trigger available via GitHub Actions Web UI / Mobile App (workflow_dispatch).

# One-off local query
python main.py "your query here"

# Manual morning brief
python -c "from scheduler import daily_brief; daily_brief()"

# Manual evening review
python -c "from scheduler import evening_review; evening_review()"

# Start local scheduler
python scheduler.py

# Check session stats
python -c "from memory.session import print_summary; print_summary()"
```

## Environment Variables (.env)
```
OPENROUTER_API_KEY=
GEMINI_API_KEY=
DEEPINFRA_TOKEN=
TAVILY_API_KEY=
OBSIDIAN_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

## Key Design Decisions
- **Deterministic economics engine**: commodity→sector impact is hardcoded logic, not LLM inference. Prevents hallucination of economic direction.
- **Validator post-pass**: fixes directional language contradictions and ticker cross-validation after LLM output.
- **Self-learning loop**: evening review compares predictions vs actuals, stores lessons, injects them into next morning's prompt.
- **Obsidian as memory**: every brief and review saved as markdown notes. learning_store reads them back for context injection.

## Models Used
| Task | Model | Provider |
|------|-------|----------|
| Market brief / orchestration | gpt-oss-120b (free) | OpenRouter |
| Code generation | gpt-oss-120b (free) | OpenRouter |
| Evening review / RCA | gpt-oss-120b (free) | OpenRouter |

## Obsidian Setup
- Obsidian must be running locally
- Install "Local REST API" plugin, enable on port 27124
- Set OBSIDIAN_API_KEY from the plugin settings
- Notes are saved under vault/nexus/ folder

## Common Issues
- `InsecureRequestWarning` from Obsidian → normal, self-signed cert, safe to ignore
- `yfinance` returns stale data on weekends → expected, market closed
- LLM returns non-JSON in evening review → handled by regex strip in `run_llm_analysis()`
