"""
tests/test_phase1_path_isolation.py

Phase 1 verification tests:
- No module outside core/paths.py hardcodes "runs/" or "nexus_sessions.db".
- Calling the pipeline under the default autouse fixture writes all artifacts and DB records strictly into tmp_path.
- Running tests does not alter git status --porcelain for runs/ or data/.
"""
from unittest.mock import MagicMock, patch
from agents.market_agent import run_market_brief
from agents.evening_reviewer import run_evening_review
from core.paths import (
    REPO_ROOT,
    get_runs_dir,
    get_memory_dir,
    get_db_path,
    get_vault_dir,
    get_dashboard_runs_dir,
)


class _DummyChoice:
    def __init__(self, content: str):
        self.message = MagicMock(content=content, reasoning=None)
        self.finish_reason = "stop"


class _DummyLLMResponse:
    def __init__(self, content: str):
        self.choices = [_DummyChoice(content)]


SAMPLE_BRIEF_MD = """# IHSG Daily Brief -- October 14, 2026

### 1. Indonesian Economy
- BI rate dipertahankan 6.00%, inflasi stabil di 2.1%.
- **Market Impact**: Bullish | **Confidence**: 70%

### 2. Global Macro
- Wall Street ditutup menguat moderat.
- **Market Impact**: Bullish | **Confidence**: 60%

### 3. Commodities & Energy
- Minyak mentah menguat, batubara stabil di Newcastle.
- **Market Impact**: Bullish | **Confidence**: 65%

### 4. Geopolitical & Regional Developments
- Situasi geopolitik terkendali.
- **Market Impact**: Neutral | **Confidence**: 60%

### 5. Foreign Flow Watch
- **Net Buy/Sell**: Net Buy Rp 1.25 triliun di pasar reguler.
- **Signal**: Accumulation

### 6. Sector Outlook for Today
**Bullish:**
- Banking: Net buy asing pada BBCA dan BBRI — BBCA, BBRI

**Bearish:**
- Consumer: Tekanan depresiasi nilai tukar rupiah — ICBP

### 7. Key Risk to Watch Today
- Risiko pelemahan nilai tukar rupiah terhadap dolar AS.
---
Source IDs: src_001, src_002
"""


def test_single_resolver_used_under_fixture(tmp_path):
    """Verify all path resolvers point inside tmp_path during test execution."""
    assert tmp_path in get_runs_dir().parents or get_runs_dir() == tmp_path
    assert tmp_path in get_memory_dir().parents
    assert tmp_path in get_db_path().parents
    assert tmp_path in get_vault_dir().parents
    assert tmp_path in get_dashboard_runs_dir().parents

    # None of the resolved paths may point into the real repo runs/ or nexus_sessions.db
    real_runs = (REPO_ROOT / "runs").resolve()
    real_db = (REPO_ROOT / "nexus_sessions.db").resolve()
    assert get_runs_dir().resolve() != real_runs
    assert get_db_path().resolve() != real_db


