import random
import asyncio
import re
import aiohttp
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from bot import Bot
from database.database import kingdb
from helper_func import is_userJoin
from config import OWNER_ID, PICS, LOG_CHANNEL
from plugins.FORMATS import FORCE_MSG 

AUTO_DELETE_TIME = 300 

def is_exact_match(query, title):
    if not title: return False
    q = query.replace(" ", "").lower()
    t = title.replace(" ", "").lower()
    if len(query) >= 20 and t.startswith(q): return True 
    return q == t

async def check_fsub_group_warn(client, message, user_id, is_callback=False, query="", req_type="ALL"):
    if not user_id: return True 
    admins = await kingdb.get_all_admins()
    if user_id == OWNER_ID or user_id in admins: return True 
        
    REQFSUB = await kingdb.get_request_forcesub()
    buttons = []
    count = 0
    total = 0

    all_channels = await kingdb.get_all_channels()
    for chat_id in all_channels:
        total += 1
        if not await is_userJoin(client, user_id, chat_id):
            try:
                data = await client.get_chat(chat_id)
                cname = data.title
                if REQFSUB and not data.username: 
                    link = await kingdb.get_stored_reqLink(chat_id)
                    await kingdb.add_reqChannel(chat_id)
                    if not link:
                        link = (await client.create_chat_invite_link(chat_id=chat_id, creates_join_request=True)).invite_link
                        await kingdb.store_reqLink(chat_id, link)
                else: link = data.invite_link
                buttons.append([InlineKeyboardButton(text=cname, url=link)])
                count += 1
            except: pass

    if count > 0:
        if query:
            buttons.append([InlineKeyboardButton(text='♻️ Tʀʏ Aɢᴀɪɴ', callback_data=f"grp_try_{req_type}_{query[:20]}")])
        else:
            try: buttons.append([InlineKeyboardButton(text='♻️ Tʀʏ Aɢᴀɪɴ', url=f"https://t.me/{client.username}")])
            except: pass
            
        caption = FORCE_MSG.format(
            first=message.from_user.first_name if message.from_user else "User",
            last=message.from_user.last_name if message.from_user else "",
            username=None if not (message.from_user and message.from_user.username) else '@' + message.from_user.username,
            mention=message.from_user.mention if message.from_user else "User",
            id=user_id, count=count, total=total
        )
        if is_callback: await message.edit_media(media=InputMediaPhoto(media=random.choice(PICS), caption=caption), reply_markup=InlineKeyboardMarkup(buttons))
        else:
            sent = await message.reply_photo(photo=random.choice(PICS), caption=caption, reply_markup=InlineKeyboardMarkup(buttons))
            await asyncio.sleep(45) 
            try: await sent.delete()
            except: pass
        return False
    return True

def clean_title_for_anilist(title):
    title = re.sub(r'\[.*?\]|\(.*?\)', '', title)
    title = re.sub(r'(?i)(hindi|dubbed|dub|subbed|sub|dual|audio|multi|1080p|720p|480p|hevc|x264|x265|blu-ray|bluray|web-dl|webrip|season\s*\d+|s\d+)', '', title)
    return title.split('|')[0].split('-')[0].strip().title()

async def fast_anilist_search(query, req_type="ALL"):
    variables = {'search': query}
    if req_type in ["anime", "manga"]:
        variables["type"] = req_type.upper()
        graphql = """query ($search: String, $type: MediaType) { Page(page: 1, perPage: 10) { media(search: $search, type: $type, sort: POPULARITY_DESC) { id title { english romaji } } } }"""
    else:
        graphql = """query ($search: String) { Page(page: 1, perPage: 10) { media(search: $search, sort: POPULARITY_DESC) { id title { english romaji } } } }"""
    async with aiohttp.ClientSession() as sess:
        try:
            async with sess.post("https://graphql.anilist.co", json={'query': graphql, 'variables': variables}, timeout=3) as resp:
                data = await resp.json()
                return data.get('data', {}).get('Page', {}).get('media', [])
        except Exception: return []

