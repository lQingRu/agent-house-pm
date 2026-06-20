"""
Issue 6 hardening: error handling in handlers and scheduler, dismiss fallback.
"""
import os
import tempfile
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.db import init_db
from bot.ingestion import store_expiry_item


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    yield path
    os.unlink(path)


@pytest.fixture
def config(db_path):
    cfg = MagicMock()
    cfg.db_path = db_path
    cfg.group_chat_id = -100123
    return cfg


# ---------------------------------------------------------------------------
# dm_message_handler: top-level exception → generic error reply
# ---------------------------------------------------------------------------

async def test_dm_handler_replies_with_error_when_exception_occurs(config):
    """Any unhandled exception must produce a 'Something went wrong' reply."""
    update = MagicMock()
    update.effective_chat.type = "private"
    update.message.text = "Panadol expires 15 Jul 2026"
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.bot_data = {"config": config}

    with patch("bot.handlers.store_expiry_item", side_effect=RuntimeError("DB exploded")):
        from bot.handlers import dm_message_handler
        await dm_message_handler(update, context)

    update.message.reply_text.assert_called_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "Something went wrong" in reply_text


# ---------------------------------------------------------------------------
# run_reminder_job: exception must not crash the job
# ---------------------------------------------------------------------------

async def test_reminder_job_does_not_raise_when_exception_occurs(config):
    """If the reminder job body raises, the exception is caught and logged."""
    context = MagicMock()
    context.bot_data = {"config": config}

    with patch("bot.scheduler.get_due_reminders", side_effect=Exception("DB locked")):
        from bot.scheduler import run_reminder_job
        # Must complete without raising
        await run_reminder_job(context)


# ---------------------------------------------------------------------------
# dismiss_callback_handler: fallback new message when edit fails
# ---------------------------------------------------------------------------

async def test_dismiss_fallback_sends_new_message_when_edit_fails(config, db_path):
    """When editing the reminder message raises, a new message is sent instead."""
    expiry = date.today() + timedelta(days=7)
    item_id = store_expiry_item(db_path, config.group_chat_id, 42, "Panadol", None, expiry)

    query = MagicMock()
    query.answer = AsyncMock()
    query.data = f"dismiss:{item_id}"
    query.from_user.id = 99
    query.message.text = "⏰ Expiry reminder — Panadol\nExpires in 7 days"
    query.edit_message_text = AsyncMock(side_effect=Exception("Message not found"))

    update = MagicMock()
    update.callback_query = query

    context = MagicMock()
    context.bot_data = {"config": config}
    context.bot.send_message = AsyncMock()

    from bot.dismiss import dismiss_callback_handler
    await dismiss_callback_handler(update, context)

    # Fallback: a new message must be sent to the group chat
    context.bot.send_message.assert_called_once()
    call_kwargs = context.bot.send_message.call_args
    assert call_kwargs[1]["chat_id"] == config.group_chat_id or call_kwargs[0][0] == config.group_chat_id
