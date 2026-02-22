import random
import asyncio
import re
import aiohttp
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from bot import Bot
from database.database import kingdb
from config import OWNER_ID, PICS  
from helper_func import is_userJoin
from plugins.FORMATS import FORCE_MSG # ✈️ Tera asli message format import kiya

async def is_admin(user_id):
    admins = await kingdb.get_all_admins()
    return user_id == OWNER_ID or user_id in admins

# --- ✈️ ASLI FSUB LOGIC TERE CODE SE ---
async def check_fsub_and_warn(client, message, user_id, is_callback=False):
    if await is_admin(user_id): return True

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
            except Exception as e:
                print(f"Search FSub Error: {e}")

    if count > 0:
        try: buttons.append([InlineKeyboardButton(text='♻️ Tʀʏ Aɢᴀɪɴ', url=f"https://t.me/{client.username}")])
        except: pass
        
        caption = FORCE_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id,
            count=count,
            total=total
        )
        if is_callback: await message.edit_media(media=InputMediaPhoto(media=random.choice(PICS), caption=caption), reply_markup=InlineKeyboardMarkup(buttons))
        else: await message.reply_photo(photo=random.choice(PICS), caption=caption, reply_markup=InlineKeyboardMarkup(buttons))
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

async def perform_search_list(client, message, query, req_type="ALL", is_callback=False):
    if not await check_fsub_and_warn(client, message, message.from_user.id, is_callback): return
    
    safe_query = re.sub(r'[*?+^$[\](){}|\\.]', '', query).strip()
    results = await kingdb.search_channels(safe_query)
    
    if req_type != "ALL": filtered = [ch for ch in results if ch.get("ani_type", "anime").lower() == req_type.lower()]
    else: filtered = results

    if not filtered:
        if is_callback: return await message.reply(f"❌ **No Results Found For:** `{query}`")
        else: return await message.reply(f"❌ **No Results Found For:** `{query}`")

    buttons = []
    for ch in filtered[:10]:
        raw_title = ch.get("title", "Unknown")
        clean_btn_name = clean_title_for_anilist(raw_title)
        btn_text = clean_btn_name if len(clean_btn_name) > 1 else raw_title[:25]
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"show_ch_{ch['_id']}_{req_type}")])

    caption = f"🔍 **Search results for:** `{query}`\n\n👇 **Please select an option below:**"
    if is_callback: await message.edit_media(media=InputMediaPhoto(media=random.choice(PICS), caption=caption), reply_markup=InlineKeyboardMarkup(buttons))
    else: await message.reply_photo(photo=random.choice(PICS), caption=caption, reply_markup=InlineKeyboardMarkup(buttons))

@Bot.on_message(filters.command("anime") & filters.private & ~filters.bot, group=-1)
async def pm_anime_cmd(client, message):
    if len(message.command) < 2: return await message.reply("ℹ️ **Usage:** `/anime <name>`")
    await perform_search_list(client, message, message.text.split(" ", 1)[1].strip(), "anime", False)
    message.stop_propagation()

@Bot.on_message(filters.command("manga") & filters.private & ~filters.bot, group=-1)
async def pm_manga_cmd(client, message):
    if len(message.command) < 2: return await message.reply("ℹ️ **Usage:** `/manga <name>`")
    await perform_search_list(client, message, message.text.split(" ", 1)[1].strip(), "manga", False)
    message.stop_propagation()

@Bot.on_message(filters.command("search") & filters.private & ~filters.bot, group=-1)
async def admin_pm_search(client, message):
    if not await is_admin(message.from_user.id): return 
    if len(message.command) < 2: return await message.reply("ℹ️ **Usage:** `/search <name>`")
    await perform_search_list(client, message, message.text.split(" ", 1)[1].strip(), "ALL", False)
    message.stop_propagation()

@Bot.on_message(filters.text & filters.private & ~filters.regex(r"^/") & ~filters.bot & ~filters.me, group=-1)
async def normal_user_auto_search(client, message):
    if await is_admin(message.from_user.id): return
    if len(message.text.strip()) < 2: return
    await perform_search_list(client, message, message.text.strip(), "ALL", False)
    message.stop_propagation()

@Bot.on_callback_query(filters.regex(r"^show_ch_(-?\d+)_(.*)$"), group=-1)
async def show_channel_details(client, query):
    try:
        if not await check_fsub_and_warn(client, query.message, query.from_user.id, True): return

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

        btn = [[InlineKeyboardButton(f"{clean_title[:25]}", url=link.invite_link)]]

        if ani_data:
            ani_title = ani_data.get('title', {}).get('english') or ani_data.get('title', {}).get('romaji') or clean_title
            caption = (
                f"<blockquote>**{ani_title}**</blockquote>\n\n"
                f"✦ **Type:** {ani_data.get('format', 'Unknown')}   |   **Status:** {ani_data.get('status', 'Unknown')}\n"
                f"✦ **Genres:** {', '.join(ani_data.get('genres', [])[:3]) if ani_data.get('genres') else 'N/A'}\n\n"
                "👇 **Please click the button below to access your files:**"
            )
            poster = f"https://img.anili.st/media/{ani_data.get('id')}" if ani_data.get('id') else random.choice(PICS)
        else:
            poster = random.choice(PICS)
            caption = f"<blockquote>**{clean_title}**</blockquote>\n\n✦ **Status:** Found in Database ✅\n\n👇 **Please click the button below to access your files:**"

        await query.message.edit_media(media=InputMediaPhoto(media=poster, caption=caption), reply_markup=InlineKeyboardMarkup(btn))
    except Exception as e:
        await query.answer("An error occurred.", show_alert=True)
