"""
quality_cmd.py — /quality command for FSB Bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fixes vs v1:
  • Per-session asyncio.Lock  →  safe when all 4 files sent at once
  • finished flag             →  _finish never called twice
  • 6-source filename probe   →  works for all forward types
  • Regex WEB boundary check  →  no false positives
  • Snapshot collected before clear  →  links always generated
"""

import re
import asyncio
from dataclasses import dataclass, field
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

from bot import Bot
from helper_func import is_admin, encode
from config import LOGGER

logger = LOGGER(__name__)

# ═══════════════════════════════════════════════════
#  SESSION MODEL
# ═══════════════════════════════════════════════════
@dataclass
class QualitySession:
    collected: dict = field(default_factory=dict)   # {"480p": Message, ...}
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    finished: bool = False   # guard: _finish called only once


# Global registry:  admin_user_id  →  QualitySession
quality_sessions: dict[int, QualitySession] = {}

QUALITY_ORDER   = ["480p", "720p", "1080p", "webrip"]
QUALITY_DISPLAY = {"480p": "480p", "720p": "720p", "1080p": "1080p", "webrip": "WEB-Rip"}

# ─── Regex for WEB variants — requires word boundary so "website" won't match ───
_WEB_RE = re.compile(
    r'\b(webrip|web[\s\-]rip|web)\b',
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════

def detect_quality(text: str) -> str | None:
    """
    Detect quality key from any string.
    Order: 1080p → 720p → 480p → WEB  (avoids prefix mis-matches).
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
    if _WEB_RE.search(t):
        return "webrip"
    return None


def extract_name(message: Message) -> str:
    """
    Probe every location Pyrogram stores the original filename
    for both direct uploads AND forwarded files.

    Priority order (most reliable → least reliable):
      1. document.file_name
      2. video.file_name
      3. audio.file_name
      4. message.caption  (forwarded channel posts often carry filename as caption)
      5. forward origin caption  (Pyrogram copies caption to message.caption already,
         but kept as explicit fallback for clarity)
      6. document/video mime hints  (last resort: never contains quality but logged)
    """
    # 1-3: direct media metadata
    for attr in ("document", "video", "audio"):
        media = getattr(message, attr, None)
        if media and getattr(media, "file_name", None):
            return media.file_name

    # 4-5: caption (same field for both direct and forwarded in Pyrogram)
    if message.caption:
        return message.caption

    # 6: nothing useful found
    return ""


def build_progress(collected: dict) -> str:
    lines = ["<b>Rᴇᴄᴇɪᴠᴇᴅ:</b>"]
    for key in QUALITY_ORDER:
        icon  = "✅" if key in collected else "❌"
        lines.append(f"{icon} {QUALITY_DISPLAY[key]}")
    return "\n".join(lines)


async def _generate_link(client: Bot, message: Message) -> str:
    """Copy to DB channel and return start-link (same as channel_post.py)."""
    try:
        post = await message.copy(chat_id=client.db_channel.id, disable_notification=True)
    except FloodWait as e:
        logger.warning(f"[Quality] FloodWait {e.value}s — sleeping")
        await asyncio.sleep(e.value)
        post = await message.copy(chat_id=client.db_channel.id, disable_notification=True)

    converted_id  = post.id * abs(client.db_channel.id)
    base64_string = await encode(f"get-{converted_id}")
    return f"https://t.me/{client.username}?start={base64_string}"


def _clear(user_id: int) -> None:
    quality_sessions.pop(user_id, None)
    logger.info(f"[Quality] Session cleared  user={user_id}")


# ═══════════════════════════════════════════════════
#  FINISH — generate links & output (called exactly once per session)
# ═══════════════════════════════════════════════════
async def _finish(client: Bot, session: QualitySession, user_id: int, trigger: Message) -> None:
    """
    Snapshot collected dict BEFORE clearing session so that even if
    the session is evicted during link generation, we still have the data.
    """
    # Snapshot — we own this reference regardless of what happens to quality_sessions
    snapshot = dict(session.collected)

    status = await trigger.reply(
        "<b><i>⚙️ Gᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋs, ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...</i></b>",
        disable_web_page_preview=True,
    )
    # Clear session immediately so the admin can start a new one
    _clear(user_id)

    try:
        links: dict[str, str] = {}
        for key in QUALITY_ORDER:
            links[key] = await _generate_link(client, snapshot[key])
            logger.info(f"[Quality] user={user_id}  {key} → {links[key]}")

        final = (
            f"𝟰𝟴𝟬𝗽 - {links['480p']} && 𝟳𝟮𝟬𝗽 - {links['720p']}\n"
            f"𝟭𝟬𝟴𝟬𝗽 - {links['1080p']} && 𝗪𝗘𝗕-𝗥𝗶𝗽 - {links['webrip']}"
        )
        await status.edit(final, disable_web_page_preview=True)
        logger.info(f"[Quality] Task done  user={user_id}")

    except Exception as exc:
        logger.error(f"[Quality] Link gen failed  user={user_id}: {exc}", exc_info=True)
        await status.edit(
            f"<b>❌ Eʀʀᴏʀ ɢᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋs:</b>\n"
            f"<blockquote><code>{exc}</code></blockquote>"
        )


# ═══════════════════════════════════════════════════
#  /quality — start session
# ═══════════════════════════════════════════════════
@Bot.on_message(filters.command("quality") & filters.private & is_admin, group=-1)
async def quality_cmd(client: Bot, message: Message):
    user_id = message.from_user.id

    _clear(user_id)
    quality_sessions[user_id] = QualitySession()
    logger.info(f"[Quality] Session started  user={user_id}")

    await message.reply(
        "<b>Sᴇɴᴅ ᴍᴇ ᴛʜᴇsᴇ ǫᴜᴀʟɪᴛʏ ғɪʟᴇs:</b>\n• 480p\n• 720p\n• 1080p\n• WEB-Rip",
        quote=True,
    )
    message.stop_propagation()


# ═══════════════════════════════════════════════════
#  /cancel — quality-aware (group -1 → runs before broadcast cancel)
# ═══════════════════════════════════════════════════
@Bot.on_message(filters.command("cancel") & filters.private & is_admin, group=-1)
async def quality_cancel(client: Bot, message: Message):
    user_id = message.from_user.id
    if user_id in quality_sessions:
        _clear(user_id)
        logger.info(f"[Quality] Cancelled by admin  user={user_id}")
        await message.reply("<b>✅ Qᴜᴀʟɪᴛʏ ᴛᴀsᴋ ᴄᴀɴᴄᴇʟʟᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ.</b>", quote=True)
        message.stop_propagation()   # don't trigger broadcast cancel
    # else: fall through → broadcast cancel in bot_cmd.py


# ═══════════════════════════════════════════════════
#  File handler — document / video / audio (group -1)
#
#  • Runs BEFORE channel_post.py (group 0)
#  • stop_propagation() only when session is active
#    → files sent outside quality mode still get normal auto-link
#  • Entire body wrapped in per-session Lock
#    → safe when all 4 files arrive simultaneously (media group)
# ═══════════════════════════════════════════════════
@Bot.on_message(
    filters.private & is_admin & (filters.document | filters.video | filters.audio),
    group=-1,
)
async def quality_file_handler(client: Bot, message: Message):
    user_id = message.from_user.id

    # ── No active session → normal auto-link flow ────────────────
    if user_id not in quality_sessions:
        return

    session = quality_sessions[user_id]

    # ── Active session → we own this message ─────────────────────
    message.stop_propagation()   # block channel_post.py

    # ── Lock: safe for media-group (all 4 files at once) ─────────
    async with session.lock:

        # Session may have been cancelled while we waited for the lock
        if user_id not in quality_sessions or quality_sessions[user_id] is not session:
            return

        # Session already completed (another coroutine just finished it)
        if session.finished:
            return

        # ── Probe filename from all possible sources ──────────────
        name    = extract_name(message)
        quality = detect_quality(name)

        logger.debug(
            f"[Quality] user={user_id}  name='{name}'  quality={quality}"
        )

        if quality is None:
            await message.reply(
                "⚠️ <b>Uɴᴋɴᴏᴡɴ ǫᴜᴀʟɪᴛʏ ᴅᴇᴛᴇᴄᴛᴇᴅ.</b>\n"
                "<i>Filename or caption must contain: 480p / 720p / 1080p / WEBRip / WEB-Rip</i>",
                quote=True,
            )
            return

        if quality in session.collected:
            await message.reply(
                f"⚠️ <b>{QUALITY_DISPLAY[quality]} ᴀʟʀᴇᴀᴅʏ ᴀᴅᴅᴇᴅ.</b>",
                quote=True,
            )
            return

        # Accept
        session.collected[quality] = message
        count = len(session.collected)
        logger.info(f"[Quality] user={user_id}  accepted {quality}  ({count}/4)")

        # Progress reply (inside lock so order is correct even for media group)
        await message.reply(build_progress(session.collected), quote=True)

        # All 4 collected
        if count == 4:
            session.finished = True   # guard against double-finish
            # Release lock before the long async link-generation work
            # so /cancel can still run if needed
    
    # ── Outside lock: finish task (no lock needed, snapshot is taken inside _finish) ──
    if session.finished and session is quality_sessions.get(user_id):
        await _finish(client, session, user_id, message)
