import datetime
from pyrogram import filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatMemberUpdated,
)
from bot import Bot
from database.database import kingdb
from config import OWNER_ID, LOG_CHANNEL

# ================= STATE ================= #
index_wait = set()

def debug(text):
    print(f"[AUTO_INDEX_DEBUG] {text}")

# ================= COMMON TIME FORMAT ================= #
def get_time():
    return datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")


# =========================================================
# 1️⃣ /INDEX COMMAND
# =========================================================

@Bot.on_message(filters.command("index") & filters.private)
async def index_cmd(client, message):
    debug("Index command received")
    user_id = message.from_user.id
    admins = await kingdb.get_all_admins()

    if user_id != OWNER_ID and user_id not in admins:
        debug(f"Unauthorized access attempt by {user_id}")
        return await message.reply("❌ **You are not authorized to use this command.**")

    index_wait.add(user_id)
    debug(f"User {user_id} added to wait list")
    await message.reply("📥 **Ab kisi bhi Channel ya Group ka post forward karo.**\n\n_Note: Bot ko us channel me admin hona chahiye agar private hai toh._")


# =========================================================
# 2️⃣ FORWARD HANDLER
# =========================================================

@Bot.on_message(filters.private & filters.forwarded)
async def index_forward(client, message):
    user_id = message.from_user.id
    if user_id not in index_wait:
        return

    debug("Forward received for indexing")
    index_wait.remove(user_id)

    chat = message.forward_from_chat or message.sender_chat
    if not chat:
        debug("Invalid forward source")
        return await message.reply("❌ **Proper channel/group se forward karo.**")

    debug(f"Detected Chat: {chat.id} | {chat.title}")

    try:
        # Step 1: Base indexing
        await kingdb.add_or_update_channel(
            channel_id=chat.id,
            title=chat.title or "Unknown",
            username=chat.username,
            join_mode="direct",
            expire_seconds=600
        )

        # Step 2: Metadata update
        await kingdb.update_channel(chat.id, {
            "is_private": chat.username is None,
            "added_by": user_id,
            "added_time": get_time()
        })
        debug("Saved in DB successfully")

    except Exception as e:
        debug(f"DB ERROR: {e}")
        return await message.reply(f"❌ **Database Error:** `{e}`")

    # LOGGING
    log_text = f"""
✅ **CHANNEL INDEXED**

👤 **Added By:** `{user_id}`
📛 **Title:** {chat.title}
🆔 **ID:** `{chat.id}`
🔗 **Link:** @{chat.username if chat.username else 'Private'}
⏰ **Time:** `{get_time()}`
"""
    try:
        await client.send_message(
            LOG_CHANNEL,
            log_text,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Remove Channel", callback_data=f"remove_{chat.id}")]]
            ),
        )
        debug("Log sent to LOG_CHANNEL")
    except Exception as e:
        debug(f"LOG ERROR: {e}")

    await message.reply(f"✅ **{chat.title}** has been indexed successfully!")


# =========================================================
# 3️⃣ AUTO INDEX WHEN BOT ADDED
# =========================================================

@Bot.on_chat_member_updated()
async def auto_index_on_add(client, event: ChatMemberUpdated):
    try:
        # Check if the bot itself was added
        if not event.new_chat_member or event.new_chat_member.user.id != client.me.id:
            return

        chat = event.chat
        debug(f"Bot added to chat: {chat.id}")

        # Security Check
        adder = event.from_user
        if adder:
            admins = await kingdb.get_all_admins()
            if adder.id != OWNER_ID and adder.id not in admins:
                debug(f"Unauthorized add by {adder.id} → Leaving...")
                await client.leave_chat(chat.id)
                return
        
        # Supported types only
        if chat.type not in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP, enums.ChatType.GROUP]:
            return

        # Indexing
        await kingdb.add_or_update_channel(
            channel_id=chat.id,
            title=chat.title,
            username=chat.username,
            join_mode="direct",
            expire_seconds=600
        )

        await kingdb.update_channel(chat.id, {
            "is_private": chat.username is None,
            "added_by": adder.id if adder else "System",
            "added_time": get_time()
        })

        await client.send_message(
            LOG_CHANNEL,
            f"🤖 **AUTO INDEXED (Bot Added)**\n\n📛 {chat.title}\n🆔 `{chat.id}`\n👤 By: `{adder.id if adder else 'System'}`\n⏰ {get_time()}"
        )
        debug("Auto indexing success")

    except Exception as e:
        debug(f"AUTO INDEX ERROR: {e}")


# =========================================================
# 4️⃣ REMOVE CALLBACK
# =========================================================

@Bot.on_callback_query(filters.regex(r"remove_"))
async def remove_channel_cb(client, query):
    user_id = query.from_user.id
    admins = await kingdb.get_all_admins()

    if user_id != OWNER_ID and user_id not in admins:
        return await query.answer("❌ You don't have permission to remove this.", show_alert=True)

    chat_id = int(query.data.split("_")[1])

    try:
        await kingdb.del_channel(chat_id)
        debug(f"Deleted chat {chat_id} from DB")
        await query.message.edit_text(f"❌ **Removed:** `{chat_id}` has been deleted from the database.")
        await query.answer("Removed Successfully")
    except Exception as e:
        debug(f"DELETE ERROR: {e}")
        await query.answer(f"Error: {e}", show_alert=True)
