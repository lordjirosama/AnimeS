from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.database import kingdb
import asyncio


@Client.on_message(filters.text & filters.group)
async def search_system(client, message):

    chat_id = message.chat.id

    approved = await kingdb.is_group_approved(chat_id)
    if not approved:
        return

    mode = await kingdb.get_search_mode(chat_id)

    if mode == "command":
        if not message.text.startswith("/search"):
            return
        query = message.text.replace("/search", "").strip()
    else:
        query = message.text.strip()

    if len(query) < 3:
        return

    results = await kingdb.search_channel(query)

    if not results:
        return

    buttons = []

    for ch in results:

        join_mode = ch.get("join_mode", "direct")

        if join_mode == "request":
            link = await client.create_chat_invite_link(
                ch["_id"],
                creates_join_request=True
            )
        else:
            link = await client.create_chat_invite_link(
                ch["_id"],
                member_limit=1
            )

        buttons.append(
            [InlineKeyboardButton(ch.get("title", "Channel"), url=link.invite_link)]
        )

    sent = await message.reply(
        "🔍 Search Results:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    expire = results[0].get("expire_seconds", 600)

    await asyncio.sleep(expire)
    await sent.delete()
