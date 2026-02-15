from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.database import kingdb
import asyncio


@Client.on_message(filters.private & filters.text)
async def pm_search(client, message):

    query = message.text.strip()

    if len(query) < 3:
        return

    results = await kingdb.search_channel(query)

    if not results:
        return await message.reply("❌ No results found")

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
        "🔍 Results:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    expire = results[0].get("expire_seconds", 600)

    await asyncio.sleep(expire)
    await sent.delete()
