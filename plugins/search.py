from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db.advanced_db import *
import asyncio

@Client.on_message(filters.text & filters.group)
async def search_system(client, message):

    approved = await is_group_approved(message.chat.id)
    if not approved:
        return

    mode = await get_search_mode()

    # COMMAND MODE
    if mode == "command":
        if not message.text.startswith("/search"):
            return
        query = message.text.replace("/search", "").strip()
    else:
        query = message.text.strip()

    if len(query) < 3:
        return

    results = await search_channel(query)

    if not results:
        return

    buttons = []

    for ch in results:

        if ch["join_mode"] == "request":
            link = await client.create_chat_invite_link(
                ch["chat_id"],
                creates_join_request=True
            )
        else:
            link = await client.create_chat_invite_link(
                ch["chat_id"],
                member_limit=1
            )

        buttons.append(
            [InlineKeyboardButton(ch["title"], url=link.invite_link)]
        )

    sent = await message.reply(
        "🔍 Search Results:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    await asyncio.sleep(results[0]["expire"])
    await sent.delete()
