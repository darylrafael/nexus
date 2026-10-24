"""Playwright fixture tests for Phase 7.6 & Phase B6: Stale, Fresh-Today, and Missing-Field UI States."""

from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.paths import REPO_ROOT, get_runs_dir
import pytest

# Playwright is an optional dev dependency (browser binaries are not installed in CI).
# Skip this module cleanly instead of failing collection for the whole suite.
sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
STALE_FIXTURE_PATH = FIXTURES_DIR / "stale_fixture.json"
FRESH_TODAY_FIXTURE_PATH = FIXTURES_DIR / "fresh_today_fixture.json"
MISSING_FIELD_FIXTURE_PATH = FIXTURES_DIR / "missing_field_fixture.json"


def load_playwright_fixture(fixture_path: Path, today_str: str | None = None) -> Dict[str, Any]:
    """Load a Playwright UI state fixture from tests/fixtures/ (outside runs/)."""
    wib_today = today_str or datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=7))
    ).strftime("%Y-%m-%d")

    raw = fixture_path.read_text(encoding="utf-8").replace("__TODAY__", wib_today)
    payload: Dict[str, Any] = json.loads(raw)
    meta = payload.get("_fixture_meta") or {}
    if not meta.get("is_test_fixture") or not meta.get("stored_outside_runs"):
        raise ValueError(f"Fixture {fixture_path} is missing required _fixture_meta markers")
    return payload


def run_playwright_fixture_state_checks(target_url: str = "http://127.0.0.1:3002") -> Dict[str, Any]:
    """Run Playwright verification against stale, fresh-today, and missing-field fixtures stored in tests/fixtures/."""
    stale_payload = load_playwright_fixture(STALE_FIXTURE_PATH)
    fresh_payload = load_playwright_fixture(FRESH_TODAY_FIXTURE_PATH)
    missing_field_payload = load_playwright_fixture(MISSING_FIELD_FIXTURE_PATH)

    results: Dict[str, Any] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Stale state fixture
        ctx_stale = browser.new_context(viewport={"width": 390, "height": 844})
        page_stale = ctx_stale.new_page()
        page_stale.route(
            "**/api/stats",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(stale_payload),
            ),
        )
        page_stale.goto(target_url, wait_until="networkidle")
        page_stale.wait_for_timeout(400)
        stale_text = page_stale.inner_text("body")
        stale_banner_visible = page_stale.locator(".stale-pipeline-banner").is_visible()
        assert stale_banner_visible, "Expected stale banner to be visible in stale fixture state"
        assert "No new call generated today" in stale_text
        assert "Hash added retroactively; not proof of pre-open lock" in stale_text
        results["stale_fixture"] = {
            "fixture_file": str(STALE_FIXTURE_PATH.relative_to(REPO_ROOT)),
            "passed": True,
            "staleBannerVisible": stale_banner_visible,
            "hasNoNewCall": "No new call generated today" in stale_text,
            "hasRetroactiveNotice": "Hash added retroactively; not proof of pre-open lock" in stale_text,
        }
        ctx_stale.close()

        # 2. Fresh-today state fixture
        ctx_fresh = browser.new_context(viewport={"width": 390, "height": 844})
        page_fresh = ctx_fresh.new_page()
        page_fresh.route(
            "**/api/stats",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(fresh_payload),
            ),
        )
        page_fresh.goto(target_url, wait_until="networkidle")
        page_fresh.wait_for_timeout(400)
        fresh_text = page_fresh.inner_text("body")
        fresh_stale_count = page_fresh.locator(".stale-pipeline-banner").count()
        assert fresh_stale_count == 0, "Expected no stale banner in fresh-today fixture state"
        assert "TODAY'S PRE-MARKET CALL" in fresh_text
        assert "No new call generated today" not in fresh_text
        assert "Locked at 06:55 WIB" in fresh_text
        results["fresh_today_fixture"] = {
            "fixture_file": str(FRESH_TODAY_FIXTURE_PATH.relative_to(REPO_ROOT)),
            "passed": True,
            "staleBannerCount": fresh_stale_count,
            "hasTodaysCallHeader": "TODAY'S PRE-MARKET CALL" in fresh_text,
            "hasPreOpenLock": "Locked at 06:55 WIB" in fresh_text,
        }
        ctx_fresh.close()

        # 3. Missing-field state fixture
        ctx_missing = browser.new_context(viewport={"width": 390, "height": 844})
        page_missing = ctx_missing.new_page()
        page_missing.route(
            "**/api/stats",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(missing_field_payload),
            ),
        )
        page_missing.goto(target_url, wait_until="networkidle")
        page_missing.wait_for_timeout(400)
        page_missing.get_by_text("Open Session Workbench").click()
        page_missing.wait_for_timeout(300)
        missing_text = page_missing.inner_text("body")
        assert "Unavailable" in missing_text, "Expected 'Unavailable' for missing USD/IDR"
        assert "Unscorable" in missing_text, "Expected 'Unscorable' for missing accuracy_score"
        assert "NaN" not in missing_text, "Found 'NaN' in missing-field state"
        assert "undefined" not in missing_text, "Found 'undefined' in missing-field state"
        assert "Rp 0" not in missing_text, "Found fabricated 'Rp 0' in missing-field state"
        results["missing_field_fixture"] = {
            "fixture_file": str(MISSING_FIELD_FIXTURE_PATH.relative_to(REPO_ROOT)),
            "passed": True,
            "hasUnavailable": "Unavailable" in missing_text,
            "hasUnscorable": "Unscorable" in missing_text,
            "zeroNaNOrUndefined": ("NaN" not in missing_text and "undefined" not in missing_text),
        }
        ctx_missing.close()

        # 4. axe-core accessibility check in both dark and light themes at 360px, 390px, and 430px (D1)
        axe_env = os.environ.get("NEXUS_AXE_PATH")
        axe_candidates = [
            Path(axe_env) if axe_env else None,
            REPO_ROOT / "dashboard" / "node_modules" / "axe-core" / "axe.min.js",
            REPO_ROOT / "audit_output" / "axe.min.js",
        ]
        axe_path = next((p for p in axe_candidates if p and p.exists()), None)
        if axe_path is not None:
            axe_results: Dict[str, Any] = {}
            for w, h in ((360, 740), (390, 844), (430, 932)):
                for theme in ("dark", "light"):
                    combo_key = f"{w}px_{theme}"
                    ctx_axe = browser.new_context(
                        viewport={"width": w, "height": h},
                        color_scheme=theme,
                    )
                    page_axe = ctx_axe.new_page()
                    page_axe.goto(target_url, wait_until="networkidle")
                    page_axe.evaluate(
                        f"""() => {{
                            document.documentElement.setAttribute('data-theme', '{theme}');
                            try {{ localStorage.setItem('nexus-theme', '{theme}'); }} catch (e) {{}}
                        }}"""
                    )
                    page_axe.wait_for_timeout(400)
                    page_axe.add_script_tag(path=str(axe_path))
                    axe_out = page_axe.evaluate(
                        """async () => {
                            const res = await window.axe.run();
                            return {
                                violations_count: res.violations.length,
                                passes_count: res.passes.length,
                                violations: res.violations.map(v => ({
                                    id: v.id,
                                    impact: v.impact,
                                    nodes: v.nodes.length
                                }))
                            };
                        }"""
                    )
                    assert axe_out["violations_count"] == 0, (
                        f"axe-core violations found in {combo_key}: {axe_out['violations']}"
                    )
                    axe_results[combo_key] = axe_out
                    ctx_axe.close()
            results["axe_core_mobile"] = axe_results

        browser.close()

    return results


