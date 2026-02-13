from pyrogram import Client
from database.database import add_channel, remove_channel
from config import OWNER_ID

@Client.on_chat_member_updated()
async def auto_index(client, update):

    me = await client.get_me()

    if update.new_chat_member.user.id != me.id:
        return

    chat = update.chat

    # BOT ADDED
    if update.new_chat_member.status in ["administrator", "member"]:

        inviter = update.from_user.id

        if inviter == OWNER_ID:
            await add_channel(chat.id, chat.title)
            print("Indexed:", chat.title)
        else:
            await client.leave_chat(chat.id)

    # BOT REMOVED
    if update.new_chat_member.status == "left":
        await remove_channel(chat.id)
        print("Removed:", chat.title)
