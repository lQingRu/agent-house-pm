import sqlite3
import tempfile
import os
import pytest
from bot.db import init_db


def get_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def test_init_db_creates_expiry_items_table():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        columns = get_table_columns(conn, "expiry_items")
        conn.close()
        assert columns == {
            "id", "chat_id", "submitted_by", "name", "category",
            "expiry_date", "created_at", "dismissed_at", "dismissed_by",
            "last_reminder_message_id",
        }
    finally:
        os.unlink(db_path)


def test_init_db_creates_reminder_log_table():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        columns = get_table_columns(conn, "reminder_log")
        conn.close()
        assert columns == {"id", "item_id", "level", "sent_at", "message_id"}
    finally:
        os.unlink(db_path)


def test_init_db_creates_calendar_notification_log_table():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        columns = get_table_columns(conn, "calendar_notification_log")
        conn.close()
        assert columns == {"id", "event_id", "level", "sent_at"}
    finally:
        os.unlink(db_path)


def test_init_db_is_idempotent():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        init_db(db_path)  # should not raise
        conn = sqlite3.connect(db_path)
        columns = get_table_columns(conn, "expiry_items")
        conn.close()
        assert "id" in columns
    finally:
        os.unlink(db_path)


def test_init_db_creates_file_at_given_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        assert not os.path.exists(db_path)
        init_db(db_path)
        assert os.path.exists(db_path)
