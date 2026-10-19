"""Live pipeline smoke runner and artifact validator (Phase C1 & C2).

Runs a real morning brief (`run_market_brief`) and evening review (`run_evening_review`)
into an isolated temporary `NEXUS_RUNS_DIR` (never the repository's real `runs/`
directory) and validates the resulting session artifacts:
  1. `morning_brief.md`, `morning_prediction.json`, `actual_market_data.json`,
     and `evening_review.json` exist;
  2. No `"error"` keys in any artifact, and `data_quality.overall_valid` is True;
  3. `foreign_flow` is a valid classification OR `"Unknown"` with an explicit reason;
  4. OHLC is valid (`high >= max(open, close)`, `low <= min(open, close)`);
  5. USD/IDR change is consistent with `(close - prev) / prev * 100` within 0.05%;
  6. Every recommended ticker in `morning_prediction.json` is in `data/idx_tickers.json`;
  7. No mock provenance anywhere (`core.provenance.is_mock_provenance`).

Safety invariant:
  Refuses to execute if `NEXUS_RUNS_DIR` (or target directory) resolves to or
  inside the repository's real `runs/` directory.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.paths import get_data_dir, get_real_repo_runs_dir, get_runs_dir
from core.provenance import is_mock_provenance
from data_sources.market_data import validate_ohlc

VALID_FOREIGN_FLOW_SIGNALS = frozenset({
    "Accumulation",
    "Distribution",
    "Neutral",
    "Stagnant",
    "Stagnant/Sideways",
    "Net Buy",
    "Net Sell",
})


def assert_safe_runs_dir(target_dir: Path) -> Path:
    """Refuse to run if target_dir resolves to or inside the repo's real runs/ directory."""
    resolved = target_dir.resolve()
    real_runs = get_real_repo_runs_dir()
    if resolved == real_runs or real_runs in resolved.parents:
        raise RuntimeError(
            f"REFUSED: NEXUS_RUNS_DIR ({resolved}) resolves inside the repository's "
            f"real runs directory ({real_runs}). Live smoke must only write to a temp directory."
        )
    return resolved


def _find_error_keys(obj: Any, path: str = "") -> list[str]:
    """Recursively find any truthy 'error' key or status=='error' in a parsed JSON object."""
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            cur = f"{path}.{k}" if path else k
            if k == "error" and v:
                found.append(f"{cur}={v!r}")
            elif k == "status" and v == "error":
                found.append(f"{cur}='error'")
            else:
                found.extend(_find_error_keys(v, cur))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            found.extend(_find_error_keys(item, f"{path}[{idx}]"))
    return found


