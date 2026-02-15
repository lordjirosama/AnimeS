from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.database import kingdb
import random
from config import OWNER_ID, PICS, VIDEOS

# =========================
# MEDIA SENDER
# =========================
async def send_media(message, text, buttons=None):

    pic = random.choice(PICS) if PICS else None

    if pic:
        return await message.reply_photo(
            photo=pic,
            caption=text,
            reply_markup=buttons
        )
    else:
        return await message.reply_text(
            text,
            reply_markup=buttons
        )

async def send_media(message, text, buttons=None):

    if VIDEOS:
        return await message.reply_video(
            video=random.choice(VIDEOS),
            caption=text,
            reply_markup=buttons
        )

    elif PICS:
        return await message.reply_photo(
            photo=random.choice(PICS),
            caption=text,
            reply_markup=buttons
        )

    else:
        return await message.reply_text(text, reply_markup=buttons)
# =========================
# APPROVE GROUP
# =========================
@Client.on_message(filters.command("approve") & filters.user(OWNER_ID))
async def approve(client, message):
    await kingdb.approve_group(message.chat.id)
    await message.reply_text("✅ Group Approved")


# =========================
# REMOVE GROUP
# =========================
@Client.on_message(filters.command("removegroup") & filters.user(OWNER_ID))
async def removegrp(client, message):
    await kingdb.disapprove_group(message.chat.id)
    await message.reply("❌ Group Removed")


# =========================
# SEARCH MODE (INLINE UI)
# =========================
@Client.on_message(filters.command("searchmode") & filters.user(OWNER_ID))
async def searchmode_ui(client, message):

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ Auto Mode", callback_data="search_auto"),
            InlineKeyboardButton("⌨ Command Mode", callback_data="search_command")
        ]
    ])

    await send_media(
        message,
        "⚙️ **Select Search Mode**",
        buttons
    )


@Client.on_callback_query(filters.regex("^search_"))
async def searchmode_callback(client, query: CallbackQuery):
    mode = query.data.split("_")[1]

    await kingdb.set_search_mode(mode)

    await query.message.edit_text(
        f"✅ Search Mode set to: **{mode.upper()}**"
    )


# =========================
# SET JOIN MODE (INLINE UI)
# =========================
@Client.on_message(filters.command("setjoinmode") & filters.user(OWNER_ID))
async def setjoin_ui(client, message):

    if len(message.command) < 2:
        return await message.reply("Usage: /setjoinmode channel_id")

    try:
        chat_id = int(message.command[1])
    except:
        return await message.reply("❌ Invalid channel id")

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📩 Request Join", callback_data=f"join_request_{chat_id}"),
            InlineKeyboardButton("🔓 Direct Join", callback_data=f"join_normal_{chat_id}")
        ]
    ])

    await send_media(
        message,
        "⚙️ **Select Join Mode**",
        buttons
    )


@Client.on_callback_query(filters.regex("^join_"))
async def joinmode_callback(client, query: CallbackQuery):
    data = query.data.split("_")

    mode = data[1]
    chat_id = int(data[2])

    await kingdb.update_channel(chat_id, {"join_mode": mode})

    await query.message.edit_text(
        f"✅ Join Mode set to: **{mode.upper()}**"
    )


# =========================
# SET EXPIRE (INLINE UI)
# =========================
@Client.on_message(filters.command("setexpire") & filters.user(OWNER_ID))
async def expire_ui(client, message):

    if len(message.command) < 2:
        return await message.reply("Usage: /setexpire channel_id")

    try:
        chat_id = int(message.command[1])
    except:
        return await message.reply("❌ Invalid channel id")

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("10s", callback_data=f"exp_10_{chat_id}"),
            InlineKeyboardButton("30s", callback_data=f"exp_30_{chat_id}"),
            InlineKeyboardButton("60s", callback_data=f"exp_60_{chat_id}")
        ],
        [
            InlineKeyboardButton("5 min", callback_data=f"exp_300_{chat_id}"),
            InlineKeyboardButton("10 min", callback_data=f"exp_600_{chat_id}")
        ]
    ])

    await send_media(
        message,
        "⏳ **Select Expire Time**",
        buttons
    )


@Client.on_callback_query(filters.regex("^exp_"))
async def expire_callback(client, query: CallbackQuery):
    data = query.data.split("_")

    seconds = int(data[1])
    chat_id = int(data[2])

    await kingdb.update_channel(chat_id, {"expire": seconds})

    await query.message.edit_text(
        f"✅ Expire set to: **{seconds} sec**"
    )
