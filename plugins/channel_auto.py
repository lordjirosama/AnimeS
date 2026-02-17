from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from database.database import kingdb
from config import OWNER_ID, LOG_CHANNEL
import datetime

# user state
index_wait = set()


# ================= INDEX COMMAND ================= #

@Bot.on_message(filters.command("index") & filters.private)
async def index_cmd(bot, message):

    user_id = message.from_user.id

    admins = await kingdb.get_all_admins()
    if user_id != OWNER_ID and user_id not in admins:
        return await message.reply("❌ Not allowed")

    index_wait.add(user_id)

    await message.reply(
        "📥 Ab channel/group ka post forward karo jisko index karna hai"
    )


# ================= FORWARD HANDLER ================= #

@Bot.on_message(filters.private & filters.forwarded)
async def index_forward(bot, message):

    user_id = message.from_user.id

    if user_id not in index_wait:
        return  # ignore random forwards

    index_wait.remove(user_id)

    # ===== DETECT CHAT =====
    chat = None

    if message.sender_chat:
        chat = message.sender_chat
    elif message.forward_from_chat:
        chat = message.forward_from_chat
    else:
        return await message.reply("❌ Forward from channel/group only")

    # ===== SAVE =====
    try:
        await kingdb.add_or_update_channel(
            channel_id=chat.id,
            title=chat.title or "Unknown",
            username=chat.username,
            is_private=chat.username is None,
            join_mode="direct",
            expire_seconds=600,
            added_by=user_id
        )
    except Exception as e:
        return await message.reply(f"❌ DB Error: {e}")

    # ===== LOG =====
    log_text = f"""
✅ **INDEXED**

👤 {message.from_user.first_name} (`{user_id}`)
📛 {chat.title}
🆔 `{chat.id}`
🔗 @{chat.username if chat.username else 'Private'}
⏰ {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}
"""

    await bot.send_message(
        LOG_CHANNEL,
        log_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Remove", callback_data=f"remove_{chat.id}")]
        ])
    )

    await message.reply("✅ Indexed successfully!")


# ================= REMOVE ================= #

@Bot.on_callback_query(filters.regex(r"remove_"))
async def remove_channel(bot, query):

    user_id = query.from_user.id
    admins = await kingdb.get_all_admins()

    if user_id != OWNER_ID and user_id not in admins:
        return await query.answer("❌ Not allowed", show_alert=True)

    chat_id = int(query.data.split("_")[1])

    await kingdb.delete_channel(chat_id)

    await query.message.edit_text("❌ Removed from DB")
