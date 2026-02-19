import random
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from database.database import kingdb
from config import OWNER_ID, PICS  

async def is_admin(user_id):
    admins = await kingdb.get_all_admins()
    return user_id == OWNER_ID or user_id in admins

@Bot.on_message(filters.command("search") & filters.private, group=-1)
async def admin_pm_search(client, message):
    
    user_id = message.from_user.id

    # 1. Admin Check
    if not await is_admin(user_id):
        return await message.reply("❌ **Sirf Admins hi PM me search kar sakte hain.**")

    # 2. Query Check
    if len(message.command) < 2:
        return await message.reply("ℹ️ **Usage:** `/search name")
        
    query = message.text.split(" ", 1)[1].strip()
    
    # 3. Search DB
    results = await kingdb.search_channels(query)

    if not results:
        return await message.reply(f"❌ **No result Found:** `{query}`")

    # 4. Buttons Generate Karo
    buttons = []
    for ch in results[:10]: 
        try:
            channel_id = ch["_id"]
            join_mode = ch.get("join_mode", "direct")
            title = ch.get("title", "Unknown")

            if join_mode == "request":
                link = await client.create_chat_invite_link(channel_id, creates_join_request=True)
            else:
                link = await client.create_chat_invite_link(channel_id)

            buttons.append([InlineKeyboardButton(f"🎬 {title}", url=link.invite_link)])

        except Exception as e:
            print(f"Link Error: {e}")
            continue

    if not buttons:
        return await message.reply("❌ Links generate nahi ho paaye. (Bot us channel me Admin nahi hai ya permission missing hai)")

    # 5. Send Result (Random Pic from Config)
    return await message.reply_photo(
        photo=random.choice(PICS), 
        caption=f"🕵️‍♂️ **Admin Search Result:**\n\n🔎 Query: `{query}`\n👇 Results niche hain:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
