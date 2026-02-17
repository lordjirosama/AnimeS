from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from database.database import kingdb
from config import OWNER_ID, LOG_CHANNEL
import datetime


# ================= INDEX HANDLER ================= #

@Bot.on_message(filters.private & filters.forwarded)
async def universal_index(bot, message):

    user_id = message.from_user.id

    # ✅ ADMIN CHECK
    admins = await kingdb.get_all_admins()
    if user_id != OWNER_ID and user_id not in admins:
        return await message.reply("❌ You are not allowed")

    chat = None

    # ✅ DETECT SOURCE
    if message.sender_chat:
        chat = message.sender_chat

    elif message.forward_from_chat:
        chat = message.forward_from_chat

    else:
        return await message.reply("❌ Forward from channel/group only")

    # ✅ SAVE IN DB
    try:
        await kingdb.add_or_update_channel(
            channel_id=chat.id,
            title=chat.title if chat.title else "Unknown",
            username=chat.username,
            is_private=chat.username is None,
            join_mode="direct",
            expire_seconds=600,
            added_by=user_id
        )
    except Exception as e:
        return await message.reply(f"❌ DB Error: {e}")

    # ✅ LOG MESSAGE
    log_text = f"""
✅ **INDEXED SUCCESSFULLY**

👤 By: {message.from_user.first_name} (`{user_id}`)
📛 Title: {chat.title}
🆔 ID: `{chat.id}`
🔗 Username: @{chat.username if chat.username else 'Private'}
⏰ Time: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}
"""

    try:
        await bot.send_message(
            chat_id=LOG_CHANNEL,
            text=log_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Remove", callback_data=f"remove_{chat.id}")]
            ])
        )
    except Exception as e:
        print("Log Error:", e)

    await message.reply("✅ Indexed successfully!")
    


# ================= REMOVE HANDLER ================= #

@Bot.on_callback_query(filters.regex(r"remove_"))
async def remove_channel(bot, query):

    user_id = query.from_user.id

    # ✅ ADMIN CHECK
    admins = await kingdb.get_all_admins()
    if user_id != OWNER_ID and user_id not in admins:
        return await query.answer("❌ Not allowed", show_alert=True)

    chat_id = int(query.data.split("_")[1])

    try:
        await kingdb.delete_channel(chat_id)
    except Exception as e:
        return await query.answer(f"DB Error: {e}", show_alert=True)

    await query.message.edit_text("❌ Channel removed from index")
