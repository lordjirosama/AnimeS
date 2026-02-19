import asyncio
from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from bot import Bot
from database.database import kingdb
from config import OWNER_ID

# --- HELPERS ---
async def is_admin(user_id):
    admins = await kingdb.get_all_admins()
    return user_id == OWNER_ID or user_id in admins

def format_time(seconds):
    if seconds >= 3600:
        return f"{seconds // 3600} Hᴏᴜʀs"
    elif seconds >= 60:
        return f"{seconds // 60} Mɪɴᴜᴛᴇs"
    else:
        return f"{seconds} Sᴇᴄᴏɴᴅs"

# --- UI BUILDERS ---

async def get_searchmode_ui(chat_id):
    mode = await kingdb.get_search_mode(chat_id)
    
    if mode == "command":
        cmd_text = "Eɴᴀʙʟᴇᴅ ✅"
        auto_text = "Dɪsᴀʙʟᴇᴅ ✖️"
        btn_row = [
            InlineKeyboardButton("Cᴏᴍᴍᴀɴᴅ ✅", callback_data="smode_command"),
            InlineKeyboardButton("Aᴜᴛᴏ ✖️", callback_data="smode_auto")
        ]
    else:
        cmd_text = "Dɪsᴀʙʟᴇᴅ ✖️"
        auto_text = "Eɴᴀʙʟᴇᴅ ✅"
        btn_row = [
            InlineKeyboardButton("Aᴜᴛᴏ ✅", callback_data="smode_auto"),
            InlineKeyboardButton("Cᴏᴍᴍᴀɴᴅ ✖️", callback_data="smode_command")
        ]

    text = (
        "🤖 **𝗦𝗲𝗮𝗿𝗰𝗵 𝗠𝗼𝗱𝗲 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦** ⚙️\n\n"
        f"🗑️ sᴇᴀʀᴄʜ ᴄᴏᴍᴍᴀɴᴅ ᴍᴏᴅᴇ : {cmd_text}\n"
        f"🗑️ ᴀᴜᴛᴏ sᴇᴀʀᴄʜ ᴍᴏᴅᴇ : {auto_text}\n\n"
        "ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴs ᴛᴏ ᴄʜᴀɴɢᴇ sᴇᴛᴛɪɴɢs"
    )

    markup = InlineKeyboardMarkup([
        btn_row,
        [
            InlineKeyboardButton("🔄 Rᴇғʀᴇsʜ", callback_data="smode_refresh"),
            InlineKeyboardButton("✖️ Cʟᴏsᴇ", callback_data="close_panel")
        ]
    ])
    return text, markup

async def get_autodel_ui():
    status = await kingdb.get_auto_delete()
    timer_secs = await kingdb.get_del_timer()
    time_str = format_time(timer_secs)

    status_text = "Eɴᴀʙʟᴇᴅ ✅" if status else "Dɪsᴀʙʟᴇᴅ ✖️"
    toggle_btn = "❌ Dɪsᴀʙʟᴇ" if status else "✅ Eɴᴀʙʟᴇ"

    text = (
        "🤖 **𝗔𝗨𝗧𝗢 𝗗𝗘𝗟𝗘𝗧𝗘 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦** ⚙️\n\n"
        f"🗑️ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴍᴏᴅᴇ: {status_text}\n"
        f"⏱ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ: {time_str}\n\n"
        "ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴs ᴛᴏ ᴄʜᴀɴɢᴇ sᴇᴛᴛɪɴɢs"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(toggle_btn, callback_data="autodel_toggle"),
            InlineKeyboardButton("⏱ Sᴇᴛ Tɪᴍᴇʀ", callback_data="autodel_settimer")
        ],
        [
            InlineKeyboardButton("🔄 Rᴇғʀᴇsʜ", callback_data="autodel_refresh"),
            InlineKeyboardButton("✖️ Cʟᴏsᴇ", callback_data="close_panel")
        ]
    ])
    return text, markup


# ================= 1. APPROVE GROUP ================= #
@Bot.on_message(filters.command("approve") & filters.group)
async def approve_group(client, message):
    if not await is_admin(message.from_user.id): 
        return
    
    chat_id = message.chat.id
    status = await kingdb.is_group_approved(chat_id)
    
    text = f"⚙️ **Group Status:** {'✅ Approved' if status else '❌ Not Approved'}"
    btn = [[InlineKeyboardButton("✅ Approve" if not status else "❌ Unapprove", callback_data="toggle_approve")]]
    
    await message.reply(text, reply_markup=InlineKeyboardMarkup(btn))

# ================= 2. SEARCH MODE ================= #
@Bot.on_message(filters.command("searchmode") & filters.group)
async def search_mode_cmd(client, message):
    if not await is_admin(message.from_user.id): 
        return
    
    text, markup = await get_searchmode_ui(message.chat.id)
    await message.reply(text, reply_markup=markup)

# ================= 3. AUTO DELETE SETTINGS ================= #
@Bot.on_message(filters.command("autodelete"))
async def auto_delete_cmd(client, message):
    if not await is_admin(message.from_user.id): 
        return
    
    text, markup = await get_autodel_ui()
    await message.reply(text, reply_markup=markup)

