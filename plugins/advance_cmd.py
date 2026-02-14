from database import kingdb  # ya jahan tera db instance hai

@Client.on_message(filters.command("approve"))
async def approve(client, message):
    await kingdb.approve_group(message.chat.id)
    await message.reply_text("✅ Group Approved")
    
@Client.on_message(filters.command("removegroup") & filters.user(OWNER_ID))
async def removegrp(client, message):
    await kingdb.disapprove_group(message.chat.id)   # ✅ FIX
    await message.reply("❌ Group Removed")

# SEARCH MODE (global)
@Client.on_message(filters.command("searchmode") & filters.user(OWNER_ID))
async def mode(client, message):
    if len(message.command) < 2:
        return await message.reply("Usage: /searchmode auto | command")

    mode = message.command[1].lower()

    if mode not in ["auto", "command"]:
        return await message.reply("❌ Only: auto / command")

    await kingdb.set_search_mode(mode)
    await message.reply(f"✅ Search Mode set to: {mode}")

# SET EXPIRE TIME
@Client.on_message(filters.command("setexpire") & filters.user(OWNER_ID))
async def setexpire(client, message):
    if len(message.command) < 3:
        return await message.reply("Usage: /setexpire channel_id seconds")

    try:
        chat_id = int(message.command[1])
        seconds = int(message.command[2])
    except:
        return await message.reply("❌ Invalid format")

    await kingdb.update_channel(chat_id, {"expire": seconds})
    await message.reply(f"✅ Expire set to {seconds} sec")

# SET JOIN MODE
@Client.on_message(filters.command("setjoinmode") & filters.user(OWNER_ID))
async def setjoin(client, message):
    if len(message.command) < 3:
        return await message.reply("Usage: /setjoinmode channel_id request | normal")

    try:
        chat_id = int(message.command[1])
    except:
        return await message.reply("❌ Invalid channel id")

    mode = message.command[2].lower()

    if mode not in ["request", "normal"]:
        return await message.reply("❌ Only: request / normal")

    await kingdb.update_channel(chat_id, {"join_mode": mode})
    await message.reply(f"✅ Join Mode set to {mode}")
