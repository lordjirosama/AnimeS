import random
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from database.database import kingdb
from config import OWNER_ID, PICS  

async def is_admin(user_id):
    admins = await kingdb.get_all_admins()
    return user_id == OWNER_ID or user_id in admins

# Common search logic dono ke liye
async def perform_search(client, message, query, user_is_admin):
    results = await kingdb.search_channels(query)

    if not results:
        return await message.reply(f"❌ **Nᴏ Rᴇsᴜʟᴛs Fᴏᴜɴᴅ Fᴏʀ:** `{query}`")

    buttons = []
    for ch in results[:10]: 
        try:
            channel_id = ch["_id"]
            join_mode = ch.get("join_mode", "direct")
            expire_seconds = ch.get("expire_seconds", 0)
            title = ch.get("title", "Unknown")

            expire_date = None
            if expire_seconds > 0:
                expire_date = datetime.now() + timedelta(seconds=expire_seconds)

            if join_mode == "request":
                link = await client.create_chat_invite_link(channel_id, creates_join_request=True, expire_date=expire_date)
            else:
                link = await client.create_chat_invite_link(channel_id, expire_date=expire_date)

            buttons.append([InlineKeyboardButton(f"🔗 {title}", url=link.invite_link)])
        except Exception as e:
            continue

    if not buttons:
        return await message.reply("❌ Links generate nahi ho paaye. (Bot permissions check karo)")

    if user_is_admin:
        caption = (
            "🕵️‍♂️ **𝗔𝗱𝗺𝗶𝗻 𝗦𝗲𝗮𝗿𝗰𝗵 𝗥𝗲𝘀𝘂𝗹𝘁𝘀** ⚙️\n\n"
            f"📝 **Qᴜᴇʀʏ:** `{query}`\n"
            f"📊 **Rᴇsᴜʟᴛs:** `{len(buttons)}` Lɪɴᴋ(s) Gᴇɴᴇʀᴀᴛᴇᴅ\n\n"
            "👇 **Cʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ᴀᴄᴄᴇss:**"
        )
    else:
        caption = (
            "🍿 **𝗦𝗲𝗮𝗿𝗰𝗵 𝗥𝗲𝘀𝘂𝗹𝘁𝘀 𝗙𝗼𝘂𝗻𝗱!**\n\n"
            f"📝 **Qᴜᴇʀʏ:** `{query}`\n"
            f"📊 **Rᴇsᴜʟᴛs:** `{len(buttons)}` Lɪɴᴋ(s) Gᴇɴᴇʀᴀᴛᴇᴅ\n\n"
            "👇 **Cʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ᴀᴄᴄᴇss:**"
        )

    await message.reply_photo(
        photo=random.choice(PICS), 
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ================= 1. ADMIN SEARCH (Command Mode) ================= #
@Bot.on_message(filters.command("search") & filters.private, group=-1)
async def admin_pm_search(client, message):
    user_id = message.from_user.id
    
    # Agar admin nahi hai, toh command ignore kar dega (kuch nahi bolega)
    if not await is_admin(user_id):
        return 
        
    if len(message.command) < 2:
        return await message.reply("ℹ️ **Usage:** `/search movie_name`")
        
    query = message.text.split(" ", 1)[1].strip()
    await perform_search(client, message, query, user_is_admin=True)
    message.stop_propagation()


# ================= 2. NORMAL USER SEARCH (Auto Mode) ================= #
@Bot.on_message(filters.text & filters.private & ~filters.regex(r"^/"), group=-1)
async def normal_user_auto_search(client, message):
    user_id = message.from_user.id
    
    # Agar admin hai, toh auto-search kaam nahi karega (force us to use /search)
    if await is_admin(user_id):
        return

    query = message.text.strip()
    if len(query) < 2:
        return
        
    await perform_search(client, message, query, user_is_admin=False)
    message.stop_propagation()
