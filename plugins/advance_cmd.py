import os
import random
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.database import kingdb
from config import OWNER_ID

# ================== CONFIG ==================

PICS = (os.environ.get(
    "PICS",
    "https://envs.sh/ZUb.png https://envs.sh/ZUi.png"
)).split()

user_temp = {}

# ================== HELPERS ==================

def format_time(seconds):
    seconds = int(seconds)

    if seconds < 60:
        return f"{seconds} Seconds"
    elif seconds < 3600:
        return f"{seconds//60} Minutes"
    else:
        return f"{seconds//3600} Hours"


async def send_media(message, text, buttons):
    media = random.choice(PICS)

    try:
        await message.reply_photo(
            photo=media,
            caption=text,
            reply_markup=buttons
        )
    except:
        await message.reply_text(text, reply_markup=buttons)


# ================== APPROVE GROUP ==================

@Client.on_message(filters.command("approvegroup") & filters.group & filters.user(OWNER_ID))
async def approve_cmd(client, message):

    status = await kingdb.is_group_approved(message.chat.id)

    text = f"""⚙️ 𝗚𝗥𝗢𝗨𝗣 𝗖𝗢𝗡𝗧𝗥𝗢𝗟 𝗣𝗔𝗡𝗘𝗟

📌 Current Status: {"Approved ✅" if status else "Not Approved ❌"}

Click below to change"""

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"aprv_{message.chat.id}"),
            InlineKeyboardButton("❌ Unapprove", callback_data=f"unaprv_{message.chat.id}")
        ],
        [InlineKeyboardButton("✖️ Close", callback_data="close")]
    ])

    await send_media(message, text, buttons)


# ================== SEARCH MODE ==================

@Client.on_message(filters.command("searchmode") & filters.user(OWNER_ID))
async def searchmode_cmd(client, message):

    current = await kingdb.get_search_mode()

    text = f"""⚙️ 𝗦𝗘𝗔𝗥𝗖𝗛 𝗠𝗢𝗗𝗘

📌 Current Mode: {current.upper()}"""

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🤖 Auto", callback_data="sm_auto"),
            InlineKeyboardButton("⌨️ Command", callback_data="sm_cmd")
        ],
        [InlineKeyboardButton("✖️ Close", callback_data="close")]
    ])

    await send_media(message, text, buttons)


# ================== SET EXPIRE ==================

@Client.on_message(filters.command("setexpire") & filters.user(OWNER_ID))
async def expire_cmd(client, message):

    if len(message.command) < 2:
        return await message.reply("Usage: /setexpire channel_id")

    chat_id = int(message.command[1])
    data = await kingdb.get_channel(chat_id)

    current = data.get("expire", 300) if data else 300

    text = f"""⏱ 𝗘𝗫𝗣𝗜𝗥𝗘 𝗦𝗘𝗧𝗧𝗜𝗡𝗚

⏱ Current Timer: {format_time(current)}

Select or set custom"""

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("10s", callback_data=f"exp_{chat_id}_10"),
            InlineKeyboardButton("60s", callback_data=f"exp_{chat_id}_60")
        ],
        [
            InlineKeyboardButton("5m", callback_data=f"exp_{chat_id}_300"),
            InlineKeyboardButton("1h", callback_data=f"exp_{chat_id}_3600")
        ],
        [
            InlineKeyboardButton("✏️ Custom", callback_data=f"custom_{chat_id}")
        ],
        [InlineKeyboardButton("✖️ Close", callback_data="close")]
    ])

    await send_media(message, text, buttons)


# ================== JOIN MODE ==================

@Client.on_message(filters.command("setjoinmode") & filters.user(OWNER_ID))
async def joinmode_cmd(client, message):

    if len(message.command) < 2:
        return await message.reply("Usage: /setjoinmode channel_id")

    chat_id = int(message.command[1])
    data = await kingdb.get_channel(chat_id)

    current = data.get("join_mode", "normal") if data else "normal"

    text = f"""🔗 𝗝𝗢𝗜𝗡 𝗠𝗢𝗗𝗘

📌 Current: {current.upper()}"""

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📩 Request", callback_data=f"jm_{chat_id}_request"),
            InlineKeyboardButton("🔗 Direct", callback_data=f"jm_{chat_id}_normal")
        ],
        [InlineKeyboardButton("✖️ Close", callback_data="close")]
    ])

    await send_media(message, text, buttons)


# ================== CALLBACK HANDLER ==================

@Client.on_callback_query()
async def callbacks(client, query):

    data = query.data

    if data == "close":
        return await query.message.delete()

    # APPROVE
    if data.startswith("aprv_"):
        chat_id = int(data.split("_")[1])
        await kingdb.approve_group(chat_id)
        return await query.answer("Approved ✅", True)

    if data.startswith("unaprv_"):
        chat_id = int(data.split("_")[1])
        await kingdb.disapprove_group(chat_id)
        return await query.answer("Removed ❌", True)

    # SEARCH MODE
    if data == "sm_auto":
        await kingdb.set_search_mode("auto")
        return await query.answer("Auto Enabled ✅", True)

    if data == "sm_cmd":
        await kingdb.set_search_mode("command")
        return await query.answer("Command Mode ✅", True)

    # EXPIRE QUICK
    if data.startswith("exp_"):
        _, chat_id, sec = data.split("_")
        await kingdb.update_channel(int(chat_id), {"expire": int(sec)})
        return await query.answer(f"{sec}s set ✅", True)

    # CUSTOM TIMER
    if data.startswith("custom_"):
        chat_id = int(data.split("_")[1])
        user_temp[query.from_user.id] = chat_id

        return await query.message.reply(
            "⏱ Send time in seconds\nExample: 300, 600\n(Valid for 1 min)"
        )

    # JOIN MODE
    if data.startswith("jm_"):
        _, chat_id, mode = data.split("_")
        await kingdb.update_channel(int(chat_id), {"join_mode": mode})
        return await query.answer(f"{mode} set ✅", True)


# ================== CUSTOM TIMER INPUT ==================

@Client.on_message(filters.text & filters.private)
async def custom_timer(client, message):

    user_id = message.from_user.id

    if user_id not in user_temp:
        return

    try:
        seconds = int(message.text)
    except:
        return await message.reply("❌ Send valid number")

    chat_id = user_temp[user_id]

    await kingdb.update_channel(chat_id, {"expire": seconds})

    del user_temp[user_id]

    await message.reply(f"✅ Timer set to {format_time(seconds)}")
