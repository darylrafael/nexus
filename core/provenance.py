"""
core/provenance.py

Defense-in-depth provenance guard to detect and reject test/mock/synthetic
artifacts across all pipeline layers (learning_store, utils/stats,
scripts/rescore_history.py, and runs/index.json generation).
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _starts_with_mock(val: Any) -> bool:
    if not isinstance(val, str):
        return False
    s = val.strip().lower()
    return s.startswith("mock") or s.startswith("src_mock") or s.startswith("synthetic")


def _is_flagged_synthetic(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    for flag_key in ("synthetic", "is_synthetic", "is_mock"):
        if obj.get(flag_key) is True:
            return True
    if _starts_with_mock(obj.get("source")) or _starts_with_mock(obj.get("confidence")):
        return True
    return False


def is_mock_provenance(*artifacts: Any) -> tuple[bool, list[str]]:
    """
    Determine whether any passed artifact dictionary has test/mock/synthetic provenance.

    Rules (Phase 2.1):
    1. Any data_quality.fields.*.source starts with 'mock' or is flagged synthetic.
    2. Top-level or nested source fields (ihsg_source, usdidr_source, source,
       ihsg.source, usdidr.source, foreign_flow.source) start with 'mock'.
    3. Any evidence_ids entry or sources key/entry starts with 'mock'.
    4. FX or index values (or root/data_quality) are flagged synthetic/is_mock.

    Returns (is_mock, reasons).
    """
    reasons: list[str] = []

    for art in artifacts:
        if not isinstance(art, dict):
            continue

        # 1. Root synthetic/mock flags and top-level source fields
        if _is_flagged_synthetic(art):
            reasons.append("root_flagged_synthetic_or_mock")

        for src_field in ("ihsg_source", "usdidr_source", "source"):
            val = art.get(src_field)
            if _starts_with_mock(val):
                reasons.append(f"{src_field}={val}")

        # 2. Nested ihsg / usdidr / foreign_flow blocks
        for block_name in ("ihsg", "usdidr", "foreign_flow"):
            block = art.get(block_name)
            if isinstance(block, dict):
                if _is_flagged_synthetic(block):
                    reasons.append(f"{block_name}.flagged_synthetic_or_mock")
                b_src = block.get("source")
                if _starts_with_mock(b_src):
                    reasons.append(f"{block_name}.source={b_src}")

        # 3. data_quality.fields.*.source and synthetic flags
        dq = art.get("data_quality")
        if isinstance(dq, dict):
            if _is_flagged_synthetic(dq):
                reasons.append("data_quality.flagged_synthetic_or_mock")
            fields = dq.get("fields")
            if isinstance(fields, dict):
                for f_name, f_meta in fields.items():
                    if isinstance(f_meta, dict):
                        f_src = f_meta.get("source")
                        if _starts_with_mock(f_src):
                            reasons.append(f"data_quality.fields.{f_name}.source={f_src}")
                        if _is_flagged_synthetic(f_meta):
                            reasons.append(f"data_quality.fields.{f_name}.synthetic")

        # 4. evidence_ids starting with "mock"
        ev_ids = art.get("evidence_ids")
        if isinstance(ev_ids, list):
            for eid in ev_ids:
                if _starts_with_mock(eid):
                    reasons.append(f"evidence_id={eid}")

        # 5. sources map (either art["sources"] or art itself if it is sources.json)
        sources_obj = art.get("sources") if isinstance(art.get("sources"), dict) else None
        if sources_obj is None and any(isinstance(k, str) and k.startswith(("src_", "mock")) for k in art.keys()):
            sources_obj = art

        if isinstance(sources_obj, dict):
            for s_key, s_val in sources_obj.items():
                if s_key == "schema_version":
                    continue
                if _starts_with_mock(s_key):
                    reasons.append(f"source_id={s_key}")
                if isinstance(s_val, dict):
                    if _starts_with_mock(s_val.get("id")) or _starts_with_mock(s_val.get("source")) or _starts_with_mock(s_val.get("category")):
                        reasons.append(f"source_entry_mock={s_key}")

    # Deduplicate reasons preserving order
    unique_reasons = list(dict.fromkeys(reasons))
    return (len(unique_reasons) > 0), unique_reasons


def has_mock_provenance(*artifacts: Any) -> bool:
    """Return True if any passed artifact has mock or synthetic provenance."""
    return is_mock_provenance(*artifacts)[0]


def check_run_dir_provenance(run_dir: Path) -> tuple[bool, list[str]]:
    """Inspect all JSON artifacts in a run directory for mock/synthetic provenance."""
    if not run_dir.exists() or not run_dir.is_dir():
        return False, []

    loaded_dicts: list[dict[str, Any]] = []
    for fname in ("evening_actuals.json", "evening_review.json", "morning_prediction.json", "sources.json"):
        fpath = run_dir / fname
        if fpath.exists():
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    loaded_dicts.append(data)
            except Exception:
                pass

    return is_mock_provenance(*loaded_dicts)


def build_runs_index(runs_root: Path, write_file: bool = True) -> dict[str, Any]:
    """
    Generate runs/index.json excluding any session with mock/synthetic provenance.
    Records any rejected mock sessions in rejected_mock_dates / rejected_mock_runs.
    """
    if not runs_root.exists():
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "total_dates": 0,
            "latest_date": None,
            "evaluated_dates": [],
            "pending_dates": [],
            "all_dates": [],
            "rejected_mock_dates": [],
            "rejected_mock_runs": [],
        }

    candidate_dirs = sorted(
        [d for d in runs_root.iterdir() if d.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", d.name)],
        key=lambda d: d.name,
        reverse=True,
    )

    session_dates: list[str] = []
    evaluated: list[str] = []
    pending: list[str] = []
    rejected_mock_dates: list[str] = []
    rejected_mock_runs: list[dict[str, Any]] = []

    for d in candidate_dirs:
        is_mock, reasons = check_run_dir_provenance(d)
        if is_mock:
            rejected_mock_dates.append(d.name)
            rejected_mock_runs.append({"date": d.name, "reasons": reasons})
            continue

        has_review = (d / "evening_review.json").exists()
        has_pred = (d / "morning_prediction.json").exists()
        if has_review or has_pred:
            session_dates.append(d.name)
            if has_review:
                evaluated.append(d.name)
            elif has_pred:
                pending.append(d.name)

    disk_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_dates": len(session_dates),
        "latest_date": session_dates[0] if session_dates else None,
        "evaluated_dates": evaluated,
        "pending_dates": pending,
        "all_dates": session_dates,
    }
    if rejected_mock_dates:
        disk_payload["rejected_mock_dates"] = rejected_mock_dates
        disk_payload["rejected_mock_runs"] = rejected_mock_runs

    if write_file:
        index_path = runs_root / "index.json"
        index_path.write_text(json.dumps(disk_payload, indent=2), encoding="utf-8")

    return {
        **disk_payload,
        "rejected_mock_dates": rejected_mock_dates,
        "rejected_mock_runs": rejected_mock_runs,
    }

