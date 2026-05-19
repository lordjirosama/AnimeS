from aiohttp import web
from plugins import web_server

import asyncio
import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.types import BotCommand  # ✅ ADD THIS IMPORT
import sys
from datetime import datetime
import subprocess

from pyrogram import Client, filters, enums
from pyrogram.types import Message

from config import OWNER_ID
from config import API_HASH, APP_ID, LOGGER, TG_BOT_TOKEN, TG_BOT_WORKERS, CHANNEL_ID, PORT, OWNER_ID
import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009147483647


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={
                "root": "plugins"
            },
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN
        )
        self.LOGGER = LOGGER

    async def set_bot_commands_list(self):  # ✅ NEW METHOD
        commands = [
            BotCommand("start", "⚡️ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ / ᴄʜᴇᴄᴋ ᴀʟɪᴠᴇ"),
            BotCommand("cmd", "⚡️ ᴏᴡɴᴇʀ"),
        ]
        await self.set_bot_commands(commands)

    async def start(self):
        await super().start()
        bot_info = await self.get_me()
        self.name = bot_info.first_name
        self.username = bot_info.username
        self.uptime = datetime.now()
                
        try:
            db_channel = await self.get_chat(CHANNEL_ID)

            if not db_channel.invite_link:
                db_channel.invite_link = await self.export_chat_invite_link(CHANNEL_ID)

            self.db_channel = db_channel
            
            test = await self.send_message(chat_id = db_channel.id, text = "Testing")
            await test.delete()
            
        except Exception as e:
            self.LOGGER(__name__).warning(e)
            self.LOGGER(__name__).warning(f"Make Sure bot is Admin in DB Channel and have proper Permissions, So Double check the CHANNEL_ID Value, Current Value {CHANNEL_ID}")
            self.LOGGER(__name__).info('Bot Stopped..')
            sys.exit()

        await self.set_bot_commands_list()  # ✅ CALL HERE

        self.set_parse_mode(ParseMode.HTML)
        self.LOGGER(__name__).info(f"Aᴅᴠᴀɴᴄᴇ Fɪʟᴇ-Sʜᴀʀɪɴɢ ʙᴏᴛV3 Mᴀᴅᴇ Bʏ ➪ @Shidoteshika1 [Tᴇʟᴇɢʀᴀᴍ Usᴇʀɴᴀᴍᴇ]")
        self.LOGGER(__name__).info(f"{self.name} Bot Running..!")
        self.LOGGER(__name__).info(f"OPERATION SUCCESSFULL ✅")
        #web-response
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, PORT).start()

        try: await self.send_message(OWNER_ID, text = f"<b><blockquote>🤖 Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ ♻️</blockquote></b>")
        except: pass

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info(f"{self.name} Bot stopped.")




@Client.on_message(filters.command("update") & filters.private)
async def update_bot(bot: Client, message: Message):

    if message.from_user.id not in OWNER_ID:
        return await message.reply_text(
            "❌ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ."
        )

    msg = await message.reply_text("🔄 ᴜᴘᴅᴀᴛɪɴɢ ʙᴏᴛ... ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ")

    try:
        git_pull = subprocess.run(
            ["git", "pull"],
            capture_output=True,
            text=True
        )

        if git_pull.returncode != 0:
            return await msg.edit_text(
                f"❌ ɢɪᴛ ᴘᴜʟʟ ғᴀɪʟᴇᴅ:\n\n<code>{git_pull.stderr}</code>",
                parse_mode=enums.ParseMode.HTML
            )

        await msg.edit_text(
            f"✅ ɢɪᴛ ᴜᴘᴅᴀᴛᴇᴅ:\n\n<code>{git_pull.stdout}</code>",
            parse_mode=enums.ParseMode.HTML
        )

        await asyncio.sleep(2)
        await msg.edit_text("📦 ɪɴsᴛᴀʟʟɪɴɢ ʀᴇǫᴜɪʀᴇᴍᴇɴᴛs...")

        subprocess.run(
            ["pip3", "install", "-r", "requirements.txt"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        await asyncio.sleep(2)
        await msg.edit_text("♻️ ʀᴇsᴛᴀʀᴛɪɴɢ ʙᴏᴛ...")
        await asyncio.sleep(2)
        await msg.delete()

    except Exception as e:
        return await msg.edit_text(
            f"❌ ᴇʀʀᴏʀ:\n<code>{e}</code>",
            parse_mode=enums.ParseMode.HTML
        )

    os.execl(sys.executable, sys.executable, *sys.argv)
