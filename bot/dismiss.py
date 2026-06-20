import sqlite3
import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def is_already_dismissed(db_path: str, item_id: int) -> bool:
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT dismissed_at FROM expiry_items WHERE id = ?", (item_id,)
    ).fetchone()
    conn.close()
    return row is not None and row[0] is not None


def dismiss_item(db_path: str, item_id: int, dismissed_by: int) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        UPDATE expiry_items
        SET dismissed_at = datetime('now'), dismissed_by = ?
        WHERE id = ? AND dismissed_at IS NULL
        """,
        (dismissed_by, item_id),
    )
    conn.commit()
    conn.close()


def get_last_reminder_message_id(db_path: str, item_id: int) -> Optional[int]:
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT last_reminder_message_id FROM expiry_items WHERE id = ?", (item_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


async def dismiss_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if not data.startswith("dismiss:"):
        return

    item_id = int(data.split(":", 1)[1])
    cfg = context.bot_data["config"]

    if is_already_dismissed(cfg.db_path, item_id):
        await query.answer("Already dismissed.", show_alert=False)
        return

    dismiss_item(cfg.db_path, item_id, dismissed_by=query.from_user.id)

    try:
        await query.edit_message_text(
            text=query.message.text + "\n\n✅ Resolved",
            reply_markup=None,
        )
    except Exception:
        logger.warning("Could not edit reminder message for item %d — sending fallback", item_id)
        await context.bot.send_message(
            chat_id=cfg.group_chat_id,
            text=f"✅ Resolved",
        )
