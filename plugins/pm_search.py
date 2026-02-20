import random
import asyncio
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from bot import Bot
from database.database import kingdb
from config import OWNER_ID, PICS  
from anilist import AniLister 

async def is_admin(user_id):
    admins = await kingdb.get_all_admins()
    return user_id == OWNER_ID or user_id in admins

async def fetch_anilist_data(query, req_type):
    try:
        anilister = AniLister(query, datetime.now().year, req_type.upper())
        return await anilister.get_anidata()
    except Exception: return {}

# --- CATEGORY SELECTION ---
async def ask_search_type(client, message, query):
    buttons = [
        [InlineKeyboardButton("🎬 Search Anime", callback_data=f"typ_anime_{query[:30]}"),
         InlineKeyboardButton("📖 Search Manga/Manhwa", callback_data=f"typ_manga_{query[:30]}")]
    ]
    caption = f"🔍 **Search Request:** `{query}`\n\n👇 **What are you looking for? Select a category:**"
    await message.reply_photo(photo=random.choice(PICS), caption=caption, reply_markup=InlineKeyboardMarkup(buttons))

# --- GENERATE LIST FROM DB ---
async def perform_search_list(client, message, query, req_type):
    results = await kingdb.search_channels(query)
    filtered = [ch for ch in results if ch.get("ani_type", "anime").lower() == req_type.lower()]

    if not filtered:
        return await message.reply(f"❌ **No {req_type.capitalize()} Results Found For:** `{query}`")

    buttons = [[InlineKeyboardButton(ch.get("title", "Unknown"), callback_data=f"show_ch_{ch['_id']}_{req_type}")] for ch in filtered[:10]]
    caption = f"🔍 **{req_type.capitalize()} Search results for:** `{query}`\n\n👇 **Please select an option below:**"
    
    if hasattr(message, "edit_media"):
        await message.edit_media(media=InputMediaPhoto(media=random.choice(PICS), caption=caption), reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply_photo(photo=random.choice(PICS), caption=caption, reply_markup=InlineKeyboardMarkup(buttons))

# --- COMMANDS ---
@Bot.on_message(filters.command("anime") & filters.private, group=-1)
async def pm_anime_cmd(client, message):
    if len(message.command) < 2: return await message.reply("ℹ️ **Usage:** `/anime <name>`")
    await perform_search_list(client, message, message.text.split(" ", 1)[1].strip(), "anime")
    message.stop_propagation()

@Bot.on_message(filters.command("manga") & filters.private, group=-1)
async def pm_manga_cmd(client, message):
    if len(message.command) < 2: return await message.reply("ℹ️ **Usage:** `/manga <name>`")
    await perform_search_list(client, message, message.text.split(" ", 1)[1].strip(), "manga")
    message.stop_propagation()

@Bot.on_message(filters.command("search") & filters.private, group=-1)
async def admin_pm_search(client, message):
    if not await is_admin(message.from_user.id): return 
    if len(message.command) < 2: return await message.reply("ℹ️ **Usage:** `/search <name>`")
    await ask_search_type(client, message, message.text.split(" ", 1)[1].strip())
    message.stop_propagation()

@Bot.on_message(filters.text & filters.private & ~filters.regex(r"^/"), group=-1)
async def normal_user_auto_search(client, message):
    if await is_admin(message.from_user.id): return
    if len(message.text.strip()) < 2: return
    await ask_search_type(client, message, message.text.strip())
    message.stop_propagation()

# --- CALLBACK ROUTERS ---
@Bot.on_callback_query(filters.regex(r"^typ_(anime|manga)_(.*)$"), group=-1)
async def type_selected_cb(client, query):
    req_type = query.matches[0].group(1)
    search_query = query.matches[0].group(2)
    await query.answer("Searching Database... ⏳")
    await perform_search_list(client, query.message, search_query, req_type)

@Bot.on_callback_query(filters.regex(r"^show_ch_(-?\d+)_(anime|manga)$"), group=-1)
async def show_channel_details(client, query):
    try:
        ch_id = int(query.matches[0].group(1))
        req_type = query.matches[0].group(2)
        ch = await kingdb.get_channel(ch_id)
        
        if not ch: return await query.answer("❌ This channel is no longer available.", show_alert=True)
            
        await query.answer("Fetching details... ⏳")
        title = ch.get("title", "Unknown")
        clean_title = title.split("|")[0].replace("Dual Audio", "").strip() 
        
        ani_data = await fetch_anilist_data(clean_title, req_type)
        
        expire_seconds = ch.get("expire_seconds", 0)
        expire_date = datetime.now() + timedelta(seconds=expire_seconds) if expire_seconds > 0 else None

        if ch.get("join_mode", "direct") == "request":
            link = await client.create_chat_invite_link(ch_id, creates_join_request=True, expire_date=expire_date)
        else:
            link = await client.create_chat_invite_link(ch_id, expire_date=expire_date)

        btn = [[InlineKeyboardButton(f"🎬 Access: {title[:20]}...", url=link.invite_link)]]

        if ani_data:
            ani_title = ani_data.get('title', {}).get('english') or ani_data.get('title', {}).get('romaji') or title
            ani_format = ani_data.get('format', 'Unknown')
            status = ani_data.get('status', 'Unknown')
            year = ani_data.get('seasonYear', 'N/A')
            genres = ", ".join(ani_data.get('genres', [])[:3]) if ani_data.get('genres') else "N/A"
            eps_chaps = f"✦ **Chapters:** {ani_data.get('chapters', 'N/A')}" if req_type == "manga" else f"✦ **Episodes:** {ani_data.get('episodes', 'N/A')}"

            synopsis = str(ani_data.get('description', 'No synopsis available.')).replace("<br>", "").replace("<i>", "").replace("</i>", "")
            if len(synopsis) > 200: synopsis = synopsis[:200] + "..."

            ani_id = ani_data.get('id')
            poster = f"https://img.anili.st/media/{ani_id}" if ani_id else random.choice(PICS)

            caption = (
                f"<blockquote>**{ani_title}**</blockquote>\n\n"
                f"✦ **Type:** {ani_format}   |   **Status:** {status}\n"
                f"{eps_chaps}   |   **Year:** {year}\n"
                f"✦ **Genres:** {genres}\n"
                f"✦ **Synopsis:** {synopsis}\n\n"
                "👇 **Click the button below to access your files:**"
            )
        else:
            poster = random.choice(PICS)
            caption = f"<blockquote>**{title}**</blockquote>\n\n✦ **Status:** Found in Database ✅\n\n👇 **Click the button below to access your files:**"

        await query.message.edit_media(media=InputMediaPhoto(media=poster, caption=caption), reply_markup=InlineKeyboardMarkup(btn))
    except Exception as e:
        await query.answer("An error occurred.", show_alert=True)
