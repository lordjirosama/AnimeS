# +++ Auto Channel Index System +++

from bot import Bot
from pyrogram.types import ChatMemberUpdated
from config import OWNER_ID
from database.database import kingdb


@Bot.on_chat_member_updated()
async def auto_index_channel(client, event: ChatMemberUpdated):

    # 1️⃣ Check bot itself is updated
    if event.new_chat_member.user.id != client.me.id:
        return

    # 2️⃣ Only for channels
    if event.chat.type != "channel":
        return

    # 3️⃣ Bot must become administrator
    if event.new_chat_member.status != "administrator":
        return

    adder = event.from_user
    if not adder:
        return

    # 4️⃣ Check if allowed (Owner or DB Admin)
    if adder.id == OWNER_ID:
        allowed = True
    else:
        admins = await kingdb.get_all_admins()
        allowed = adder.id in admins

    if not allowed:
        print("❌ Unauthorized user tried to add bot.")
        try:
            await client.leave_chat(event.chat.id)
        except:
            pass
        return

    # 5️⃣ Auto Index Channel
    try:
        await kingdb.add_or_update_channel(
            channel_id=event.chat.id,
            title=event.chat.title,
            username=event.chat.username,
            join_mode="normal",        # default mode
            expire_seconds=3600,       # default 1 hour
            added_by=adder.id
        )

        print(f"✅ Channel Auto Indexed: {event.chat.title}")

    except Exception as e:
        print("Auto Index Error:", e)
