# +++ Channel Search System +++

import time
import asyncio
import random

from bot import Bot
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import PICS
from database.database import kingdb


@Bot.on_message(filters.group & filters.text)
async def group_channel_search(client, message):

    keyword = message.text.strip()

    if len(keyword) < 3:
        return

    # 🔎 Search from DB
    channel_results = await kingdb.search_channels(keyword)

    if not channel_results:
        return

    buttons = []

    for channel in channel_results:
        try:
            # Join Mode Logic
            if channel.get("join_mode") == "request":
                link = await client.create_chat_invite_link(
                    chat_id=channel["channel_id"],
                    creates_join_request=True
                )
            else:
                link = await client.create_chat_invite_link(
                    chat_id=channel["channel_id"],
                    expire_date=int(time.time()) + channel.get("expire_seconds", 3600),
                    member_limit=1
                )

            buttons.append([
                InlineKeyboardButton(
                    text=channel["title"],
                    url=link.invite_link
                )
            ])

        except Exception as e:
            print("Invite Error:", e)
            continue

    if not buttons:
        return

    # 🔥 SAME START IMAGE STYLE
    sent_msg = await message.reply_photo(
        photo=random.choice(PICS),
        caption="✨ <b>[ Your Results ]</b> ✨",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    # 🗑 Auto Delete After 60 Sec
    await asyncio.sleep(60)
    try:
        await sent_msg.delete()
    except:
        pass
