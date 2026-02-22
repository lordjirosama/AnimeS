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
from config import OWNER_ID, PICS

AUTO_DELETE_TIME = 300 

async def check_fsub_group_warn(client, message, user_id, is_callback=False):
    if not user_id: return True 
    admins = await kingdb.get_all_admins()
    if user_id == OWNER_ID or user_id in admins: return True 
        
    REQFSUB = await kingdb.get_request_forcesub()
    buttons = []
    count = 0

    all_channels = await kingdb.get_all_channels()
    for chat_id in all_channels:
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
            except: pass

    if count > 0:
        warn_text = f"⚠️ **Hello {message.from_user.mention}!**\n\nAapne channel join nahi kiye hain. Pehle join karein tabhi access milega."
        if is_callback: await message.edit_media(media=InputMediaPhoto(media=random.choice(PICS), caption=warn_text), reply_markup=InlineKeyboardMarkup(buttons))
        else:
            sent = await message.reply_photo(photo=random.choice(PICS), caption=warn_text, reply_markup=InlineKeyboardMarkup(buttons))
            await asyncio.sleep(45) 
            try: await sent.delete()
            except: pass
        return False
    return True

def clean_title_for_anilist(title):
    title = re.sub(r'\[.*?\]|\(.*?\)', '', title)
    title = re.sub(r'(?i)(hindi|dubbed|dub|subbed|sub|dual|audio|multi|1080p|720p|480p|hevc|x264|x265|blu-ray|bluray|web-dl|webrip|season\s*\d+|s\d+)', '', title)
    title = title.split('|')[0].split('-')[0]
    return title.strip().title()

async def fast_anilist_fetch(query, req_type="ALL"):
    variables = {'search': query}
    if req_type in ["anime", "manga"]:
        variables["type"] = req_type.upper()
        graphql = """
        query ($search: String, $type: MediaType) {
          Media (search: $search, type: $type, sort: POPULARITY_DESC) {
            id title { english romaji } type format status episodes chapters seasonYear genres description(asHtml: false)
          }
        }
        """
    else:
        graphql = """
        query ($search: String) {
          Media (search: $search, sort: POPULARITY_DESC) {
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

async def perform_search_list_group(client, message, query, req_type="ALL", is_callback=False):
    user_id = message.from_user.id if message.from_user else None
    if not await check_fsub_group_warn(client, message, user_id, is_callback): return

    safe_query = re.sub(r'[*?+^$[\](){}|\\.]', '', query).strip()
    results = await kingdb.search_channels(safe_query)
    
    if req_type != "ALL": filtered = [ch for ch in results if ch.get("ani_type", "anime").lower() == req_type.lower()]
    else: filtered = results

    if not filtered:
        if is_callback: return await message.reply(f"❌ **No Results Found For:** `{query}`")
        else:
            msg = await message.reply(f"❌ **No Results Found For:** `{query}`")
            await asyncio.sleep(10)
            try: await msg.delete()
            except: pass
            return

    buttons = []
    for ch in filtered[:10]:
        raw_title = ch.get("title", "Unknown")
        clean_btn_name = clean_title_for_anilist(raw_title)
        btn_text = clean_btn_name if len(clean_btn_name) > 1 else raw_title[:25]
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"grp_show_ch_{ch['_id']}_{req_type}")])

    caption = f"🔍 **Search results for:** `{query}`\n\n👇 **Please select an option below:**\n⏳ _This message will be deleted in {AUTO_DELETE_TIME // 60} minutes._"
    
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
    
    if text.lower().startswith("/anime "): return await perform_search_list_group(client, message, text.replace("/anime ", "", 1).strip(), "anime", False)
    if text.lower().startswith("/manga "): return await perform_search_list_group(client, message, text.replace("/manga ", "", 1).strip(), "manga", False)

    query = ""
    if mode == "command":
        if text.lower().startswith("/search "): query = text.replace("/search ", "", 1).strip()
        else: return 
    elif mode == "auto":
        if text.startswith("/"): return 
        query = text
    
    if len(query) < 2: return 
    await perform_search_list_group(client, message, query, "ALL", False)

@Bot.on_callback_query(filters.regex(r"^grp_show_ch_(-?\d+)_(.*)$"), group=-1)
async def group_show_channel_details(client, query):
    try:
        if not await check_fsub_group_warn(client, query.message, query.from_user.id, True): return

        ch_id = int(query.matches[0].group(1))
        req_type = query.matches[0].group(2)
        ch = await kingdb.get_channel(ch_id)
        if not ch: return await query.answer("❌ This channel is no longer available.", show_alert=True)
            
        await query.answer("Fetching details... ⏳")
        raw_title = ch.get("title", "Unknown")
        clean_title = clean_title_for_anilist(raw_title)
        ani_data = await fast_anilist_fetch(clean_title, req_type)
        
        join_mode = ch.get("join_mode", "direct")
        expire_seconds = ch.get("expire_seconds", 0)
        expire_date = datetime.now() + timedelta(seconds=expire_seconds) if expire_seconds > 0 else None

        if join_mode == "request": link = await client.create_chat_invite_link(ch_id, creates_join_request=True, expire_date=expire_date)
        else: link = await client.create_chat_invite_link(ch_id, expire_date=expire_date)

        btn = [[InlineKeyboardButton(f"🎬 Access: {clean_title[:25]}", url=link.invite_link)]]

        if ani_data:
            ani_title = ani_data.get('title', {}).get('english') or ani_data.get('title', {}).get('romaji') or clean_title
            caption = f"<blockquote>**{ani_title}**</blockquote>\n\n✦ **Status:** {ani_data.get('status', 'Unknown')}\n\n👇 **Please click the button below to access your files:**\n⏳ _This message will be deleted shortly._"
            poster = f"https://img.anili.st/media/{ani_data.get('id')}" if ani_data.get('id') else random.choice(PICS)
        else:
            poster = random.choice(PICS)
            caption = f"<blockquote>**{clean_title}**</blockquote>\n\n✦ **Status:** Found in Database ✅\n\n👇 **Please click the button below to access your files:**\n⏳ _This message will be deleted shortly._"

        await query.message.edit_media(media=InputMediaPhoto(media=poster, caption=caption), reply_markup=InlineKeyboardMarkup(btn))
    except Exception as e:
        await query.answer("An error occurred.", show_alert=True)
