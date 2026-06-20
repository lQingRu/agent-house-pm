import logging
from datetime import date

from telegram.ext import ContextTypes

from bot.reminders import get_due_reminders, record_reminder_sent
from bot.utils import resolve_display_name

logger = logging.getLogger(__name__)


async def run_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = context.bot_data["config"]
    try:
        today = date.today()
        dues = get_due_reminders(cfg.db_path, today)
    except Exception:
        logger.error("Reminder job failed to fetch due reminders", exc_info=True)
        return

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    for due in dues:
        category_str = f" ({due.category})" if due.category else ""
        days_remaining = (due.expiry_date - today).days
        if days_remaining == 0:
            days_str = "expires today"
        else:
            days_str = f"expires in {days_remaining} days ({due.expiry_date.strftime('%-d %b %Y')})"

        submitter_name = await resolve_display_name(context.bot, due.submitted_by)

        text = (
            f"⏰ Expiry reminder — {due.item_name}{category_str}\n"
            f"{days_str.capitalize()}\n"
            f"Added by {submitter_name}"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Dismiss ✓", callback_data=f"dismiss:{due.item_id}")]]
        )
        msg = await context.bot.send_message(
            chat_id=cfg.group_chat_id,
            text=text,
            reply_markup=keyboard,
        )
        record_reminder_sent(cfg.db_path, due.item_id, due.level, msg.message_id)
        logger.info("Sent %s reminder for item %d", due.level, due.item_id)
