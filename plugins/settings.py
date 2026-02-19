import asyncio
import random
from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from bot import Bot
from database.database import kingdb
from config import OWNER_ID

# ================= RANDOM PICS FOR SETTINGS ================= #
SETTINGS_PICS = [
    "https://envs.sh/ZUb.png?2ftEB=1",
    "https://envs.sh/ZUi.png?KNgjn=1",
    "https://envs.sh/oD5.jpg",
    "https://envs.sh/7nm.jpg",
    "https://envs.sh/Chb.jpg"
] 

# --- HELPERS ---
async def is_admin(user_id):
    admins = await kingdb.get_all_admins()
    return user_id == OWNER_ID or user_id in admins

def format_time(seconds):
    if seconds <= 0:
        return "Lɪғᴇᴛɪᴍᴇ (Nᴏ Exᴘɪʀᴇ) ✖️"
    if seconds >= 3600:
        return f"{seconds // 3600} Hᴏᴜʀs"
    elif seconds >= 60:
        return f"{seconds // 60} Mɪɴᴜᴛᴇs"
    else:
        return f"{seconds} Sᴇᴄᴏɴᴅs"

# ================= UI BUILDERS ================= #

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
        [InlineKeyboardButton("🔄 Rᴇғʀᴇsʜ", callback_data="smode_refresh"), InlineKeyboardButton("✖️ Cʟᴏsᴇ", callback_data="close_panel")]
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
        [InlineKeyboardButton(toggle_btn, callback_data="autodel_toggle"), InlineKeyboardButton("⏱ Sᴇᴛ Tɪᴍᴇʀ", callback_data="autodel_settimer")],
        [InlineKeyboardButton("🔄 Rᴇғʀᴇsʜ", callback_data="autodel_refresh"), InlineKeyboardButton("✖️ Cʟᴏsᴇ", callback_data="close_panel")]
    ])
    return text, markup

async def get_approve_ui(chat_id):
    status = await kingdb.is_group_approved(chat_id)
    status_text = "Eɴᴀʙʟᴇᴅ ✅" if status else "Dɪsᴀʙʟᴇᴅ ✖️"
    btn_text = "❌ Dɪsᴀʙʟᴇ Aᴘᴘʀᴏᴠᴀʟ" if status else "✅ Eɴᴀʙʟᴇ Aᴘᴘʀᴏᴠᴀʟ"
    
    text = (
        "🤖 **𝗚𝗿𝗼𝘂𝗽 𝗔𝗽𝗽𝗿𝗼𝘃𝗮𝗹 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦** ⚙️\n\n"
        f"🛡️ ᴄᴜʀʀᴇɴᴛ sᴛᴀᴛᴜs : {status_text}\n\n"
        "ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴs ᴛᴏ ᴄʜᴀɴɢᴇ sᴇᴛᴛɪɴɢs"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(btn_text, callback_data="toggle_approve")],
        [InlineKeyboardButton("🔄 Rᴇғʀᴇsʜ", callback_data="approve_refresh"), InlineKeyboardButton("✖️ Cʟᴏsᴇ", callback_data="close_panel")]
    ])
    return text, markup

async def get_joinmode_ui():
    text = (
        "🤖 **𝗝𝗼𝗶𝗻 𝗠𝗼𝗱𝗲 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦** ⚙️\n\n"
        "🔗 sᴇʟᴇᴄᴛ ʜᴏᴡ ᴜsᴇʀs sʜᴏᴜʟᴅ ᴊᴏɪɴ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟs.\n\n"
        "ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴs ᴛᴏ ᴄʜᴀɴɢᴇ sᴇᴛᴛɪɴɢs"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Gʟᴏʙᴀʟ Dɪʀᴇᴄᴛ", callback_data="gmode_direct"), InlineKeyboardButton("🌍 Gʟᴏʙᴀʟ Rᴇǫᴜᴇsᴛ", callback_data="gmode_request")],
        [InlineKeyboardButton("🎯 Cʜᴀɴɢᴇ Pᴀʀᴛɪᴄᴜʟᴀʀ", callback_data="gmode_particular")],
        [InlineKeyboardButton("🔄 Rᴇғʀᴇsʜ", callback_data="joinmode_refresh"), InlineKeyboardButton("✖️ Cʟᴏsᴇ", callback_data="close_panel")]
    ])
    return text, markup

async def get_linkexpire_ui():
    channels = await kingdb.get_indexed_channels()
    current_expire = channels[0].get("expire_seconds", 0) if channels else 0
    time_str = format_time(current_expire)

    text = (
        "🤖 **𝗟𝗶𝗻𝗸 𝗘𝘅𝗽𝗶𝗿𝗮𝘁𝗶𝗼𝗻 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦** ⚙️\n\n"
        f"⏳ ᴄᴜʀʀᴇɴᴛ ᴇxᴘɪʀᴀᴛɪᴏɴ : {time_str}\n\n"
        "ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴs ᴛᴏ ᴄʜᴀɴɢᴇ sᴇᴛᴛɪɴɢs"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱ Sᴇᴛ Exᴘɪʀᴇ Tɪᴍᴇ", callback_data="expire_settimer"), InlineKeyboardButton("✖️ Rᴇᴍᴏᴠᴇ Exᴘɪʀᴇ", callback_data="expire_remove")],
        [InlineKeyboardButton("🔄 Rᴇғʀᴇsʜ", callback_data="expire_refresh"), InlineKeyboardButton("✖️ Cʟᴏsᴇ", callback_data="close_panel")]
    ])
    return text, markup


