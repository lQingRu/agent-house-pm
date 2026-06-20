"""
Issue 7 — Google Calendar integration tests.
"""
import os
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.db import init_db


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    yield path
    os.unlink(path)


# ---------------------------------------------------------------------------
# calendar_notification_log DB helpers
# ---------------------------------------------------------------------------

def test_get_sent_calendar_notifications_returns_empty_for_new_event(db_path):
    from bot.calendar_service import get_sent_calendar_notifications
    result = get_sent_calendar_notifications(db_path, "event_abc")
    assert result == set()


def test_record_calendar_notification_sent_inserts_row(db_path):
    from bot.calendar_service import record_calendar_notification_sent, get_sent_calendar_notifications
    record_calendar_notification_sent(db_path, "event_abc", "7d")
    result = get_sent_calendar_notifications(db_path, "event_abc")
    assert "7d" in result


def test_get_sent_calendar_notifications_returns_only_this_events_levels(db_path):
    from bot.calendar_service import record_calendar_notification_sent, get_sent_calendar_notifications
    record_calendar_notification_sent(db_path, "event_abc", "7d")
    record_calendar_notification_sent(db_path, "event_xyz", "1d")
    result = get_sent_calendar_notifications(db_path, "event_abc")
    assert result == {"7d"}  # event_xyz's levels should not appear


# ---------------------------------------------------------------------------
# Notification text formatting
# ---------------------------------------------------------------------------

def test_build_calendar_notification_text_7d_with_time():
    from bot.calendar_service import CalendarEvent, build_calendar_notification_text
    event = CalendarEvent(
        event_id="e1",
        summary="Dad's dentist appointment",
        start_date=date(2026, 6, 21),
        start_datetime=datetime(2026, 6, 21, 10, 0),
        is_all_day=False,
    )
    text = build_calendar_notification_text(event, "7d")
    assert "📅 Upcoming event — in 7 days" in text
    assert "Dad's dentist appointment" in text
    assert "21 Jun 2026" in text
    assert "10:00" in text


def test_build_calendar_notification_text_1d_all_day():
    from bot.calendar_service import CalendarEvent, build_calendar_notification_text
    event = CalendarEvent(
        event_id="e2",
        summary="Family BBQ",
        start_date=date(2026, 6, 15),
        start_datetime=None,
        is_all_day=True,
    )
    text = build_calendar_notification_text(event, "1d")
    assert "📅 Upcoming event — in 1 day" in text
    assert "Family BBQ" in text
    assert "15 Jun 2026" in text
    # All-day events must NOT show a time
    assert "00:00" not in text
    assert "AM" not in text


# ---------------------------------------------------------------------------
# run_calendar_job scheduling logic
# ---------------------------------------------------------------------------

async def test_run_calendar_job_posts_7d_notification(db_path):
    from bot.calendar_service import CalendarEvent

    event_date = date.today() + timedelta(days=7)
    fake_event = CalendarEvent(
        event_id="evt_7d",
        summary="School play",
        start_date=event_date,
        start_datetime=None,
        is_all_day=True,
    )

    cfg = MagicMock()
    cfg.db_path = db_path
    cfg.group_chat_id = -100
    cfg.google_calendar_id = "cal@group.calendar.google.com"
    cfg.google_service_account_key_path = "/fake/key.json"

    context = MagicMock()
    context.bot_data = {"config": cfg}
    context.bot.send_message = AsyncMock(return_value=MagicMock(message_id=42))

    with patch("bot.calendar_service.get_upcoming_calendar_events", return_value=[fake_event]):
        from bot.calendar_service import run_calendar_job
        await run_calendar_job(context)

    context.bot.send_message.assert_called_once()
    text_sent = context.bot.send_message.call_args[1]["text"]
    assert "School play" in text_sent


async def test_run_calendar_job_skips_already_notified_event(db_path):
    from bot.calendar_service import CalendarEvent, record_calendar_notification_sent

    event_date = date.today() + timedelta(days=7)
    fake_event = CalendarEvent(
        event_id="evt_already",
        summary="Doctor",
        start_date=event_date,
        start_datetime=None,
        is_all_day=True,
    )
    record_calendar_notification_sent(db_path, "evt_already", "7d")

    cfg = MagicMock()
    cfg.db_path = db_path
    cfg.group_chat_id = -100
    cfg.google_calendar_id = "cal@group.calendar.google.com"
    cfg.google_service_account_key_path = "/fake/key.json"

    context = MagicMock()
    context.bot_data = {"config": cfg}
    context.bot.send_message = AsyncMock()

    with patch("bot.calendar_service.get_upcoming_calendar_events", return_value=[fake_event]):
        from bot.calendar_service import run_calendar_job
        await run_calendar_job(context)

    context.bot.send_message.assert_not_called()


async def test_run_calendar_job_skips_when_calendar_not_configured(db_path):
    cfg = MagicMock()
    cfg.db_path = db_path
    cfg.google_calendar_id = None
    cfg.google_service_account_key_path = None

    context = MagicMock()
    context.bot_data = {"config": cfg}
    context.bot.send_message = AsyncMock()

    from bot.calendar_service import run_calendar_job
    await run_calendar_job(context)

    context.bot.send_message.assert_not_called()


# ---------------------------------------------------------------------------
# /upcoming command includes calendar events
# ---------------------------------------------------------------------------

def test_build_upcoming_text_includes_calendar_events(db_path):
    from bot.calendar_service import CalendarEvent
    from bot.commands import build_upcoming_text

    event_date = date.today() + timedelta(days=3)
    cal_events = [
        CalendarEvent(
            event_id="e1",
            summary="Parent meeting",
            start_date=event_date,
            start_datetime=None,
            is_all_day=True,
        )
    ]
    text = build_upcoming_text(db_path, today=date.today(), calendar_events=cal_events)
    assert "Parent meeting" in text


def test_build_upcoming_text_works_without_calendar_events(db_path):
    from bot.commands import build_upcoming_text
    # Should not raise when no calendar_events passed (backwards compat)
    text = build_upcoming_text(db_path, today=date.today())
    assert isinstance(text, str)
