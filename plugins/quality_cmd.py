"""
quality_cmd.py — /quality command for FSB Bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Collects 4 quality files (480p, 720p, 1080p, WEB-Rip) from admins,
auto-detects quality from filename/caption, generates links via the
bot's existing link generation system, and outputs a nano-style
formatted message.

Handler group = -1  →  runs BEFORE channel_post.py (group 0),
allowing stop_propagation() to prevent double-processing.
"""

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

from bot import Bot
from helper_func import is_admin, encode
from config import LOGGER

logger = LOGGER(__name__)

# ─────────────────────────────────────────────
# Per-admin quality session store
#   key  : admin user_id (int)
#   value: dict  {"480p": Message, "720p": Message, ...}
# ─────────────────────────────────────────────
quality_sessions: dict[int, dict] = {}

# Canonical quality keys in the order they appear in the final output
QUALITY_ORDER = ["480p", "720p", "1080p", "webrip"]

# Human-readable display labels for each key
QUALITY_DISPLAY = {
    "480p":   "480p",
    "720p":   "720p",
    "1080p":  "1080p",
    "webrip": "WEB-Rip",
}


# ══════════════════════════════════════════════
#  HELPER  — detect quality from any text
# ══════════════════════════════════════════════
def detect_quality(text: str) -> str | None:
    """
    Return canonical quality key from a filename or caption string.
    Order of checks matters: test 1080p before 720p before 480p so
    '1080p' isn't matched as '80p' or similar.
    Returns None when no valid quality keyword is found.
    """
    if not text:
        return None
    t = text.lower()

    if "1080p" in t:
        return "1080p"
    if "720p" in t:
        return "720p"
    if "480p" in t:
        return "480p"
    # WEBRip / WEB-Rip / WEB Rip / WEB  (keep last — broadest match)
    if any(kw in t for kw in ["webrip", "web-rip", "web rip", "web"]):
        return "webrip"

    return None


# ══════════════════════════════════════════════
#  HELPER  — build progress status block
# ══════════════════════════════════════════════
def build_progress(collected: dict) -> str:
    lines = ["<b>Rᴇᴄᴇɪᴠᴇᴅ:</b>"]
    for key in QUALITY_ORDER:
        icon  = "✅" if key in collected else "❌"
        label = QUALITY_DISPLAY[key]
        lines.append(f"{icon} {label}")
    return "\n".join(lines)


# ══════════════════════════════════════════════
#  HELPER  — copy file to DB channel → link
# ══════════════════════════════════════════════
async def _generate_link(client: Bot, message: Message) -> str:
    """
    Copy a message to the DB channel (same pattern as channel_post.py)
    and return a bot start-link for it.
    Raises on unexpected errors so the caller can handle them.
    """
    try:
        post = await message.copy(
            chat_id=client.db_channel.id,
            disable_notification=True,
        )
    except FloodWait as e:
        logger.warning(f"FloodWait {e.value}s while copying to DB channel")
        await asyncio.sleep(e.value)
        post = await message.copy(
            chat_id=client.db_channel.id,
            disable_notification=True,
        )

    converted_id   = post.id * abs(client.db_channel.id)
    base64_string  = await encode(f"get-{converted_id}")
    link           = f"https://t.me/{client.username}?start={base64_string}"
    return link


# ══════════════════════════════════════════════
#  HELPER  — clear session for a user
# ══════════════════════════════════════════════
def _clear_session(user_id: int) -> None:
    quality_sessions.pop(user_id, None)
    logger.info(f"[Quality] Session cleared for admin {user_id}")


# ══════════════════════════════════════════════
#  INTERNAL  — generate all links & send result
# ══════════════════════════════════════════════
async def _finish_quality_task(
    client: Bot,
    user_id: int,
    reply_target: Message,
) -> None:
    """
    Called once all 4 qualities are present.
    Generates links, formats the nano-style output, sends it, then
    clears the session whether the task succeeds or fails.
    """
    collected = quality_sessions.get(user_id, {})

    status_msg = await reply_target.reply(
        "<b><i>⚙️ Gᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋs, ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...</i></b>",
        quote=False,
        disable_web_page_preview=True,
    )

    try:
        links: dict[str, str] = {}
        for key in QUALITY_ORDER:
            msg  = collected[key]
            link = await _generate_link(client, msg)
            links[key] = link
            logger.info(f"[Quality] admin={user_id} key={key} link={link}")

        # ── Final nano-style formatted output ──────────────────────
        final_text = (
            f"𝟰𝟴𝟬𝗽 - {links['480p']} && 𝟳𝟮𝟬𝗽 - {links['720p']}\n"
            f"𝟭𝟬𝟴𝟬𝗽 - {links['1080p']} && 𝗪𝗘𝗕-𝗥𝗶𝗽 - {links['webrip']}"
        )
        await status_msg.edit(final_text, disable_web_page_preview=True)
        logger.info(f"[Quality] Task completed for admin {user_id}")

    except Exception as exc:
        logger.error(f"[Quality] Link generation failed for admin {user_id}: {exc}", exc_info=True)
        await status_msg.edit(
            f"<b>❌ Eʀʀᴏʀ ᴡʜɪʟᴇ ɢᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋs:</b>\n"
            f"<blockquote><code>{exc}</code></blockquote>"
        )
    finally:
        _clear_session(user_id)


