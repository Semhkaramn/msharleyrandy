import os
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

ALLOWED_CHAT_ID = os.getenv("ALLOWED_CHAT_ID")

def get_allowed_chat_id() -> int:
    """Get the first allowed chat ID from env."""
    if not ALLOWED_CHAT_ID:
        return None
    allowed_ids = [int(x.strip()) for x in ALLOWED_CHAT_ID.split(",") if x.strip()]
    return allowed_ids[0] if allowed_ids else None

async def is_admin(update: Update) -> bool:
    """Check if user is admin in current chat."""
    if not update.effective_chat or not update.effective_user:
        return False

    if update.effective_chat.type == "private":
        return True

    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

async def is_admin_of_chat(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    """Check if a user is admin of a specific chat."""
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

async def check_private_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple:
    """
    Check admin permission for private chat commands.
    Uses ALLOWED_CHAT_ID from env to verify admin status.

    Returns (chat_id, is_valid, error_message) tuple.
    """
    allowed_chat_id = get_allowed_chat_id()

    if not allowed_chat_id:
        return None, False, "Bot yapilandirmasi eksik (ALLOWED_CHAT_ID)."

    user_id = update.effective_user.id

    # Check if user is admin in the allowed chat
    if not await is_admin_of_chat(context, allowed_chat_id, user_id):
        return None, False, "Bu botu kullanmak icin izinli grupta yonetici olmaniz gerekiyor."

    return allowed_chat_id, True, None
