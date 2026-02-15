import os
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import kingdb
from config import OWNER_ID

PICS = (os.environ.get(
    "PICS",
    "https://envs.sh/ZUb.png https://envs.sh/ZUi.png https://envs.sh/oD5.jpg"
)).split()

user_states = {}

# ================= APPROVE GROUP ================= #

@Client.on_message(filters.command("approvegroup") & filters.group)
async def approve_group(client, message):
    buttons = [
        [
            InlineKeyboardButton("✅ Approve", callback_data="grp_approve"),
            InlineKeyboardButton("❌ Cancel", callback_data="close")
        ]
    ]

    await message.reply_photo(
        random.choice(PICS),
        caption="⚙️ GROUP CONTROL PANEL\n\nSelect Action:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ================= SEARCH MODE ================= #

@Client.on_message(filters.command("searchmode") & filters.user(OWNER_ID))
async def search_mode(client, message):
    buttons = [
        [
            InlineKeyboardButton("⚡ Auto", callback_data="search_auto"),
            InlineKeyboardButton("⌨️ Command", callback_data="search_command")
        ]
    ]

    await message.reply_photo(
        random.choice(PICS),
        caption="⚙️ SELECT SEARCH MODE",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ================= JOIN MODE ================= #

@Client.on_message(filters.command("setjoinmode") & filters.user(OWNER_ID))
async def join_mode(client, message):
    chat_id = message.chat.id

    buttons = [
        [
            InlineKeyboardButton("📩 Request", callback_data=f"join_request_{chat_id}"),
            InlineKeyboardButton("🔓 Direct", callback_data=f"join_direct_{chat_id}")
        ]
    ]

    await message.reply_photo(
        random.choice(PICS),
        caption="🔗 SELECT JOIN MODE",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ================= SET EXPIRE ================= #

@Client.on_message(filters.command("setexpire") & filters.user(OWNER_ID))
async def setexpire_cmd(client, message):
    buttons = [
        [InlineKeyboardButton("🌍 All Channels", callback_data="exp_all")],
        [InlineKeyboardButton("🎯 Particular Channel", callback_data="exp_particular")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ]

    await message.reply_photo(
        random.choice(PICS),
        caption="⏱ SELECT EXPIRE MODE",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ================= CALLBACK ================= #

@Client.on_callback_query()
async def callbacks(client, query):
    data = query.data
    user_id = query.from_user.id

    # ===== APPROVE =====
    if data == "grp_approve":
        await kingdb.approve_group(query.message.chat.id)
        await query.message.edit_text("✅ Group Approved")

    # ===== SEARCH MODE =====
    elif data.startswith("search_"):
        mode = data.split("_")[1]
        await kingdb.set_search_mode(mode)
        await query.message.edit_text(f"✅ Search Mode: {mode}")

    # ===== JOIN MODE =====
    elif data.startswith("join_"):
        _, mode, chat_id = data.split("_")
        await kingdb.update_channel(int(chat_id), {"join_mode": mode})
        await query.message.edit_text(f"✅ Join Mode: {mode}")

    # ===== EXPIRE ALL =====
    elif data == "exp_all":
        user_states[user_id] = {"mode": "all"}

        buttons = [
            [InlineKeyboardButton("5 min", callback_data="exp_set_300")],
            [InlineKeyboardButton("10 min", callback_data="exp_set_600")],
            [InlineKeyboardButton("15 min", callback_data="exp_set_900")],
            [InlineKeyboardButton("⚙️ Custom", callback_data="exp_custom")]
        ]

        await query.message.edit_text(
            "⏱ SELECT TIMER (ALL CHANNELS)",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ===== EXPIRE PARTICULAR =====
    elif data == "exp_particular":
        user_states[user_id] = {"mode": "wait_channel"}

        await query.message.edit_text(
            "📥 Send Channel ID\nExample: -1001234567890"
        )

    # ===== SET TIME =====
    elif data.startswith("exp_set_"):
        sec = int(data.split("_")[-1])
        state = user_states.get(user_id)

        if not state:
            return await query.answer("Session expired", show_alert=True)

        if state["mode"] == "all":
            await kingdb.update_channel("global", {"expire": sec})
            await query.message.edit_text(f"✅ Global Expire: {sec} sec")

        elif state["mode"] == "particular":
            chat_id = state["chat_id"]
            await kingdb.update_channel(chat_id, {"expire": sec})
            await query.message.edit_text(f"✅ Expire {sec}s for {chat_id}")

    # ===== CUSTOM =====
    elif data == "exp_custom":
        user_states[user_id]["custom"] = True

        await query.message.edit_text(
            "📥 Send custom seconds\nExample: 300"
        )

    elif data == "close":
        await query.message.delete()


# ================= INPUT HANDLER ================= #

@Client.on_message(filters.text & filters.user(OWNER_ID))
async def inputs(client, message):
    user_id = message.from_user.id

    if user_id not in user_states:
        return

    state = user_states[user_id]

    # CHANNEL ID
    if state.get("mode") == "wait_channel":
        try:
            chat_id = int(message.text)
        except:
            return await message.reply("❌ Invalid ID")

        user_states[user_id] = {
            "mode": "particular",
            "chat_id": chat_id
        }

        buttons = [
            [InlineKeyboardButton("5 min", callback_data="exp_set_300")],
            [InlineKeyboardButton("10 min", callback_data="exp_set_600")],
            [InlineKeyboardButton("15 min", callback_data="exp_set_900")],
            [InlineKeyboardButton("⚙️ Custom", callback_data="exp_custom")]
        ]

        await message.reply(
            f"⏱ SELECT TIMER FOR {chat_id}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # CUSTOM TIME
    elif state.get("custom"):
        try:
            sec = int(message.text)
        except:
            return await message.reply("❌ Invalid number")

        if state["mode"] == "all":
            await kingdb.update_channel("global", {"expire": sec})
            await message.reply(f"✅ Global Expire: {sec} sec")

        elif state["mode"] == "particular":
            chat_id = state["chat_id"]
            await kingdb.update_channel(chat_id, {"expire": sec})
            await message.reply(f"✅ Expire {sec}s for {chat_id}")

        user_states.pop(user_id)
