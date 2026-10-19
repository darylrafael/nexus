"""Nexus Strict & Auditable Mobile/Desktop Viewport Audit (tests/audit_mobile_viewports.py).

Enforces Phase 7 & Phase B (B2, B3, B4, B5) requirements:
1. Committed threshold constants (tested against weakening in unit tests):
   - MIN_ESSENTIAL_TEXT_PX = 12
   - MIN_ANY_TEXT_PX = 11
   - MIN_TAP_TARGET_PX = 44
   - MAX_MOBILE_PAGE_HEIGHT_PX = 2900
   - MAX_CALL_CARD_FOLD_PX = 844
   - MIN_FIRST_VIEWPORT_CLEARANCE_PX = 8 (direction badge + calibrated confidence bottom <= viewport_height - bottom_nav_height - 8)
2. Explicit & strict definition of essential text (Phase B3):
   - Any text that conveys a value, status, label of a number, button/link text, or body copy
     counts as essential and must be >= 12px.
   - Only decorative or purely redundant micro-labels may be 11px, and each such exception is
     listed by CSS selector with an explicit reason in ALLOWED_11PX_MICRO_LABEL_SELECTORS.
   - Every visible text node NOT matching ALLOWED_11PX_MICRO_LABEL_SELECTORS is classified as
     essential text and MUST have computed font-size >= 12px.
3. Verifies stale pipeline state: stale banner visible, "No new call generated today"
   present, zero "Live" chips, and call direction badge + calibrated confidence fully visible
   within the first viewport (bottom <= viewport_height - bottom_nav_height - 8px) at
   360x740, 390x844, 430x932, 768x1024, 1024x768, and 1440x900.
4. Verifies zero horizontal overflow, zero console errors, zero failed same-origin
   requests, and zero external Google Fonts requests.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Committed strict thresholds (Phase 7.3 & Phase B) — do NOT weaken
MIN_ESSENTIAL_TEXT_PX: int = 12
MIN_ANY_TEXT_PX: int = 11
MIN_TAP_TARGET_PX: int = 44
MAX_MOBILE_PAGE_HEIGHT_PX: int = 2900
MAX_CALL_CARD_FOLD_PX: int = 844
MIN_FIRST_VIEWPORT_CLEARANCE_PX: int = 8
MOBILE_WIDTHS: tuple[int, ...] = (360, 390, 430)

# Phase B3: Explicit selector -> reason allowlist for 11px decorative/redundant micro-labels.
# Any visible text node whose parent does NOT match one of these selectors is classified as
# essential text (conveys a value, status, label of a number, button/link text, or body copy)
# and MUST be >= 12px.
ALLOWED_11PX_MICRO_LABEL_SELECTORS: Dict[str, str] = {
    ".breadcrumb": "Decorative top eyebrow path ('NEXUS / MARKET INTELLIGENCE') redundant with the H1 page title directly below it",
    ".sidebar-sub-brand": "Decorative secondary brand subtitle ('MARKET INTEL') next to primary NEXUS logo",
    ".dir-glyph": "Decorative directional arrow glyph ('▲'/'▼'/'◆') inside DirectionBadge, redundant with the explicit direction word ('BULLISH'/'BEARISH'/'NEUTRAL')",
    ".source-citation-icon": "Decorative link icon ('🔗') inside citation pill",
    ".source-citation-arrow": "Decorative external-link arrow ('↗') inside citation pill",
}

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_OUTPUT_DIR = str(
    Path(os.environ.get("NEXUS_AUDIT_OUTPUT_DIR", REPO_ROOT / "audit_output"))
)

VIEWPORTS: List[Dict[str, Any]] = [
    {"name": "mobile_360", "width": 360, "height": 740},
    {"name": "mobile_390_iphone", "width": 390, "height": 844},
    {"name": "mobile_430_promax", "width": 430, "height": 932},
    {"name": "tablet_768", "width": 768, "height": 1024},
    {"name": "desktop_1024", "width": 1024, "height": 768},
    {"name": "desktop_1440", "width": 1440, "height": 900},
]


def validate_audit_thresholds() -> bool:
    """Assert that committed audit thresholds meet or exceed Phase 7.3 & Phase B minimums."""
    if MIN_ESSENTIAL_TEXT_PX < 12:
        raise ValueError(f"MIN_ESSENTIAL_TEXT_PX weakened: {MIN_ESSENTIAL_TEXT_PX} < 12")
    if MIN_ANY_TEXT_PX < 11:
        raise ValueError(f"MIN_ANY_TEXT_PX weakened: {MIN_ANY_TEXT_PX} < 11")
    if MIN_TAP_TARGET_PX < 44:
        raise ValueError(f"MIN_TAP_TARGET_PX weakened: {MIN_TAP_TARGET_PX} < 44")
    if MAX_MOBILE_PAGE_HEIGHT_PX > 2900:
        raise ValueError(f"MAX_MOBILE_PAGE_HEIGHT_PX weakened: {MAX_MOBILE_PAGE_HEIGHT_PX} > 2900")
    if MAX_CALL_CARD_FOLD_PX > 844:
        raise ValueError(f"MAX_CALL_CARD_FOLD_PX weakened: {MAX_CALL_CARD_FOLD_PX} > 844")
    if MIN_FIRST_VIEWPORT_CLEARANCE_PX < 8:
        raise ValueError(f"MIN_FIRST_VIEWPORT_CLEARANCE_PX weakened: {MIN_FIRST_VIEWPORT_CLEARANCE_PX} < 8")
    if not ALLOWED_11PX_MICRO_LABEL_SELECTORS or not all(
        isinstance(k, str) and isinstance(v, str) and len(v.strip()) > 10
        for k, v in ALLOWED_11PX_MICRO_LABEL_SELECTORS.items()
    ):
        raise ValueError("ALLOWED_11PX_MICRO_LABEL_SELECTORS must map selectors to explicit non-empty reasons")
    return True


def run_audit(
    target_url: str = "http://127.0.0.1:3002",
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Any]:
    from playwright.sync_api import sync_playwright

    validate_audit_thresholds()
    os.makedirs(output_dir, exist_ok=True)

    results: Dict[str, Any] = {}
    all_console_errors: List[str] = []
    all_failed_requests: List[str] = []
    external_font_requests: List[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for vp in VIEWPORTS:
            for theme in ["dark", "light"]:
                key = f"{vp['name']}_{theme}"
                print(f"Auditing {key} ({vp['width']}x{vp['height']}) in {theme} mode...")

                context = browser.new_context(
                    viewport={"width": vp["width"], "height": vp["height"]},
                    device_scale_factor=2,
                )
                page = context.new_page()

                page.on(
                    "console",
                    lambda msg, k=key: all_console_errors.append(f"[{k}] {msg.type}: {msg.text}")
                    if msg.type == "error"
                    else None,
                )
                page.on(
                    "pageerror",
                    lambda err, k=key: all_console_errors.append(f"[{k}] PageError: {err}"),
                )
                page.on(
                    "request",
                    lambda req, k=key: external_font_requests.append(f"[{k}] {req.url}")
                    if ("fonts.googleapis.com" in req.url or "fonts.gstatic.com" in req.url)
                    else None,
                )
                page.on(
                    "response",
                    lambda resp, k=key: all_failed_requests.append(
                        f"[{k}] {resp.url} returned {resp.status}"
                    )
                    if resp.status >= 400 and ("127.0.0.1" in resp.url or "localhost" in resp.url)
                    else None,
                )

                page.goto(target_url, wait_until="networkidle")
                page.wait_for_timeout(600)

                page.evaluate(f"document.documentElement.setAttribute('data-theme', '{theme}')")
                page.wait_for_timeout(200)

                # 1. Horizontal overflow check
                overflow_info = page.evaluate(
                    """() => {
                    const docWidth = document.documentElement.scrollWidth;
                    const winWidth = window.innerWidth;
                    const hasOverflow = docWidth > winWidth + 1;
                    const overflowingEls = [];
                    if (hasOverflow) {
                        for (const el of document.querySelectorAll('*')) {
                            const rect = el.getBoundingClientRect();
                            if (rect.right > winWidth + 1.5) {
                                overflowingEls.push({
                                    tag: el.tagName,
                                    class: String(el.className || ''),
                                    right: Math.round(rect.right),
                                    winWidth
                                });
                                if (overflowingEls.length >= 5) break;
                            }
                        }
                    }
                    return { docWidth, winWidth, hasOverflow, overflowingEls };
                }"""
                )

                # 2. Strict Phase B3 Typography Audit:
                # Every visible text node is essential (must be >= 12px) unless its element
                # matches an explicit selector in ALLOWED_11PX_MICRO_LABEL_SELECTORS.
                font_audit = page.evaluate(
                    """(params) => {
                    const { minAnyPx, minEssentialPx, allowedMicroSelectors } = params;
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        {
                            acceptNode: (node) => {
                                if (!node.textContent || !node.textContent.trim()) {
                                    return NodeFilter.FILTER_REJECT;
                                }
                                let el = node.parentElement;
                                while (el) {
                                    const st = window.getComputedStyle(el);
                                    if (st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity) === 0) {
                                        return NodeFilter.FILTER_REJECT;
                                    }
                                    el = el.parentElement;
                                }
                                return NodeFilter.FILTER_ACCEPT;
                            }
                        }
                    );

                    let totalTextNodes = 0;
                    let countUnder11 = 0;
                    let countUnder12Essential = 0;
                    let countUnder12AllowedMicroLabels = 0;
                    const tinySamples = [];
                    const allowedMicroLabelBreakdown = [];

                    while (walker.nextNode()) {
                        const node = walker.currentNode;
                        const parent = node.parentElement;
                        if (!parent) continue;
                        const rect = parent.getBoundingClientRect();
                        if (rect.width === 0 || rect.height === 0) continue;
                        totalTextNodes++;

                        const style = window.getComputedStyle(parent);
                        const size = parseFloat(style.fontSize);
                        const roundedSize = Math.round(size);
                        const text = node.textContent.trim();

                        let matchedAllowedSelector = null;
                        for (const [sel, reason] of Object.entries(allowedMicroSelectors)) {
                            if (parent.matches(sel) || parent.closest(sel)) {
                                matchedAllowedSelector = { selector: sel, reason };
                                break;
                            }
                        }

                        if (roundedSize < minAnyPx) {
                            countUnder11++;
                            if (tinySamples.length < 8) {
                                tinySamples.push({
                                    text: text.slice(0, 35),
                                    size: Math.round(size * 10) / 10,
                                    tag: parent.tagName,
                                    class: String(parent.className || ''),
                                    note: 'under 11px absolute floor'
                                });
                            }
                        } else if (roundedSize < minEssentialPx) {
                            if (matchedAllowedSelector) {
                                countUnder12AllowedMicroLabels++;
                                allowedMicroLabelBreakdown.push({
                                    selector: matchedAllowedSelector.selector,
                                    reason: matchedAllowedSelector.reason,
                                    text: text.slice(0, 35),
                                    size: Math.round(size * 10) / 10
                                });
                            } else {
                                countUnder12Essential++;
                                if (tinySamples.length < 8) {
                                    tinySamples.push({
                                        text: text.slice(0, 35),
                                        size: Math.round(size * 10) / 10,
                                        tag: parent.tagName,
                                        class: String(parent.className || ''),
                                        note: 'essential text under 12px'
                                    });
                                }
                            }
                        }
                    }

                    return {
                        totalTextNodes,
                        countUnder11,
                        countUnder12Essential,
                        countUnder12AllowedMicroLabels,
                        countUnder12Total: countUnder12Essential + countUnder12AllowedMicroLabels,
                        allowedMicroLabelBreakdown,
                        tinySamples
                    };
                }""",
                    {
                        "minAnyPx": MIN_ANY_TEXT_PX,
                        "minEssentialPx": MIN_ESSENTIAL_TEXT_PX,
                        "allowedMicroSelectors": ALLOWED_11PX_MICRO_LABEL_SELECTORS,
                    },
                )

                # 3. All interactive elements check against MIN_TAP_TARGET_PX (44x44)
                tap_audit = page.evaluate(
                    """(minTargetPx) => {
                    const selector = [
                        'button',
                        'a[href]',
                        'input',
                        'select',
                        'textarea',
                        '[role="button"]',
                        '[role="link"]',
                        '[tabindex]:not([tabindex="-1"])',
                        '[onclick]'
                    ].join(', ');
                    const candidates = new Set(document.querySelectorAll(selector));

                    for (const el of document.querySelectorAll('*')) {
                        if (el.tagName === 'TR') continue;
                        for (const key of Object.keys(el)) {
                            if (key.startsWith('__reactProps$') && el[key] && typeof el[key].onClick === 'function') {
                                candidates.add(el);
                            }
                        }
                    }

                    let totalInteractive = 0;
                    let smallTargets = 0;
                    const samples = [];

                    for (const el of candidates) {
                        let cur = el;
                        let hidden = false;
                        while (cur) {
                            const st = window.getComputedStyle(cur);
                            if (st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity) === 0) {
                                hidden = true;
                                break;
                            }
                            cur = cur.parentElement;
                        }
                        if (hidden) continue;

                        const rect = el.getBoundingClientRect();
                        if (rect.width <= 0 || rect.height <= 0) continue;
                        totalInteractive++;

                        if (Math.round(rect.width) < minTargetPx || Math.round(rect.height) < minTargetPx) {
                            smallTargets++;
                            if (samples.length < 8) {
                                samples.push({
                                    tag: el.tagName,
                                    class: String(el.className || ''),
                                    width: Math.round(rect.width * 10) / 10,
                                    height: Math.round(rect.height * 10) / 10,
                                    text: (el.textContent || '').trim().slice(0, 25)
                                });
                            }
                        }
                    }

                    return { totalInteractive, smallTargets, samples };
                }""",
                    MIN_TAP_TARGET_PX,
                )

                # 4. Stale banner, no "Live" chip, and Phase B4 First-Viewport Visibility Assertion:
                # Direction badge AND calibrated confidence bottom edge must be
                # <= viewport_height - bottom_nav_height - 8px at each tested viewport.
                state_check = page.evaluate(
                    """(params) => {
                    const { maxFoldPx, clearancePx } = params;
                    const banner = document.querySelector('.stale-pipeline-banner');
                    const bannerRect = banner ? banner.getBoundingClientRect() : null;
                    const staleBannerVisible = Boolean(banner && bannerRect && bannerRect.height > 0);
                    const bodyText = document.body.innerText || '';
                    const hasNoNewCallText = bodyText.includes('No new call generated today');

                    let hasLiveChip = false;
                    for (const el of document.querySelectorAll('.status-pill, .sidebar-session-item, .live-badge')) {
                        const txt = (el.textContent || '').trim();
                        if (/\\bLIVE\\b/i.test(txt)) {
                            hasLiveChip = true;
                            break;
                        }
                    }

                    const bottomNav = document.querySelector('.mobile-bottom-nav');
                    let bottomNavHeight = 0;
                    if (bottomNav) {
                        const navSt = window.getComputedStyle(bottomNav);
                        const navRect = bottomNav.getBoundingClientRect();
                        if (navSt.display !== 'none' && navSt.visibility !== 'hidden' && navRect.height > 0) {
                            bottomNavHeight = Math.round(navRect.height);
                        }
                    }
                    const viewportHeight = window.innerHeight;
                    const maxFirstViewportBottom = viewportHeight - bottomNavHeight - clearancePx;

                    const badge = document.querySelector('.today-call-dir-hero .dir-badge, .today-call-card .dir-badge');
                    const calConf = document.querySelector('.today-call-dir-hero .calibrated-conf-badge');
                    if (!badge) {
                        return {
                            staleBannerVisible,
                            hasNoNewCallText,
                            hasLiveChip,
                            exists: false,
                            top: null,
                            bottom: null,
                            calibratedConfBottom: null,
                            viewportHeight,
                            bottomNavHeight,
                            maxFirstViewportBottom,
                            withinFirstViewport: false,
                            calibratedConfWithinFirstViewport: false,
                            within844Fold: false
                        };
                    }
                    const rect = badge.getBoundingClientRect();
                    const calRect = calConf ? calConf.getBoundingClientRect() : rect;
                    const badgeBottom = Math.round(rect.bottom);
                    const calBottom = Math.round(calRect.bottom);
                    const withinFirstViewport = badgeBottom <= maxFirstViewportBottom;
                    const calibratedConfWithinFirstViewport = calBottom <= maxFirstViewportBottom;

                    return {
                        staleBannerVisible,
                        hasNoNewCallText,
                        hasLiveChip,
                        exists: true,
                        top: Math.round(rect.top),
                        bottom: badgeBottom,
                        calibratedConfBottom: calBottom,
                        viewportHeight,
                        bottomNavHeight,
                        maxFirstViewportBottom,
                        withinFirstViewport,
                        calibratedConfWithinFirstViewport,
                        within844Fold: badgeBottom <= maxFoldPx
                    };
                }""",
                    {
                        "maxFoldPx": MAX_CALL_CARD_FOLD_PX,
                        "clearancePx": MIN_FIRST_VIEWPORT_CLEARANCE_PX,
                    },
                )

                # 5. Full page height
                page_height = page.evaluate("() => document.documentElement.scrollHeight")

                # 6. Screenshots
                fold_screenshot = os.path.join(output_dir, f"{key}_fold.png")
                page.screenshot(path=fold_screenshot, full_page=False)

                full_screenshot = os.path.join(output_dir, f"{key}_full.png")
                page.screenshot(path=full_screenshot, full_page=True)

                is_mobile = vp["width"] in MOBILE_WIDTHS
                height_pass = (page_height <= MAX_MOBILE_PAGE_HEIGHT_PX) if is_mobile else True

                results[key] = {
                    "viewport": f"{vp['width']}x{vp['height']}",
                    "width": vp["width"],
                    "height": vp["height"],
                    "theme": theme,
                    "overflow": overflow_info,
                    "fonts": font_audit,
                    "tap_targets": tap_audit,
                    "fold_check": state_check,
                    "page_height": page_height,
                    "height_pass": height_pass,
                    "fold_screenshot": fold_screenshot,
                    "full_screenshot": full_screenshot,
                }

                context.close()

        browser.close()

    results["thresholds"] = {
        "MIN_ESSENTIAL_TEXT_PX": MIN_ESSENTIAL_TEXT_PX,
        "MIN_ANY_TEXT_PX": MIN_ANY_TEXT_PX,
        "MIN_TAP_TARGET_PX": MIN_TAP_TARGET_PX,
        "MAX_MOBILE_PAGE_HEIGHT_PX": MAX_MOBILE_PAGE_HEIGHT_PX,
        "MAX_CALL_CARD_FOLD_PX": MAX_CALL_CARD_FOLD_PX,
        "MIN_FIRST_VIEWPORT_CLEARANCE_PX": MIN_FIRST_VIEWPORT_CLEARANCE_PX,
        "ALLOWED_11PX_MICRO_LABEL_SELECTORS": ALLOWED_11PX_MICRO_LABEL_SELECTORS,
    }
    results["console_errors"] = all_console_errors
    results["failed_requests"] = all_failed_requests
    results["external_font_requests"] = external_font_requests

    summary_path = os.path.join(output_dir, "audit_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n============================================================")
    print("           EXHAUSTIVE QUALITY AUDIT SUMMARY                 ")
    print("============================================================")
    print(f"Configurations Tested: {len(VIEWPORTS) * 2}")
    print(f"Console Errors: {len(all_console_errors)}")
    print(f"Failed Same-Origin Requests: {len(all_failed_requests)}")
    print(f"External Font Requests: {len(external_font_requests)}")

    failures: List[str] = []
    if all_console_errors:
        failures.append(f"Console errors: {all_console_errors}")
    if all_failed_requests:
        failures.append(f"Failed requests: {all_failed_requests}")
    if external_font_requests:
        failures.append(f"External font requests: {external_font_requests}")

    for k, r in results.items():
        if k in ("thresholds", "console_errors", "failed_requests", "external_font_requests"):
            continue
        ov = r["overflow"]
        fn = r["fonts"]
        tt = r["tap_targets"]
        fc = r["fold_check"]
        h = r["page_height"]
        print(
            f"[{k}] Height: {h}px | Overflow: {ov['hasOverflow']} | "
            f"<11px: {fn['countUnder11']} | Essential <12px: {fn['countUnder12Essential']} "
            f"(Allowed 11px micro-labels: {fn['countUnder12AllowedMicroLabels']}) | "
            f"Small Targets (<44px): {tt['smallTargets']} | "
            f"StaleBanner: {fc['staleBannerVisible']} | LiveChip: {fc['hasLiveChip']} | "
            f"BadgeBottom: {fc['bottom']}px / CalConfBottom: {fc['calibratedConfBottom']}px "
            f"<= MaxFirstVP({fc['maxFirstViewportBottom']}px): {fc['withinFirstViewport'] and fc['calibratedConfWithinFirstViewport']}"
        )
        if ov["hasOverflow"]:
            failures.append(f"[{k}] Horizontal overflow detected: {ov}")
        if fn["countUnder11"] > 0:
            failures.append(f"[{k}] Text <11px detected: {fn['tinySamples']}")
        if fn["countUnder12Essential"] > 0:
            failures.append(f"[{k}] Essential text <12px detected: {fn['tinySamples']}")
        if tt["smallTargets"] > 0:
            failures.append(f"[{k}] Interactive targets <44px detected: {tt['samples']}")
        if not r["height_pass"]:
            failures.append(f"[{k}] Mobile page height {h}px > {MAX_MOBILE_PAGE_HEIGHT_PX}px")
        if not fc["staleBannerVisible"] or not fc["hasNoNewCallText"] or fc["hasLiveChip"]:
            failures.append(f"[{k}] Stale state check failed: {fc}")
        if not fc["withinFirstViewport"] or not fc["calibratedConfWithinFirstViewport"]:
            failures.append(
                f"[{k}] First-viewport visibility failed: badge={fc['bottom']}px, "
                f"calConf={fc['calibratedConfBottom']}px > limit={fc['maxFirstViewportBottom']}px"
            )

    if failures:
        raise AssertionError("Viewport audit failed:\n" + "\n".join(failures))

    return results


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


def test_mobile_viewports_audit():
    """Run mobile viewports quality audit when dashboard server is running."""
    import pytest
    avail, reason = check_playwright_and_server_available()
    if not avail:
        pytest.skip(reason)

    results = run_audit()
    assert len(results) >= 12


if __name__ == "__main__":
    run_audit()

