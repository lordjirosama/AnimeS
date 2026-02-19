import random
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from database.database import kingdb
from config import PICS  

# Ab koi admin check nahi chahiye, sab search kar sakte hain
@Bot.on_message(filters.text & filters.private)
async def pm_auto_search(client, message):
    
    text = message.text.strip()

    # Agar koi command daal raha hai (jaise /start ya /index), toh search mat karo
    if text.startswith("/"):
        return

    # Agar 2 letter se chhota word hai, toh ignore karo
    if len(text) < 2:
        return
        
    query = text
    
    # Database me search
    results = await kingdb.search_channels(query)

    if not results:
        return await message.reply(f"❌ **Nᴏ Rᴇsᴜʟᴛs Fᴏᴜɴᴅ Fᴏʀ:** `{query}`")

    # Buttons Generate Karo
    buttons = []
    for ch in results[:10]: 
        try:
            channel_id = ch["_id"]
            join_mode = ch.get("join_mode", "direct")
            expire_seconds = ch.get("expire_seconds", 0)
            title = ch.get("title", "Unknown")

            # Expire time calculate karo (agar set hai toh)
            expire_date = None
            if expire_seconds > 0:
                expire_date = datetime.now() + timedelta(seconds=expire_seconds)

            if join_mode == "request":
                link = await client.create_chat_invite_link(channel_id, creates_join_request=True, expire_date=expire_date)
            else:
                link = await client.create_chat_invite_link(channel_id, expire_date=expire_date)

            buttons.append([InlineKeyboardButton(f"🔗 {title}", url=link.invite_link)])

        except Exception as e:
            print(f"Link Error: {e}")
            continue

    if not buttons:
        return await message.reply("❌ Links generate nahi ho paaye. (Bot permissions check karo)")

    # --- ✨ PREMIUM UI CAPTION ✨ ---
    caption = (
        "🍿 **𝗦𝗲𝗮𝗿𝗰𝗵 𝗥𝗲𝘀𝘂𝗹𝘁𝘀 𝗙𝗼𝘂𝗻𝗱!**\n\n"
        f"📝 **Qᴜᴇʀʏ:** `{query}`\n"
        f"📊 **Rᴇsᴜʟᴛs:** `{len(buttons)}` Lɪɴᴋ(s) Gᴇɴᴇʀᴀᴛᴇᴅ\n\n"
        "👇 **Cʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ᴀᴄᴄᴇss:**"
    )

    # Result Bhejo Random Pic ke sath
    await message.reply_photo(
        photo=random.choice(PICS), 
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