# ================= 4. JOIN MODE ================= #
@Bot.on_message(filters.command("setjoinmode") & filters.private)
async def set_join_mode(client, message):
    if not await is_admin(message.from_user.id): 
        return

    text = "**🔗 Join Mode Settings**\nSelect how users should join your channels."
    btn = [
        [InlineKeyboardButton("🌍 Global Direct", callback_data="gmode_direct"),
         InlineKeyboardButton("🌍 Global Request", callback_data="gmode_request")],
        [InlineKeyboardButton("🎯 Change Particular", callback_data="gmode_particular")]
    ]
    await message.reply(text, reply_markup=InlineKeyboardMarkup(btn))

# ================= 5. CALLBACKS ================= #
@Bot.on_callback_query()
async def settings_callback(client, query):
    data = query.data
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    if not await is_admin(user_id):
        return await query.answer("❌ You are not authorized to perform this action.", show_alert=True)

    # --- CLOSE PANEL ---
    if data == "close_panel":
        return await query.message.delete()

    # --- GROUP APPROVAL ---
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
        if data == "smode_auto":
            await kingdb.set_search_mode(chat_id, "auto")
        elif data == "smode_command":
            await kingdb.set_search_mode(chat_id, "command")
        elif data == "smode_refresh":
            await query.answer("Refreshed! 🔄")
        
        text, markup = await get_searchmode_ui(chat_id)
        try:
            await query.message.edit_text(text, reply_markup=markup)
        except Exception:
            pass 

    # --- AUTO DELETE TOGGLE ---
    elif data == "autodel_toggle":
        curr = await kingdb.get_auto_delete()
        await kingdb.set_auto_delete(not curr)
        text, markup = await get_autodel_ui()
        try:
            await query.message.edit_text(text, reply_markup=markup)
        except Exception:
            pass

    elif data == "autodel_refresh":
        text, markup = await get_autodel_ui()
        try:
            await query.message.edit_text(text, reply_markup=markup)
        except Exception:
            await query.answer("Already updated! 🔄")

    # --- SET TIMER WITH TIMEOUT (USING PYROMOD) ---
    elif data == "autodel_settimer":
        await query.message.delete()
        timer_secs = await kingdb.get_del_timer()
        time_str = format_time(timer_secs)

        prompt_text = (
            f"⏱ Cᴜʀʀᴇɴᴛ Tɪᴍᴇʀ: {time_str}\n\n"
            "Tᴏ ᴄʜᴀɴɢᴇ ᴛɪᴍᴇʀ, Pʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ ɪɴ sᴇᴄᴏɴᴅs ᴡɪᴛʜɪɴ 1 ᴍɪɴᴜᴛᴇ.\n"
            "Fᴏʀ ᴇxᴀᴍᴘʟᴇ: 300, 600, 900"
        )
        
        try:
            # Requires pyromod installed (client.ask)
            answer = await client.ask(chat_id, prompt_text, timeout=60, filters=filters.user(user_id))
            
            new_time = int(answer.text)
            await kingdb.set_del_timer(new_time)
            await answer.reply(f"✅ Auto-delete timer successfully updated to **{format_time(new_time)}**.")
            
        except asyncio.TimeoutError:
            await client.send_message(chat_id, "❗️ Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ..\n\nRᴇᴀsᴏɴ: 1 minute Time out ..")
        except ValueError:
            await client.send_message(chat_id, "❗️ Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ..\n\nRᴇᴀsᴏɴ: Invalid number format. Please send digits only.")

    # --- GLOBAL MODES ---
    elif data == "gmode_direct":
        channels = await kingdb.get_indexed_channels()
        for ch in channels:
            await kingdb.update_channel_join_mode(ch['_id'], "direct")
        await query.answer("All channels updated.")
        await query.message.edit_text("✅ All channels have been set to **DIRECT LINK**.")

    elif data == "gmode_request":
        channels = await kingdb.get_indexed_channels()
        for ch in channels:
            await kingdb.update_channel_join_mode(ch['_id'], "request")
        await query.answer("All channels updated.")
        await query.message.edit_text("✅ All channels have been set to **REQUEST LINK**.")

    # --- PARTICULAR MODE ---
    elif data == "gmode_particular":
        await query.message.delete()
        await client.send_message(
            chat_id, 
            "🆔 **Please send the Channel ID:**\nExample: `-1001234567890`", 
            reply_markup=ForceReply(True)
        )

    # --- SET PARTICULAR MODE ---
    elif data.startswith("part_"):
        try:
            _, mode, ch_id = data.split("_")
            await kingdb.update_channel_join_mode(int(ch_id), mode)
            await query.message.edit_text(f"✅ Join mode for channel `{ch_id}` has been set to **{mode.upper()}**.")
        except Exception as e:
            await query.answer(f"Error: {e}")

# ================= 6. FORCE REPLY HANDLER (For Particular ID) ================= #
@Bot.on_message(filters.reply & filters.private)
async def particular_reply_handler(client, message):
    if not message.reply_to_message.reply_markup: return
    if not isinstance(message.reply_to_message.reply_markup, ForceReply): return

    try:
        channel_id = int(message.text.strip())
        
        ch = await kingdb.get_channel(channel_id)
        if not ch:
            return await message.reply("❌ This channel is not found in the database.")

        btn = [
            [InlineKeyboardButton("Direct Link", callback_data=f"part_direct_{channel_id}"),
             InlineKeyboardButton("Request Link", callback_data=f"part_request_{channel_id}")]
        ]
        
        await message.reply(
            f"⚙️ **Settings for:** `{ch.get('title')}`\nSelect the desired join mode:", 
            reply_markup=InlineKeyboardMarkup(btn)
        )

    except ValueError:
        await message.reply("❌ Please send a valid numeric ID (e.g., -100...).")
