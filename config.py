import asyncio
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
load_dotenv()


#Bot token @Botfather, --⚠️ REQUIRED--
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")

#Your API ID from my.telegram.org, --⚠️ REQUIRED--
APP_ID = int(os.environ.get("APP_ID", ""))

#Your API Hash from my.telegram.org, --⚠️ REQUIRED--
API_HASH = os.environ.get("API_HASH", "")

#Your db channel Id --⚠️ REQUIRED--
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", ""))

#OWNER ID --⚠️ REQUIRED--
OWNER_ID = int(os.environ.get("OWNER_ID", ""))

# Agar aisi line hai:
# LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "-100123456789") 

# Toh use aise change kar de (int lagana zaroori hai):
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", ""))
#SUPPORT_GROUP: This is used for normal users for getting help if they don't understand how to use the bot --⚠ OPTIONAL--
SUPPORT_GROUP = os.environ.get("SUPPORT_GROUP", "")

#Port
PORT = os.environ.get("PORT", "")

#Database --⚠️ REQUIRED--
DB_URI = os.environ.get("DATABASE_URL", "")

DB_NAME = os.environ.get("DATABASE_NAME", "")


TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", ""))

#Collection of pics for Bot // #Optional but atleast one pic link should be replaced if you don't want predefined links
PICS = (os.environ.get("PICS", "https://ibb.co/sdQKGJ0Y")).split() #Required
VIDEOS = (os.environ.get("VIDEOS", "")).split()
#set your Custom Caption here, Keep None for Disable Custom Caption
CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", "<b><blockquote expandable>{filename}</blockquote></b>")

LOG_FILE_NAME = "filesharingbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