async def fast_anilist_fetch_by_id(ani_id):
    graphql = """query ($id: Int) { Media (id: $id) { id title { english romaji } type format status episodes chapters seasonYear genres description(asHtml: false) } }"""
    async with aiohttp.ClientSession() as sess:
        try:
            async with sess.post("https://graphql.anilist.co", json={'query': graphql, 'variables': {'id': ani_id}}, timeout=3) as resp:
                data = await resp.json()
                return data.get('data', {}).get('Media') or {}
        except Exception: return {}

async def perform_search_list_group(client, message, query, req_type="ALL", is_callback=False, is_auto=False, cb_user_id=None):
    user_id = cb_user_id or (message.from_user.id if message.from_user else None)
    safe_query = re.sub(r'[*?+^$[\](){}|\\.]', '', query).strip()
    
    if not await check_fsub_group_warn(client, message, user_id, is_callback, safe_query, req_type): return

    db_results = await kingdb.search_channels(safe_query)
    if req_type != "ALL": db_results = [ch for ch in db_results if ch.get("ani_type", "anime").lower() == req_type.lower()]
    ani_results = await fast_anilist_search(safe_query, req_type)

    exact_db = []
    for ch in db_results:
        clean = clean_title_for_anilist(ch.get("title", ""))
        if is_exact_match(safe_query, clean): exact_db.append(ch)
    db_results = exact_db

    exact_ani = []
    for media in ani_results:
        eng = media.get('title', {}).get('english') or ""
        rom = media.get('title', {}).get('romaji') or ""
        if is_exact_match(safe_query, eng) or is_exact_match(safe_query, rom): exact_ani.append(media)
    ani_results = exact_ani

    if not db_results and not ani_results:
        if is_auto: return 
        msg = await message.reply(f"❌ **No Exact Results Found For:** `{query}`")
        if not is_callback:
            await asyncio.sleep(10)
            try: await msg.delete()
            except: pass
        return

    buttons = []
    added_titles = set()
    short_query = safe_query[:20]

    for ch in db_results[:5]:
        title = ch.get("title", "Unknown")
        clean = clean_title_for_anilist(title)
        if clean.lower() not in added_titles:
            added_titles.add(clean.lower())
            buttons.append([InlineKeyboardButton(clean[:30], callback_data=f"grp_dbch_{ch['_id']}_{req_type}_{short_query}")])

    for media in ani_results:
        title = media.get('title', {}).get('english') or media.get('title', {}).get('romaji') or "Unknown"
        if title.lower() not in added_titles:
            added_titles.add(title.lower())
            buttons.append([InlineKeyboardButton(title[:30], callback_data=f"grp_aclk_{media['id']}_{req_type}_{short_query}")])

    buttons.append([InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data="grp_close_panel")])
    caption = f"🔍 Search results for: `{query}`\n\n👇 Select an option below:\n⏳ This message will be deleted in {AUTO_DELETE_TIME // 60} minutes."
    
    if is_callback: await message.edit_media(media=InputMediaPhoto(media=random.choice(PICS), caption=caption), reply_markup=InlineKeyboardMarkup(buttons))
    else:
        sent = await message.reply_photo(photo=random.choice(PICS), caption=caption, reply_markup=InlineKeyboardMarkup(buttons))
        await asyncio.sleep(AUTO_DELETE_TIME)
        try: await sent.delete()
        except: pass

@Bot.on_message(filters.text & filters.group & ~filters.bot, group=-1)
async def group_search_handler(client, message):
    chat_id = message.chat.id
    text = message.text.strip()
    if not await kingdb.is_group_approved(chat_id): return
    mode = await kingdb.get_search_mode(chat_id)
    
    if text.lower().startswith("/anime "): return await perform_search_list_group(client, message, text.replace("/anime ", "", 1).strip(), "anime", False, False)
    if text.lower().startswith("/manga "): return await perform_search_list_group(client, message, text.replace("/manga ", "", 1).strip(), "manga", False, False)

    query = ""
    is_auto = False
    if mode == "command":
        if text.lower().startswith("/search "): query = text.replace("/search ", "", 1).strip()
        else: return 
    elif mode == "auto":
        if text.startswith("/"): return 
        query = text
        is_auto = True
    
    if len(query) < 2: return 
    await perform_search_list_group(client, message, query, "ALL", False, is_auto)

