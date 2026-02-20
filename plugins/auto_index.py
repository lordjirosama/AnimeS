import datetime
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from bot import Bot
from database.database import kingdb
from config import OWNER_ID, LOG_CHANNEL

index_wait = set()

def get_time():
    return datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

def detect_type(title):
    title_lower = title.lower()
    if any(word in title_lower for word in ["manga", "manhwa", "manhua", "comic", "webtoon"]):
        return "manga"
    return "anime"

def get_log_markup(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Set Anime", callback_data=f"settype_anime_{chat_id}"), 
         InlineKeyboardButton("📖 Set Manga", callback_data=f"settype_manga_{chat_id}")],
        [InlineKeyboardButton("🗑 Remove", callback_data=f"remove_{chat_id}"),
         InlineKeyboardButton("✖️ Close", callback_data="close_panel")]
    ])

# ================= 1. /INDEX COMMAND ================= #
@Bot.on_message(filters.command("index") & filters.private)
async def index_cmd(client, message):
    user_id = message.from_user.id
    admins = await kingdb.get_all_admins()

    if user_id != OWNER_ID and user_id not in admins:
        return await message.reply("❌ **Only Admins are allowed to use this command.**")

    index_wait.add(user_id)
    await message.reply(
        "📥 **Indexing Mode Enabled**\n\n"
        "Please **Forward** a message from the target Channel or Group.\n"
        "_(Note: The bot must be an admin there)_"
    )

# ================= 2. FORWARD HANDLER ================= #
@Bot.on_message(filters.private & filters.forwarded, group=-1)
async def index_forward(client, message):
    user_id = message.from_user.id
    
    if user_id not in index_wait: return
    index_wait.remove(user_id)
    
    chat = message.forward_from_chat or message.sender_chat

    if not chat:
        await message.reply("❌ **Error:** Please forward from a valid Channel or Group.")
        return message.stop_propagation()

    try:
        ani_type = detect_type(chat.title or "")
        
        await kingdb.add_or_update_channel(
            channel_id=chat.id,
            title=chat.title or "Unknown Title",
            username=chat.username,
            join_mode="direct",
            expire_seconds=600,
            added_by=user_id
        )
        await kingdb.update_channel(chat.id, {"ani_type": ani_type})

        await message.reply(
            f"✅ **Successfully Indexed!**\n\n"
            f"📛 **Title:** {chat.title}\n"
            f"🆔 **ID:** `{chat.id}`\n"
            f"⚙️ **Detected Type:** {ani_type.upper()}\n\n"
            "You can change the category using the buttons below.",
            reply_markup=get_log_markup(chat.id)
        )

        await client.send_message(
            LOG_CHANNEL,
            f"✅ **NEW INDEX ADDED**\n\n📛 **Title:** {chat.title}\n🆔 **ID:** `{chat.id}`\n"
            f"⚙️ **Type:** {ani_type.upper()}\n👤 **Added By:** {message.from_user.mention}\n⏰ **Time:** {get_time()}",
            reply_markup=get_log_markup(chat.id)
        )

    except Exception as e:
        await message.reply(f"❌ **Error:** {e}")

    message.stop_propagation()

# ================= 3. AUTO ADD (Admin Check Applied) ================= #
@Bot.on_chat_member_updated()
async def auto_index_on_add(client, event: ChatMemberUpdated):
    if not event.new_chat_member or event.new_chat_member.user.id != client.me.id:
        return

    chat = event.chat
    if chat.type not in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP]:
        return

    adder_id = event.from_user.id
    admins = await kingdb.get_all_admins()
    
    if adder_id != OWNER_ID and adder_id not in admins:
        try:
            await client.leave_chat(chat.id)
        except: pass
        return

    try:
        ani_type = detect_type(chat.title or "")
        
        await kingdb.add_or_update_channel(
            channel_id=chat.id,
            title=chat.title or "Unknown",
            username=chat.username,
            join_mode="direct",
            expire_seconds=600,
            added_by=adder_id
        )
        await kingdb.update_channel(chat.id, {"ani_type": ani_type})

        await client.send_message(
            LOG_CHANNEL,
            f"🤖 **AUTO INDEXED (Bot Added By Admin)**\n\n📛 **Title:** {chat.title}\n"
            f"🆔 **ID:** `{chat.id}`\n⚙️ **Type:** {ani_type.upper()}\n"
            f"👤 **Added By:** {event.from_user.mention}\n⏰ **Time:** {get_time()}",
            reply_markup=get_log_markup(chat.id)
        )
    except Exception as e:
        print(f"Auto Index Error: {e}")

# ================= 4. CALLBACKS ================= #
@Bot.on_callback_query(filters.regex(r"^(remove_|settype_)"), group=-1)
async def log_channel_cb(client, query):
    user_id = query.from_user.id
    admins = await kingdb.get_all_admins()

    if user_id != OWNER_ID and user_id not in admins:
        return await query.answer("❌ You are not authorized.", show_alert=True)

    data = query.data

    if data.startswith("remove_"):
        chat_id = int(data.split("_")[1])
        await kingdb.del_channel(chat_id)
        await query.message.edit_text(f"🗑 **Channel Removed Permanently:** `{chat_id}`")
        
    elif data.startswith("settype_"):
        parts = data.split("_")
        new_type = parts[1] 
        chat_id = int(parts[2])
        
        await kingdb.update_channel(chat_id, {"ani_type": new_type})
        await query.answer(f"✅ Category updated to {new_type.upper()}!", show_alert=True)