# ══════════════════════════════════════════════
#  /quality  — start collection session
# ══════════════════════════════════════════════
@Bot.on_message(
    filters.command("quality") & filters.private & is_admin,
    group=-1,
)
async def quality_cmd(client: Bot, message: Message):
    user_id = message.from_user.id

    # Reset any stale session for this admin
    _clear_session(user_id)
    quality_sessions[user_id] = {}

    logger.info(f"[Quality] Session started for admin {user_id}")

    await message.reply(
        "<b>Sᴇɴᴅ ᴍᴇ ᴛʜᴇsᴇ ǫᴜᴀʟɪᴛʏ ғɪʟᴇs:</b>\n"
        "• 480p\n"
        "• 720p\n"
        "• 1080p\n"
        "• WEB-Rip",
        quote=True,
    )

    # stop_propagation so channel_post doesn't echo the command back
    message.stop_propagation()


# ══════════════════════════════════════════════
#  /cancel  — quality-aware cancel (group -1)
#
#  Runs BEFORE the broadcast /cancel in bot_cmd.py (group 0).
#  If the admin has an active quality session, cancels it and stops
#  propagation so the broadcast cancel is NOT also triggered.
#  If no quality session is active, propagation continues normally
#  so the broadcast cancel runs unchanged.
# ══════════════════════════════════════════════
@Bot.on_message(
    filters.command("cancel") & filters.private & is_admin,
    group=-1,
)
async def quality_cancel(client: Bot, message: Message):
    user_id = message.from_user.id

    if user_id in quality_sessions:
        _clear_session(user_id)
        logger.info(f"[Quality] Session cancelled by admin {user_id}")
        await message.reply(
            "<b>✅ Qᴜᴀʟɪᴛʏ ᴛᴀsᴋ ᴄᴀɴᴄᴇʟʟᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ.</b>",
            quote=True,
        )
        # Prevent the broadcast /cancel handler from also firing
        message.stop_propagation()

    # else: no quality session → fall through to broadcast cancel in bot_cmd.py


# ══════════════════════════════════════════════
#  File handler — document / video (group -1)
#
#  Intercepts incoming files ONLY when the sender has an active
#  quality session.  Calls stop_propagation() so channel_post.py
#  does NOT copy the same file a second time.
# ══════════════════════════════════════════════
@Bot.on_message(
    filters.private & is_admin & (filters.document | filters.video),
    group=-1,
)
async def quality_file_handler(client: Bot, message: Message):
    user_id = message.from_user.id

    # ── No active session → let channel_post.py handle it normally ──
    if user_id not in quality_sessions:
        return

    # ── Active session → we own this message; block channel_post ────
    message.stop_propagation()

    collected = quality_sessions[user_id]

    # Resolve filename (prefer explicit file_name, fall back to caption)
    filename: str = ""
    if message.document and message.document.file_name:
        filename = message.document.file_name
    elif message.video and message.video.file_name:
        filename = message.video.file_name

    caption: str = message.caption or ""

    # Detect quality — filename takes priority over caption
    quality = detect_quality(filename) or detect_quality(caption)

    if quality is None:
        logger.warning(
            f"[Quality] admin={user_id} could not detect quality "
            f"from filename='{filename}' caption='{caption}'"
        )
        await message.reply(
            "⚠️ <b>Uɴᴋɴᴏᴡɴ ǫᴜᴀʟɪᴛʏ ᴅᴇᴛᴇᴄᴛᴇᴅ.</b>\n"
            "<i>Please send a file whose name or caption contains: "
            "480p, 720p, 1080p, WEBRip / WEB-Rip</i>",
            quote=True,
        )
        return

    # Duplicate check
    if quality in collected:
        logger.info(f"[Quality] admin={user_id} duplicate quality={quality}")
        await message.reply(
            f"⚠️ <b>{QUALITY_DISPLAY[quality]} ᴀʟʀᴇᴀᴅʏ ᴀᴅᴅᴇᴅ.</b>",
            quote=True,
        )
        return

    # Accept the file
    collected[quality] = message
    count = len(collected)
    logger.info(f"[Quality] admin={user_id} accepted quality={quality} ({count}/4)")

    # Show live progress
    await message.reply(build_progress(collected), quote=True)

    # All 4 collected → generate links & finish
    if count == 4:
        await _finish_quality_task(client, user_id, message)
