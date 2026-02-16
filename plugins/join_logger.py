from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

from config import LOG_CHANNEL, OWNER_ID

# ===== SIMPLE MEMORY DB =====
approved_chats = set()


async def approve_group(chat_id):
    approved_chats.add(chat_id)


async def disapprove_group(chat_id):
    approved_chats.discard(chat_id)


async def is_group_approved(chat_id):
    return chat_id in approved_chats


# ===== BOT START LOG =====
@Client.on_message(filters.command("alive") & filters.user(OWNER_ID))
async def alive_log(client, message):
    await client.send_message(
        LOG_CHANNEL,
        f"🚀 **BOT STARTED**\n\n👤 Owner: `{OWNER_ID}`\n⏰ {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
    )
    await message.reply("✅ Logged in log channel")


# ===== BOT JOIN / LEAVE LOGGER =====
@Client.on_chat_member_updated()
async def join_logger(client, member):

    if not member.new_chat_member:
        return

    if member.new_chat_member.user.is_self:

        chat = member.chat
        user = member.from_user

        # ===== BOT ADDED =====
        if member.new_chat_member.status in ["administrator", "member"]:

            await approve_group(chat.id)

            text = f"""
✅ **BOT ADDED & APPROVED**

👤 **Added By:** {user.first_name}
🆔 **User ID:** `{user.id}`
🔗 **Username:** @{user.username if user.username else 'N/A'}

📢 **Chat Name:** {chat.title}
🆔 **Chat ID:** `{chat.id}`

⚙️ **Status:** APPROVED ✅
⏰ **Time:** {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
"""

            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ REMOVE FROM INDEX", callback_data=f"remove_{chat.id}")]
            ])

            await client.send_message(LOG_CHANNEL, text, reply_markup=btn)

        # ===== BOT REMOVED =====
        elif member.new_chat_member.status in ["kicked", "left"]:

            await disapprove_group(chat.id)

            text = f"""
❌ **BOT REMOVED**

📢 **Chat Name:** {chat.title}
🆔 **Chat ID:** `{chat.id}`

⚙️ **Status:** DISAPPROVED ❌
⏰ **Time:** {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
"""

            await client.send_message(LOG_CHANNEL, text)


# ===== CALLBACK HANDLER (SAME FILE) =====
@Client.on_callback_query(filters.regex("remove_"))
async def remove_callback(client, query):

    chat_id = int(query.data.split("_")[1])

    await disapprove_group(chat_id)

    await query.message.edit_text(
        f"""
❌ **REMOVED FROM INDEX**

🆔 Chat ID: `{chat_id}`

⚙️ Status: DISAPPROVED
⏰ {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
"""
    )

    await query.answer("Removed from index ✅", show_alert=True)