# ================= COMMANDS (SUPER HIGH PRIORITY: group=-2) ================= #

@Bot.on_message(filters.command("approve") & filters.group, group=-2)
async def approve_cmd(client, message):
    if not await is_admin(message.from_user.id): return
    text, markup = await get_approve_ui(message.chat.id)
    await message.reply_photo(photo=random.choice(SETTINGS_PICS), caption=text, reply_markup=markup)
    message.stop_propagation()

@Bot.on_message(filters.command("searchmode") & filters.group, group=-2)
async def search_mode_cmd(client, message):
    if not await is_admin(message.from_user.id): return
    text, markup = await get_searchmode_ui(message.chat.id)
    await message.reply_photo(photo=random.choice(SETTINGS_PICS), caption=text, reply_markup=markup)
    message.stop_propagation()

@Bot.on_message(filters.command("autodelete"), group=-2)
async def auto_delete_cmd(client, message):
    if not await is_admin(message.from_user.id): return
    text, markup = await get_autodel_ui()
    await message.reply_photo(photo=random.choice(SETTINGS_PICS), caption=text, reply_markup=markup)
    message.stop_propagation()

@Bot.on_message(filters.command("setjoinmode"), group=-2)
async def set_join_mode_cmd(client, message):
    if not await is_admin(message.from_user.id): return
    text, markup = await get_joinmode_ui()
    await message.reply_photo(photo=random.choice(SETTINGS_PICS), caption=text, reply_markup=markup)
    message.stop_propagation()

@Bot.on_message(filters.command("setexpire"), group=-2)
async def set_expire_cmd(client, message):
    if not await is_admin(message.from_user.id): return
    text, markup = await get_linkexpire_ui()
    await message.reply_photo(photo=random.choice(SETTINGS_PICS), caption=text, reply_markup=markup)
    message.stop_propagation()


