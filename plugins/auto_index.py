import asyncio
import random
import datetime
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated, InputMediaPhoto
from bot import Bot
from database.database import kingdb
from config import OWNER_ID, LOG_CHANNEL, PICS

# --- STATE MANAGEMENT ---
index_wait = set()
blacklisted_chats = set()

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
        [InlineKeyboardButton("🗑 Remove", callback_data=f"log_remove_{chat_id}"),
         InlineKeyboardButton("✖️ Close", callback_data="close_panel")]
    ])

# ================= UI BUILDERS ================= #

def get_index_panel_ui():
    text = (
        "🤖 **Index Management Panel** ⚙️\n\n"
        "Welcome to the Central Indexing Dashboard. Please select an action below to manage your indexed channels."
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Index", callback_data="idx_add"), InlineKeyboardButton("🗑 Remove Index", callback_data="idx_remove")],
        [InlineKeyboardButton("📋 Index List", callback_data="idx_list"), InlineKeyboardButton("🔄 Reindex All", callback_data="idx_reindex")],
        [InlineKeyboardButton("♻️ Refresh", callback_data="idx_refresh"), InlineKeyboardButton("✖️ Close", callback_data="close_panel")]
    ])
    return text, markup

def get_index_list_ui():
    text = (
        "📋 **Indexed Channels List**\n\n"
        "Select a category below to view the currently indexed channels."
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Anime Channels", callback_data="idx_show_anime"), InlineKeyboardButton("📖 Manga Channels", callback_data="idx_show_manga")],
        [InlineKeyboardButton("🌍 All Channels", callback_data="idx_show_all")],
        [InlineKeyboardButton("🔙 Back", callback_data="idx_back"), InlineKeyboardButton("✖️ Close", callback_data="close_panel")]
    ])
    return text, markup

async def is_admin(user_id):
    admins = await kingdb.get_all_admins()
    return user_id == OWNER_ID or user_id in admins

# ================= 1. /INDEX COMMAND (DASHBOARD) ================= #
@Bot.on_message(filters.command("index") & filters.private, group=-1)
async def index_cmd(client, message):
    if not await is_admin(message.from_user.id):
        return await message.reply("❌ **Only Admins are allowed to use this command.**")

    text, markup = get_index_panel_ui()
    await message.reply_photo(photo=random.choice(PICS), caption=text, reply_markup=markup)
    message.stop_propagation()

