from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.database import kingdb
from config import OWNER_ID
import asyncio


@Client.on_message(filters.private & filters.text)
async def pm_search(client, message):

    user_id = message.from_user.id
    text = message.text.strip()

    # ✅ ADMIN CHECK
    admins = await kingdb.get_all_admins()
    is_admin = user_id in admins or user_id == OWNER_ID

    # ---------------- ADMIN / OWNER ----------------
    if is_admin:
        # only /search allowed
        if not text.startswith("/search"):
            return

        query = text.replace("/search", "").strip()
        if len(query) < 3:
            return await message.reply("❌ Query too short")

    # ---------------- NORMAL USER ----------------
    else:
        # ignore commands
        if text.startswith("/"):
            return
        query = text
        if len(query) < 3:
            return

    # ---------------- SEARCH ----------------
    results = await kingdb.search_channels(query)

    if not results:
        return await message.reply("❌ No results found")

    buttons = []

    for ch in results:

        join_mode = ch.get("join_mode", "direct")

        try:
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

        except Exception:
            continue  # skip broken channels

    if not buttons:
        return await message.reply("❌ No valid links found")

    sent = await message.reply(
        "🔍 Results:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    expire = results[0].get("expire_seconds", 600)

    await asyncio.sleep(expire)

    try:
        await sent.delete()
    except:
        pass
