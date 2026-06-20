import sqlite3
import tempfile
import os
from datetime import date, timedelta
import pytest
from bot.db import init_db
from bot.ingestion import store_expiry_item
from bot.dismiss import dismiss_item, get_last_reminder_message_id


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    yield path
    os.unlink(path)


def add_item(db_path, name="Panadol", days=7):
    expiry = date.today() + timedelta(days=days)
    return store_expiry_item(db_path, -100123, 42, name, "medicine", expiry)


def test_dismiss_item_sets_dismissed_at(db_path):
    item_id = add_item(db_path)
    dismiss_item(db_path, item_id, dismissed_by=99)
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT dismissed_at, dismissed_by FROM expiry_items WHERE id = ?", (item_id,)
    ).fetchone()
    conn.close()
    assert row[0] is not None
    assert row[1] == 99


def test_dismiss_item_is_idempotent(db_path):
    item_id = add_item(db_path)
    dismiss_item(db_path, item_id, dismissed_by=99)
    dismiss_item(db_path, item_id, dismissed_by=99)  # should not raise
    conn = sqlite3.connect(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM expiry_items WHERE id = ? AND dismissed_at IS NOT NULL", (item_id,)
    ).fetchone()[0]
    conn.close()
    assert count == 1


def test_get_last_reminder_message_id_returns_none_when_no_reminder(db_path):
    item_id = add_item(db_path)
    assert get_last_reminder_message_id(db_path, item_id) is None


def test_get_last_reminder_message_id_returns_stored_id(db_path):
    item_id = add_item(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE expiry_items SET last_reminder_message_id = 555 WHERE id = ?", (item_id,)
    )
    conn.commit()
    conn.close()
    assert get_last_reminder_message_id(db_path, item_id) == 555
