from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.database import kingdb
import asyncio


@Client.on_message(filters.text & filters.group)
async def search_system(client, message):

    chat_id = message.chat.id

    # ===== APPROVAL CHECK =====
    try:
        approved = await kingdb.is_group_approved(chat_id)
    except:
        approved = False

    if not approved:
        return

    # ===== SEARCH MODE =====
    try:
        mode = await kingdb.get_search_mode(chat_id)
    except:
        mode = "auto"

    if mode == "command":
        if not message.text.startswith("/search"):
            return
        query = message.text.replace("/search", "").strip()
    else:
        query = message.text.strip()

    # ===== MIN LENGTH CHECK =====
    if len(query) < 3:
        return

    # ===== SEARCH FROM DB =====
    try:
        results = await kingdb.search_channel(query)
    except:
        return

    if not results:
        return

    buttons = []

    # ===== CREATE BUTTONS =====
    for ch in results[:10]:  # limit for safety

        try:
            join_mode = ch.get("join_mode", "direct")
            channel_id = ch["_id"]

            if join_mode == "request":
                link = await client.create_chat_invite_link(
                    channel_id,
                    creates_join_request=True
                )
            else:
                link = await client.create_chat_invite_link(
                    channel_id,
                    member_limit=1
                )

            buttons.append(
                [
                    InlineKeyboardButton(
                        ch.get("title", "Channel"),
                        url=link.invite_link
                    )
                ]
            )

        except Exception:
            continue  # skip broken channels

    if not buttons:
        return

    # ===== SEND RESULT =====
    sent = await message.reply(
        "🔍 **Search Results:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    # ===== EXPIRE SYSTEM =====
    try:
        expire = results[0].get("expire_seconds", 600)
    except:
        expire = 600

    try:
        await asyncio.sleep(expire)
        await sent.delete()
    except:
        pass
