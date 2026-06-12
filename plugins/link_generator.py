from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from helper_func import encode, get_message_id, is_admin


@Bot.on_message(filters.command('batch') & filters.private & is_admin)
async def batch(client: Client, message: Message):
    channel = f"<a href={client.db_channel.invite_link}>ᴅʙ ᴄʜᴀɴɴᴇʟ</a>"
    bot_messages = []  # Store all bot messages for deletion
    
    try:
        # First message loop
        while True:
            try:
                first_message = await client.ask(
                    text=f"<b><blockquote>Fᴏʀᴡᴀʀᴅ ᴛʜᴇ Fɪʀsᴛ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel} (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n<blockquote>Oʀ Sᴇɴᴅ ᴛʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</blockquote>\n\n<blockquote>❌ /cancel ᴛᴏ ᴀʙᴏʀᴛ</blockquote></b>",
                    chat_id=message.from_user.id,
                    filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                    timeout=60,
                    disable_web_page_preview=True
                )
            except Exception as e:
                print(f"Error in first message ask: {e}")
                await delete_messages(client, message.from_user.id, bot_messages)
                return

            # ✅ Cancel check
            if first_message.text and first_message.text.strip().lower() == "/cancel":
                reply = await first_message.reply("<b>❌ ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
                bot_messages.append(reply.id)
                await delete_messages(client, message.from_user.id, bot_messages)
                return

            f_msg_id = await get_message_id(client, first_message)
            if f_msg_id:
                break
            else:
                reply = await first_message.reply(
                    f"<b>❌ Eʀʀᴏʀ..\n<blockquote>Tʜɪs Fᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ᴏʀ ᴍᴇssᴀɢᴇ ʟɪɴᴋ ɪs ɴᴏᴛ ғʀᴏᴍ ᴍʏ {channel}</blockquote></b>",
                    quote=True,
                    disable_web_page_preview=True
                )
                bot_messages.append(reply.id)
                continue

        # Second message loop
        while True:
            try:
                second_message = await client.ask(
                    text=f"<b><blockquote>Fᴏʀᴡᴀʀᴅ ᴛʜᴇ Lᴀsᴛ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel} (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n<blockquote>Oʀ Sᴇɴᴅ ᴛʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</blockquote>\n\n<blockquote>❌ /cancel ᴛᴏ ᴀʙᴏʀᴛ</blockquote></b>",
                    chat_id=message.from_user.id,
                    filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                    timeout=60,
                    disable_web_page_preview=True
                )
            except Exception as e:
                print(f"Error in second message ask: {e}")
                await delete_messages(client, message.from_user.id, bot_messages)
                return

            # ✅ Cancel check
            if second_message.text and second_message.text.strip().lower() == "/cancel":
                reply = await second_message.reply("<b>❌ ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
                bot_messages.append(reply.id)
                await delete_messages(client, message.from_user.id, bot_messages)
                return

            s_msg_id = await get_message_id(client, second_message)
            if s_msg_id:
                break
            else:
                reply = await second_message.reply(
                    f"<b>❌ Eʀʀᴏʀ..\n<blockquote>Tʜɪs Fᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ᴏʀ ᴍᴇssᴀɢᴇ ʟɪɴᴋ ɪs ɴᴏᴛ ғʀᴏᴍ ᴍʏ {channel}</blockquote></b>",
                    quote=True,
                    disable_web_page_preview=True
                )
                bot_messages.append(reply.id)
                continue

        # Generate link
        string = f"get-{f_msg_id * abs(client.db_channel.id)}-{s_msg_id * abs(client.db_channel.id)}"
        base64_string = await encode(string)
        link = f"https://t.me/{client.username}?start={base64_string}"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Sʜᴀʀᴇ URL", url=f'https://telegram.me/share/url?url={link}')]
        ])
        await second_message.reply_text(
            f"<b>Bᴇʟᴏᴡ ɪs ʏᴏᴜʀ ʟɪɴᴋ:</b>\n<blockquote>{link}</blockquote>",
            quote=True,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Unexpected error in batch command: {e}")
        await delete_messages(client, message.from_user.id, bot_messages)
        return


@Bot.on_message(filters.command('genlink') & filters.private & is_admin)
async def link_generator(client: Client, message: Message):
    channel = f"<a href={client.db_channel.invite_link}>ᴅʙ ᴄʜᴀɴɴᴇʟ</a>"
    bot_messages = []  # Store all bot messages for deletion
    
    try:
        while True:
            try:
                channel_message = await client.ask(
                    text=f"<b><blockquote>Fᴏʀᴡᴀʀᴅ ᴛʜᴇ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel} (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n<blockquote>Oʀ Sᴇɴᴅ ᴛʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</blockquote>\n\n<blockquote>❌ /cancel ᴛᴏ ᴀʙᴏʀᴛ</blockquote></b>",
                    chat_id=message.from_user.id,
                    filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                    timeout=60,
                    disable_web_page_preview=True
                )
            except Exception as e:
                print(f"Error in genlink ask: {e}")
                await delete_messages(client, message.from_user.id, bot_messages)
                return
            
            # ✅ Cancel check
            if channel_message.text and channel_message.text.strip().lower() == "/cancel":
                reply = await channel_message.reply("<b>❌ ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
                bot_messages.append(reply.id)
                await delete_messages(client, message.from_user.id, bot_messages)
                return
            
            msg_id = await get_message_id(client, channel_message)
            if msg_id:
                break
            else:
                reply = await channel_message.reply(
                    f"<b>❌ Eʀʀᴏʀ..\n<blockquote>Tʜɪs Fᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ᴏʀ ᴍᴇssᴀɢᴇ ʟɪɴᴋ ɪs ɴᴏᴛ ғʀᴏᴍ ᴍʏ {channel}</blockquote></b>",
                    quote=True,
                    disable_web_page_preview=True
                )
                bot_messages.append(reply.id)
                continue

        # Generate link
        base64_string = await encode(f"get-{msg_id * abs(client.db_channel.id)}")
        link = f"https://t.me/{client.username}?start={base64_string}"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Sʜᴀʀᴇ URL", url=f'https://telegram.me/share/url?url={link}')]
        ])
        await channel_message.reply_text(
            f"<b>Bᴇʟᴏᴡ ɪs ʏᴏᴜʀ ʟɪɴᴋ:</b>\n<blockquote>{link}</blockquote>",
            quote=True,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Unexpected error in genlink command: {e}")
        await delete_messages(client, message.from_user.id, bot_messages)
        return


async def delete_messages(client: Client, user_id: int, message_ids: list):
    """Delete all bot messages"""
    for msg_id in message_ids:
        try:
            await client.delete_messages(user_id, msg_id)
        except Exception as e:
            print(f"Error deleting message {msg_id}: {e}")
            continue
        
