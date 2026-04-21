import asyncio
import random
import datetime
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated, InputMediaPhoto
from bot import Bot
from database.database import kingdb
from config import OWNER_ID, LOG_CHANNEL, PICS

# --- STATE MANAGEMENT ---
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
        [InlineKeyboardButton("➕ Add Index", callback_data="idx_add"),
         InlineKeyboardButton("🗑 Remove Index", callback_data="idx_remove")],
        [InlineKeyboardButton("📋 Index List", callback_data="idx_list"),
         InlineKeyboardButton("🔄 Reindex All", callback_data="idx_reindex")],
        [InlineKeyboardButton("♻️ Refresh", callback_data="idx_refresh"),
         InlineKeyboardButton("✖️ Close", callback_data="close_panel")]
    ])
    return text, markup

def get_index_list_ui():
    text = (
        "📋 **Indexed Channels List**\n\n"
        "Select a category below to view the currently indexed channels."
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Anime Channels", callback_data="idx_show_anime"),
         InlineKeyboardButton("📖 Manga Channels", callback_data="idx_show_manga")],
        [InlineKeyboardButton("🌍 All Channels", callback_data="idx_show_all")],
        [InlineKeyboardButton("🔙 Back", callback_data="idx_back"),
         InlineKeyboardButton("✖️ Close", callback_data="close_panel")]
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

    # --- REFRESH / BACK ---
    if data == "idx_refresh" or data == "idx_back":
        text, markup = get_index_panel_ui()
        try:
            await query.message.edit_media(
                media=InputMediaPhoto(media=random.choice(PICS), caption=text),
                reply_markup=markup
            )
        except Exception:
            await query.answer("Already updated! 🔄")

    # --- INDEX LIST ---
    elif data == "idx_list":
        text, markup = get_index_list_ui()
        try:
            await query.message.edit_media(
                media=InputMediaPhoto(media=random.choice(PICS), caption=text),
                reply_markup=markup
            )
        except Exception:
            pass

    # ✅ ADD INDEX — listen() based, no state/memory needed
    elif data == "idx_add":
        await query.message.delete()
        try:
            prompt = await client.send_message(
                user_id,
                "📥 **Indexing Mode Activated**\n\n"
                "Please **Forward** a message from the target Channel or Group.\n"
                "_(Note: The bot must be an admin there)_\n\n"
                "/cancel - to cancel"
            )

            # Wait for user to forward a message (120 second timeout)
            fwd_msg = await client.listen(chat_id=user_id, timeout=120)

            # Cancel check
            if fwd_msg.text and fwd_msg.text.strip() == "/cancel":
                await fwd_msg.delete()
                await prompt.delete()
                text, markup = get_index_panel_ui()
                return await client.send_photo(
                    user_id,
                    photo=random.choice(PICS),
                    caption="❌ **Indexing Cancelled.**",
                    reply_markup=markup
                )

            # ✅ Multi-method chat detection
            chat = None

            # Method 1: forward_origin (new Telegram API — Pyrogram 2.x)
            if hasattr(fwd_msg, 'forward_origin') and fwd_msg.forward_origin:
                origin = fwd_msg.forward_origin
                print(f"[DEBUG] forward_origin = {origin}, type = {type(origin)}")
                if hasattr(origin, 'chat') and origin.chat:
                    chat = origin.chat
                    print(f"[DEBUG] Method 1 success: {chat.id} - {chat.title}")

            # Method 2: forward_from_chat (classic)
            if not chat and fwd_msg.forward_from_chat:
                chat = fwd_msg.forward_from_chat
                print(f"[DEBUG] Method 2 success: {chat.id} - {chat.title}")

            # Method 3: sender_chat (anonymous channel post)
            if not chat and fwd_msg.sender_chat:
                chat = fwd_msg.sender_chat
                print(f"[DEBUG] Method 3 success: {chat.id} - {chat.title}")

            # Method 4: get_chat via origin.chat_id
            if not chat and hasattr(fwd_msg, 'forward_origin') and fwd_msg.forward_origin:
                try:
                    origin = fwd_msg.forward_origin
                    if hasattr(origin, 'chat_id'):
                        chat = await client.get_chat(origin.chat_id)
                        print(f"[DEBUG] Method 4 success: {chat.id} - {chat.title}")
                except Exception as e:
                    print(f"[DEBUG] Method 4 failed: {e}")

            print(f"[DEBUG] forward_from_chat = {fwd_msg.forward_from_chat}")
            print(f"[DEBUG] sender_chat = {fwd_msg.sender_chat}")
            print(f"[DEBUG] Final resolved chat = {chat}")

            if not chat:
                await fwd_msg.delete()
                await prompt.delete()
                text, markup = get_index_panel_ui()
                return await client.send_photo(
                    user_id,
                    photo=random.choice(PICS),
                    caption=(
                        "❌ **Could not detect source channel!**\n\n"
                        "**Possible reasons:**\n"
                        "▪️ Channel has **forwarding privacy** enabled\n"
                        "▪️ You forwarded from a user/group instead of a channel\n\n"
                        "**Solution:** Add the bot as admin in the channel, then retry."
                    ),
                    reply_markup=markup
                )

            # ✅ Remove from blacklist if previously removed
            if chat.id in blacklisted_chats:
                blacklisted_chats.discard(chat.id)
                print(f"[DEBUG] Removed {chat.id} from blacklist")

            ani_type = detect_type(chat.title or "")
            print(f"[DEBUG] Detected type: {ani_type} for title: {chat.title}")

            await kingdb.add_or_update_channel(
                channel_id=chat.id,
                title=chat.title or "Unknown Title",
                username=getattr(chat, 'username', None),
                join_mode="direct",
                expire_seconds=600,
                added_by=user_id
            )
            await kingdb.update_channel(chat.id, {"ani_type": ani_type})

            print(f"[DEBUG] ✅ Successfully indexed: {chat.id} - {chat.title}")

            await fwd_msg.delete()
            await prompt.delete()

            text, markup = get_index_panel_ui()
            await client.send_photo(
                user_id,
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
                f"✅ **NEW INDEX ADDED**\n\n"
                f"📛 **Title:** {chat.title}\n"
                f"🆔 **ID:** `{chat.id}`\n"
                f"⚙️ **Type:** {ani_type.upper()}\n"
                f"👤 **Added By:** {query.from_user.mention}\n"
                f"⏰ **Time:** {get_time()}",
                reply_markup=get_log_markup(chat.id)
            )

        except asyncio.TimeoutError:
            text, markup = get_index_panel_ui()
            await client.send_photo(
                user_id,
                photo=random.choice(PICS),
                caption="⏰ **Timed out!** Please click Add Index and try again.",
                reply_markup=markup
            )
        except Exception as e:
            print(f"[DEBUG] idx_add Exception: {e}")
            await client.send_message(user_id, f"❌ **Error:** `{e}`")

    # --- REMOVE INDEX ---
    elif data == "idx_remove":
        await query.message.delete()
        try:
            ask = await client.ask(
                query.message.chat.id,
                "🗑 **Send the Channel ID to remove:**\n"
                "Example: `-1001234567890`\n\n"
                "_Note: You have 60 seconds to reply._",
                timeout=60,
                filters=filters.user(user_id)
            )
            ch_id = int(ask.text.strip())
            await kingdb.del_indexed_channel(ch_id)
            blacklisted_chats.add(ch_id)

            text, markup = get_index_panel_ui()
            await ask.reply_photo(
                photo=random.choice(PICS),
                caption=(
                    f"✅ **Channel `{ch_id}` removed successfully!**\n\n"
                    "🚫 _It has been blacklisted and will not be auto-indexed again "
                    "unless manually added via the Add Index button._"
                ),
                reply_markup=markup
            )
        except asyncio.TimeoutError:
            await client.send_message(query.message.chat.id, "❗️ **Error:** Request timed out. Please try again.")
        except ValueError:
            await client.send_message(query.message.chat.id, "❗️ **Error:** Invalid ID format. Please provide a numeric ID.")

    # --- SHOW LISTS (ANIME / MANGA / ALL) ---
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
            await query.message.edit_media(
                media=InputMediaPhoto(media=random.choice(PICS), caption=msg_text),
                reply_markup=markup
            )
        except Exception:
            pass

    # --- REINDEX ALL ---
    elif data == "idx_reindex":
        await query.message.delete()
        status_msg = await client.send_message(
            query.message.chat.id,
            "🔄 **Reindexing started...**\n_Please wait, fetching latest data from Telegram._"
        )

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
            caption=(
                f"✅ **Reindex Operation Completed!**\n\n"
                f"📊 **Successfully Updated:** `{success}`\n"
                f"❌ **Failed/Unavailable:** `{failed}`\n\n"
            ) + text,
            reply_markup=markup
        )

    # --- LOG CHANNEL: REMOVE ---
    elif data.startswith("log_remove_"):
        chat_id = int(data.split("_")[2])
        await kingdb.del_indexed_channel(chat_id)
        blacklisted_chats.add(chat_id)
        await query.message.edit_text(f"🗑 **Channel Removed Permanently:** `{chat_id}`")

    # --- LOG CHANNEL: SET TYPE ---
    elif data.startswith("settype_"):
        parts = data.split("_")
        new_type = parts[1]
        chat_id = int(parts[2])
        await kingdb.update_channel(chat_id, {"ani_type": new_type})
        await query.answer(f"✅ Category updated to {new_type.upper()}!", show_alert=True)


# ================= 3. AUTO ADD ON BOT JOIN ================= #
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
        try:
            await client.leave_chat(chat.id)
        except Exception:
            pass
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
            f"🤖 **AUTO INDEXED (Bot Added By Admin)**\n\n"
            f"📛 **Title:** {chat.title}\n"
            f"🆔 **ID:** `{chat.id}`\n"
            f"⚙️ **Type:** {ani_type.upper()}\n"
            f"👤 **Added By:** {event.from_user.mention}\n"
            f"⏰ **Time:** {get_time()}",
            reply_markup=get_log_markup(chat.id)
        )
    except Exception as e:
        print(f"[DEBUG] Auto Index Error: {e}")
