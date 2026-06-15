from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from helper_func import encode, get_message_id, is_admin

# Session tracking ke liye dictionary
batch_sessions = {}


@Bot.on_message(filters.command('batch') & filters.private & is_admin)
async def batch(client: Client, message: Message):
    user_id = message.from_user.id
    batch_sessions[user_id] = True  # ✅ Session start
    
    channel = f"<a href={client.db_channel.invite_link}>ᴅʙ ᴄʜᴀɴɴᴇʟ</a>" 
    while True:
        try:
            first_message = await client.ask(text=f"<b><blockquote>Fᴏʀᴡᴀʀᴅ ᴛʜᴇ Fɪʀsᴛ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel} (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n<blockquote>Oʀ Sᴇɴᴅ ᴛʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</blockquote></b>", chat_id = message.from_user.id, filters=(filters.forwarded | (filters.text & ~filters.forwarded)), timeout=60, disable_web_page_preview=True)
        except:
            batch_sessions.pop(user_id, None)  # ✅ Session cleanup
            return
        
        # ✅ Check if user cancelled
        if user_id not in batch_sessions:
            return
            
        f_msg_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        else:
            await first_message.reply(f"<b>❌ Eʀʀᴏʀ..\n<blockquote>Tʜɪs Fᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ᴏʀ ᴍᴇssᴀɢᴇ ʟɪɴᴋ ɪs ɴᴏᴛ ғʀᴏᴍ ᴍʏ {channel}</blockquote></b>", quote = True, disable_web_page_preview=True)
            continue

    while True:
        try:
            second_message = await client.ask(text =f"<b><blockquote>Fᴏʀᴡᴀʀᴅ ᴛʜᴇ Lᴀsᴛ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel} (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n<blockquote>Oʀ Sᴇɴᴅ ᴛʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</blockquote></b>", chat_id = message.from_user.id, filters=(filters.forwarded | (filters.text & ~filters.forwarded)), timeout=60, disable_web_page_preview=True)
        except:
            batch_sessions.pop(user_id, None)  # ✅ Session cleanup
            return
        
        # ✅ Check if user cancelled
        if user_id not in batch_sessions:
            return
            
        s_msg_id = await get_message_id(client, second_message)
        if s_msg_id:
            break
        else:
            await second_message.reply(f"<b>❌ Eʀʀᴏʀ..\n<blockquote>Tʜɪs Fᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ᴏʀ ᴍᴇssᴀɢᴇ ʟɪɴᴋ ɪs ɴᴏᴛ ғʀᴏᴍ ᴍʏ {channel}</blockquote></b>", quote=True, disable_web_page_preview=True)
            continue

    string = f"get-{f_msg_id * abs(client.db_channel.id)}-{s_msg_id * abs(client.db_channel.id)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Sʜᴀʀᴇ URL", url=f'https://telegram.me/share/url?url={link}')]])
    await second_message.reply_text(f"<b>Bᴇʟᴏᴡ ɪs ʏᴏᴜʀ ʟɪɴᴋ:</b>\n<blockquote>{link}</blockquote>", quote=True, reply_markup=reply_markup, disable_web_page_preview=True)
    
    batch_sessions.pop(user_id, None)  # ✅ Session cleanup


@Bot.on_message(filters.command('cancel') & filters.private)
async def cancel_batch(client: Client, message: Message):
    user_id = message.from_user.id
    
    # ✅ Check if user has active batch session
    if user_id in batch_sessions:
        batch_sessions.pop(user_id)
        await message.reply_text(
            f"<b>✅ Bᴀᴛᴄʜ Cᴀɴᴄᴇʟᴇᴅ</b>\n"
            f"<blockquote>Yᴏᴜʀ /batch operation has been cancelled.</blockquote>",
            disable_web_page_preview=True
        )
    else:
        await message.reply_text(
            f"<b>❌ Nᴏ Aᴄᴛɪᴠᴇ Bᴀᴛᴄʜ</b>\n"
            f"<blockquote>Yᴏᴜ dᴏɴ'ᴛ have any active /batch operation.</blockquote>",
            disable_web_page_preview=True
        )


@Bot.on_message(filters.command('genlink') & filters.private & is_admin)
async def link_generator(client: Client, message: Message):
    user_id = message.from_user.id
    batch_sessions[user_id] = True  # ✅ Session start
    
    channel = f"<a href={client.db_channel.invite_link}>ᴅʙ ᴄʜᴀɴɴᴇʟ</a>"
    while True:
        try:
            channel_message = await client.ask(text =f"<b><blockquote>Fᴏʀᴡᴀʀᴅ ᴛʜᴇ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel} (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n<blockquote>Oʀ Sᴇɴᴅ ᴛʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</blockquote></b>", chat_id = message.from_user.id, filters=(filters.forwarded | (filters.text & ~filters.forwarded)), timeout=60, disable_web_page_preview=True)
        except:
            batch_sessions.pop(user_id, None)  # ✅ Session cleanup
            return
        
        # ✅ Check if user cancelled
        if user_id not in batch_sessions:
            return
            
        msg_id = await get_message_id(client, channel_message)
        if msg_id:
            break
        else:
            await channel_message.reply(f"<b>❌ Eʀʀᴏʀ..\n<blockquote>Tʜɪs Fᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ᴏʀ ᴍᴇssᴀɢᴇ ʟɪɴᴋ ɪs ɴᴏᴛ ғʀᴏᴍ ᴍʏ {channel}</blockquote></b>", quote=True, disable_web_page_preview=True)
            continue

    base64_string = await encode(f"get-{msg_id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Sʜᴀʀᴇ URL", url=f'https://telegram.me/share/url?url={link}')]])
    await channel_message.reply_text(f"<b>Bᴇʟᴏᴡ ɪs ʏᴏᴜʀ ʟɪɴᴋ:</b>\n<blockquote>{link}</blockquote>", quote=True, reply_markup=reply_markup, disable_web_page_preview=True)
    
    batch_sessions.pop(user_id, None)  # ✅ Session cleanup
