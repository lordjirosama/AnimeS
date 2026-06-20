# +++ Made By Obito [@i_killed_my_clan] +++
import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

from bot import Bot
from config import CHANNEL_ID
from helper_func import encode, is_admin

# FIXED: Ab ye handler tabhi chalega jab explicitly /genlink command bhejoge aur admin hoga. No more auto-generation.
@Bot.on_message(filters.command('genlink') & filters.private & is_admin)
async def channel_post(client: Client, message: Message):
    # Agar reply nahi kiya hai aur direct message hai, toh target isi message ko banao, nahi toh replied message ko copy karo
    target_msg = message.reply_to_message if message.reply_to_message else message
    
    # Agar target message khud command hai aur koi content nahi hai, toh guide karo
    if target_msg == message and len(message.command) == 1 and not message.media:
        await message.reply_text(
            "❌ <b>Usage Format Error!</b>\n\n"
            "<blockquote>Reply to any file/message with <code>/genlink</code>, or send the file directly along with the caption <code>/genlink</code>.</blockquote>",
            quote=True
        )
        return
        
    reply_text = await message.reply_text("<b><i>Pʀᴏᴄᴇssɪɴɢ....</i></b>", quote=True)
    try:
        post_message = await target_msg.copy(chat_id=client.db_channel.id, disable_notification=True)
    except FloodWait as e:
        await asyncio.sleep(e.x)
        post_message = await target_msg.copy(chat_id=client.db_channel.id, disable_notification=True)
    except Exception as e:
        print(e)
        await reply_text.edit_text("<b>Sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ..!</b>")
        return
        
    converted_id = post_message.id * abs(client.db_channel.id)
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Sʜᴀʀᴇ URL", url=f'https://telegram.me/share/url?url={link}')]])

    await reply_text.edit(f"<b>Bᴇʟ6ᴡ ɪs ʏ6ᴜʀ ʟɪɴᴋ::</b>\n<blockquote>{link}</blockquote>", reply_markup=reply_markup, disable_web_page_preview=True)


"""@Bot.on_message(filters.channel & filters.incoming & filters.chat(CHANNEL_ID))
async def new_post(client: Client, message: Message):

    if True:
        return

    converted_id = message.id * abs(client.db_channel.id)
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    try:
        await message.edit_reply_markup(reply_markup)
    except Exception as e:
        print(e)
        pass"""
