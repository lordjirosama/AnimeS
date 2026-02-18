import datetime
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from bot import Bot
from database.database import kingdb
from config import OWNER_ID, LOG_CHANNEL

# --- STATE ---
index_wait = set()

def get_time():
    return datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

# ================= 1. /INDEX COMMAND ================= #
@Bot.on_message(filters.command("index") & filters.private)
async def index_cmd(client, message):
    user_id = message.from_user.id
    admins = await kingdb.get_all_admins()

    if user_id != OWNER_ID and user_id not in admins:
        return await message.reply("❌ **Sirf Admins allowed hain.**")

    index_wait.add(user_id)
    await message.reply(
        "📥 **Indexing Mode ON**\n\n"
        "Ab kisi bhi Channel ya Group se ek message **Forward** karo.\n"
        "_(Note: Bot wahan admin hona chahiye)_"
    )

# ================= 2. FORWARD HANDLER ================= #
@Bot.on_message(filters.private & filters.forwarded)
async def index_forward(client, message):
    user_id = message.from_user.id
    if user_id not in index_wait:
        return

    index_wait.remove(user_id)
    chat = message.forward_from_chat or message.sender_chat

    if not chat:
        return await message.reply("❌ **Error:** Proper Channel/Group se forward karo.")

    try:
        # Default Settings: Direct Mode, 600s Expire
        await kingdb.add_or_update_channel(
            channel_id=chat.id,
            title=chat.title,
            username=chat.username,
            join_mode="direct",
            expire_seconds=600,
            added_by=user_id
        )

        await message.reply(
            f"✅ **Successfully Indexed!**\n\n"
            f"📛 **Title:** {chat.title}\n"
            f"🆔 **ID:** `{chat.id}`\n"
            f"⚙️ **Mode:** Direct Join"
        )

        # Log
        await client.send_message(
            LOG_CHANNEL,
            f"✅ **NEW INDEX ADDED**\n\n📛 {chat.title}\n🆔 `{chat.id}`\n👤 By: {message.from_user.mention}\n⏰ {get_time()}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑 Remove", callback_data=f"remove_{chat.id}")]])
        )

    except Exception as e:
        await message.reply(f"❌ **Error:** {e}")

# ================= 3. AUTO ADD (Bot Added to Channel) ================= #
@Bot.on_chat_member_updated()
async def auto_index_on_add(client, event: ChatMemberUpdated):
    if not event.new_chat_member or event.new_chat_member.user.id != client.me.id:
        return

    chat = event.chat
    # Sirf Channels aur Supergroups allow karein
    if chat.type not in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP]:
        return

    try:
        await kingdb.add_or_update_channel(
            channel_id=chat.id,
            title=chat.title,
            username=chat.username,
            join_mode="direct",
            expire_seconds=600
        )

        await client.send_message(
            LOG_CHANNEL,
            f"🤖 **AUTO INDEXED (Bot Added)**\n\n📛 {chat.title}\n🆔 `{chat.id}`\n⏰ {get_time()}"
        )
    except Exception as e:
        print(f"Auto Index Error: {e}")

# ================= 4. REMOVE CALLBACK ================= #
@Bot.on_callback_query(filters.regex(r"remove_"))
async def remove_channel_cb(client, query):
    user_id = query.from_user.id
    admins = await kingdb.get_all_admins()

    if user_id != OWNER_ID and user_id not in admins:
        return await query.answer("❌ Not Allowed", show_alert=True)

    chat_id = int(query.data.split("_")[1])
    
    # Database se delete
    await kingdb.del_channel(chat_id)
    
    await query.message.edit_text(f"🗑 **Channel Removed:** `{chat_id}`")
