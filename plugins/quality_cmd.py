"""
quality_cmd.py — /quality command  (v3 — ROOT BUG FIX)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ROOT BUG (v1 & v2):
    message.stop_propagation() raises StopPropagation IMMEDIATELY.
    Calling it BEFORE the processing code meant the handler
    intercepted every file (blocking channel_post) but NEVER
    ran any detection/collection logic.

FIX:
    stop_propagation() is now called at the VERY END of
    quality_file_handler, after _process() has fully completed.
    The exception then prevents channel_post.py from also running.

Other improvements:
    • print() at every step (visible in all log levels)
    • extract ALL text: file_name + caption + message.text
    • handles all media types (document/video/audio/animation/…)
    • FloodWait compat:  e.value (new Pyrogram) / e.x (old Pyrogram)
    • unknown quality reply now shows WHAT was checked → easy debug
"""

import re
import asyncio
import traceback
from dataclasses import dataclass, field

from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

from bot import Bot
from helper_func import is_admin, encode
from config import LOGGER

logger = LOGGER(__name__)

# ─────────────────────────────────────────────────────────
#  command list  (same as channel_post.py — keep in sync)
# ─────────────────────────────────────────────────────────
try:
    from plugins.channel_post import command_list as _CMD_LIST
    print("[Quality] imported command_list from channel_post.py")
except Exception as _e:
    print(f"[Quality] could not import command_list ({_e}), using fallback")
    _CMD_LIST = [
        'start','users','broadcast','batch','genlink','help','cmd','info',
        'add_fsub','fsub_chnl','restart','del_fsub','add_admins','del_admins',
        'admin_list','cancel','auto_del','forcesub','files','add_banuser',
        'del_banuser','banuser_list','status','search','req_fsub','setexpire',
        'setjoinmode','approvegroup','disapprovegroup','index','setsearchmode',
        'flink','quality',
    ]


# ─────────────────────────────────────────────────────────
#  Session model
# ─────────────────────────────────────────────────────────
@dataclass
class QualitySession:
    collected: dict = field(default_factory=dict)   # {key: Message}
    lock:      asyncio.Lock = field(default_factory=asyncio.Lock)
    finished:  bool = False

quality_sessions: dict[int, QualitySession] = {}

QUALITY_ORDER   = ["480p", "720p", "1080p", "webrip"]
QUALITY_DISPLAY = {
    "480p":   "480p",
    "720p":   "720p",
    "1080p":  "1080p",
    "webrip": "WEB-Rip",
}

_WEB_RE = re.compile(r'\b(webrip|web[\s\-]rip|web)\b', re.IGNORECASE)


# ─────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────
def detect_quality(text: str) -> str | None:
    """Return canonical quality key or None."""
    if not text:
        return None
    t = text.lower()
    if "1080p" in t: return "1080p"
    if "720p"  in t: return "720p"
    if "480p"  in t: return "480p"
    if _WEB_RE.search(t): return "webrip"
    return None


def extract_all_text(message: Message) -> list[str]:
    """
    Collect every piece of text that might contain a quality tag,
    in priority order: media file_name → caption → message text.
    """
    sources: list[str] = []

    for attr in ("document", "video", "audio", "animation", "voice", "video_note"):
        media = getattr(message, attr, None)
        if media:
            fn = getattr(media, "file_name", None)
            if fn:
                sources.append(fn)

    if message.caption:
        sources.append(message.caption)
    if message.text:
        sources.append(message.text)

    return sources


def has_media(message: Message) -> bool:
    return bool(
        message.document or message.video or message.audio or
        message.animation or message.voice or message.video_note or
        message.photo or message.sticker
    )


def build_progress(collected: dict) -> str:
    lines = ["<b>Rᴇᴄᴇɪᴠᴇᴅ:</b>"]
    for key in QUALITY_ORDER:
        icon = "✅" if key in collected else "❌"
        lines.append(f"{icon} {QUALITY_DISPLAY[key]}")
    return "\n".join(lines)


