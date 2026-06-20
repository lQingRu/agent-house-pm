import sqlite3
import tempfile
import os
from datetime import date, timedelta
import pytest
from bot.db import init_db
from bot.ingestion import store_expiry_item
from bot.commands import build_list_text, build_upcoming_text


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    yield path
    os.unlink(path)


def add_item(db_path, name, days, dismissed=False):
    expiry = date.today() + timedelta(days=days)
    item_id = store_expiry_item(db_path, -100123, 42, name, None, expiry)
    if dismissed:
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE expiry_items SET dismissed_at = datetime('now') WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
    return item_id


def test_build_list_text_shows_active_items(db_path):
    add_item(db_path, "Panadol", 7)
    add_item(db_path, "milk", 3)
    text = build_list_text(db_path)
    assert "Panadol" in text
    assert "milk" in text


def test_build_list_text_shows_dismissed_items_as_resolved(db_path):
    add_item(db_path, "Panadol", 7, dismissed=True)
    text = build_list_text(db_path)
    assert "Panadol" in text
    assert "Resolved" in text or "✅" in text


def test_build_list_text_empty_message_when_no_items(db_path):
    text = build_list_text(db_path)
    assert "no items" in text.lower() or "empty" in text.lower()


def test_build_upcoming_text_shows_items_within_7_days(db_path):
    add_item(db_path, "eggs", 5)
    text = build_upcoming_text(db_path, today=date.today())
    assert "eggs" in text


def test_build_upcoming_text_excludes_items_beyond_7_days(db_path):
    add_item(db_path, "flour", 10)
    text = build_upcoming_text(db_path, today=date.today())
    assert "flour" not in text


def test_build_upcoming_text_excludes_dismissed_items(db_path):
    add_item(db_path, "Panadol", 3, dismissed=True)
    text = build_upcoming_text(db_path, today=date.today())
    assert "Panadol" not in text


def test_build_upcoming_text_empty_when_nothing_due(db_path):
    text = build_upcoming_text(db_path, today=date.today())
    assert "nothing" in text.lower() or "no items" in text.lower()


def test_build_list_text_shows_submitter_when_names_provided(db_path):
    add_item(db_path, "Panadol", 7)  # submitted_by=42 per the fixture
    text = build_list_text(db_path, names={42: "Alice"})
    assert "added by Alice" in text


def test_build_list_text_omits_submitter_when_names_not_provided(db_path):
    add_item(db_path, "Panadol", 7)
    text = build_list_text(db_path)
    assert "added by" not in text
