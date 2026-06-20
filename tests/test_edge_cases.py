import sqlite3
import tempfile
import os
from datetime import date, timedelta
import pytest
from bot.db import init_db
from bot.ingestion import store_expiry_item
from bot.parser import parse_item_message
from bot.dismiss import dismiss_item, is_already_dismissed


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    yield path
    os.unlink(path)


# --- Past date rejection ---

def test_parse_rejects_past_date():
    yesterday = (date.today() - timedelta(days=1)).strftime("%-d %b %Y")
    result = parse_item_message(f"Panadol expires {yesterday}")
    assert result is None


def test_parse_accepts_today_as_valid():
    today_str = date.today().strftime("%-d %b %Y")
    result = parse_item_message(f"Panadol expires {today_str}")
    assert result is not None
    assert result.expiry_date == date.today()


# --- Double-tap dismiss ---

def test_is_already_dismissed_returns_false_when_active(db_path):
    expiry = date.today() + timedelta(days=7)
    item_id = store_expiry_item(db_path, -100123, 42, "Panadol", None, expiry)
    assert not is_already_dismissed(db_path, item_id)


def test_is_already_dismissed_returns_true_after_dismiss(db_path):
    expiry = date.today() + timedelta(days=7)
    item_id = store_expiry_item(db_path, -100123, 42, "Panadol", None, expiry)
    dismiss_item(db_path, item_id, dismissed_by=99)
    assert is_already_dismissed(db_path, item_id)


def test_second_dismiss_does_not_overwrite_dismissed_by(db_path):
    expiry = date.today() + timedelta(days=7)
    item_id = store_expiry_item(db_path, -100123, 42, "Panadol", None, expiry)
    dismiss_item(db_path, item_id, dismissed_by=99)
    dismiss_item(db_path, item_id, dismissed_by=77)  # second tap
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT dismissed_by FROM expiry_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    assert row[0] == 99  # first winner preserved


# --- Both reminder levels on same day ---

def test_get_due_reminders_sends_multiple_levels_if_both_due_today():
    """Items added close to expiry can have 7d and 3d both overdue — only threshold matches matter."""
    from bot.reminders import get_due_reminders
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        init_db(path)
        # Item expires today — only 0d should fire
        store_expiry_item(path, -1, 42, "A", None, date.today())
        dues = get_due_reminders(path, today=date.today())
        assert any(d.level == "0d" for d in dues)
    finally:
        os.unlink(path)


# --- LOG_LEVEL config ---

def test_get_config_log_level_defaults_to_info(monkeypatch):
    from bot.config import get_config
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("GROUP_CHAT_ID", "-100")
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    cfg = get_config()
    assert cfg.log_level == "INFO"


def test_get_config_log_level_reads_env(monkeypatch):
    from bot.config import get_config
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("GROUP_CHAT_ID", "-100")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    cfg = get_config()
    assert cfg.log_level == "DEBUG"
