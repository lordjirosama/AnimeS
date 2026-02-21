import random
import asyncio
import re
import aiohttp
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from bot import Bot
from database.database import kingdb
from config import PICS  

AUTO_DELETE_TIME = 300 # 5 Minutes

def clean_title_for_anilist(title):
    title = re.sub(r'\[.*?\]|\(.*?\)', '', title)
    title = re.sub(r'(?i)(hindi|dubbed|dub|subbed|sub|dual|audio|multi|1080p|720p|480p|hevc|x264|x265|blu-ray|bluray|web-dl|webrip|season\s*\d+|s\d+)', '', title)
    title = title.split('|')[0].split('-')[0]
    return title.strip()

async def fast_anilist_fetch(query, req_type="ALL"):
    variables = {'search': query}
    if req_type in ["anime", "manga"]:
        variables["type"] = req_type.upper()
        graphql = """
        query ($search: String, $type: MediaType) {
          Media (search: $search, type: $type) {
            id title { english romaji } type format status episodes chapters seasonYear genres description(asHtml: false)
          }
        }
        """
    else:
        graphql = """
        query ($search: String) {
          Media (search: $search) {
            id title { english romaji } type format status episodes chapters seasonYear genres description(asHtml: false)
          }
        }
        """
    async with aiohttp.ClientSession() as sess:
        try:
            async with sess.post("https://graphql.anilist.co", json={'query': graphql, 'variables': variables}, timeout=3) as resp:
                data = await resp.json()
                return data.get('data', {}).get('Media') or {}
        except Exception: return {}

# --- GENERATE LIST FROM DB ---
async def perform_search_list_group(client, message, query, req_type="ALL"):
    safe_query = re.sub(r'[*?+^$[\](){}|\\.]', '', query).strip()
    results = await kingdb.search_channels(safe_query)
    
    if req_type != "ALL":
        filtered = [ch for ch in results if ch.get("ani_type", "anime").lower() == req_type.lower()]
    else:
        filtered = results

    if not filtered:
        msg = await message.reply(f"❌ **No Results Found For:** `{query}`")
        await asyncio.sleep(10)
        try: await msg.delete()
        except: pass
        return

    buttons = []
    # Seedha channel names ki list
    for ch in filtered[:10]:
        title = ch.get("title", "Unknown")
        buttons.append([InlineKeyboardButton(title, callback_data=f"grp_show_ch_{ch['_id']}_{req_type}")])

    caption = (
        f"🔍 **Search results for:** `{query}`\n\n"
        "👇 **Please select a channel below:**\n"
        f"⏳ _This message will be deleted in {AUTO_DELETE_TIME // 60} minutes._"
    )
    
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
    
    if text.lower().startswith("/anime "): return await perform_search_list_group(client, message, text.replace("/anime ", "", 1).strip(), "anime")
    if text.lower().startswith("/manga "): return await perform_search_list_group(client, message, text.replace("/manga ", "", 1).strip(), "manga")

    query = ""
    if mode == "command":
        if text.lower().startswith("/search "): query = text.replace("/search ", "", 1).strip()
        else: return 
    elif mode == "auto":
        if text.startswith("/"): return 
        query = text
    
    if len(query) < 2: return 
    await perform_search_list_group(client, message, query, "ALL")

# ================= GROUP SPECIFIC CALLBACK ================= #
@Bot.on_callback_query(filters.regex(r"^grp_show_ch_(-?\d+)_(.*)$"), group=-1)
async def group_show_channel_details(client, query):
    try:
        ch_id = int(query.matches[0].group(1))
        req_type = query.matches[0].group(2)
        
        ch = await kingdb.get_channel(ch_id)
        if not ch: return await query.answer("❌ This channel is no longer available.", show_alert=True)
            
        await query.answer("Fetching details... ⏳")
        raw_title = ch.get("title", "Unknown")
        
        # ✈️ Sirf fetch ke liye clean name
        clean_title = clean_title_for_anilist(raw_title)
        ani_data = await fast_anilist_fetch(clean_title, req_type)
        
        join_mode = ch.get("join_mode", "direct")
        expire_seconds = ch.get("expire_seconds", 0)
        expire_date = datetime.now() + timedelta(seconds=expire_seconds) if expire_seconds > 0 else None

        if join_mode == "request": link = await client.create_chat_invite_link(ch_id, creates_join_request=True, expire_date=expire_date)
        else: link = await client.create_chat_invite_link(ch_id, expire_date=expire_date)

        btn = [[InlineKeyboardButton(f"🎬 Access: {raw_title[:25]}", url=link.invite_link)]]

        if ani_data:
            ani_title = ani_data.get('title', {}).get('english') or ani_data.get('title', {}).get('romaji') or clean_title
            ani_format = ani_data.get('format', 'Unknown')
            status = ani_data.get('status', 'Unknown')
            year = ani_data.get('seasonYear', 'N/A')
            genres = ", ".join(ani_data.get('genres', [])[:3]) if ani_data.get('genres') else "N/A"
            eps_chaps = f"✦ **Chapters:** {ani_data.get('chapters', 'N/A')}" if ani_data.get('type') == "MANGA" else f"✦ **Episodes:** {ani_data.get('episodes', 'N/A')}"

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
                "👇 **Please click the button below to access your files:**\n"
                f"⏳ _This message will be deleted shortly._"
            )
        else:
            poster = random.choice(PICS)
            caption = (
                f"<blockquote>**{raw_title}**</blockquote>\n\n"
                "✦ **Status:** Found in Database ✅\n\n"
                "👇 **Please click the button below to access your files:**\n"
                f"⏳ _This message will be deleted shortly._"
            )

        await query.message.edit_media(media=InputMediaPhoto(media=poster, caption=caption), reply_markup=InlineKeyboardMarkup(btn))
    except Exception as e:
        await query.answer("An error occurred.", show_alert=True)
