from telegram import Update
from telegram.constants import ChatMemberStatus

async def is_admin(update: Update) -> bool:
    if not update.effective_chat or not update.effective_user:
        return False

    if update.effective_chat.type == "private":
        return True

    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False
