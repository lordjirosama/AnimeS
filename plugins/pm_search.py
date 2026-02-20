import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from database.database import kingdb
from config import OWNER_ID, PICS  
from .anilist import AniLister # Import your class here

async def is_admin(user_id):
    admins = await kingdb.get_all_admins()
    return user_id == OWNER_ID or user_id in admins

async def fetch_anilist_data(query):
    try:
        # Using your AniLister class to fetch data
        anilister = AniLister(query, datetime.now().year)
        data = await anilister.get_anidata()
        return data
    except Exception:
        return {}

async def perform_search(client, message, query):
    
    # ✈️ AEROPLANE SPEED: Search DB and Anilist at the exact same time!
    db_task = asyncio.create_task(kingdb.search_channels(query))
    ani_task = asyncio.create_task(fetch_anilist_data(query))
    
    results, ani_data = await asyncio.gather(db_task, ani_task)

    if not results:
        return await message.reply(f"❌ **No Results Found For:** `{query}`")

    # --- BUTTONS GENERATOR ---
    buttons = []
    for ch in results[:10]: 
        try:
            channel_id = ch["_id"]
            join_mode = ch.get("join_mode", "direct")
            expire_seconds = ch.get("expire_seconds", 0)
            title = ch.get("title", "Unknown")

            expire_date = datetime.now() + timedelta(seconds=expire_seconds) if expire_seconds > 0 else None

            if join_mode == "request":
                link = await client.create_chat_invite_link(channel_id, creates_join_request=True, expire_date=expire_date)
            else:
                link = await client.create_chat_invite_link(channel_id, expire_date=expire_date)

            buttons.append([InlineKeyboardButton(f"🎬 {title}", url=link.invite_link)])
        except Exception:
            continue

    if not buttons:
        return await message.reply("❌ Failed to generate links. Please check bot permissions.")

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

        # Fetching poster using your ID logic
        ani_id = ani_data.get('id')
        poster = f"https://img.anili.st/media/{ani_id}" if ani_id else random.choice(PICS)

        caption = (
            f"<blockquote>**{title}**</blockquote>\n\n"
            f"✦ **Type:** {ani_type}   |   **Status:** {status}\n"
            f"✦ **Episodes:** {episodes}   |   **Year:** {year}\n"
            f"✦ **Genres:** {genres}\n"
            f"✦ **Synopsis:** {synopsis}\n\n"
            "👇 **Please click the buttons below to access your files:**"
        )
    else:
        poster = random.choice(PICS)
        caption = (
            f"<blockquote>**{query.title()}**</blockquote>\n\n"
            "✦ **Status:** Found in Database ✅\n"
            f"✦ **Results:** `{len(buttons)}` Links Generated\n\n"
            "👇 **Please click the buttons below to access your files:**"
        )

    await message.reply_photo(
        photo=poster, 
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Bot.on_message(filters.command("search") & filters.private, group=-1)
async def admin_pm_search(client, message):
    if not await is_admin(message.from_user.id): return 
    if len(message.command) < 2:
        return await message.reply("ℹ️ **Usage:** `/search <movie_name>`")
        
    query = message.text.split(" ", 1)[1].strip()
    await perform_search(client, message, query)
    message.stop_propagation()

@Bot.on_message(filters.text & filters.private & ~filters.regex(r"^/"), group=-1)
async def normal_user_auto_search(client, message):
    if await is_admin(message.from_user.id): return
    query = message.text.strip()
    if len(query) < 2: return
        
    await perform_search(client, message, query)
    message.stop_propagation()
