import sqlite3
from datetime import date
from typing import Optional


def store_expiry_item(
    db_path: str,
    group_chat_id: int,
    submitted_by: int,
    name: str,
    category: Optional[str],
    expiry_date: date,
) -> int:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        """
        INSERT INTO expiry_items (chat_id, submitted_by, name, category, expiry_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (group_chat_id, submitted_by, name, category, expiry_date.isoformat()),
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def fetch_expiry_items(db_path: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM expiry_items WHERE dismissed_at IS NULL"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
