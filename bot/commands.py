import sqlite3
import logging
from datetime import date, timedelta
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

_HELP_TEXT = (
    "Here's what I can do:\n\n"
    "*Add an item* — just send me a message like:\n"
    "  `Panadol (medicine) expires 15 Jul 2026`\n"
    "  `Milk best before 25 Jun 2026`\n"
    "  `Sunscreen (skincare) use by 2027-03`\n\n"
    "*/add* — show this add reminder\n"
    "*/list* — list all tracked items\n"
    "*/upcoming* — items expiring in the next 7 days\n"
    "*/config* — show current bot settings\n"
    "*/help* — show this message"
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! I track expiry dates for household items and remind the group before they expire.\n\n"
        + _HELP_TEXT,
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(_HELP_TEXT, parse_mode="Markdown")


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "To add an item, just send me a message in this chat like:\n\n"
        "  `Panadol (medicine) expires 15 Jul 2026`\n"
        "  `Milk best before 25 Jun 2026`\n\n"
        "The category in parentheses is optional.",
        parse_mode="Markdown",
    )


async def config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = context.bot_data["config"]
    lines = [
        "⚙️ <b>Bot configuration</b>",
        "",
        f"Reminder time: {cfg.reminder_job_time} daily",
        "Reminder schedule: 7 days, 3 days, on the day",
    ]
    if cfg.google_calendar_id and cfg.google_service_account_key_path:
        lines.append("Google Calendar: connected ✅")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


def build_list_text(db_path: str, names: dict[int, str] | None = None) -> str:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT name, category, expiry_date, dismissed_at, submitted_by FROM expiry_items ORDER BY expiry_date"
    ).fetchall()
    conn.close()

    if not rows:
        return "No items tracked yet."

    lines = []
    for r in rows:
        cat = f" ({r['category']})" if r["category"] else ""
        status = "✅ Resolved" if r["dismissed_at"] else f"expires {r['expiry_date']}"
        by = ""
        if names and r["submitted_by"] in names:
            by = f" (added by {names[r['submitted_by']]})"
        lines.append(f"• {r['name']}{cat}{by} — {status}")
    return "\n".join(lines)


def build_upcoming_text(db_path: str, today: date, calendar_events: Optional[list] = None) -> str:
    cutoff = today + timedelta(days=7)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT name, category, expiry_date FROM expiry_items
        WHERE dismissed_at IS NULL
          AND expiry_date >= ?
          AND expiry_date <= ?
        ORDER BY expiry_date
        """,
        (today.isoformat(), cutoff.isoformat()),
    ).fetchall()
    conn.close()

    lines = []
    for r in rows:
        cat = f" ({r['category']})" if r["category"] else ""
        lines.append(f"• {r['name']}{cat} — {r['expiry_date']}")

    for event in (calendar_events or []):
        lines.append(f"📅 {event.summary} — {event.start_date.isoformat()}")

    if not lines:
        return "Nothing expiring in the next 7 days."
    return "\n".join(lines)


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = context.bot_data["config"]

    conn = sqlite3.connect(cfg.db_path)
    conn.row_factory = sqlite3.Row
    user_id_rows = conn.execute(
        "SELECT DISTINCT submitted_by FROM expiry_items"
    ).fetchall()
    conn.close()

    names: dict[int, str] = {}
    for row in user_id_rows:
        uid = row["submitted_by"]
        try:
            chat = await context.bot.get_chat(uid)
            names[uid] = chat.first_name or chat.username or str(uid)
        except Exception:
            names[uid] = str(uid)

    text = build_list_text(cfg.db_path, names=names)
    await update.message.reply_text(text)


async def upcoming_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = context.bot_data["config"]
    text = build_upcoming_text(cfg.db_path, today=date.today())
    await update.message.reply_text(text)
