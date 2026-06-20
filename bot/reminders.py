import sqlite3
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_THRESHOLDS = {"7d": 7, "3d": 3, "0d": 0}


@dataclass
class ReminderDue:
    item_id: int
    item_name: str
    category: Optional[str]
    expiry_date: date
    level: str
    submitted_by: int


def get_due_reminders(db_path: str, today: date) -> list[ReminderDue]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    items = conn.execute(
        "SELECT id, name, category, expiry_date, submitted_by FROM expiry_items WHERE dismissed_at IS NULL"
    ).fetchall()

    due = []
    for item in items:
        expiry = date.fromisoformat(item["expiry_date"])
        for level, days in _THRESHOLDS.items():
            if expiry - timedelta(days=days) != today:
                continue
            already_sent = conn.execute(
                "SELECT 1 FROM reminder_log WHERE item_id = ? AND level = ?",
                (item["id"], level),
            ).fetchone()
            if already_sent:
                continue
            due.append(ReminderDue(
                item_id=item["id"],
                item_name=item["name"],
                category=item["category"],
                expiry_date=expiry,
                level=level,
                submitted_by=item["submitted_by"],
            ))

    conn.close()
    return due


def record_reminder_sent(db_path: str, item_id: int, level: str, message_id: int) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO reminder_log (item_id, level, message_id) VALUES (?, ?, ?)",
        (item_id, level, message_id),
    )
    conn.execute(
        "UPDATE expiry_items SET last_reminder_message_id = ? WHERE id = ?",
        (message_id, item_id),
    )
    conn.commit()
    conn.close()