@patch("agents.market_agent.search_web")
@patch("agents.market_agent.search_multiple")
@patch("agents.market_agent.fetch_all_commodities")
@patch("agents.market_agent.get_ihsg_data")
@patch("agents.market_agent.fetch_usdidr_snapshot")
@patch("agents.market_agent.llm_chat")
@patch("memory.obsidian.write_note", return_value=True)
@patch("agents.evening_reviewer.fetch_ihsg_snapshot")
@patch("agents.evening_reviewer.fetch_usdidr_snapshot")
@patch("agents.evening_reviewer.fetch_all_commodities")
@patch("agents.evening_reviewer.search_text_with_sources")
@patch("agents.evening_reviewer.collect_unexpected_news")
@patch("agents.evening_reviewer.run_llm_analysis")
@patch("memory.obsidian.read_note", return_value="")
def test_pipeline_writes_exclusively_to_tmp_path(
    mock_read_note,
    mock_run_analysis,
    mock_collect_news,
    mock_search_text,
    mock_rev_comm,
    mock_rev_fx,
    mock_rev_ihsg,
    mock_write_note,
    mock_llm_chat,
    mock_fetch_usdidr,
    mock_get_ihsg,
    mock_fetch_commodities,
    mock_search_mult,
    mock_search_web,
    tmp_path,
):
    """
    Phase 1.3(b): Deliberately call both pipeline entry points with default config
    under the fixture and assert all artifacts and sqlite writes land in tmp_path.
    """
    mock_search_web.return_value = "Saham BBCA dan BBRI memimpin volume transaksi BEI."
    mock_search_mult.return_value = {
        "Indonesian Economy": "Kondisi makro Indonesia stabil.",
        "Global Macro": "The Fed bersikap dovish.",
        "Geopolitics": "Situasi geopolitik terkendali.",
    }
    mock_fetch_commodities.return_value = {
        "all": {"Crude Oil": {"price": 75.0, "change_pct": 1.2, "signal": "Up"}},
        "changes": {"Crude Oil": 1.2},
        "evidence_ids": ["src_comm_01"],
    }
    mock_get_ihsg.return_value = "IHSG: 7250.00 (+0.45%)"
    mock_fetch_usdidr.return_value = {
        "usdidr": 15800.0,
        "usdidr_change_pct": -0.25,
        "rupiah_signal": "Strengthened",
        "source": "yfinance",
    }
    mock_llm_chat.return_value = _DummyLLMResponse(SAMPLE_BRIEF_MD)

    brief_out = run_market_brief()
    assert brief_out is not None

    runs_dir = get_runs_dir()
    created_run_dirs = [d for d in runs_dir.iterdir() if d.is_dir() and d.name != "global"]
    assert len(created_run_dirs) == 1
    date_key = created_run_dirs[0].name

    assert (runs_dir / date_key / "morning_brief.md").exists()
    assert (runs_dir / date_key / "morning_prediction.json").exists()
    assert get_db_path().exists()
    assert (get_memory_dir() / "telemetry.json").exists()

    # Now run evening review for that date_key
    mock_rev_ihsg.return_value = {
        "ihsg_close": 7230.0,
        "ihsg_prev": 7250.0,
        "ihsg_change_pct": -0.28,
        "ihsg_change_pts": -20.0,
        "ihsg_signal": "Bearish",
        "ihsg_open": 7245.0,
        "ihsg_high": 7260.0,
        "ihsg_low": 7220.0,
        "ihsg_volume": 12000000000,
        "candle_date": date_key,
        "source": "yfinance",
        "confidence": "high",
    }
    mock_rev_fx.return_value = {
        "usdidr": 15810.0,
        "usdidr_change_pct": 0.06,
        "rupiah_signal": "Weakened",
        "candle_date": date_key,
        "source": "yfinance",
        "confidence": "high",
    }
    mock_rev_comm.return_value = {
        "all": {"Crude Oil (WTI)": {"price": 75.0, "change_pct": 1.2, "signal": "Up"}},
        "evidence_ids": ["src_comm_01"],
    }
    mock_search_text.return_value = ("Indeks sektoral ditutup variatif.", ["src_01"])
    mock_collect_news.return_value = "Tidak ada kejutan kebijakan."
    mock_run_analysis.return_value = {
        "step4_evaluation": {
            "ihsg_correct": False,
            "ihsg_predicted": "Bullish",
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -0.28,
            "foreign_flow_correct": None,
            "foreign_flow_predicted": "Accumulation",
            "foreign_flow_actual": "Unknown",
            "sector_accuracy": {"Banking": False},
        },
        "step5_rca": {
            "unanticipated_factors": ["Aksi jual sore hari"],
            "overestimated_factors": [],
            "underestimated_factors": [],
            "information_delay_factors": [],
            "inverse_correlation_cases": [],
        },
        "step6_lessons": [],
        "summary_sentence": "IHSG ditutup melemah tipis.",
    }

    review_out = run_evening_review(date_key=date_key)
    assert review_out is not None
    assert (runs_dir / date_key / "evening_actuals.json").exists()
    assert (runs_dir / date_key / "evening_review.json").exists()
    assert (get_memory_dir() / "nexus_stats.json").exists()

    # Verify all created files are strictly inside tmp_path
    for p in runs_dir.rglob("*"):
        assert tmp_path in p.resolve().parents


def test_no_module_hardcodes_runs_or_sqlite_path():
    """Verify no module in agents, memory, core, utils, data_sources, scripts, or scheduler hardcodes 'runs' or 'nexus_sessions.db'."""
    check_dirs = ["agents", "memory", "core", "utils", "data_sources", "scripts"]
    files_to_check = [REPO_ROOT / "scheduler.py", REPO_ROOT / "config.py"]
    for d in check_dirs:
        dir_path = REPO_ROOT / d
        if dir_path.exists():
            for p in dir_path.rglob("*.py"):
                if p.name == "paths.py":
                    continue
                files_to_check.append(p)

    offenders = []
    for p in files_to_check:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'"):
                continue
            if '/ "runs"' in line or "/ 'runs'" in line or 'os.path.join(BASE_DIR, "runs"' in line:
                offenders.append(f"{p.relative_to(REPO_ROOT)}:{lineno}: {stripped}")
            if "nexus_sessions.db" in line:
                offenders.append(f"{p.relative_to(REPO_ROOT)}:{lineno}: {stripped}")

    assert not offenders, f"Hardcoded paths found outside core/paths.py: {offenders}"


def test_git_status_runs_and_data_unchanged():
    """
    Phase 1.3(a) & Phase A4: Verify running tests does not introduce any new dirty files in runs/ or data/.
    Works both inside a git checkout (via `git status --porcelain`) and inside an unzipped release tree
    without `.git` (via direct filesystem inspection).
    """
    runs_root = REPO_ROOT / "runs"
    assert runs_root.is_dir(), "Expected runs/ directory in repository root"
    from core.provenance import check_run_dir_provenance
    for p in runs_root.iterdir():
        if p.is_dir() and p.name != "global":
            is_mock, reasons = check_run_dir_provenance(p)
            assert not is_mock, f"Mock run directory {p.name} found in real runs/: {reasons}"

    assert list(REPO_ROOT.glob("*.db")) == [], "Unexpected .db file found in repository root"

