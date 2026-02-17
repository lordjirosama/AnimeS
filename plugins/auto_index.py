from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from database.database import kingdb
from config import OWNER_ID, LOG_CHANNEL
from datetime import datetime


# ================= INDEX COMMAND ================= #

@Bot.on_message(filters.command("index") & filters.private)
async def index_cmd(client, message):

    user_id = message.from_user.id
    admins = await kingdb.get_all_admins()

    if user_id != OWNER_ID and user_id not in admins:
        return await message.reply("❌ You are not allowed")

    await message.reply(
        "📥 Forward channel post to index\n⚠️ Bot must be admin"
    )


# ================= FORWARD INDEX ================= #

@Bot.on_message(filters.private & filters.forwarded)
async def index_forward(client, message):

    user_id = message.from_user.id
    admins = await kingdb.get_all_admins()

    if user_id != OWNER_ID and user_id not in admins:
        return

    if not message.sender_chat:
        return await message.reply("❌ Forward from channel only")

    chat = message.sender_chat

    if chat.type != "channel":
        return await message.reply("❌ Only channel allowed")

    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    # ================= SAVE ================= #
    await kingdb.add_or_update_channel(
        channel_id=chat.id,
        title=chat.title,
        username=chat.username,
        join_mode="direct",
        expire_seconds=600
    )

    await kingdb.update_channel(chat.id, {
        "chat_id": chat.id,
        "title": chat.title,
        "username": chat.username,
        "is_private": chat.username is None,
        "added_by": user_id,
        "added_time": now
    })

    # ================= INLINE BUTTON ================= #
    buttons = [
        [InlineKeyboardButton("🗑 Remove Channel", callback_data=f"remove_{chat.id}")]
    ]

    # ================= LOG CHANNEL ================= #
    await client.send_message(
        LOG_CHANNEL,
        f"📥 **NEW CHANNEL INDEXED**\n\n"
        f"📺 **Name:** {chat.title}\n"
        f"🆔 **ID:** `{chat.id}`\n"
        f"👤 **Added By:** `{user_id}`\n"
        f"⏰ **Time:** {now}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    # OPTIONAL reply
    await message.reply("✅ Channel Indexed & Logged")


# ================= REMOVE CALLBACK ================= #

@Bot.on_callback_query(filters.regex("^remove_"))
async def remove_channel_callback(client, query):

    user_id = query.from_user.id
    admins = await kingdb.get_all_admins()

    if user_id != OWNER_ID and user_id not in admins:
        return await query.answer("❌ Not allowed", show_alert=True)

    chat_id = int(query.data.split("_")[1])

    await kingdb.del_channel(chat_id)

    await query.message.edit_text(
        f"🗑 Channel Removed\n🆔 `{chat_id}`"
    )
