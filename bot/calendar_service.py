import logging
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_THRESHOLDS = {"7d": 7, "1d": 1}


@dataclass
class CalendarEvent:
    event_id: str
    summary: str
    start_date: date
    start_datetime: Optional[datetime]
    is_all_day: bool


def get_sent_calendar_notifications(db_path: str, event_id: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT level FROM calendar_notification_log WHERE event_id = ?",
        (event_id,),
    ).fetchall()
    conn.close()
    return {row[0] for row in rows}


def record_calendar_notification_sent(db_path: str, event_id: str, level: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO calendar_notification_log (event_id, level) VALUES (?, ?)",
        (event_id, level),
    )
    conn.commit()
    conn.close()


def build_calendar_notification_text(event: CalendarEvent, level: str) -> str:
    days = _THRESHOLDS[level]
    day_word = "day" if days == 1 else "days"
    header = f"📅 Upcoming event — in {days} {day_word}"

    if event.is_all_day or event.start_datetime is None:
        date_line = f"📆 {event.start_date.strftime('%-d %b %Y')}"
    else:
        date_line = f"📆 {event.start_datetime.strftime('%-d %b %Y, %I:%M %p').lstrip('0')}"

    return f"{header}\n{event.summary}\n{date_line}"


def get_upcoming_calendar_events(
    key_path: str,
    calendar_id: str,
    days: int = 8,
) -> list[CalendarEvent]:
    """Fetch events from Google Calendar using a service account."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        key_path,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    service = build("calendar", "v3", credentials=creds)

    today = date.today()
    time_min = datetime.combine(today, datetime.min.time()).isoformat() + "Z"
    time_max = datetime.combine(today + timedelta(days=days), datetime.min.time()).isoformat() + "Z"

    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = []
    for item in result.get("items", []):
        start = item.get("start", {})
        if "date" in start:
            # All-day event
            start_date = date.fromisoformat(start["date"])
            events.append(CalendarEvent(
                event_id=item["id"],
                summary=item.get("summary", "(No title)"),
                start_date=start_date,
                start_datetime=None,
                is_all_day=True,
            ))
        elif "dateTime" in start:
            dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
            events.append(CalendarEvent(
                event_id=item["id"],
                summary=item.get("summary", "(No title)"),
                start_date=dt.date(),
                start_datetime=dt.replace(tzinfo=None),
                is_all_day=False,
            ))

    return events


async def run_calendar_job(context) -> None:
    cfg = context.bot_data["config"]

    if not getattr(cfg, "google_calendar_id", None) or not getattr(cfg, "google_service_account_key_path", None):
        logger.warning("Google Calendar not configured — skipping calendar job")
        return

    try:
        events = get_upcoming_calendar_events(
            cfg.google_service_account_key_path,
            cfg.google_calendar_id,
        )
    except Exception:
        logger.error("Failed to fetch Google Calendar events", exc_info=True)
        return

    today = date.today()
    for event in events:
        sent = get_sent_calendar_notifications(cfg.db_path, event.event_id)
        for level, days in _THRESHOLDS.items():
            if event.start_date - timedelta(days=days) != today:
                continue
            if level in sent:
                continue
            text = build_calendar_notification_text(event, level)
            try:
                await context.bot.send_message(
                    chat_id=cfg.group_chat_id,
                    text=text,
                )
                record_calendar_notification_sent(cfg.db_path, event.event_id, level)
                logger.info(
                    "calendar_notification_sent event_id=%s level=%s",
                    event.event_id,
                    level,
                )
            except Exception:
                logger.error(
                    "Failed to send calendar notification event_id=%s level=%s",
                    event.event_id,
                    level,
                    exc_info=True,
                )
