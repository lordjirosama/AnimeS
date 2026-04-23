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
                else:
                    link = data.invite_link

                buttons.append([InlineKeyboardButton(text=cname, url=link)])
                count += 1
            except:
                pass

    if count > 0:
        if query:
            buttons.append([InlineKeyboardButton(text='♻️ Tʀʏ Aɢᴀɪɴ', callback_data=f"grp_try_{req_type}_{query[:20]}")])
        else:
            try:
                buttons.append([InlineKeyboardButton(text='♻️ Tʀʏ Aɢᴀɪɴ', url=f"https://t.me/{client.username}")])
            except:
                pass
            
        caption = FORCE_MSG.format(
            first=message.from_user.first_name if message.from_user else "User",
            last=message.from_user.last_name if message.from_user else "",
            username=None if not (message.from_user and message.from_user.username) else '@' + message.from_user.username,
            mention=message.from_user.mention if message.from_user else "User",
            id=user_id, count=count, total=total
        )

        if is_callback:
            await message.edit_media(
                media=InputMediaPhoto(media=random.choice(PICS), caption=caption),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            sent = await message.reply_photo(
                photo=random.choice(PICS),
                caption=caption,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await asyncio.sleep(45)
            try:
                await sent.delete()
            except:
                pass
        return False
    return True

def clean_title_for_anilist(title):
    title = re.sub(r'.*?|.*?', '', title)
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
        except:
            return []

async def fast_anilist_fetch_by_id(ani_id):
    graphql = """query ($id: Int) { Media (id: $id) { id title { english romaji } type format status episodes chapters seasonYear genres description(asHtml: false) } }"""
    async with aiohttp.ClientSession() as sess:
        try:
            async with sess.post("https://graphql.anilist.co", json={'query': graphql, 'variables': {'id': ani_id}}, timeout=3) as resp:
                data = await resp.json()
                return data.get('data', {}).get('Media') or {}
        except:
            return {}

async def perform_search_list_group(client, message, query, req_type="ALL", is_callback=False, is_auto=False, cb_user_id=None):
    user_id = cb_user_id or (message.from_user.id if message.from_user else None)
    safe_query = re.sub(r'[*?+^$[\](){}|\\.]', '', query).strip()
    
    if not await check_fsub_group_warn(client, message, user_id, is_callback, safe_query, req_type):
        return

    db_results = await kingdb.search_channels(safe_query)
    if req_type != "ALL":
        db_results = [ch for ch in db_results if ch.get("ani_type", "anime").lower() == req_type.lower()]

    ani_results = await fast_anilist_search(safe_query, req_type)

    exact_db = []
    for ch in db_results:
        clean = clean_title_for_anilist(ch.get("title", ""))
        if is_exact_match(safe_query, clean):
            exact_db.append(ch)
    db_results = exact_db

    exact_ani = []
    for media in ani_results:
        eng = media.get('title', {}).get('english') or ""
        rom = media.get('title', {}).get('romaji') or ""
        if is_exact_match(safe_query, eng) or is_exact_match(safe_query, rom):
            exact_ani.append(media)
    ani_results = exact_ani

    if not db_results and not ani_results:
        if is_auto:
            return
        msg = await message.reply(
            f"❌ <b>No Exact Results Found For:</b> <code>{query}</code>",
            parse_mode="html"
        )
        if not is_callback:
            await asyncio.sleep(10)
            try:
                await msg.delete()
            except:
                pass
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

    caption = (
        f"🔍 <b>Search results for:</b> <code>{query}</code>\n\n"
        f"👇 <b>Select an option below:</b>\n"
        f"⏳ <i>This message will be deleted in {AUTO_DELETE_TIME // 60} minutes.</i>"
    )

    if is_callback:
        await message.edit_media(
            media=InputMediaPhoto(media=random.choice(PICS), caption=caption, parse_mode="html"),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        sent = await message.reply_photo(
            photo=random.choice(PICS),
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="html"
        )
        await asyncio.sleep(AUTO_DELETE_TIME)
        try:
            await sent.delete()
        except:
            pass
