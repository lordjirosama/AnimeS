import random
import asyncio
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from bot import Bot
from database.database import kingdb
from config import PICS  
from anilist import AniLister

AUTO_DELETE_TIME = 300 # 5 Minutes

# --- HELPER FOR ANILIST ---
async def fetch_anilist_data(query, req_type):
    try:
        anilister = AniLister(query, datetime.now().year, req_type.upper())
        return await anilister.get_anidata()
    except Exception: return {}

# --- CATEGORY SELECTION ---
async def ask_search_type_group(message, query):
    buttons = [
        # Yahan 'grp_' prefix lagaya hai taaki PM callbacks se clash na ho
        [InlineKeyboardButton("🎬 Anime", callback_data=f"grp_typ_anime_{query[:25]}"),
         InlineKeyboardButton("📖 Manga/Manhwa", callback_data=f"grp_typ_manga_{query[:25]}")]
    ]
    caption = (
        f"🔍 **Search Request:** `{query}`\n\n"
        "👇 **What are you looking for? Select a category:**\n"
        f"⏳ _This message will be deleted in {AUTO_DELETE_TIME // 60} minutes._"
    )
    sent = await message.reply_photo(photo=random.choice(PICS), caption=caption, reply_markup=InlineKeyboardMarkup(buttons))
    
    # Auto Delete Process
    await asyncio.sleep(AUTO_DELETE_TIME)
    try: await sent.delete() 
    except: pass

# --- GENERATE LIST FROM DB ---
async def perform_search_list_group(message, query, req_type, is_callback=False):
    results = await kingdb.search_channels(query)
    filtered = [ch for ch in results if ch.get("ani_type", "anime").lower() == req_type.lower()]

    if not filtered:
        if is_callback:
            return await message.reply(f"❌ **No {req_type.capitalize()} Results Found For:** `{query}`")
        else:
            msg = await message.reply(f"❌ **No {req_type.capitalize()} Results Found For:** `{query}`")
            await asyncio.sleep(10)
            try: await msg.delete()
            except: pass
            return

    # Yahan bhi 'grp_' lagaya hai
    buttons = [[InlineKeyboardButton(ch.get("title", "Unknown"), callback_data=f"grp_show_ch_{ch['_id']}_{req_type}")] for ch in filtered[:10]]
    caption = (
        f"🔍 **{req_type.capitalize()} Search results for:** `{query}`\n\n"
        "👇 **Please select an option below:**\n"
        f"⏳ _This message will be deleted in {AUTO_DELETE_TIME // 60} minutes._"
    )
    
    if is_callback:
        await message.edit_media(media=InputMediaPhoto(media=random.choice(PICS), caption=caption), reply_markup=InlineKeyboardMarkup(buttons))
    else:
        sent = await message.reply_photo(photo=random.choice(PICS), caption=caption, reply_markup=InlineKeyboardMarkup(buttons))
        await asyncio.sleep(AUTO_DELETE_TIME)
        try: await sent.delete()
        except: pass

# --- MAIN GROUP MESSAGE HANDLER ---
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


# ================= GROUP SPECIFIC CALLBACK ROUTERS ================= #

@Bot.on_callback_query(filters.regex(r"^grp_typ_(anime|manga)_(.*)$"), group=-1)
async def group_type_selected_cb(client, query):
    req_type = query.matches[0].group(1)
    search_query = query.matches[0].group(2)
    await query.answer("Searching Database... ⏳")
    await perform_search_list_group(query.message, search_query, req_type, is_callback=True)

@Bot.on_callback_query(filters.regex(r"^grp_show_ch_(-?\d+)_(anime|manga)$"), group=-1)
async def group_show_channel_details(client, query):
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
                "👇 **Click the button below to access your files:**\n"
                f"⏳ _This message will be deleted shortly._"
            )
        else:
            poster = random.choice(PICS)
            caption = (
                f"<blockquote>**{title}**</blockquote>\n\n"
                "✦ **Status:** Found in Database ✅\n\n"
                "👇 **Click the button below to access your files:**\n"
                f"⏳ _This message will be deleted shortly._"
            )

        await query.message.edit_media(media=InputMediaPhoto(media=poster, caption=caption), reply_markup=InlineKeyboardMarkup(btn))
    except Exception as e:
        await query.answer("An error occurred.", show_alert=True)
