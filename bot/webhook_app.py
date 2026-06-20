"""
Flask WSGI app for PythonAnywhere webhook-based deployment.

Receives Telegram updates via POST /webhook and dispatches them
to the same handlers used in polling mode.
"""
import logging
from flask import Flask, request, abort

from bot.db import init_db
from bot.handlers import dm_message_handler
from bot.dismiss import dismiss_callback_handler
from bot.commands import list_command, upcoming_command

logger = logging.getLogger(__name__)

# Patched in tests; real dispatch happens via python-telegram-bot Application.
process_update = None


def create_app(bot_token: str, db_path: str, group_chat_id: int) -> Flask:
    import asyncio
    import json as _json

    from telegram import Update, Bot
    from telegram.ext import (
        Application, MessageHandler, CallbackQueryHandler,
        CommandHandler, filters,
    )

    init_db(db_path)

    ptb_app = Application.builder().token(bot_token).build()

    from bot.config import Config
    cfg = Config(
        telegram_bot_token=bot_token,
        db_path=db_path,
        group_chat_id=group_chat_id,
        reminder_job_time="08:00",
        log_level="INFO",
        google_service_account_key_path=None,
        google_calendar_id=None,
    )
    ptb_app.bot_data["config"] = cfg

    ptb_app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, dm_message_handler))
    ptb_app.add_handler(CallbackQueryHandler(dismiss_callback_handler, pattern=r"^dismiss:"))
    ptb_app.add_handler(CommandHandler("list", list_command))
    ptb_app.add_handler(CommandHandler("upcoming", upcoming_command))

    flask_app = Flask(__name__)

    async def _dispatch(json_data: dict) -> None:
        async with ptb_app:
            update = Update.de_json(json_data, ptb_app.bot)
            await ptb_app.process_update(update)

    def _run_dispatch(json_data: dict) -> None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_dispatch(json_data))
        finally:
            loop.close()

    # Allow test to patch this at the module level
    global process_update
    process_update = _run_dispatch

    @flask_app.post("/webhook")
    def webhook():
        if not request.is_json:
            abort(400)
        data = request.get_json(silent=True)
        if data is None:
            abort(400)
        try:
            process_update(data)
        except Exception:
            logger.error("Error processing update", exc_info=True)
        return "", 200

    return flask_app