# ================= 2. DASHBOARD CALLBACKS ================= #
@Bot.on_callback_query(filters.regex(r"^(idx_|log_remove_|settype_)"), group=-1)
async def index_callbacks(client, query):
    user_id = query.from_user.id
    if not await is_admin(user_id):
        return await query.answer("❌ You are not authorized.", show_alert=True)

    data = query.data

    if data == "idx_refresh" or data == "idx_back":
        text, markup = get_index_panel_ui()
        try: 
            await query.message.edit_media(media=InputMediaPhoto(media=random.choice(PICS), caption=text), reply_markup=markup)
        except Exception: 
            await query.answer("Already updated! 🔄")

    elif data == "idx_list":
        text, markup = get_index_list_ui()
        try:
            await query.message.edit_media(media=InputMediaPhoto(media=random.choice(PICS), caption=text), reply_markup=markup)
        except Exception:
            pass

    # --- ADD INDEX (FIX: Store in DB instead of memory) ---
    elif data == "idx_add":
        # ✅ FIX: Save to DB so it survives bot restart
        await kingdb.set_user_state(user_id, "index_wait")
        index_wait.add(user_id)
        
        print(f"[DEBUG] idx_add: Added user {user_id} to index_wait. Current set: {index_wait}")
        
        await query.answer("Forward mode activated! Send a message now.", show_alert=True)
        await query.message.reply(
            "📥 **Indexing Mode Activated**\n\n"
            "Please **Forward** a message from the target Channel or Group.\n"
            "_(Note: The bot must be an admin there)_\n\n"
            f"🔑 **Your Session ID:** `{user_id}` _(for debug)_"
        )

    elif data == "idx_remove":
        await query.message.delete()
        try:
            ask = await client.ask(
                query.message.chat.id, 
                "🗑 **Send the Channel ID to remove:**\nExample: `-1001234567890`\n\n_Note: You have 60 seconds to reply._", 
                timeout=60, 
                filters=filters.user(user_id)
            )
            ch_id = int(ask.text.strip())
            await kingdb.del_indexed_channel(ch_id) 
            blacklisted_chats.add(ch_id) 

            text, markup = get_index_panel_ui()
            await ask.reply_photo(
                photo=random.choice(PICS),
                caption=f"✅ **Channel `{ch_id}` removed successfully!**\n\n🚫 _Blacklisted._",
                reply_markup=markup
            )
        except asyncio.TimeoutError:
            await client.send_message(query.message.chat.id, "❗️ **Error:** Request timed out.")
        except ValueError:
            await client.send_message(query.message.chat.id, "❗️ **Error:** Invalid ID format.")

    elif data.startswith("idx_show_"):
        cat = data.split("_")[2]
        channels = await kingdb.get_indexed_channels()
        
        if cat != "all":
            channels = [ch for ch in channels if ch.get("ani_type", "anime") == cat]
            
        if not channels:
            return await query.answer(f"❌ No {cat.capitalize()} channels found!", show_alert=True)
            
        msg_text = f"📋 **{cat.capitalize()} Indexed Channels:**\n\n"
        for ch in channels:
            title = ch.get('title', 'Unknown')
            msg_text += f"▪️ **{title}** (`{ch['_id']}`)\n"
            
        if len(msg_text) > 1000:
            msg_text = msg_text[:950] + "\n\n_...and more (List truncated)._"
            
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to List", callback_data="idx_list")]])
        try:
            await query.message.edit_media(media=InputMediaPhoto(media=random.choice(PICS), caption=msg_text), reply_markup=markup)
        except Exception:
            pass

    elif data == "idx_reindex":
        await query.message.delete()
        status_msg = await client.send_message(query.message.chat.id, "🔄 **Reindexing started...**")
        
        channels = await kingdb.get_indexed_channels()
        success, failed = 0, 0
        
        for ch in channels:
            try:
                chat = await client.get_chat(ch['_id'])
                await kingdb.add_or_update_channel(
                    channel_id=chat.id,
                    title=chat.title,
                    username=chat.username,
                    join_mode=ch.get("join_mode", "direct"),
                    expire_seconds=ch.get("expire_seconds", 600),
                    added_by=ch.get("added_by", OWNER_ID)
                )
                await kingdb.update_channel(chat.id, {"ani_type": ch.get("ani_type", "anime")})
                success += 1
                await asyncio.sleep(1)
            except Exception:
                failed += 1

        text, markup = get_index_panel_ui()
        await status_msg.delete()
        await client.send_photo(
            query.message.chat.id,
            photo=random.choice(PICS),
            caption=f"✅ **Reindex Done!**\n\n✔️ Updated: `{success}`\n❌ Failed: `{failed}`\n\n" + text,
            reply_markup=markup
        )

    elif data.startswith("log_remove_"):
        chat_id = int(data.split("_")[2])
        await kingdb.del_indexed_channel(chat_id)
        blacklisted_chats.add(chat_id)
        await query.message.edit_text(f"🗑 **Channel Removed:** `{chat_id}`")
        
    elif data.startswith("settype_"):
        parts = data.split("_")
        new_type = parts[1]
        chat_id = int(parts[2])
        await kingdb.update_channel(chat_id, {"ani_type": new_type})
        await query.answer(f"✅ Category updated to {new_type.upper()}!", show_alert=True)


