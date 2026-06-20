# +++ Made By Obito [@i_killed_my_clan] +++
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from helper_func import encode, get_message_id, is_admin

batch_sessions = {}


@Bot.on_message(filters.command('batch') & filters.private & is_admin)
async def batch(client: Client, message: Message):
    user_id = message.from_user.id
    batch_sessions[user_id] = True
    
    channel = f"<a href={client.db_channel.invite_link}>ᴅʙ ᴄʜᴀɴɴᴇʟ</a>"
    
    # ✅ First Message
    while True:
        if user_id not in batch_sessions:
            return
            
        try:
            first_message = await client.ask(
                chat_id=user_id,
                text=f"<b><blockquote>Fᴏʀᴡᴀʀᴅ ᴛʜᴇ Fɪʀsᴛ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel} (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n<blockquote>Oʀ Sᴇɴᴅ ᴛʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</blockquote></b>",
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=120,
                disable_web_page_preview=True
            )
        except Exception as e:
            batch_sessions.pop(user_id, None)
            return
        
        f_msg_id = await get_message_id(client, first_message)
        
        if f_msg_id:
            break
        else:
            try:
                await first_message.reply(
                    f"<b>❌ Eʀʀᴏʀ..\n<blockquote>Tʜɪs ɪs ɴᴏᴛ ғʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ!</blockquote></b>",
                    quote=True,
                    disable_web_page_preview=True
                )
            except:
                pass
            continue

    # ✅ Second Message
    while True:
        if user_id not in batch_sessions:
            return
            
        try:
            second_message = await client.ask(
                chat_id=user_id,
                text=f"<b><blockquote>Fᴏʀᴡᴀʀᴅ ᴛʜᴇ Lᴀsᴛ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel} (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n<blockquote>Oʀ Sᴇɴᴅ ᴛʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</blockquote></b>",
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=120,
                disable_web_page_preview=True
            )
        except Exception as e:
            batch_sessions.pop(user_id, None)
            return
        
        s_msg_id = await get_message_id(client, second_message)
        
        if s_msg_id:
            break
        else:
            try:
                await second_message.reply(
                    f"<b>❌ Eʀʀᴏʀ..\n<blockquote>Tʜɪs ɪs ɴᴏᴛ ғʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ!</blockquote></b>",
                    quote=True,
                    disable_web_page_preview=True
                )
            except:
                pass
            continue

    # ✅ Generate Link
    try:
        string = f"get-{f_msg_id * abs(client.db_channel.id)}-{s_msg_id * abs(client.db_channel.id)}"
        base64_string = await encode(string)
        link = f"https://t.me/{client.username}?start={base64_string}"
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Sʜᴀʀᴇ URL", url=f'https://telegram.me/share/url?url={link}')]
        ])
        
        await client.send_message(
            chat_id=user_id,
            text=f"<b>✅ Lɪɴᴋ Gᴇɴᴇʀᴀᴛᴇded:</b>\n<blockquote>{link}</blockquote>",
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    except Exception as e:
        await client.send_message(
            chat_id=user_id,
            text=f"<b>❌ Eʀʀᴏʀ generating link!</b>",
            disable_web_page_preview=True
        )
    finally:
        batch_sessions.pop(user_id, None)


@Bot.on_message(filters.command('cancel') & filters.private)
async def cancel_batch(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id in batch_sessions:
        batch_sessions.pop(user_id)
        await message.reply_text(
            f"<b>✅ Oᴘᴇʀᴀᴛɪ6ɴ Cᴀɴᴄᴇʟᴇᴅ</b>\n<blockquote>Bᴀᴛᴄʜ ᴏᴘᴇʀᴀᴛɪᴏɴ ᴄᴀɴᴄᴇʟᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ.</blockquote>",
            disable_web_page_preview=True
        )
    else:
        await message.reply_text(
            f"<b>❌ Nᴏ Aᴄᴛɪᴠᴇ Sᴇssɪᴏɴ</b>\n<blockquote>Yᴏᴜ dᴏɴ'ᴛ have any active batch operation.</blockquote>",
            disable_web_page_preview=True
        )


@Bot.on_message(filters.command('genlink') & filters.private & is_admin)
async def link_generator(client: Client, message: Message):
    user_id = message.from_user.id
    batch_sessions[user_id] = True
    
    channel = f"<a href={client.db_channel.invite_link}>ᴅʙ ᴄʜᴀɴɴᴇʟ</a>"
    
    while True:
        if user_id not in batch_sessions:
            return
            
        try:
            channel_message = await client.ask(
                chat_id=user_id,
                text=f"<b><blockquote>F6ʀᴡ6ʀᴅ ᴛʜᴇ Mᴇss6ɢᴇ ғʀ6ᴍ {channel} (ᴡɪᴛʜ ǫᴜ6ᴛᴇs)..</blockquote>\n<blockquote>Oʀ Sᴇɴᴅ ᴛʜᴇ {channel} P6sᴛ Lɪɴᴋ</blockquote></b>",
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=120,
                disable_web_page_preview=True
            )
        except Exception as e:
            batch_sessions.pop(user_id, None)
            return
        
        msg_id = await get_message_id(client, channel_message)
        
        if msg_id:
            break
        else:
            try:
                await channel_message.reply(
                    f"<b>❌ Eʀʀᴏʀ..\n<blockquote>Tʜɪs ɪs ɴ6ᴛ ғʀ6ᴍ ᴅʙ ᴄʜ6ɴɴᴇʟ!</blockquote></b>",
                    quote=True,
                    disable_web_page_preview=True
                )
            except:
                pass
            continue

    # ✅ Generate Link
    try:
        base64_string = await encode(f"get-{msg_id * abs(client.db_channel.id)}")
        link = f"https://t.me/{client.username}?start={base64_string}"
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Sʜᴀʀᴇ URL", url=f'https://telegram.me/share/url?url={link}')]
        ])
        
        await client.send_message(
            chat_id=user_id,
            text=f"<b>✅ Lɪɴᴋ Gᴇɴᴇʀ6ᴛᴇᴅ:</b>\n<blockquote>{link}</blockquote>",
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    except Exception as e:
        await client.send_message(
            chat_id=user_id,
            text=f"<b>❌ Eʀʀᴏʀ generating link!</b>",
            disable_web_page_preview=True
        )
    finally:
        batch_sessions.pop(user_id, None)
        
