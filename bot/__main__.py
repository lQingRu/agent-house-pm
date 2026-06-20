import logging
import os
from datetime import time as dtime

from dotenv import load_dotenv
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, CommandHandler, filters

from bot.config import get_config
from bot.db import init_db
from bot.handlers import dm_message_handler
from bot.dismiss import dismiss_callback_handler
from bot.commands import list_command, upcoming_command, start_command, help_command, add_command
from bot.scheduler import run_reminder_job
from bot.calendar_service import run_calendar_job

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)
logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()
    cfg = get_config()

    logging.getLogger().setLevel(cfg.log_level)

    os.makedirs(os.path.dirname(cfg.db_path) or ".", exist_ok=True)
    init_db(cfg.db_path)

    app = Application.builder().token(cfg.telegram_bot_token).build()
    app.bot_data["config"] = cfg

    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, dm_message_handler))
    app.add_handler(CallbackQueryHandler(dismiss_callback_handler, pattern=r"^dismiss:"))
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("upcoming", upcoming_command))

    h, m = (int(x) for x in cfg.reminder_job_time.split(":"))
    app.job_queue.run_daily(run_reminder_job, time=dtime(h, m))
    if cfg.google_calendar_id and cfg.google_service_account_key_path:
        app.job_queue.run_daily(run_calendar_job, time=dtime(h, m))
    else:
        logger.warning("GOOGLE_CALENDAR_ID or GOOGLE_SERVICE_ACCOUNT_KEY_PATH not set — calendar job disabled")

    logger.info("Bot started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