async def _gen_link(client: Bot, message: Message) -> str:
    """Copy to DB channel → return bot start-link (same as channel_post.py)."""
    try:
        post = await message.copy(chat_id=client.db_channel.id, disable_notification=True)
    except FloodWait as e:
        wait = getattr(e, "value", getattr(e, "x", 5))
        print(f"[Quality] FloodWait {wait}s")
        await asyncio.sleep(wait)
        post = await message.copy(chat_id=client.db_channel.id, disable_notification=True)

    cid  = post.id * abs(client.db_channel.id)
    b64  = await encode(f"get-{cid}")
    return f"https://t.me/{client.username}?start={b64}"


def _clear(user_id: int) -> None:
    quality_sessions.pop(user_id, None)
    msg = f"[Quality] Session cleared  user={user_id}"
    logger.info(msg); print(msg)


async def _finish(client: Bot, session: QualitySession, user_id: int, trigger: Message) -> None:
    """Generate links for all 4 qualities, send result, clear session."""
    snapshot = dict(session.collected)   # snapshot before clear
    _clear(user_id)

    status = await trigger.reply(
        "<b><i>⚙️ Gᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋs...</i></b>",
        disable_web_page_preview=True,
    )
    try:
        links: dict[str, str] = {}
        for key in QUALITY_ORDER:
            links[key] = await _gen_link(client, snapshot[key])
            msg = f"[Quality] link  user={user_id}  {key} → {links[key]}"
            logger.info(msg); print(msg)

        final = (
            f"` 𝟰𝟴𝟬𝗽 - {links['480p']} && 𝟳𝟮𝟬𝗽 - {links['720p']}\n"
            f"𝟭𝟬𝟴𝟬𝗽 - {links['1080p']} && 𝗪𝗘𝗕-𝗥𝗶𝗽 - {links['webrip']} `"
        )
        await status.edit(final, disable_web_page_preview=True)
        msg = f"[Quality] Task done  user={user_id}"
        logger.info(msg); print(msg)

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(f"[Quality] _finish error  user={user_id}: {exc}")
        print(f"[Quality] _finish error  user={user_id}: {exc}\n{tb}")
        await status.edit(
            f"<b>❌ Eʀʀᴏʀ:</b>\n<blockquote><code>{exc}</code></blockquote>"
        )


# ─────────────────────────────────────────────────────────
#  Inner processing — separated so stop_propagation()
#  can be called AFTER this returns in the outer handler.
# ─────────────────────────────────────────────────────────
async def _process(client: Bot, message: Message, user_id: int, session: QualitySession) -> None:
    """Detect quality, store file, send progress. Called inside quality_file_handler."""

    print(f"[Quality] _process called  user={user_id}  has_media={has_media(message)}")

    async with session.lock:

        # Session might have been cancelled while waiting for lock
        if quality_sessions.get(user_id) is not session:
            print(f"[Quality] session changed/gone during lock wait  user={user_id}")
            return

        if session.finished:
            print(f"[Quality] already finished  user={user_id}")
            return

        # ── Require actual media ───────────────────────────────────
        if not has_media(message):
            print(f"[Quality] no media  user={user_id}")
            await message.reply(
                "⚠️ <b>Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ ғɪʟᴇ</b> (document, video, etc.)",
                quote=True,
            )
            return

        # ── Probe every available text source ─────────────────────
        sources = extract_all_text(message)
        quality = None
        matched = None
        for src in sources:
            q = detect_quality(src)
            if q:
                quality = q
                matched = src
                break

        print(f"[Quality] detection  user={user_id}  sources={sources}  result={quality}")
        logger.info(f"[Quality] detection  user={user_id}  sources={sources}  result={quality}")

        if quality is None:
            preview = ", ".join(repr(s[:50]) for s in sources) if sources else "NONE FOUND"
            await message.reply(
                f"⚠️ <b>Uɴᴋɴᴏᴡɴ ǫᴜᴀʟɪᴛʏ.</b>\n"
                f"<b>Checked:</b> <code>{preview}</code>\n"
                f"<i>Need 480p / 720p / 1080p / WEBRip / WEB-Rip in filename or caption.</i>",
                quote=True,
            )
            return

        if quality in session.collected:
            await message.reply(
                f"⚠️ <b>{QUALITY_DISPLAY[quality]} ᴀʟʀᴇᴀᴅʏ ᴀᴅᴅᴇᴅ.</b>",
                quote=True,
            )
            return

        # ── Accept ────────────────────────────────────────────────
        session.collected[quality] = message
        count = len(session.collected)
        msg = f"[Quality] accepted  user={user_id}  quality={quality}  {count}/4  from='{matched}'"
        logger.info(msg); print(msg)

        await message.reply(build_progress(session.collected), quote=True)

        if count == 4:
            session.finished = True

    # ── Outside lock: finish if all 4 collected ────────────────────
    if session.finished and quality_sessions.get(user_id) is session:
        await _finish(client, session, user_id, message)


