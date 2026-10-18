"""Unit tests for Phase 7: Audit Thresholds, Telegram HTTP Failure Alert, and APScheduler Isolation."""

from __future__ import annotations

import datetime
import time

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

import delivery.telegram as tg_mod
import scheduler as sched_mod
import tests.audit_mobile_viewports as audit_mod
from core.paths import REPO_ROOT


def test_audit_thresholds_are_strict_and_fail_when_weakened(monkeypatch):
    """Phase 7.3: Committed audit thresholds meet strict targets and fail if weakened."""
    assert audit_mod.MIN_ESSENTIAL_TEXT_PX >= 12
    assert audit_mod.MIN_ANY_TEXT_PX >= 11
    assert audit_mod.MIN_TAP_TARGET_PX >= 44
    assert audit_mod.MAX_MOBILE_PAGE_HEIGHT_PX <= 2900
    assert audit_mod.MAX_CALL_CARD_FOLD_PX <= 844
    assert audit_mod.validate_audit_thresholds() is True

    monkeypatch.setattr(audit_mod, "MIN_ESSENTIAL_TEXT_PX", 11)
    with pytest.raises(ValueError, match="MIN_ESSENTIAL_TEXT_PX weakened"):
        audit_mod.validate_audit_thresholds()

    monkeypatch.setattr(audit_mod, "MIN_ESSENTIAL_TEXT_PX", 12)
    monkeypatch.setattr(audit_mod, "MIN_TAP_TARGET_PX", 40)
    with pytest.raises(ValueError, match="MIN_TAP_TARGET_PX weakened"):
        audit_mod.validate_audit_thresholds()

    monkeypatch.setattr(audit_mod, "MIN_TAP_TARGET_PX", 44)
    monkeypatch.setattr(audit_mod, "MAX_MOBILE_PAGE_HEIGHT_PX", 3000)
    with pytest.raises(ValueError, match="MAX_MOBILE_PAGE_HEIGHT_PX weakened"):
        audit_mod.validate_audit_thresholds()


def test_security_md_documents_in_memory_rate_limiter_limitation():
    """Phase 7.7: SECURITY.md documents the per-instance in-memory rate limiter limitation."""
    sec_text = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "ipBuckets" in sec_text
    assert "per-instance" in sec_text
    assert "in-memory" in sec_text.lower()


def test_telegram_failure_alert_makes_http_request_on_pipeline_failure(monkeypatch):
    """Phase 7.8: Verify Telegram failure alert with a mocked HTTP layer on pipeline failure."""
    import json
    from telegram.request import BaseRequest

    monkeypatch.setattr(tg_mod, "TELEGRAM_BOT_TOKEN", "123456789:" + ("A" * 35))
    monkeypatch.setattr(tg_mod, "TELEGRAM_CHAT_ID", "-100987654321")

    captured_http_calls = []

    class FakeHTTPXRequest(BaseRequest):
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        @property
        def read_timeout(self):
            return 30.0

        async def initialize(self):
            pass

        async def shutdown(self):
            pass

        async def do_request(self, url: str, method: str, request_data=None, **kwargs):
            params = request_data.parameters if request_data is not None else {}
            captured_http_calls.append({"url": url, "method": method, "params": params})
            if url.endswith("/getMe"):
                payload = {
                    "ok": True,
                    "result": {
                        "id": 123456789,
                        "is_bot": True,
                        "first_name": "NexusBot",
                        "username": "nexus_ihsg_bot",
                    },
                }
            else:
                payload = {
                    "ok": True,
                    "result": {
                        "message_id": 42,
                        "date": 1700000000,
                        "chat": {"id": -100987654321, "type": "channel"},
                        "text": params.get("text", ""),
                    },
                }
            return 200, json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(tg_mod.telegram.request, "HTTPXRequest", FakeHTTPXRequest)
    monkeypatch.setattr(
        sched_mod,
        "run_market_brief",
        lambda: (_ for _ in ()).throw(RuntimeError("Simulated upstream LLM outage")),
    )

    with pytest.raises(RuntimeError, match="Simulated upstream LLM outage"):
        sched_mod.daily_brief(force=True)

    send_calls = [c for c in captured_http_calls if c["url"].endswith("/sendMessage")]
    assert len(send_calls) == 1
    assert send_calls[0]["method"] == "POST"
    assert str(send_calls[0]["params"].get("chat_id")) == "-100987654321"
    assert "Morning Brief FAILED" in send_calls[0]["params"].get("text", "")
    assert "Simulated upstream LLM outage" in send_calls[0]["params"].get("text", "")


def test_raising_in_scheduler_job_does_not_stop_subsequent_apscheduler_jobs(monkeypatch):
    """Phase 7.8: Verify raising in scheduler.py does not stop other APScheduler jobs."""
    events = []

    def failing_morning_job():
        events.append("morning_started")
        monkeypatch.setattr(
            sched_mod,
            "run_market_brief",
            lambda: (_ for _ in ()).throw(RuntimeError("Morning job crash")),
        )
        monkeypatch.setattr(sched_mod, "send_report", lambda msg: events.append("alert_sent"))
        sched_mod.daily_brief(force=True)

    def healthy_second_job():
        events.append("second_job_completed")

    scheduler = BackgroundScheduler(timezone="Asia/Jakarta")
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    scheduler.add_job(
        failing_morning_job,
        "date",
        run_date=now + datetime.timedelta(milliseconds=100),
        id="job_1_failing",
    )
    scheduler.add_job(
        healthy_second_job,
        "date",
        run_date=now + datetime.timedelta(milliseconds=350),
        id="job_2_healthy",
    )

    scheduler.start()
    try:
        deadline = time.time() + 4.0
        while time.time() < deadline and "second_job_completed" not in events:
            time.sleep(0.1)
    finally:
        scheduler.shutdown(wait=True)

    assert "morning_started" in events
    assert "alert_sent" in events
    assert "second_job_completed" in events
