"""
Standalone reminder runner for PythonAnywhere scheduled tasks.

Usage:
    python -m bot.run_reminders

PythonAnywhere scheduled task command:
    python /home/<username>/house-pm/bot/run_reminders.py
"""
import logging
import os
from datetime import date

from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import get_config
from bot.db import init_db
from bot.reminders import get_due_reminders, record_reminder_sent

logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()
    cfg = get_config()

    logging.basicConfig(
        level=cfg.log_level,
        format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
    )

    os.makedirs(os.path.dirname(cfg.db_path) or ".", exist_ok=True)
    init_db(cfg.db_path)

    today = date.today()
    dues = get_due_reminders(cfg.db_path, today)

    if not dues:
        logger.info("No reminders due today")
        return

    with Bot(token=cfg.telegram_bot_token) as bot:
        for due in dues:
            days_remaining = (due.expiry_date - today).days
            category_str = f" ({due.category})" if due.category else ""
            if days_remaining == 0:
                days_str = "expires today"
            else:
                days_str = f"expires in {days_remaining} days ({due.expiry_date.strftime('%-d %b %Y')})"

            text = (
                f"⏰ Expiry reminder — {due.item_name}{category_str}\n"
                f"{days_str.capitalize()}"
            )
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Dismiss ✓", callback_data=f"dismiss:{due.item_id}")]]
            )
            try:
                msg = bot.send_message(
                    chat_id=cfg.group_chat_id,
                    text=text,
                    reply_markup=keyboard,
                )
                record_reminder_sent(cfg.db_path, due.item_id, due.level, msg.message_id)
                logger.info("reminder_sent item_id=%d level=%s", due.item_id, due.level)
            except Exception:
                logger.error(
                    "Failed to send reminder item_id=%d level=%s", due.item_id, due.level,
                    exc_info=True,
                )


if __name__ == "__main__":
    main()
