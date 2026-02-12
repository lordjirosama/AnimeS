from pyrogram import Client, filters
from db.advanced_db import *
from config import OWNER_ID

# APPROVE GROUP
@Client.on_message(filters.command("approvegroup") & filters.user(OWNER_ID))
async def approve(client, message):
    await approve_group(message.chat.id)
    await message.reply("✅ Group Approved")

# REMOVE GROUP
@Client.on_message(filters.command("removegroup") & filters.user(OWNER_ID))
async def removegrp(client, message):
    await remove_group(message.chat.id)
    await message.reply("❌ Group Removed")

# SEARCH MODE
@Client.on_message(filters.command("searchmode") & filters.user(OWNER_ID))
async def mode(client, message):
    if len(message.command) < 2:
        return await message.reply("Use: /searchmode auto|command")

    mode = message.command[1]

    if mode not in ["auto", "command"]:
        return await message.reply("auto or command only")

    await set_search_mode(mode)
    await message.reply(f"✅ Mode set to {mode}")

# SET EXPIRE
@Client.on_message(filters.command("setexpire") & filters.user(OWNER_ID))
async def setexpire(client, message):
    if len(message.command) < 3:
        return await message.reply("Usage: /setexpire channel_id seconds")

    chat_id = int(message.command[1])
    seconds = int(message.command[2])

    await update_channel(chat_id, {"expire": seconds})
    await message.reply("✅ Expire Updated")

# SET JOIN MODE
@Client.on_message(filters.command("setjoinmode") & filters.user(OWNER_ID))
async def setjoin(client, message):
    if len(message.command) < 3:
        return await message.reply("Usage: /setjoinmode channel_id request|normal")

    chat_id = int(message.command[1])
    mode = message.command[2]

    if mode not in ["request", "normal"]:
        return await message.reply("request or normal")

    await update_channel(chat_id, {"join_mode": mode})
    await message.reply("✅ Join Mode Updated")
