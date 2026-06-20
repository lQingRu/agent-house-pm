import sqlite3
from datetime import date
from typing import Optional


def get_item(db_path: str, item_id: int) -> Optional[dict]:
    """Return item dict, or None if the item doesn't exist or has been dismissed."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, name, category, expiry_date FROM expiry_items WHERE id = ? AND dismissed_at IS NULL",
        (item_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_item_name(db_path: str, item_id: int, new_name: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE expiry_items SET name = ? WHERE id = ?", (new_name, item_id))
    conn.commit()
    conn.close()


def update_item_category(db_path: str, item_id: int, new_category: Optional[str]) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE expiry_items SET category = ? WHERE id = ?", (new_category, item_id))
    conn.commit()
    conn.close()


def update_item_expiry(db_path: str, item_id: int, new_expiry: date) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE expiry_items SET expiry_date = ? WHERE id = ?",
        (new_expiry.isoformat(), item_id),
    )
    conn.commit()
    conn.close()


def delete_item(db_path: str, item_id: int) -> None:
    # FK constraints are disabled by default in SQLite; reminder_log rows are left as orphans.
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM expiry_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
