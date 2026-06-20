"""Shared utility functions for the bot."""


async def resolve_display_name(bot, user_id: int) -> str:
    """Resolve a Telegram user ID to a display name; falls back to the numeric ID as string."""
    try:
        chat = await bot.get_chat(user_id)
        return chat.first_name or chat.username or str(user_id)
    except Exception:
        return str(user_id)
