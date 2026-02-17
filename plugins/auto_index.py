# +++ INDEX SYSTEM (CMD + FORWARD FLOW) +++

from bot import Bot
from pyrogram import filters
from pyrogram.types import Message
from database.database import kingdb
from config import OWNER_ID, LOG_CHANNEL
index_wait = set()  # users waiting for forward


# =========================================================
# 🔥 STEP 1: /index COMMAND
# =========================================================

@Bot.on_message(filters.command("index") & filters.private)
async def index_cmd(client: Bot, message: Message):

    user_id = message.from_user.id

    admins = await kingdb.get_all_admins()

    if user_id != OWNER_ID and user_id not in admins:
        return await message.reply("❌ You are not allowed")

    index_wait.add(user_id)

    await message.reply(
        "📥 Forward any channel post to index it\n\n"
        "⚠️ Bot must be admin in that channel"
    )


# =========================================================
# 🔥 STEP 2: FORWARD HANDLER
# =========================================================

@Bot.on_message(filters.forwarded & filters.private)
async def index_forward(client: Bot, message: Message):

    user_id = message.from_user.id

    if user_id not in index_wait:
        return  # ignore random forwards

    if not message.forward_from_chat:
        return await message.reply("❌ Forward a channel post")

    chat = message.forward_from_chat

    if chat.type != "channel":
        return await message.reply("❌ Only channel allowed")

    # check bot admin
    bot_id = (await client.get_me()).id

    try:
        member = await client.get_chat_member(chat.id, bot_id)
    except:
        return await message.reply("❌ Bot not in channel")

    if member.status not in ["administrator", "creator"]:
        return await message.reply("❌ Bot must be admin")

    # SAVE TO DB
    await kingdb.add_or_update_channel(
        channel_id=chat.id,
        title=chat.title,
        username=chat.username
    )

    # remove from waiting
    index_wait.remove(user_id)

    # reply
    await message.reply(
        f"✅ Channel Indexed Successfully\n\n"
        f"📛 {chat.title}\n"
        f"🆔 `{chat.id}`"
    )

    print(f"✅ Indexed: {chat.title}")

    # LOG
    try:
        await client.send_message(
            LOG_CHANNEL,
            f"📥 NEW CHANNEL INDEXED\n\n"
            f"👤 User: {message.from_user.mention}\n"
            f"📛 {chat.title}\n"
            f"🆔 `{chat.id}`"
        )
    except:
        pass
