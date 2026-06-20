import sqlite3
import tempfile
import os
from datetime import date
import pytest
from bot.db import init_db
from bot.ingestion import store_expiry_item, fetch_expiry_items


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    yield path
    os.unlink(path)


def test_store_expiry_item_inserts_row(db_path):
    store_expiry_item(
        db_path=db_path,
        group_chat_id=-100123,
        submitted_by=42,
        name="Panadol",
        category="medicine",
        expiry_date=date(2026, 7, 15),
    )
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT name, category, expiry_date, chat_id, submitted_by, dismissed_at FROM expiry_items").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0] == ("Panadol", "medicine", "2026-07-15", -100123, 42, None)


def test_store_expiry_item_without_category(db_path):
    store_expiry_item(
        db_path=db_path,
        group_chat_id=-100123,
        submitted_by=42,
        name="milk",
        category=None,
        expiry_date=date(2026, 8, 1),
    )
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT category FROM expiry_items").fetchone()
    conn.close()
    assert row[0] is None


def test_store_multiple_items_creates_distinct_rows(db_path):
    store_expiry_item(db_path, -100123, 42, "Item A", None, date(2026, 7, 1))
    store_expiry_item(db_path, -100123, 42, "Item B", None, date(2026, 8, 1))
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM expiry_items").fetchone()[0]
    conn.close()
    assert count == 2


def test_fetch_expiry_items_returns_all_active(db_path):
    store_expiry_item(db_path, -100123, 42, "Panadol", "medicine", date(2026, 7, 15))
    items = fetch_expiry_items(db_path)
    assert len(items) == 1
    assert items[0]["name"] == "Panadol"
    assert items[0]["dismissed_at"] is None