# ✈️ SMART TRY AGAIN HANDLER FOR GROUP
@Bot.on_callback_query(filters.regex(r"^grp_try_(.*)_(.*)$"), group=-1)
async def grp_try_again_cb(client, query):
    req_type = query.matches[0].group(1)
    sq = query.matches[0].group(2)
    await perform_search_list_group(client, query.message, sq, req_type, True, False, query.from_user.id)

def build_details_caption_group(ani_data, clean_title):
    if ani_data:
        ani_title = ani_data.get('title', {}).get('english') or ani_data.get('title', {}).get('romaji') or clean_title
        ani_format = ani_data.get('format', 'Unknown')
        status = ani_data.get('status', 'Unknown')
        year = ani_data.get('seasonYear', 'N/A')
        genres = ", ".join(ani_data.get('genres', [])[:3]) if ani_data.get('genres') else "N/A"
        eps_chaps = f"✦ **Chapters:** {ani_data.get('chapters', 'N/A')}" if ani_data.get('type') == "MANGA" else f"✦ **Episodes:** {ani_data.get('episodes', 'N/A')}"
        synopsis = str(ani_data.get('description', 'No synopsis available.')).replace("<br>", "").replace("<i>", "").replace("</i>", "")
        if len(synopsis) > 200: synopsis = synopsis[:200] + "..."
        poster = f"https://img.anili.st/media/{ani_data.get('id')}" if ani_data.get('id') else random.choice(PICS)

        caption = (
            f"<blockquote>**{ani_title}**</blockquote>\n\n"
            f"✦ **Type:** {ani_format}   |   **Status:** {status}\n"
            f"{eps_chaps}   |   **Year:** {year}\n"
            f"✦ **Genres:** {genres}\n"
            f"✦ **Synopsis:** {synopsis}\n\n"
        )
        return poster, caption
    else: return random.choice(PICS), f"<blockquote>**{clean_title}**</blockquote>\n\n✦ **Status:** Found in Database ✅\n\n"

@Bot.on_callback_query(filters.regex(r"^grp_dbch_(-?\d+)_(.*)_(.*)$"), group=-1)
async def grp_dbch_details(client, query):
    ch_id, req_type, sq = int(query.matches[0].group(1)), query.matches[0].group(2), query.matches[0].group(3)
    if not await check_fsub_group_warn(client, query.message, query.from_user.id, True, sq, req_type): return
    
    ch = await kingdb.get_channel(ch_id)
    if not ch: return await query.answer("❌ Not available.", show_alert=True)
    await query.answer("Fetching Details... ⏳")
        
    raw_title = ch.get("title", "Unknown")
    clean_title = clean_title_for_anilist(raw_title)
    
    ani_data = None
    if ch.get("ani_id"): ani_data = await fast_anilist_fetch_by_id(ch.get("ani_id"))
    if not ani_data: 
        search_results = await fast_anilist_search(clean_title, req_type)
        if search_results and 'id' in search_results[0]: ani_data = await fast_anilist_fetch_by_id(search_results[0]['id']) 
        else: ani_data = {}

    join_mode, expire_seconds = ch.get("join_mode", "direct"), ch.get("expire_seconds", 0)
    expire_date = datetime.now() + timedelta(seconds=expire_seconds) if expire_seconds > 0 else None
    if join_mode == "request": link = await client.create_chat_invite_link(ch_id, creates_join_request=True, expire_date=expire_date)
    else: link = await client.create_chat_invite_link(ch_id, expire_date=expire_date)

    poster, caption = build_details_caption_group(ani_data, clean_title)
    caption += "👇 **Please click the button below to access your files:**\n⏳ _This message will be deleted shortly._"
    btn = [
        [InlineKeyboardButton(f"🎥🍿: {clean_title[:15]}", url=link.invite_link)],
        [InlineKeyboardButton("ʙᴀᴄᴋ", callback_data=f"grp_bck_{sq}"), InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data="grp_close_panel")]
    ]
    await query.message.edit_media(media=InputMediaPhoto(media=poster, caption=caption), reply_markup=InlineKeyboardMarkup(btn))

