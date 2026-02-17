from bot import Bot
from pyrogram import filters
from pyrogram.types import ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
from database.database import kingdb
from config import OWNER_ID, LOG_CHANNEL
import datetime

# ================= AUTO INDEX (BOT ADD) ================= #

@Bot.on_chat_member_updated()
async def auto_index(client, event: ChatMemberUpdated):

    try:
        if not event.new_chat_member:
            return

        # bot check
        if event.new_chat_member.user.id != client.me.id:
            return

        chat = event.chat

        if chat.type not in ["channel", "supergroup"]:
            return

        user = event.from_user

        # allow only owner/admin
        admins = await kingdb.get_all_admins()
        if user.id != OWNER_ID and user.id not in admins:
            await client.leave_chat(chat.id)
            return

        await save_channel(client, chat, user.id)

    except Exception as e:
        print("AUTO INDEX ERROR:", e)


# ================= FORWARD INDEX ================= #

@Bot.on_message(filters.private & filters.forwarded)
async def forward_index(client, message):

    try:
        user_id = message.from_user.id

        admins = await kingdb.get_all_admins()
        if user_id != OWNER_ID and user_id not in admins:
            return

        chat = None

        # FIXED DETECTION 🔥
        if message.forward_from_chat:
            chat = message.forward_from_chat
        elif message.sender_chat:
            chat = message.sender_chat
        else:
            return await message.reply("❌ Channel/group se forward karo")

        await save_channel(client, chat, user_id)

        await message.reply("✅ Indexed successfully!")

    except Exception as e:
        await message.reply(f"❌ Error: {e}")


# ================= SAVE FUNCTION ================= #

async def save_channel(client, chat, user_id):

    await kingdb.add_or_update_channel(
        channel_id=chat.id,
        title=chat.title or "Unknown",
        username=chat.username,
        is_private=chat.username is None,
        join_mode="direct",
        expire_seconds=600,
        added_by=user_id
    )

    log_text = f"""
✅ **NEW INDEX**

👤 User: `{user_id}`
📛 Title: {chat.title}
🆔 `{chat.id}`
🔗 @{chat.username if chat.username else 'Private'}
⏰ {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}
"""

    await client.send_message(
        LOG_CHANNEL,
        log_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Remove", callback_data=f"remove_{chat.id}")]
        ])
    )


# ================= REMOVE ================= #

@Bot.on_callback_query(filters.regex(r"remove_"))
async def remove_channel(client, query):

    user_id = query.from_user.id
    admins = await kingdb.get_all_admins()

    if user_id != OWNER_ID and user_id not in admins:
        return await query.answer("❌ Not allowed", show_alert=True)

    chat_id = int(query.data.split("_")[1])

    await kingdb.delete_channel(chat_id)

    await query.message.edit_text("❌ Removed from DB")
