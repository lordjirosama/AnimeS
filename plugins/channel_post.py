# +++ Channel Post Content Core Engine - Made By Obito +++

import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

from bot import Bot
from config import CHANNEL_ID
from helper_func import encode, is_admin

# ==================== 1. PM DIRECT REPLY GENERATOR ====================
@Bot.on_message(filters.command('genlink') & filters.private & is_admin)
async def channel_post(client: Client, message: Message):
    # Ensures it explicitly targets the message you are replying to inside PM
    if not message.reply_to_message:
        await message.reply_text(
            "❌ <b>Usage Format Error!</b>\n\n"
            "<blockquote>Please <b>reply to any file, photo, or message inside PM</b> with <code>/genlink</code> to generate its link.</blockquote>",
            quote=True
        )
        return

    target_msg = message.reply_to_message
    reply_text = await message.reply_text("<b><i>Pʀ6ᴄᴇssɪɴɢ....</i></b>", quote=True)
    
    try:
        post_message = await target_msg.copy(chat_id=client.db_channel.id, disable_notification=True)
    except FloodWait as e:
        await asyncio.sleep(e.x)
        post_message = await target_msg.copy(chat_id=client.db_channel.id, disable_notification=True)
    except Exception as e:
        print(e)
        await reply_text.edit_text("<b>S6ᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀ6ɴɢ..!</b>")
        return
        
    converted_id = post_message.id * abs(client.db_channel.id)
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Sʜᴀʀᴇ URL", url=f'https://telegram.me/share/url?url={link}')]])

    await reply_text.edit(f"<b>Bᴇʟᴏᴡ ɪs ʏᴏᴜʀ ʟɪɴᴋ::</b>\n<blockquote>{link}</blockquote>", reply_markup=reply_markup, disable_web_page_preview=True)


# ==================== 2. AUTO CHANNEL BUTTON POST INTELLIGENCE ====================
"""@Bot.on_message(filters.channel & filters.incoming & filters.chat(CHANNEL_ID))
async def new_post(client: Client, message: Message):

    if True:
        return

    converted_id = message.id * abs(client.db_channel.id)
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Sʜᴀʀᴇ URL", url=f'https://telegram.me/share/url?url={link}')]])
    try:
        await message.edit_reply_markup(reply_markup)
    except Exception as e:
        print(e)
        pass"""
        