# ================= 3. FORWARD HANDLER (MANUAL ADD) ================= #
@Bot.on_message(filters.private & filters.forwarded, group=-1)
async def index_forward(client, message):
    user_id = message.from_user.id
    
    print(f"[DEBUG] Forward received from user: {user_id}")
    print(f"[DEBUG] Current index_wait set: {index_wait}")
    
    # ✅ FIX: Check DB state as fallback (survives bot restart)
    in_memory = user_id in index_wait
    db_state = await kingdb.get_user_state(user_id)
    in_db = db_state == "index_wait"
    
    print(f"[DEBUG] in_memory={in_memory}, in_db={in_db}, db_state={db_state}")
    
    if not in_memory and not in_db:
        print(f"[DEBUG] User {user_id} NOT in index_wait — skipping forward handler")
        return  # Let other handlers process it
    
    # Clean up state
    index_wait.discard(user_id)
    await kingdb.clear_user_state(user_id)
    
    print(f"[DEBUG] Processing forward for indexing...")
    print(f"[DEBUG] message.forward_from_chat = {message.forward_from_chat}")
    print(f"[DEBUG] message.sender_chat = {message.sender_chat}")
    print(f"[DEBUG] hasattr forward_origin = {hasattr(message, 'forward_origin')}")
    
    # ✅ FIX: Multi-method chat detection
    chat = None

    # Method 1: New Telegram API — forward_origin
    if hasattr(message, 'forward_origin') and message.forward_origin:
        origin = message.forward_origin
        print(f"[DEBUG] forward_origin type = {type(origin)}, attrs = {dir(origin)}")
        if hasattr(origin, 'chat') and origin.chat:
            chat = origin.chat
            print(f"[DEBUG] Chat found via forward_origin.chat: {chat.id} - {chat.title}")

    # Method 2: Classic forward_from_chat
    if not chat and message.forward_from_chat:
        chat = message.forward_from_chat
        print(f"[DEBUG] Chat found via forward_from_chat: {chat.id} - {chat.title}")

    # Method 3: sender_chat
    if not chat and message.sender_chat:
        chat = message.sender_chat
        print(f"[DEBUG] Chat found via sender_chat: {chat.id} - {chat.title}")

    # Method 4: Try get_chat on forward_origin chat id
    if not chat and hasattr(message, 'forward_origin') and message.forward_origin:
        try:
            origin = message.forward_origin
            if hasattr(origin, 'chat_id'):
                chat = await client.get_chat(origin.chat_id)
                print(f"[DEBUG] Chat found via get_chat(origin.chat_id): {chat.id}")
        except Exception as e:
            print(f"[DEBUG] Method 4 failed: {e}")

    print(f"[DEBUG] Final chat resolved: {chat}")

    if not chat:
        await message.reply(
            "❌ **Could not detect source channel!**\n\n"
            "**Possible reasons:**\n"
            "▪️ Channel has **forwarding privacy** enabled\n"
            "▪️ You forwarded from a **user/group** instead of a channel\n\n"
            "**Solution:** Add the bot as admin to the channel first, then try /index again."
        )
        return message.stop_propagation()

    try:
        if chat.id in blacklisted_chats:
            blacklisted_chats.discard(chat.id)
            print(f"[DEBUG] Removed {chat.id} from blacklist")

        ani_type = detect_type(chat.title or "")
        print(f"[DEBUG] Detected ani_type: {ani_type} for title: {chat.title}")
        
        await kingdb.add_or_update_channel(
            channel_id=chat.id,
            title=chat.title or "Unknown Title",
            username=getattr(chat, 'username', None),
            join_mode="direct",
            expire_seconds=600,
            added_by=user_id
        )
        await kingdb.update_channel(chat.id, {"ani_type": ani_type})
        
        print(f"[DEBUG] ✅ Successfully indexed channel: {chat.id}")

        text, markup = get_index_panel_ui()
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=(
                f"✅ **Successfully Indexed!**\n\n"
                f"📛 **Title:** {chat.title}\n"
                f"🆔 **ID:** `{chat.id}`\n"
                f"⚙️ **Detected Type:** {ani_type.upper()}\n\n"
                "You can change the category via the log channel buttons."
            ),
            reply_markup=markup
        )

        await client.send_message(
            LOG_CHANNEL,
            f"✅ **NEW INDEX ADDED**\n\n📛 **Title:** {chat.title}\n🆔 **ID:** `{chat.id}`\n"
            f"⚙️ **Type:** {ani_type.upper()}\n👤 **Added By:** {message.from_user.mention}\n⏰ **Time:** {get_time()}",
            reply_markup=get_log_markup(chat.id)
        )

    except Exception as e:
        print(f"[DEBUG] ❌ Exception during indexing: {e}")
        await message.reply(f"❌ **Error:** `{e}`")

    message.stop_propagation()


# ================= 4. AUTO ADD ON BOT JOIN ================= #
@Bot.on_chat_member_updated()
async def auto_index_on_add(client, event: ChatMemberUpdated):
    is_bot_added = False
    
    if event.new_chat_member and event.new_chat_member.user.is_self:
        if event.new_chat_member.status in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR]:
            is_bot_added = True

    if not is_bot_added:
        return

    chat = event.chat
    if chat.type not in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP]:
        return

    if chat.id in blacklisted_chats:
        return

    adder_id = event.from_user.id
    admins = await kingdb.get_all_admins()
    
    if adder_id != OWNER_ID and adder_id not in admins:
        try: await client.leave_chat(chat.id)
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
