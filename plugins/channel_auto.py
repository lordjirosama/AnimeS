from bot import Bot
from pyrogram.types import ChatMemberUpdated
from database.database import kingdb
from config import OWNER_ID


@Bot.on_chat_member_updated()
async def auto_index(client, event: ChatMemberUpdated):

    try:
        # 🔒 Safety checks
        if not event.new_chat_member:
            return

        if not event.new_chat_member.user:
            return

        # 🤖 Bot ID
        bot_id = (await client.get_me()).id

        # ✅ Check bot added / promoted
        if event.new_chat_member.user.id != bot_id:
            return

        # ✅ Only channel (group hata diya intentionally)
        if event.chat.type != "channel":
            return

        # ✅ Only when bot becomes admin
        if event.new_chat_member.status != "administrator":
            return

        # 👤 Kisne add kiya
        adder = event.from_user
        if not adder:
            return

        # 🔐 Permission check (OWNER ya DB admins)
        if adder.id == OWNER_ID:
            allowed = True
        else:
            admins = await kingdb.get_all_admins()
            allowed = adder.id in admins

        if not allowed:
            print("❌ Unauthorized add, leaving...")
            await client.leave_chat(event.chat.id)
            return

        # 💾 SAVE CHANNEL (INDEX)
        await kingdb.add_or_update_channel(
            channel_id=event.chat.id,
            title=event.chat.title,
            username=event.chat.username,
            join_mode="direct",       # default fix
            expire_seconds=600        # default fix
        )

        print(f"✅ Indexed: {event.chat.title} ({event.chat.id})")

    except Exception as e:
        print("❌ AUTO INDEX ERROR:", e)
