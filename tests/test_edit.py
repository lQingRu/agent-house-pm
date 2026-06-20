import sqlite3
import tempfile
import os
from datetime import date, timedelta
import pytest
from bot.db import init_db
from bot.ingestion import store_expiry_item
from bot.edit import get_item, update_item_name, update_item_category, update_item_expiry, delete_item


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


def test_get_item_returns_dict_for_existing_item(db_path):
    item_id = add_item(db_path, "Panadol")
    item = get_item(db_path, item_id)
    assert item is not None
    assert item["name"] == "Panadol"
    assert item["id"] == item_id


def test_get_item_returns_none_for_missing_id(db_path):
    assert get_item(db_path, 9999) is None


def test_get_item_returns_none_for_dismissed_item(db_path):
    item_id = add_item(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE expiry_items SET dismissed_at = datetime('now') WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    assert get_item(db_path, item_id) is None


def test_update_item_name_changes_name(db_path):
    item_id = add_item(db_path, "Panadol")
    update_item_name(db_path, item_id, "Panadol Extra")
    item = get_item(db_path, item_id)
    assert item["name"] == "Panadol Extra"


def test_update_item_category_changes_category(db_path):
    item_id = add_item(db_path)
    update_item_category(db_path, item_id, "food")
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT category FROM expiry_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    assert row[0] == "food"


def test_update_item_category_accepts_none(db_path):
    item_id = add_item(db_path)
    update_item_category(db_path, item_id, None)
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT category FROM expiry_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    assert row[0] is None


def test_update_item_expiry_changes_date(db_path):
    item_id = add_item(db_path)
    new_date = date.today() + timedelta(days=30)
    update_item_expiry(db_path, item_id, new_date)
    item = get_item(db_path, item_id)
    assert item["expiry_date"] == new_date.isoformat()


def test_delete_item_removes_row(db_path):
    item_id = add_item(db_path)
    delete_item(db_path, item_id)
    assert get_item(db_path, item_id) is None
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT id FROM expiry_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    assert row is None