@Bot.on_callback_query(filters.regex(r"^grp_aclk_(\d+)_(.*)_(.*)$"), group=-1)
async def grp_aclk_details(client, query):
    ani_id, req_type, sq = int(query.matches[0].group(1)), query.matches[0].group(2), query.matches[0].group(3)
    if not await check_fsub_group_warn(client, query.message, query.from_user.id, True, sq, req_type): return
    await query.answer("Fetching Details... ⏳")
    
    ani_data = await fast_anilist_fetch_by_id(ani_id)
    title = ani_data.get('title', {}).get('english') or ani_data.get('title', {}).get('romaji') or "Unknown"
    
    db_results = await kingdb.search_channels(title)
    if not db_results and ani_data.get('title', {}).get('romaji'): db_results = await kingdb.search_channels(ani_data.get('title', {}).get('romaji'))

    poster, caption = build_details_caption_group(ani_data, title)
    btn = []
    
    if db_results:
        ch = db_results[0]
        join_mode, expire_seconds = ch.get("join_mode", "direct"), ch.get("expire_seconds", 0)
        expire_date = datetime.now() + timedelta(seconds=expire_seconds) if expire_seconds > 0 else None
        if join_mode == "request": link = await client.create_chat_invite_link(ch['_id'], creates_join_request=True, expire_date=expire_date)
        else: link = await client.create_chat_invite_link(ch['_id'], expire_date=expire_date)
        caption += "👇 **Please click the button below to access your files:**\n⏳ _This message will be deleted shortly._"
        btn.append([InlineKeyboardButton(f"🎥🍿: {title[:15]}", url=link.invite_link)])
    else:
        caption += "⚠️ Status: Not available in Database.\n👇 Click the button below to request an upload!\n⏳ _This message will be deleted shortly."
        btn.append([InlineKeyboardButton("ʀᴇǫᴜᴇꜱᴛ ᴛᴏ ᴜᴘʟᴏᴀᴅ", callback_data=f"grp_req_{ani_id}")])

    btn.append([InlineKeyboardButton("ʙᴀᴄᴋ", callback_data=f"grp_bck_{sq}"), InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data="grp_close_panel")])
    await query.message.edit_media(media=InputMediaPhoto(media=poster, caption=caption), reply_markup=InlineKeyboardMarkup(btn))

@Bot.on_callback_query(filters.regex(r"^grp_req_(\d+)$"), group=-1)
async def grp_request_upload(client, query):
    ani_id = int(query.matches[0].group(1))
    ani_data = await fast_anilist_fetch_by_id(ani_id)
    title = ani_data.get('title', {}).get('english') or ani_data.get('title', {}).get('romaji') or "Unknown"
    
    await client.send_message(
        LOG_CHANNEL, 
        f"📥 NEW UPLOAD REQUEST**\n\n👤 User: {query.from_user.mention} (`{query.from_user.id}`)\n🎬 Title: {title}\n🔗 Anilist: https://anilist.co/anime/{ani_id}"
    )
    await query.answer("✅ Request Sent to Admins!", show_alert=True)

@Bot.on_callback_query(filters.regex(r"^grp_bck_(.*)$"), group=-1)
async def grp_back_to_search(client, query):
    sq = query.matches[0].group(1)
    await perform_search_list_group(client, query.message, sq, "ALL", is_callback=True, cb_user_id=query.from_user.id)

@Bot.on_callback_query(filters.regex(r"^grp_close_panel$"), group=-1)
async def grp_close_panel_cb(client, query):
    await query.message.delete()
