"""
Issue 8 — webhook app and standalone reminder script tests.
"""
import json
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


# ---------------------------------------------------------------------------
# webhook_app: Flask app creation and /webhook endpoint
# ---------------------------------------------------------------------------

def test_webhook_app_creates_flask_app():
    from bot.webhook_app import create_app
    app = create_app(bot_token="fake-token", db_path=":memory:", group_chat_id=-100)
    assert app is not None


def test_webhook_endpoint_returns_200_for_valid_json(monkeypatch):
    """POST /webhook with valid JSON returns HTTP 200."""
    from bot.webhook_app import create_app

    app = create_app(bot_token="fake-token", db_path=":memory:", group_chat_id=-100)
    client = app.test_client()

    payload = json.dumps({"update_id": 1, "message": {"text": "hello"}})
    with patch("bot.webhook_app.process_update"):
        resp = client.post(
            "/webhook",
            data=payload,
            content_type="application/json",
        )
    assert resp.status_code == 200


def test_webhook_endpoint_returns_400_for_non_json(monkeypatch):
    from bot.webhook_app import create_app

    app = create_app(bot_token="fake-token", db_path=":memory:", group_chat_id=-100)
    client = app.test_client()

    resp = client.post("/webhook", data="not json", content_type="text/plain")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# run_reminders.py: standalone reminder runner
# ---------------------------------------------------------------------------

def test_run_reminders_sends_due_reminders(db_path, monkeypatch):
    """Standalone reminder runner posts messages for due items."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("GROUP_CHAT_ID", "-100")
    monkeypatch.setenv("DB_PATH", db_path)

    expiry = date.today() + timedelta(days=7)
    store_expiry_item(db_path, -100, 42, "Panadol", None, expiry)

    sent_messages = []

    def fake_send(chat_id, text, reply_markup=None):
        sent_messages.append({"chat_id": chat_id, "text": text})
        return MagicMock(message_id=99)

    with patch("bot.run_reminders.Bot") as MockBot:
        mock_bot = MagicMock()
        mock_bot.send_message.side_effect = fake_send
        MockBot.return_value.__enter__ = MagicMock(return_value=mock_bot)
        MockBot.return_value.__exit__ = MagicMock(return_value=False)

        from bot import run_reminders
        run_reminders.main()

    assert len(sent_messages) == 1
    assert "Panadol" in sent_messages[0]["text"]


def test_run_reminders_no_messages_when_nothing_due(db_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("GROUP_CHAT_ID", "-100")
    monkeypatch.setenv("DB_PATH", db_path)

    # Item expires in 5 days — not on any threshold
    expiry = date.today() + timedelta(days=5)
    store_expiry_item(db_path, -100, 42, "Panadol", None, expiry)

    with patch("bot.run_reminders.Bot") as MockBot:
        mock_bot = MagicMock()
        mock_bot.send_message = MagicMock()
        MockBot.return_value.__enter__ = MagicMock(return_value=mock_bot)
        MockBot.return_value.__exit__ = MagicMock(return_value=False)

        from bot import run_reminders
        run_reminders.main()

    mock_bot.send_message.assert_not_called()
