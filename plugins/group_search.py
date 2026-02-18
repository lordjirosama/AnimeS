import asyncio
import random
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from database.database import kingdb
from config import PICS  # <--- Config se import kiya

# Auto Delete Time (Seconds)
AUTO_DELETE_TIME = 300 

@Bot.on_message(filters.text & filters.group)
async def group_search_handler(client, message):
    chat_id = message.chat.id
    text = message.text.strip()

    # 1. Check Group Approval
    if not await kingdb.is_group_approved(chat_id):
        return

    # 2. Check Search Mode
    mode = await kingdb.get_search_mode(chat_id)
    
    query = ""
    if mode == "command":
        if text.lower().startswith("/search "):
            query = text.replace("/search ", "", 1).strip()
        else:
            return 
    elif mode == "auto":
        if text.startswith("/"): return 
        query = text
    
    if len(query) < 2: return 

    # 3. Search Database
    results = await kingdb.search_channels(query)
    
    if not results:
        if mode == "command":
            msg = await message.reply("❌ **No Results Found.**", quote=True)
            await asyncio.sleep(10)
            await msg.delete()
        return

    # 4. Generate Buttons
    buttons = []
    for ch in results[:10]: 
        try:
            channel_id = ch["_id"]
            join_mode = ch.get("join_mode", "direct")
            title = ch.get("title", "Unknown Channel")
            
            if join_mode == "request":
                link = await client.create_chat_invite_link(channel_id, creates_join_request=True)
            else:
                link = await client.create_chat_invite_link(channel_id, member_limit=1)

            buttons.append([InlineKeyboardButton(f"🎬 {title}", url=link.invite_link)])
            
        except Exception as e:
            continue

    if not buttons: return

    # 5. Send Result (Random Pic from Config)
    sent = await message.reply_photo(
        photo=random.choice(PICS),  # <--- Random Pic Yahan
        caption=f"🔍 **Your Results for:** `{query}`\n\n👇 **Click below to watch/download:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    # 6. Auto Delete
    await asyncio.sleep(AUTO_DELETE_TIME)
    try:
        await sent.delete()
        await message.delete()
    except:
        pass