# ================= CALLBACKS (BUTTON CLICKS: SUPER HIGH PRIORITY) ================= #
# Yahan sirf settings_ ke buttons pakdenge taaki dusre code kharab na ho
@Bot.on_callback_query(filters.regex(r"^(close_panel|toggle_approve|approve_refresh|smode_|autodel_|gmode_|joinmode_|part_|expire_)"), group=-2)
async def settings_callback(client, query):
    data = query.data
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    if not await is_admin(user_id):
        return await query.answer("❌ You are not authorized.", show_alert=True)

    if data == "close_panel":
        return await query.message.delete()

    # --- APPROVE ---
    if data == "toggle_approve":
        curr = await kingdb.is_group_approved(chat_id)
        if curr: await kingdb.disapprove_group(chat_id)
        else: await kingdb.approve_group(chat_id)
        text, markup = await get_approve_ui(chat_id)
        try: await query.message.edit_caption(caption=text, reply_markup=markup)
        except: pass

    elif data == "approve_refresh":
        text, markup = await get_approve_ui(chat_id)
        try: await query.message.edit_caption(caption=text, reply_markup=markup)
        except: await query.answer("Already updated! 🔄")

    # --- SEARCH MODE ---
    elif data.startswith("smode_"):
        if data == "smode_auto": await kingdb.set_search_mode(chat_id, "auto")
        elif data == "smode_command": await kingdb.set_search_mode(chat_id, "command")
        text, markup = await get_searchmode_ui(chat_id)
        try: await query.message.edit_caption(caption=text, reply_markup=markup)
        except: await query.answer("Refreshed! 🔄")

    # --- AUTO DELETE ---
    elif data == "autodel_toggle":
        curr = await kingdb.get_auto_delete()
        await kingdb.set_auto_delete(not curr)
        text, markup = await get_autodel_ui()
        try: await query.message.edit_caption(caption=text, reply_markup=markup)
        except: pass

    elif data == "autodel_refresh":
        text, markup = await get_autodel_ui()
        try: await query.message.edit_caption(caption=text, reply_markup=markup)
        except: await query.answer("Already updated! 🔄")

    elif data == "autodel_settimer":
        await query.message.delete()
        time_str = format_time(await kingdb.get_del_timer())
        prompt_text = f"⏱ Cᴜʀʀᴇɴᴛ Tɪᴍᴇʀ: {time_str}\n\nTᴏ ᴄʜᴀɴɢᴇ ᴛɪᴍᴇʀ, Pʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ ɪɴ sᴇᴄᴏɴᴅs ᴡɪᴛʜɪɴ 1 ᴍɪɴᴜᴛᴇ.\nFᴏʀ ᴇxᴀᴍᴘʟᴇ: 300, 600, 900"
        try:
            answer = await client.ask(chat_id, prompt_text, timeout=60, filters=filters.user(user_id))
            await kingdb.set_del_timer(int(answer.text))
            await answer.reply(f"✅ Auto-delete timer set to **{format_time(int(answer.text))}**.")
        except asyncio.TimeoutError:
            await client.send_message(chat_id, "❗️ Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ..\n\nRᴇᴀsᴏɴ: 1 minute Time out ..")
        except ValueError:
            await client.send_message(chat_id, "❗️ Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ..\n\nRᴇᴀsᴏɴ: Invalid number.")

    # --- JOIN MODE ---
    elif data == "gmode_direct":
        channels = await kingdb.get_indexed_channels()
        for ch in channels: await kingdb.update_channel_join_mode(ch['_id'], "direct")
        await query.answer("Global Direct Enabled ✅")
        text, markup = await get_joinmode_ui()
        try: await query.message.edit_caption(caption=text, reply_markup=markup)
        except: pass

    elif data == "gmode_request":
        channels = await kingdb.get_indexed_channels()
        for ch in channels: await kingdb.update_channel_join_mode(ch['_id'], "request")
        await query.answer("Global Request Enabled ✅")
        text, markup = await get_joinmode_ui()
        try: await query.message.edit_caption(caption=text, reply_markup=markup)
        except: pass

    elif data == "joinmode_refresh":
        text, markup = await get_joinmode_ui()
        try: await query.message.edit_caption(caption=text, reply_markup=markup)
        except: await query.answer("Refreshed! 🔄")

    elif data == "gmode_particular":
        await query.message.delete()
        await client.send_message(chat_id, "🆔 **Please send the Channel ID:**\nExample: `-1001234567890`", reply_markup=ForceReply(True))

    elif data.startswith("part_"):
        _, mode, ch_id = data.split("_")
        await kingdb.update_channel_join_mode(int(ch_id), mode)
        await query.message.edit_caption(caption=f"✅ Join mode for `{ch_id}` set to **{mode.upper()}**.")

    # --- LINK EXPIRATION ---
    elif data == "expire_remove":
        channels = await kingdb.get_indexed_channels()
        for ch in channels: await kingdb.update_channel(ch['_id'], {"expire_seconds": 0})
        await query.answer("Expiration Removed ✖️")
        text, markup = await get_linkexpire_ui()
        try: await query.message.edit_caption(caption=text, reply_markup=markup)
        except: pass

    elif data == "expire_refresh":
        text, markup = await get_linkexpire_ui()
        try: await query.message.edit_caption(caption=text, reply_markup=markup)
        except: await query.answer("Already updated! 🔄")

    elif data == "expire_settimer":
        await query.message.delete()
        channels = await kingdb.get_indexed_channels()
        current = channels[0].get("expire_seconds", 0) if channels else 0
        prompt_text = f"⏳ Cᴜʀʀᴇɴᴛ Lɪɴᴋ Exᴘɪʀᴀᴛɪᴏɴ: {format_time(current)}\n\nTᴏ ᴄʜᴀɴɢᴇ ᴇxᴘɪʀᴀᴛɪᴏɴ, Pʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ ɪɴ sᴇᴄᴏɴᴅs ᴡɪᴛʜɪɴ 1 ᴍɪɴᴜᴛᴇ.\nFᴏʀ ᴇxᴀᴍᴘʟᴇ: 300, 600, 3600"
        try:
            answer = await client.ask(chat_id, prompt_text, timeout=60, filters=filters.user(user_id))
            new_time = int(answer.text)
            for ch in channels:
                await kingdb.update_channel(ch['_id'], {"expire_seconds": new_time})
            await answer.reply(f"✅ Link expiration successfully set to **{format_time(new_time)}**.")
        except asyncio.TimeoutError:
            await client.send_message(chat_id, "❗️ Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ..\n\nRᴇᴀsᴏɴ: 1 minute Time out ..")
        except ValueError:
            await client.send_message(chat_id, "❗️ Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ..\n\nRᴇᴀsᴏɴ: Invalid number.")

@Bot.on_message(filters.reply & filters.private, group=-2)
async def particular_reply_handler(client, message):
    if not message.reply_to_message.reply_markup: return
    if not isinstance(message.reply_to_message.reply_markup, ForceReply): return
    if "Please send the Channel ID" not in message.reply_to_message.text: return

    try:
        channel_id = int(message.text.strip())
        ch = await kingdb.get_channel(channel_id)
        if not ch: return await message.reply("❌ This channel is not found in the database.")

        btn = [
            [InlineKeyboardButton("Direct Link", callback_data=f"part_direct_{channel_id}"), InlineKeyboardButton("Request Link", callback_data=f"part_request_{channel_id}")]
        ]
        await message.reply_photo(
            photo=random.choice(SETTINGS_PICS),
            caption=f"⚙️ **Settings for:** `{ch.get('title')}`\nSelect the desired join mode:", 
            reply_markup=InlineKeyboardMarkup(btn)
        )
        message.stop_propagation()
    except ValueError:
        await message.reply("❌ Please send a valid numeric ID (e.g., -100...).")
