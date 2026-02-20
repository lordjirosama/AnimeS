
import random
import asyncio
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from database.database import kingdb
from config import PICS  

AUTO_DELETE_TIME = 300 # 5 Minutes

async def ask_search_type_group(message, query):
    buttons = [
        [InlineKeyboardButton("🎬 Search Anime", callback_data=f"typ_anime_{query[:30]}"),
         InlineKeyboardButton("📖 Search Manga/Manhwa", callback_data=f"typ_manga_{query[:30]}")]
    ]
    caption = (
        f"🔍 **Search Request:** `{query}`\n\n"
        "👇 **What are you looking for? Select a category:**\n"
        f"⏳ _This message will be deleted in {AUTO_DELETE_TIME // 60} minutes._"
    )
    sent = await message.reply_photo(photo=random.choice(PICS), caption=caption, reply_markup=InlineKeyboardMarkup(buttons))
    await asyncio.sleep(AUTO_DELETE_TIME)
    try: await sent.delete() 
    except: pass

async def perform_search_list_group(message, query, req_type):
    results = await kingdb.search_channels(query)
    filtered = [ch for ch in results if ch.get("ani_type", "anime").lower() == req_type.lower()]

    if not filtered:
        msg = await message.reply(f"❌ **No {req_type.capitalize()} Results Found For:** `{query}`")
        await asyncio.sleep(10)
        try: await msg.delete()
        except: pass
        return

    buttons = [[InlineKeyboardButton(ch.get("title", "Unknown"), callback_data=f"show_ch_{ch['_id']}_{req_type}")] for ch in filtered[:10]]
    caption = (
        f"🔍 **{req_type.capitalize()} Search results for:** `{query}`\n\n"
        "👇 **Please select an option below:**\n"
        f"⏳ _This message will be deleted in {AUTO_DELETE_TIME // 60} minutes._"
    )
    
    sent = await message.reply_photo(photo=random.choice(PICS), caption=caption, reply_markup=InlineKeyboardMarkup(buttons))
    await asyncio.sleep(AUTO_DELETE_TIME)
    try: await sent.delete()
    except: pass

@Bot.on_message(filters.text & filters.group, group=-1)
async def group_search_handler(client, message):
    chat_id = message.chat.id
    text = message.text.strip()

    if not await kingdb.is_group_approved(chat_id): return

    mode = await kingdb.get_search_mode(chat_id)
    
    # Check direct commands first
    if text.lower().startswith("/anime "):
        return await perform_search_list_group(message, text.replace("/anime ", "", 1).strip(), "anime")
    if text.lower().startswith("/manga "):
        return await perform_search_list_group(message, text.replace("/manga ", "", 1).strip(), "manga")

    query = ""
    if mode == "command":
        if text.lower().startswith("/search "): query = text.replace("/search ", "", 1).strip()
        else: return 
    elif mode == "auto":
        if text.startswith("/"): return 
        query = text
    
    if len(query) < 2: return 
    
    # General Search opens selection
    await ask_search_type_group(message, query)
