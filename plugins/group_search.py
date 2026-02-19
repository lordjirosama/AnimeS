import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from database.database import kingdb
from config import PICS  

AUTO_DELETE_TIME = 300 # 5 Minutes

@Bot.on_message(filters.text & filters.group)
async def group_search_handler(client, message):
    chat_id = message.chat.id
    text = message.text.strip()

    if not await kingdb.is_group_approved(chat_id): return

    mode = await kingdb.get_search_mode(chat_id)
    query = ""
    if mode == "command":
        if text.lower().startswith("/search "):
            query = text.replace("/search ", "", 1).strip()
        else: return 
    elif mode == "auto":
        if text.startswith("/"): return 
        query = text
    
    if len(query) < 2: return 

    results = await kingdb.search_channels(query)
    
    if not results:
        if mode == "command":
            msg = await message.reply("❌ **Nᴏ Rᴇsᴜʟᴛs Fᴏᴜɴᴅ Fᴏʀ:** `{}`".format(query), quote=True)
            await asyncio.sleep(10)
            await msg.delete()
        return

    buttons = []
    for ch in results[:10]: 
        try:
            channel_id = ch["_id"]
            join_mode = ch.get("join_mode", "direct")
            expire_seconds = ch.get("expire_seconds", 0)
            title = ch.get("title", "Unknown Channel")
            
            # Expire time logic
            expire_date = None
            if expire_seconds > 0:
                expire_date = datetime.now() + timedelta(seconds=expire_seconds)

            if join_mode == "request":
                link = await client.create_chat_invite_link(channel_id, creates_join_request=True, expire_date=expire_date)
            else:
                link = await client.create_chat_invite_link(channel_id, expire_date=expire_date)

            buttons.append([InlineKeyboardButton(f"🎬 {title}", url=link.invite_link)])
            
        except Exception as e:
            continue

    if not buttons: return

    # --- ✨ NEW PREMIUM UI CAPTION ✨ ---
    caption = (
        "🍿 𝗦𝗲𝗮𝗿𝗰𝗵 𝗥𝗲𝘀𝘂𝗹𝘁𝘀 𝗙𝗼𝘂𝗻𝗱!\n\n"
        f"📝 Qᴜᴇʀʏ: `{query}`\n"
        f"📊 Rᴇsᴜʟᴛs: `{len(buttons)}` Lɪɴᴋ(s) Gᴇɴᴇʀᴀᴛᴇᴅ\n\n"
        "👇 Cʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ᴀᴄᴄᴇss:\n"
        f"⏳ Tʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ {AUTO_DELETE_TIME // 60} ᴍɪɴᴜᴛᴇs._"
    )

    sent = await message.reply_photo(
        photo=random.choice(PICS), 
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    # Auto Delete
    await asyncio.sleep(AUTO_DELETE_TIME)
    try:
        await sent.delete()
        await message.delete()
    except:
        pass