def _load_idx_whitelist() -> set[str]:
    tickers_file = get_data_dir() / "idx_tickers.json"
    data = json.loads(tickers_file.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "tickers" in data:
        return {str(t).upper() for t in data["tickers"]}
    if isinstance(data, list):
        return {str(t).upper() for t in data}
    return set()


def validate_smoke_session(session_dir: Path) -> dict[str, Any]:
    """Validate all 7 Phase C1 criteria on a single session directory."""
    assert_safe_runs_dir(session_dir)

    checks: dict[str, dict[str, Any]] = {}

    # 1. Required files exist
    required_files = [
        "morning_brief.md",
        "morning_prediction.json",
        "actual_market_data.json",
        "evening_review.json",
    ]
    missing_files = [f for f in required_files if not (session_dir / f).is_file()]
    checks["artifacts_exist"] = {
        "passed": len(missing_files) == 0,
        "detail": "All 4 artifacts present" if not missing_files else f"Missing: {missing_files}",
    }

    if missing_files:
        for remaining in (
            "no_error_keys_and_dq_passing",
            "foreign_flow_valid",
            "ohlc_valid",
            "usdidr_change_consistent",
            "tickers_in_idx_whitelist",
            "no_mock_provenance",
        ):
            checks[remaining] = {"passed": False, "detail": "Skipped because required artifacts are missing"}
        return {"passed": False, "session_dir": str(session_dir), "checks": checks}

    brief_md = (session_dir / "morning_brief.md").read_text(encoding="utf-8")
    pred = json.loads((session_dir / "morning_prediction.json").read_text(encoding="utf-8"))
    actual = json.loads((session_dir / "actual_market_data.json").read_text(encoding="utf-8"))
    review = json.loads((session_dir / "evening_review.json").read_text(encoding="utf-8"))

    # 2. No "error" keys in any artifact, and data_quality passing
    err_keys = (
        _find_error_keys(pred, "morning_prediction")
        + _find_error_keys(actual, "actual_market_data")
        + _find_error_keys(review, "evening_review")
    )
    dq_actual = (actual.get("data_quality") or {}).get("overall_valid") is True
    dq_review = (review.get("data_quality") or {}).get("overall_valid") is True
    checks["no_error_keys_and_dq_passing"] = {
        "passed": len(err_keys) == 0 and dq_actual and dq_review,
        "detail": (
            f"0 error keys; data_quality.overall_valid={dq_actual}"
            if (len(err_keys) == 0 and dq_actual and dq_review)
            else f"error_keys={err_keys}, dq_actual={dq_actual}, dq_review={dq_review}"
        ),
    }

    # 3. foreign_flow is a valid classification OR "Unknown" with reason
    ff_obj = actual.get("foreign_flow") if isinstance(actual.get("foreign_flow"), dict) else {}
    ff_sig = ff_obj.get("signal") or actual.get("foreign_flow_signal")
    ff_reason = (
        ff_obj.get("reason")
        or ff_obj.get("unscorable_reason")
        or (actual.get("data_quality") or {}).get("flow_reason")
    )
    if ff_sig in VALID_FOREIGN_FLOW_SIGNALS:
        ff_ok = True
        ff_detail = f"Classified as {ff_sig}"
    elif ff_sig == "Unknown" and isinstance(ff_reason, str) and len(ff_reason.strip()) > 0:
        ff_ok = True
        ff_detail = f"Unknown with explicit reason='{ff_reason}'"
    else:
        ff_ok = False
        ff_detail = f"Invalid foreign_flow signal={ff_sig!r}, reason={ff_reason!r}"
    checks["foreign_flow_valid"] = {"passed": ff_ok, "detail": ff_detail}

    # 4. OHLC valid (high >= max(open,close), low <= min(open,close))
    ihsg_sub = actual.get("ihsg") if isinstance(actual.get("ihsg"), dict) else {}
    o_val = ihsg_sub.get("open") if ihsg_sub.get("open") is not None else actual.get("ihsg_open")
    h_val = ihsg_sub.get("high") if ihsg_sub.get("high") is not None else actual.get("ihsg_high")
    l_val = ihsg_sub.get("low") if ihsg_sub.get("low") is not None else actual.get("ihsg_low")
    c_val = ihsg_sub.get("close") if ihsg_sub.get("close") is not None else actual.get("ihsg_close")
    ohlc_ok = validate_ohlc(o_val, h_val, l_val, c_val)
    checks["ohlc_valid"] = {
        "passed": ohlc_ok,
        "detail": f"O={o_val}, H={h_val}, L={l_val}, C={c_val} -> valid={ohlc_ok}",
    }

    # 5. USD/IDR change consistent with (close - prev)/prev within 0.05%
    fx_sub = actual.get("usdidr") if isinstance(actual.get("usdidr"), dict) else {}
    fx_close = fx_sub.get("rate") if fx_sub.get("rate") is not None else actual.get("usdidr_rate")
    if fx_close is None and isinstance(actual.get("usdidr"), (int, float)):
        fx_close = actual.get("usdidr")
    fx_prev = fx_sub.get("prev") if fx_sub.get("prev") is not None else actual.get("usdidr_prev")
    fx_pct = fx_sub.get("change_pct") if fx_sub.get("change_pct") is not None else actual.get("usdidr_change_pct")

    fx_ok = False
    fx_detail = f"close={fx_close}, prev={fx_prev}, change_pct={fx_pct}"
    try:
        if fx_close is not None and fx_prev is not None and fx_pct is not None and float(fx_prev) != 0:
            expected_pct = ((float(fx_close) - float(fx_prev)) / float(fx_prev)) * 100.0
            diff_pct = abs(expected_pct - float(fx_pct))
            fx_ok = diff_pct <= 0.05
            fx_detail = (
                f"close={fx_close}, prev={fx_prev}, stored={float(fx_pct):.4f}%, "
                f"computed={expected_pct:.4f}%, diff={diff_pct:.4f}% (<=0.05%)"
            )
    except (TypeError, ValueError) as exc:
        fx_detail = f"FX parse error: {exc}"
    checks["usdidr_change_consistent"] = {"passed": fx_ok, "detail": fx_detail}

    # 6. Every ticker in morning_prediction.json is in data/idx_tickers.json
    whitelist = _load_idx_whitelist()
    rec_tickers = pred.get("recommended_tickers") or []
    invalid_tickers = [t for t in rec_tickers if str(t).upper() not in whitelist]
    tickers_ok = isinstance(rec_tickers, list) and len(invalid_tickers) == 0
    checks["tickers_in_idx_whitelist"] = {
        "passed": tickers_ok,
        "detail": (
            f"{len(rec_tickers)} tickers verified in idx_tickers.json: {rec_tickers}"
            if tickers_ok
            else f"Invalid tickers not in idx_tickers.json: {invalid_tickers}"
        ),
    }

    # 7. No mock provenance anywhere
    mock_reasons: list[str] = []
    for name, payload in (
        ("morning_prediction.json", pred),
        ("actual_market_data.json", actual),
        ("evening_review.json", review),
    ):
        is_mock, reason = is_mock_provenance(payload)
        if is_mock:
            mock_reasons.append(f"{name}: {reason}")
    if "mock_" in brief_md.lower():
        mock_reasons.append("morning_brief.md contains 'mock_'")

    checks["no_mock_provenance"] = {
        "passed": len(mock_reasons) == 0,
        "detail": "0 mock provenance flags" if not mock_reasons else "; ".join(mock_reasons),
    }

    # 8. Validator inconsistencies reviewed
    val_file = session_dir / "validator_flags.json"
    if val_file.is_file():
        try:
            vdata = json.loads(val_file.read_text(encoding="utf-8"))
            vflags = vdata.get("flags", [])
            vcount = vdata.get("count", len(vflags))
            is_reviewed = vdata.get("reviewed") is True
            explanations = vdata.get("explanations", [])
            if vcount == 0:
                v_ok = True
                v_detail = "0 directional/numeric inconsistencies flagged"
            else:
                all_explained = is_reviewed and (len(explanations) == vcount or all("explanation" in f for f in vflags))
                v_ok = all_explained
                verbatim_lines = "; ".join(f"L{f.get('line_number')}: {f.get('issue')} ('{f.get('line', '').strip()[:60]}')" for f in vflags)
                if all_explained:
                    v_detail = f"{vcount} inconsistencies flagged and reviewed with explanations: {verbatim_lines}"
                else:
                    v_detail = f"{vcount} unexplained inconsistencies flagged: {verbatim_lines}"
        except Exception as e:
            v_ok = False
            v_detail = f"Failed to parse validator_flags.json: {e}"
    else:
        v_ok = True
        v_detail = "0 inconsistencies (validator_flags.json not present)"
    checks["validator_inconsistencies_reviewed"] = {"passed": v_ok, "detail": v_detail}

    all_passed = all(c["passed"] for c in checks.values())
    return {
        "passed": all_passed,
        "session_dir": str(session_dir),
        "checks": checks,
    }


def print_validation_table(report: dict[str, Any]) -> None:
    print("\n" + "=" * 78)
    print(f"LIVE SMOKE VALIDATION REPORT — {report['session_dir']}")
    print("=" * 78)
    for check_name, info in report["checks"].items():
        status = "PASS" if info["passed"] else "FAIL"
        print(f"  [{status}] {check_name:<34} | {info['detail']}")
    print("-" * 78)
    overall = "PASS" if report["passed"] else "FAIL"
    print(f"  OVERALL: {overall}")
    print("=" * 78 + "\n")


def _has_live_provider_keys() -> tuple[bool, list[str]]:
    missing: list[str] = []
    llm_key = os.getenv("OPENROUTER_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not llm_key or llm_key.startswith("dummy_") or llm_key.startswith("your_"):
        missing.append("OPENROUTER_API_KEY (or GEMINI_API_KEY)")
    if not tavily_key or tavily_key.startswith("dummy_") or tavily_key.startswith("your_"):
        missing.append("TAVILY_API_KEY")
    return len(missing) == 0, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run and validate Nexus live smoke test in an isolated temp dir.")
    parser.add_argument(
        "--validate-dir",
        type=str,
        default=None,
        help="Validate an existing isolated session directory instead of running live network calls.",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date YYYY-MM-DD for live smoke test.",
    )
    parser.add_argument(
        "--allow-non-trading",
        action="store_true",
        help="Allow running smoke test against a non-trading date (marked as non-representative).",
    )
    args = parser.parse_args(argv)

    if args.validate_dir:
        session_path = Path(args.validate_dir)
        assert_safe_runs_dir(session_path)
        report = validate_smoke_session(session_path)
        print_validation_table(report)
        return 0 if report["passed"] else 1

    # Check if NEXUS_RUNS_DIR was explicitly provided by caller
    env_runs = os.getenv("NEXUS_RUNS_DIR")
    if env_runs:
        assert_safe_runs_dir(Path(env_runs))

    # Load .env if present so we can inspect whether real rotated keys exist
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env", override=False)
    except Exception:
        pass

    keys_ok, missing_keys = _has_live_provider_keys()
    if not keys_ok:
        print(
            f"[live_smoke] SKIPPED LIVE EXECUTION: Missing or placeholder provider keys: {', '.join(missing_keys)}.\n"
            "Set rotated OPENROUTER_API_KEY and TAVILY_API_KEY in the environment to run live network smoke."
        )
        return 2

    from core.calendar import get_last_trading_day, is_idx_trading_day, get_holiday_reason
    from core.time import jakarta_now

    target_date = args.date
    if target_date:
        if not is_idx_trading_day(target_date):
            reason = get_holiday_reason(target_date) or "Non-trading day"
            if not args.allow_non_trading:
                print(f"[live_smoke] ERROR: Target date {target_date} is a non-trading day ({reason}). Use --allow-non-trading to bypass.")
                return 1
            print(f"[live_smoke] ⚠️ NON-TRADING TARGET: {target_date} ({reason}) results not representative.")
    else:
        today_date = jakarta_now().date()
        today_str = today_date.strftime("%Y-%m-%d")
        if not is_idx_trading_day(today_str):
            reason = get_holiday_reason(today_str) or "Non-trading day"
            target_date = get_last_trading_day(today_str)
            print(f"[live_smoke] Today ({today_str}) is a non-trading day ({reason}). Selecting last completed IDX trading session: {target_date}")
        else:
            target_date = get_last_trading_day(today_str)
            print(f"[live_smoke] Selecting last completed IDX trading session for full evening evaluation: {target_date}")

    with tempfile.TemporaryDirectory(prefix="nexus_live_smoke_", ignore_cleanup_errors=True) as tmp_root_str:
        tmp_root = Path(tmp_root_str)
        runs_dir = Path(env_runs) if env_runs else (tmp_root / "isolated_runs")
        assert_safe_runs_dir(runs_dir)
        runs_dir.mkdir(parents=True, exist_ok=True)

        os.environ["NEXUS_RUNS_DIR"] = str(runs_dir)
        os.environ["NEXUS_MEMORY_DIR"] = str(runs_dir / "global")
        os.environ["NEXUS_VAULT_DIR"] = str(tmp_root / "vault")
        os.environ["NEXUS_DB_PATH"] = str(tmp_root / "live_smoke_sessions.sqlite")

        from agents.evening_reviewer import run_evening_review
        from agents.market_agent import run_market_brief

        print(f"[live_smoke] Running live morning brief for {target_date} into isolated dir: {get_runs_dir()}")
        run_market_brief(target_date=target_date, allow_non_trading=args.allow_non_trading)

        session_dir = runs_dir / target_date
        if not session_dir.is_dir():
            print(f"[live_smoke] ERROR: Morning brief did not create session directory: {session_dir}")
            return 1

        print(f"[live_smoke] Running live evening review for session {target_date}...")
        run_evening_review(date_key=target_date, allow_non_trading=args.allow_non_trading)

        report = validate_smoke_session(session_dir)
        print_validation_table(report)
        return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
