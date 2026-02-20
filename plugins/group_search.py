import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from database.database import kingdb
from config import PICS  
from .anilist import AniLister # Import your class here

AUTO_DELETE_TIME = 300 # 5 Minutes

async def fetch_anilist_data(query):
    try:
        anilister = AniLister(query, datetime.now().year)
        data = await anilister.get_anidata()
        return data
    except Exception:
        return {}

@Bot.on_message(filters.text & filters.group, group=-1)
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

    # ✈️ AEROPLANE SPEED
    db_task = asyncio.create_task(kingdb.search_channels(query))
    ani_task = asyncio.create_task(fetch_anilist_data(query))
    
    results, ani_data = await asyncio.gather(db_task, ani_task)
    
    if not results:
        if mode == "command":
            msg = await message.reply(f"❌ **No Results Found For:** `{query}`", quote=True)
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
            
            expire_date = datetime.now() + timedelta(seconds=expire_seconds) if expire_seconds > 0 else None

            if join_mode == "request":
                link = await client.create_chat_invite_link(channel_id, creates_join_request=True, expire_date=expire_date)
            else:
                link = await client.create_chat_invite_link(channel_id, expire_date=expire_date)

            buttons.append([InlineKeyboardButton(f"🎬 {title}", url=link.invite_link)])
        except Exception:
            continue

    if not buttons: return

    # --- PREMIUM UI BUILDER ---
    if ani_data:
        title = ani_data.get('title', {}).get('english') or ani_data.get('title', {}).get('romaji') or query.title()
        ani_type = ani_data.get('format', 'Unknown')
        status = ani_data.get('status', 'Unknown')
        episodes = ani_data.get('episodes', 'N/A')
        year = ani_data.get('seasonYear', 'N/A')
        genres = ", ".join(ani_data.get('genres', [])[:3]) if ani_data.get('genres') else "N/A"
        
        synopsis = str(ani_data.get('description', 'No synopsis available.'))
        synopsis = synopsis.replace("<br>", "").replace("<i>", "").replace("</i>", "")
        if len(synopsis) > 200:
            synopsis = synopsis[:200] + "..."

        ani_id = ani_data.get('id')
        poster = f"https://img.anili.st/media/{ani_id}" if ani_id else random.choice(PICS)

        caption = (
            f"<blockquote>**{title}**</blockquote>\n\n"
            f"✦ **Type:** {ani_type}   |   **Status:** {status}\n"
            f"✦ **Episodes:** {episodes}   |   **Year:** {year}\n"
            f"✦ **Genres:** {genres}\n"
            f"✦ **Synopsis:** {synopsis}\n\n"
            "👇 **Please click the buttons below to access your files:**\n"
            f"⏳ _This message will be deleted in {AUTO_DELETE_TIME // 60} minutes._"
        )
    else:
        poster = random.choice(PICS)
        caption = (
            f"<blockquote>**{query.title()}**</blockquote>\n\n"
            "✦ **Status:** Found in Database ✅\n"
            f"✦ **Results:** `{len(buttons)}` Links Generated\n\n"
            "👇 **Please click the buttons below to access your files:**\n"
            f"⏳ _This message will be deleted in {AUTO_DELETE_TIME // 60} minutes._"
        )

    sent = await message.reply_photo(
        photo=poster, 
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    await asyncio.sleep(AUTO_DELETE_TIME)
    try:
        await sent.delete()
        await message.delete()
    except:
        pass