def test_fixture_state_payloads_schema_and_location():
    """Verify fixture payloads for stale, fresh-today, and missing-field UI states live outside runs/."""
    real_runs = REPO_ROOT.joinpath("runs").resolve()
    active_runs = get_runs_dir().resolve()

    for path in (STALE_FIXTURE_PATH, FRESH_TODAY_FIXTURE_PATH, MISSING_FIELD_FIXTURE_PATH):
        assert path.exists(), f"Missing fixture file: {path}"
        resolved = path.resolve()
        assert not resolved.is_relative_to(real_runs), f"Fixture {path} must never live inside runs/"
        assert not resolved.is_relative_to(active_runs), f"Fixture {path} must never live inside active runs/"

    stale = load_playwright_fixture(STALE_FIXTURE_PATH, today_str="2026-10-18")
    assert stale["_fixture_meta"]["fixture_name"] == "stale"
    assert stale["pipelineHealth"]["isStale"] is True
    assert stale["reviews"][0]["lock_status"] == "retroactive"

    fresh = load_playwright_fixture(FRESH_TODAY_FIXTURE_PATH, today_str="2026-10-18")
    assert fresh["_fixture_meta"]["fixture_name"] == "fresh-today"
    assert fresh["pipelineHealth"]["isStale"] is False
    assert fresh["reviews"][0]["date"] == "2026-10-18"
    assert fresh["reviews"][0]["lock_status"] == "locked_pre_open"

    missing = load_playwright_fixture(MISSING_FIELD_FIXTURE_PATH, today_str="2026-10-18")
    assert missing["_fixture_meta"]["fixture_name"] == "missing-field"
    assert missing["reviews"][0]["actual_usdidr"] is None
    assert missing["reviews"][0]["accuracy_score"] is None
    assert missing["reviews"][0]["isUnscorable"] is True


def check_playwright_and_server_available(target_url: str = "http://127.0.0.1:3002") -> tuple[bool, str]:
    """Check if Playwright, chromium browser, and dashboard server are available."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return False, "playwright package is not installed"

    import urllib.request
    try:
        req = urllib.request.Request(target_url, headers={"User-Agent": "Nexus-Test-Check"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status >= 500:
                return False, f"Dashboard server at {target_url} returned HTTP {resp.status}"
    except Exception:
        return False, f"Dashboard server at {target_url} is not running or unreachable"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as e:
        return False, f"Playwright chromium browser unavailable: {e}"

    return True, "Available"


def test_playwright_fixture_state_integration():
    """Run Playwright verification against UI fixtures when dashboard server is running."""
    import pytest
    avail, reason = check_playwright_and_server_available()
    if not avail:
        pytest.skip(reason)

    results = run_playwright_fixture_state_checks()
    assert results["stale_fixture"]["passed"] is True
    assert results["fresh_today_fixture"]["passed"] is True
    assert results["missing_field_fixture"]["passed"] is True


if __name__ == "__main__":
    res = run_playwright_fixture_state_checks()
    print(json.dumps(res, indent=2))

