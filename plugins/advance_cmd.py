import os
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.database import kingdb
from config import OWNER_ID

PICS = (os.environ.get(
    "PICS",
    "https://envs.sh/ZUb.png https://envs.sh/ZUi.png https://envs.sh/oD5.jpg"
)).split()

user_states = {}

# ================= APPROVE GROUP ================= #

@Client.on_message(filters.command("approvegroup") & filters.group)
async def approve_group(client, message):

    is_approved = await kingdb.is_group_approved(message.chat.id)

    buttons = [
        [
            InlineKeyboardButton(
                f"{'✅ ' if is_approved else ''}Approve",
                callback_data="grp_approve"
            ),
            InlineKeyboardButton(
                f"{'✅ ' if not is_approved else ''}Unapprove",
                callback_data="grp_unapprove"
            )
        ]
    ]

    await message.reply_photo(
        random.choice(PICS),
        caption=f"⚙️ GROUP CONTROL PANEL\n\nStatus: {'✅ Approved' if is_approved else '❌ Not Approved'}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ================= SEARCH MODE ================= #

@Client.on_message(filters.command("searchmode") & filters.group)
async def search_mode(client, message):

    mode = await kingdb.get_search_mode(message.chat.id)

    buttons = [
        [
            InlineKeyboardButton(
                f"{'✅ ' if mode=='auto' else ''}Auto",
                callback_data="search_auto"
            ),
            InlineKeyboardButton(
                f"{'✅ ' if mode=='command' else ''}Command",
                callback_data="search_command"
            )
        ]
    ]

    await message.reply_photo(
        random.choice(PICS),
        caption=f"⚙️ SEARCH MODE\n\nCurrent: {mode.upper()}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ================= JOIN MODE ================= #

@Client.on_message(filters.command("setjoinmode") & filters.group)
async def join_mode(client, message):

    channels = await kingdb.get_indexed_channels()

    # assume first channel ka mode (global feel)
    current_mode = "direct"
    if channels:
        current_mode = channels[0].get("join_mode", "direct")

    buttons = [
        [
            InlineKeyboardButton(
                f"{'✅ ' if current_mode=='request' else ''}Request",
                callback_data="join_request"
            ),
            InlineKeyboardButton(
                f"{'✅ ' if current_mode=='direct' else ''}Direct",
                callback_data="join_direct"
            )
        ]
    ]

    await message.reply_photo(
        random.choice(PICS),
        caption=f"🔗 JOIN MODE\n\nCurrent: {current_mode.upper()}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ================= CALLBACK ================= #

@Client.on_callback_query()
async def callbacks(client, query):
    data = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    # ===== APPROVE =====
    if data == "grp_approve":
        await kingdb.approve_group(chat_id)

    elif data == "grp_unapprove":
        await kingdb.disapprove_group(chat_id)

    # ===== SEARCH MODE =====
    elif data.startswith("search_"):
        mode = data.split("_")[1]
        await kingdb.set_search_mode(chat_id, mode)

    # ===== JOIN MODE =====
    elif data.startswith("join_"):
        mode = data.split("_")[1]

        channels = await kingdb.get_indexed_channels()
        for ch in channels:
            await kingdb.update_channel(ch["_id"], {"join_mode": mode})

    # ===== REFRESH UI =====
    # re-render same panel after click

    if data.startswith("grp_"):
        is_approved = await kingdb.is_group_approved(chat_id)

        buttons = [
            [
                InlineKeyboardButton(
                    f"{'✅ ' if is_approved else ''}Approve",
                    callback_data="grp_approve"
                ),
                InlineKeyboardButton(
                    f"{'✅ ' if not is_approved else ''}Unapprove",
                    callback_data="grp_unapprove"
                )
            ]
        ]

        await query.message.edit_caption(
            caption=f"⚙️ GROUP CONTROL PANEL\n\nStatus: {'✅ Approved' if is_approved else '❌ Not Approved'}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("search_"):
        mode = await kingdb.get_search_mode(chat_id)

        buttons = [
            [
                InlineKeyboardButton(
                    f"{'✅ ' if mode=='auto' else ''}Auto",
                    callback_data="search_auto"
                ),
                InlineKeyboardButton(
                    f"{'✅ ' if mode=='command' else ''}Command",
                    callback_data="search_command"
                )
            ]
        ]

        await query.message.edit_caption(
            caption=f"⚙️ SEARCH MODE\n\nCurrent: {mode.upper()}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("join_"):
        channels = await kingdb.get_indexed_channels()

        current_mode = "direct"
        if channels:
            current_mode = channels[0].get("join_mode", "direct")

        buttons = [
            [
                InlineKeyboardButton(
                    f"{'✅ ' if current_mode=='request' else ''}Request",
                    callback_data="join_request"
                ),
                InlineKeyboardButton(
                    f"{'✅ ' if current_mode=='direct' else ''}Direct",
                    callback_data="join_direct"
                )
            ]
        ]

        await query.message.edit_caption(
            caption=f"🔗 JOIN MODE\n\nCurrent: {current_mode.upper()}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "close":
        await query.message.delete()
