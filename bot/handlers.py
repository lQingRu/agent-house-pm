import html as _html
import logging
from datetime import date, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from bot.parser import parse_item_message
from bot.ingestion import store_expiry_item

logger = logging.getLogger(__name__)

_THRESHOLDS = [("7 days", 7), ("3 days", 3), ("on the day", 0)]


def build_reminder_schedule_html(expiry_date: date) -> str:
    today = date.today()
    parts = []
    for label, days in _THRESHOLDS:
        fire_date = expiry_date - timedelta(days=days)
        if fire_date < today:
            parts.append(f"<s>{label}</s>")
        else:
            date_display = fire_date.strftime("%-d %b")
            parts.append(f"✓ {label} ({date_display})")
    return ", ".join(parts)


async def dm_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private":
        return

    try:
        text = update.message.text or ""
        result = parse_item_message(text)

        if result is None:
            await update.message.reply_text(
                "I couldn't find an expiry date in your message.\n\n"
                "Try something like:\n"
                "`Panadol (medicine) expires 15 Jul 2026`\n"
                "`Milk best before 25 Jun 2026`\n\n"
                "Or send /help to see all commands.",
                parse_mode="Markdown",
            )
            return

        cfg = context.bot_data["config"]
        store_expiry_item(
            db_path=cfg.db_path,
            group_chat_id=cfg.group_chat_id,
            submitted_by=update.effective_user.id,
            name=result.name,
            category=result.category,
            expiry_date=result.expiry_date,
        )
        logger.info("item_submitted name=%s submitted_by=%s", result.name, update.effective_user.id)

        category_str = f" ({_html.escape(result.category)})" if result.category else ""
        date_str = result.expiry_date.strftime("%-d %b %Y")
        schedule_html = build_reminder_schedule_html(result.expiry_date)

        await update.message.reply_text(
            f"Got it! I've noted <b>{_html.escape(result.name)}</b>{category_str} — expires <b>{date_str}</b>.\n\n"
            f"Reminders: {schedule_html}",
            parse_mode="HTML",
        )
    except Exception:
        logger.error("Unhandled exception in dm_message_handler", exc_info=True)
        await update.message.reply_text(
            "Something went wrong — please try again."
        )
