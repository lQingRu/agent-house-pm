import sqlite3


def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS expiry_items (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id                 INTEGER NOT NULL,
            submitted_by            INTEGER NOT NULL,
            name                    TEXT NOT NULL,
            category                TEXT,
            expiry_date             TEXT NOT NULL,
            created_at              TEXT NOT NULL DEFAULT (datetime('now')),
            dismissed_at            TEXT,
            dismissed_by            INTEGER,
            last_reminder_message_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS reminder_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id    INTEGER NOT NULL REFERENCES expiry_items(id),
            level      TEXT NOT NULL CHECK (level IN ('7d', '3d', '0d')),
            sent_at    TEXT NOT NULL DEFAULT (datetime('now')),
            message_id INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS calendar_notification_log (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            level    TEXT NOT NULL CHECK (level IN ('7d', '1d')),
            sent_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()
