import sqlite3
import tempfile
import os
from datetime import date, timedelta
import pytest
from bot.db import init_db
from bot.ingestion import store_expiry_item
from bot.reminders import get_due_reminders, ReminderDue, record_reminder_sent


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    yield path
    os.unlink(path)


def add_item(db_path, name, days_from_now, category=None):
    expiry = date.today() + timedelta(days=days_from_now)
    return store_expiry_item(db_path, -100123, 42, name, category, expiry)


def test_get_due_reminders_returns_7d_item(db_path):
    add_item(db_path, "Panadol", 7, "medicine")
    dues = get_due_reminders(db_path, today=date.today())
    assert len(dues) == 1
    assert dues[0].level == "7d"
    assert dues[0].item_name == "Panadol"


def test_get_due_reminders_returns_3d_item(db_path):
    add_item(db_path, "milk", 3)
    dues = get_due_reminders(db_path, today=date.today())
    assert len(dues) == 1
    assert dues[0].level == "3d"


def test_get_due_reminders_returns_0d_item(db_path):
    add_item(db_path, "eggs", 0)
    dues = get_due_reminders(db_path, today=date.today())
    assert len(dues) == 1
    assert dues[0].level == "0d"


def test_get_due_reminders_skips_non_threshold_days(db_path):
    add_item(db_path, "flour", 5)
    dues = get_due_reminders(db_path, today=date.today())
    assert dues == []


def test_get_due_reminders_skips_dismissed_items(db_path):
    item_id = add_item(db_path, "Panadol", 7)
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE expiry_items SET dismissed_at = datetime('now') WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    dues = get_due_reminders(db_path, today=date.today())
    assert dues == []


def test_get_due_reminders_skips_already_sent_level(db_path):
    item_id = add_item(db_path, "Panadol", 7)
    record_reminder_sent(db_path, item_id, "7d", message_id=999)
    dues = get_due_reminders(db_path, today=date.today())
    assert dues == []


def test_record_reminder_sent_inserts_log_row(db_path):
    item_id = add_item(db_path, "milk", 3)
    record_reminder_sent(db_path, item_id, "3d", message_id=12345)
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT item_id, level, message_id FROM reminder_log WHERE item_id = ?", (item_id,)
    ).fetchone()
    last_msg = conn.execute(
        "SELECT last_reminder_message_id FROM expiry_items WHERE id = ?", (item_id,)
    ).fetchone()
    conn.close()
    assert row == (item_id, "3d", 12345)
    assert last_msg[0] == 12345


def test_get_due_reminders_multiple_items_different_thresholds(db_path):
    add_item(db_path, "A", 7)
    add_item(db_path, "B", 3)
    add_item(db_path, "C", 0)
    add_item(db_path, "D", 5)
    dues = get_due_reminders(db_path, today=date.today())
    assert len(dues) == 3
    levels = {d.level for d in dues}
    assert levels == {"7d", "3d", "0d"}


def test_get_due_reminders_includes_submitted_by(db_path):
    add_item(db_path, "Panadol", 7, "medicine")
    dues = get_due_reminders(db_path, today=date.today())
    assert len(dues) == 1
    assert dues[0].submitted_by == 42