# ═══════════════════════════════════════════════════════════
#  /quality  — start session
# ═══════════════════════════════════════════════════════════
@Bot.on_message(filters.command("quality") & filters.private & is_admin, group=-1)
async def quality_cmd(client: Bot, message: Message):
    user_id = message.from_user.id
    _clear(user_id)
    quality_sessions[user_id] = QualitySession()
    msg = f"[Quality] Session started  user={user_id}"
    logger.info(msg); print(msg)

    await message.reply(
        "<b>Sᴇɴᴅ ᴍᴇ ᴛʜᴇsᴇ ǫᴜᴀʟɪᴛʏ ғɪʟᴇs:</b>\n• 480p\n• 720p\n• 1080p\n• WEB-Rip",
        quote=True,
    )
    message.stop_propagation()


# ═══════════════════════════════════════════════════════════
#  /cancel  — quality-aware (group -1 → before broadcast cancel)
# ═══════════════════════════════════════════════════════════
@Bot.on_message(filters.command("cancel") & filters.private & is_admin, group=-1)
async def quality_cancel(client: Bot, message: Message):
    user_id = message.from_user.id
    if user_id in quality_sessions:
        _clear(user_id)
        print(f"[Quality] Cancelled  user={user_id}")
        await message.reply("<b>✅ Qᴜᴀʟɪᴛʏ ᴛᴀsᴋ ᴄᴀɴᴄᴇʟʟᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ.</b>", quote=True)
        message.stop_propagation()   # block broadcast cancel
    # else: fall through to broadcast cancel in bot_cmd.py


# ═══════════════════════════════════════════════════════════
#  File/message handler  (group -1 → runs before channel_post)
#
#  ┌─ CRITICAL DESIGN NOTE ──────────────────────────────────┐
#  │  stop_propagation() is called at the VERY END,          │
#  │  AFTER _process() has fully finished.                   │
#  │                                                         │
#  │  Calling it at the TOP (as in v1/v2) raises             │
#  │  StopPropagation immediately — skipping ALL code        │
#  │  below it, so files were intercepted but never          │
#  │  processed. That was the root bug.                      │
#  └─────────────────────────────────────────────────────────┘
# ═══════════════════════════════════════════════════════════
@Bot.on_message(
    ~filters.command(_CMD_LIST) & filters.private & is_admin,
    group=-1,
)
async def quality_file_handler(client: Bot, message: Message):
    user_id = message.from_user.id

    print(f"[Quality] HANDLER ENTRY  user={user_id}  session_active={user_id in quality_sessions}")

    # No active session → let channel_post.py handle normally
    if user_id not in quality_sessions:
        return

    session = quality_sessions[user_id]

    # ── Run all processing FIRST ──────────────────────────────────
    try:
        await _process(client, message, user_id, session)
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(f"[Quality] handler error  user={user_id}: {exc}")
        print(f"[Quality] handler error  user={user_id}: {exc}\n{tb}")
        try:
            await message.reply(f"<b>❌ Eʀʀᴏʀ:</b>\n<code>{exc}</code>", quote=True)
        except Exception:
            pass

    # ── THEN raise StopPropagation to block channel_post.py ───────
    # (This is safe here because all awaits are done above.)
    print(f"[Quality] stopping propagation  user={user_id}")
    message.stop_propagation()
