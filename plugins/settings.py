from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from bot import Bot
from database.database import kingdb
from config import OWNER_ID

# --- HELPERS ---
async def is_admin(user_id):
    admins = await kingdb.get_all_admins()
    return user_id == OWNER_ID or user_id in admins

# ================= 1. APPROVE GROUP ================= #
@Bot.on_message(filters.command("approve") & filters.group)
async def approve_group(client, message):
    if not await is_admin(message.from_user.id): return
    
    chat_id = message.chat.id
    status = await kingdb.is_group_approved(chat_id)
    
    text = f"⚙️ **Group Status:** {'✅ Approved' if status else '❌ Not Approved'}"
    btn = [[InlineKeyboardButton("✅ Approve" if not status else "❌ Unapprove", callback_data="toggle_approve")]]
    
    await message.reply(text, reply_markup=InlineKeyboardMarkup(btn))

# ================= 2. SEARCH MODE ================= #
@Bot.on_message(filters.command("searchmode") & filters.group)
async def search_mode_cmd(client, message):
    if not await is_admin(message.from_user.id): return
    
    mode = await kingdb.get_search_mode(message.chat.id)
    
    btn = [
        [InlineKeyboardButton(f"{'🟢' if mode=='auto' else '⚫️'} Auto Mode", callback_data="smode_auto"),
         InlineKeyboardButton(f"{'🟢' if mode=='command' else '⚫️'} Command Mode", callback_data="smode_command")]
    ]
    await message.reply("⚙️ **Select Search Mode:**", reply_markup=InlineKeyboardMarkup(btn))

# ================= 3. JOIN MODE (Direct/Request/Particular) ================= #
@Bot.on_message(filters.command("setjoinmode") & filters.private)
async def set_join_mode(client, message):
    if not await is_admin(message.from_user.id): return

    text = "**🔗 Join Mode Settings**\nSelect how users should join your channels."
    
    btn = [
        [InlineKeyboardButton("🌍 Global Direct", callback_data="gmode_direct"),
         InlineKeyboardButton("🌍 Global Request", callback_data="gmode_request")],
        [InlineKeyboardButton("🎯 Change Particular", callback_data="gmode_particular")]
    ]
    await message.reply(text, reply_markup=InlineKeyboardMarkup(btn))

# ================= 4. CALLBACKS ================= #
@Bot.on_callback_query()
async def settings_callback(client, query):
    data = query.data
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    if not await is_admin(user_id):
        return await query.answer("❌ Only Admins!", show_alert=True)

    # --- APPROVE TOGGLE ---
    if data == "toggle_approve":
        curr = await kingdb.is_group_approved(chat_id)
        if curr:
            await kingdb.disapprove_group(chat_id)
            await query.message.edit_text("⚙️ **Group Status:** ❌ Not Approved", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data="toggle_approve")]]))
        else:
            await kingdb.approve_group(chat_id)
            await query.message.edit_text("⚙️ **Group Status:** ✅ Approved", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Unapprove", callback_data="toggle_approve")]]))

    # --- SEARCH MODE ---
    elif data.startswith("smode_"):
        mode = data.split("_")[1]
        await kingdb.set_search_mode(chat_id, mode)
        await query.answer(f"Mode set to {mode.upper()}")
        await query.message.delete()

    # --- GLOBAL MODES ---
    elif data == "gmode_direct":
        # Note: Expensive operation if you have 1000s of channels
        channels = await kingdb.get_indexed_channels()
        for ch in channels:
            await kingdb.update_channel_join_mode(ch['_id'], "direct")
        await query.answer("All channels set to DIRECT")
        await query.message.edit_text("✅ All channels set to **DIRECT LINK**")

    elif data == "gmode_request":
        channels = await kingdb.get_indexed_channels()
        for ch in channels:
            await kingdb.update_channel_join_mode(ch['_id'], "request")
        await query.answer("All channels set to REQUEST")
        await query.message.edit_text("✅ All channels set to **REQUEST LINK**")

    # --- PARTICULAR MODE (Ask ID) ---
    elif data == "gmode_particular":
        await query.message.delete()
        await client.send_message(
            chat_id, 
            "🆔 **Send Channel ID:**\nExample: `-1001234567890`", 
            reply_markup=ForceReply(True)
        )

    # --- SET PARTICULAR ---
    elif data.startswith("part_"):
        # Format: part_mode_channelID
        try:
            _, mode, ch_id = data.split("_")
            await kingdb.update_channel_join_mode(int(ch_id), mode)
            await query.message.edit_text(f"✅ Channel `{ch_id}` set to **{mode.upper()}**")
        except Exception as e:
            await query.answer(f"Error: {e}")

# ================= 5. FORCE REPLY HANDLER (For Particular ID) ================= #
@Bot.on_message(filters.reply & filters.private)
async def particular_reply_handler(client, message):
    if not message.reply_to_message.reply_markup: return
    if not isinstance(message.reply_to_message.reply_markup, ForceReply): return

    try:
        channel_id = int(message.text.strip())
        
        # Check if channel exists in DB
        ch = await kingdb.get_channel(channel_id)
        if not ch:
            return await message.reply("❌ Ye Channel Indexed nahi hai.")

        btn = [
            [InlineKeyboardButton("Direct Link", callback_data=f"part_direct_{channel_id}"),
             InlineKeyboardButton("Request Link", callback_data=f"part_request_{channel_id}")]
        ]
        
        await message.reply(
            f"⚙️ **Settings for:** `{ch.get('title')}`\nSelect Join Mode:", 
            reply_markup=InlineKeyboardMarkup(btn)
        )

    except ValueError:
        await message.reply("❌ Valid Number ID bhejo (e.g., -100...)")
