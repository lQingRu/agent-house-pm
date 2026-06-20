import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.parser import parse_item_message
from bot.ingestion import store_expiry_item

logger = logging.getLogger(__name__)


async def dm_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private":
        return

    try:
        text = update.message.text or ""
        result = parse_item_message(text)

        if result is None:
            await update.message.reply_text(
                "I couldn't find an expiry date in your message.\n\n"
                "Try something like:\n"
                "`Panadol (medicine) expires 15 Jul 2026`\n"
                "`Milk best before 25 Jun 2026`\n\n"
                "Or send /help to see all commands.",
                parse_mode="Markdown",
            )
            return

        cfg = context.bot_data["config"]
        store_expiry_item(
            db_path=cfg.db_path,
            group_chat_id=cfg.group_chat_id,
            submitted_by=update.effective_user.id,
            name=result.name,
            category=result.category,
            expiry_date=result.expiry_date,
        )
        logger.info("item_submitted name=%s submitted_by=%s", result.name, update.effective_user.id)

        category_str = f" ({result.category})" if result.category else ""
        date_str = result.expiry_date.strftime("%-d %b %Y")
        await update.message.reply_text(
            f"Got it! I've noted **{result.name}**{category_str} — expires **{date_str}**. "
            f"I'll remind the group at 7 days, 3 days, and on the day.",
            parse_mode="Markdown",
        )
    except Exception:
        logger.error("Unhandled exception in dm_message_handler", exc_info=True)
        await update.message.reply_text(
            "Something went wrong — please try again."
        )
