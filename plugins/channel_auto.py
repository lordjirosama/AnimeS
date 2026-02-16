from pyrogram import Client
from database.database import kingdb


@Client.on_chat_member_updated()
async def auto_index_channel(client, event):

    # SAFETY CHECK
    if not event.new_chat_member:
        return

    if not event.new_chat_member.user:
        return

    # BOT ID
    bot_id = (await client.get_me()).id

    # CHECK BOT ADDED
    if event.new_chat_member.user.id != bot_id:
        return

    chat = event.chat

    # ONLY CHANNEL / GROUP
    if chat.type not in ["channel", "supergroup"]:
        return

    # SAVE TO DB
    await kingdb.add_or_update_channel(
        channel_id=chat.id,
        title=chat.title,
        username=chat.username
    )

    print(f"✅ Indexed: {chat.title} ({chat.id})")
