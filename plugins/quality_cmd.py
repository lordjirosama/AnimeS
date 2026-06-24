"""
quality_cmd.py — /quality + /squality commands  (v5 — COMBINED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/quality   — Collect all 4 qualities (480p, 720p, 1080p, HDRip)
/squality  — Admin selects which qualities to SKIP via inline
             buttons, then sends only the required files.

Both commands:
    • Delete all "Received:" progress messages after task finishes
    • Send one final tap-to-copy links message
    • Support /cancel to abort active session
    • Use stop_propagation() AFTER processing (v3+ fix)

Group assignments:
    /squality handlers → group=-2  (runs first)
    /quality  handlers → group=-1  (runs after)
    File handler at each group only fires for its own session type.
"""

import re
import asyncio
import traceback
from dataclasses import dataclass, field

from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from pyrogram.errors import FloodWait

from bot import Bot
from helper_func import is_admin, encode
from config import LOGGER

logger = LOGGER(__name__)


# ─────────────────────────────────────────────────────────
#  Command list  (keep in sync with channel_post.py)
# ─────────────────────────────────────────────────────────
try:
    from plugins.channel_post import command_list as _CMD_LIST
    _CMD_LIST = list(_CMD_LIST)
    for _cmd in ("quality", "squality"):
        if _cmd not in _CMD_LIST:
            _CMD_LIST.append(_cmd)
    print("[Quality] imported command_list from channel_post.py")
except Exception as _e:
    print(f"[Quality] could not import command_list ({_e}), using fallback")
    _CMD_LIST = [
        'start', 'users', 'broadcast', 'batch', 'genlink', 'help', 'cmd',
        'info', 'add_fsub', 'fsub_chnl', 'restart', 'del_fsub', 'add_admins',
        'del_admins', 'admin_list', 'cancel', 'auto_del', 'forcesub', 'files',
        'add_banuser', 'del_banuser', 'banuser_list', 'status', 'search',
        'req_fsub', 'setexpire', 'setjoinmode', 'approvegroup',
        'disapprovegroup', 'index', 'setsearchmode', 'flink',
        'quality', 'squality',
    ]


# ─────────────────────────────────────────────────────────
#  Shared constants
# ─────────────────────────────────────────────────────────
QUALITY_ORDER = ["480p", "720p", "1080p", "hdrip"]
QUALITY_DISPLAY = {
    "480p":   "480p",
    "720p":   "720p",
    "1080p":  "1080p",
    "hdrip": "HDRip",
}
_WEB_RE = re.compile(r'\b(hdrip|hd[\s\-]rip|hdtv)\b', re.IGNORECASE)

# Demo button labels for each quality
QUALITY_BUTTON_LABEL = {
    "480p":  "𝟰𝟴𝟬𝗽",
    "720p":  "𝟳𝟮𝟬𝗽",
    "1080p": "𝟭𝟬𝟴𝟬𝗽",
    "hdrip": "𝗛𝗗𝗿𝗶𝗽",
}


# ═══════════════════════════════════════════════════════════
#  SESSION MODELS
# ═══════════════════════════════════════════════════════════

@dataclass
class QualitySession:
    """Session for /quality — always collects all 4."""
    collected:     dict         = field(default_factory=dict)
    lock:          asyncio.Lock = field(default_factory=asyncio.Lock)
    finished:      bool         = False
    progress_msgs: list         = field(default_factory=list)


@dataclass
class SQualitySession:
    """Session for /squality — admin picks which to skip."""
    # Selection phase
    skipped:       set          = field(default_factory=set)
    confirmed:     bool         = False
    select_msg:    object       = None

    # Collection phase
    required:      list         = field(default_factory=list)
    collected:     dict         = field(default_factory=dict)
    lock:          asyncio.Lock = field(default_factory=asyncio.Lock)
    finished:      bool         = False
    progress_msgs: list         = field(default_factory=list)


# Global session registries
quality_sessions:  dict[int, QualitySession]  = {}
squality_sessions: dict[int, SQualitySession] = {}


# ═══════════════════════════════════════════════════════════
#  SHARED HELPERS
# ═══════════════════════════════════════════════════════════

def detect_quality(text: str) -> str | None:
    """Return canonical quality key or None."""
    if not text:
        return None
    t = text.lower()
    if "1080p" in t: return "1080p"
    if "720p"  in t: return "720p"
    if "480p"  in t: return "480p"
    if _WEB_RE.search(t): return "hdrip"
    return None


def extract_all_text(message: Message) -> list[str]:
    """Collect text from: media filename → caption → message text."""
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


async def _gen_link(client: Bot, message: Message) -> str:
    """Copy to DB channel → return bot start-link."""
    try:
        post = await message.copy(chat_id=client.db_channel.id, disable_notification=True)
    except FloodWait as e:
        wait = getattr(e, "value", getattr(e, "x", 5))
        print(f"[Quality] FloodWait {wait}s")
        await asyncio.sleep(wait)
        post = await message.copy(chat_id=client.db_channel.id, disable_notification=True)

    cid = post.id * abs(client.db_channel.id)
    b64 = await encode(f"get-{cid}")
    return f"https://t.me/{client.username}?start={b64}"


async def _delete_progress(msgs: list) -> None:
    """Delete all progress reply messages silently."""
    for pm in msgs:
        try:
            await pm.delete()
        except Exception as del_err:
            print(f"[Quality] could not delete progress msg: {del_err}")


def _build_demo_keyboard(keys: list, links: dict) -> InlineKeyboardMarkup:
    """Build inline keyboard with one URL button per quality (2 per row)."""
    rows = []
    row  = []
    for key in keys:
        row.append(InlineKeyboardButton(
            QUALITY_BUTTON_LABEL[key],
            url=links[key],
        ))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


# ═══════════════════════════════════════════════════════════
#  ░░░  /quality  ░░░
# ═══════════════════════════════════════════════════════════

def _q_build_progress(collected: dict) -> str:
    lines = ["<b>Rᴇᴄᴇɪᴠᴇᴅ:</b>"]
    for key in QUALITY_ORDER:
        icon = "✅" if key in collected else "❌"
        lines.append(f"{icon} {QUALITY_DISPLAY[key]}")
    return "\n".join(lines)


def _q_clear(user_id: int) -> None:
    quality_sessions.pop(user_id, None)
    msg = f"[Quality] Session cleared  user={user_id}"
    logger.info(msg); print(msg)


async def _q_finish(
    client:  Bot,
    session: QualitySession,
    user_id: int,
    trigger: Message,
) -> None:
    snapshot   = dict(session.collected)
    saved_msgs = list(session.progress_msgs)
    _q_clear(user_id)

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

        await _delete_progress(saved_msgs)

        # ── Text in blockquote (tap-to-copy) ──
        final = (
            "<b>🎬 Qᴜᴀʟɪᴛʏ Lɪɴᴋs Rᴇᴀᴅʏ!</b>\n\n"
            "<blockquote>"
            f"<code>𝟰𝟴𝟬𝗽 - {links['480p']} && 𝟳𝟮𝟬𝗽 - {links['720p']}\n"
            f"𝟭𝟬𝟴𝟬𝗽 - {links['1080p']} && 𝗛𝗗𝗿𝗶𝗽 - {links['hdrip']}</code>"
            "</blockquote>\n\n"
            "<i>💡 Tap text to copy • Buttons to preview</i>"
        )

        # ── Demo buttons (2 per row) ──
        keyboard = _build_demo_keyboard(QUALITY_ORDER, links)

        await status.edit(
            final,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

        # ── Sticker → DB channel ──
        STICKER_ID = "CAACAgUAAxkBAAEEXwtqIa-Jx7bGFBePEgd6b33KgQx0ugAChxwAAhmRCVWJiF1D-DjjgjsE"
        try:
            await client.send_sticker(chat_id=client.db_channel.id, sticker=STICKER_ID)
            print(f"[Quality] Sticker sent to DB channel  user={user_id}")
        except Exception as stk_err:
            print(f"[Quality] Sticker send failed: {stk_err}")

        msg = f"[Quality] Task done  user={user_id}"
        logger.info(msg); print(msg)

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(f"[Quality] _finish error  user={user_id}: {exc}")
        print(f"[Quality] _finish error  user={user_id}: {exc}\n{tb}")
        await status.edit(
            f"<b>❌ Eʀʀᴏʀ:</b>\n<blockquote><code>{exc}</code></blockquote>"
        )


async def _q_process(
    client:  Bot,
    message: Message,
    user_id: int,
    session: QualitySession,
) -> None:
    print(f"[Quality] _process called  user={user_id}  has_media={has_media(message)}")

    async with session.lock:

        if quality_sessions.get(user_id) is not session:
            print(f"[Quality] session changed/gone  user={user_id}")
            return
        if session.finished:
            print(f"[Quality] already finished  user={user_id}")
            return

        if not has_media(message):
            await message.reply(
                "⚠️ <b>Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ ғɪʟᴇ</b> (document, video, etc.)",
                quote=True,
            )
            return

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
                f"<i>Need 480p / 720p / 1080p / HDRip / HD-Rip in filename or caption.</i>",
                quote=True,
            )
            return

        if quality in session.collected:
            await message.reply(
                f"⚠️ <b>{QUALITY_DISPLAY[quality]} ᴀʟʀᴇᴀᴅʏ ᴀᴅᴅᴇᴅ.</b>",
                quote=True,
            )
            return

        session.collected[quality] = message
        count = len(session.collected)
        msg = f"[Quality] accepted  user={user_id}  quality={quality}  {count}/4  from='{matched}'"
        logger.info(msg); print(msg)

        progress_reply = await message.reply(_q_build_progress(session.collected), quote=True)
        session.progress_msgs.append(progress_reply)

        if count == 4:
            session.finished = True

    if session.finished and quality_sessions.get(user_id) is session:
        await _q_finish(client, session, user_id, message)


# ───────────────────────────── /quality handlers ──────────

@Bot.on_message(filters.command("quality") & filters.private & is_admin, group=-1)
async def quality_cmd(client: Bot, message: Message):
    user_id = message.from_user.id
    _q_clear(user_id)
    quality_sessions[user_id] = QualitySession()
    msg = f"[Quality] Session started  user={user_id}"
    logger.info(msg); print(msg)

    await message.reply(
        "<b>Sᴇɴᴅ ᴍᴇ ᴛʜᴇsᴇ ǫᴜᴀʟɪᴛʏ ғɪʟᴇs:</b>\n• 480p\n• 720p\n• 1080p\n• HDRip /n /cancel to cancel.",
        quote=True,
    )
    message.stop_propagation()


@Bot.on_message(filters.command("cancel") & filters.private & is_admin, group=-1)
async def quality_cancel(client: Bot, message: Message):
    user_id = message.from_user.id
    if user_id in quality_sessions:
        _q_clear(user_id)
        print(f"[Quality] Cancelled  user={user_id}")
        await message.reply("<b>✅ Qᴜᴀʟɪᴛʏ ᴛᴀsᴋ ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>", quote=True)
        message.stop_propagation()


@Bot.on_message(
    ~filters.command(_CMD_LIST) & filters.private & is_admin,
    group=-1,
)
async def quality_file_handler(client: Bot, message: Message):
    user_id = message.from_user.id
    print(f"[Quality] HANDLER ENTRY  user={user_id}  session_active={user_id in quality_sessions}")

    if user_id not in quality_sessions:
        return

    session = quality_sessions[user_id]

    try:
        await _q_process(client, message, user_id, session)
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(f"[Quality] handler error  user={user_id}: {exc}")
        print(f"[Quality] handler error  user={user_id}: {exc}\n{tb}")
        try:
            await message.reply(f"<b>❌ Eʀʀᴏʀ:</b>\n<code>{exc}</code>", quote=True)
        except Exception:
            pass

    print(f"[Quality] stopping propagation  user={user_id}")
    message.stop_propagation()


# ═══════════════════════════════════════════════════════════
#  ░░░  /squality  ░══
# ═══════════════════════════════════════════════════════════

def _sq_build_skip_keyboard(skipped: set) -> InlineKeyboardMarkup:
    """4 toggle buttons (2 per row) + Confirm."""
    rows = []
    row  = []
    for key in QUALITY_ORDER:
        icon  = "❌" if key in skipped else "✅"
        label = f"{icon} {QUALITY_DISPLAY[key]}"
        row.append(InlineKeyboardButton(label, callback_data=f"sqtoggle_{key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("✔️ Cᴏɴғɪʀᴍ", callback_data="sqconfirm")])
    return InlineKeyboardMarkup(rows)


def _sq_build_progress(collected: dict, required: list) -> str:
    lines = ["<b>Rᴇᴄᴇɪᴠᴇᴅ:</b>"]
    for key in required:
        icon = "✅" if key in collected else "❌"
        lines.append(f"{icon} {QUALITY_DISPLAY[key]}")
    return "\n".join(lines)


def _sq_clear(user_id: int) -> None:
    squality_sessions.pop(user_id, None)
    msg = f"[SQuality] Session cleared  user={user_id}"
    logger.info(msg); print(msg)


async def _sq_finish(
    client:  Bot,
    session: SQualitySession,
    user_id: int,
    trigger: Message,
) -> None:
    snapshot   = dict(session.collected)
    required   = list(session.required)
    saved_msgs = list(session.progress_msgs)
    _sq_clear(user_id)

    status = await trigger.reply(
        "<b><i>⚙️ Gᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋs...</i></b>",
        disable_web_page_preview=True,
    )
    try:
        links: dict[str, str] = {}
        for key in required:
            links[key] = await _gen_link(client, snapshot[key])
            msg = f"[SQuality] link  user={user_id}  {key} → {links[key]}"
            logger.info(msg); print(msg)

        await _delete_progress(saved_msgs)

        # ── Text in blockquote (tap-to-copy) ──
        parts = " && ".join(f"{QUALITY_DISPLAY[k]} - {links[k]}" for k in required)
        final = (
            "<b>🎬 Qᴜᴀʟɪᴛʏ Lɪɴᴋs Rᴇᴀᴅʏ!</b>\n\n"
            f"<blockquote>{parts}</blockquote>\n\n"
            "<i>💡 Tap text to copy • Buttons to preview</i>"
        )

        # ── Demo buttons (2 per row) ──
        keyboard = _build_demo_keyboard(required, links)

        await status.edit(
            final,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

        # ── Sticker → DB channel ──
        STICKER_ID = "CAACAgUAAxkBAAEEXwtqIa-Jx7bGFBePEgd6b33KgQx0ugAChxwAAhmRCVWJiF1D-DjjgjsE"
        try:
            await client.send_sticker(chat_id=client.db_channel.id, sticker=STICKER_ID)
            print(f"[SQuality] Sticker sent to DB channel  user={user_id}")
        except Exception as stk_err:
            print(f"[SQuality] Sticker send failed: {stk_err}")

        msg = f"[SQuality] Task done  user={user_id}"
        logger.info(msg); print(msg)

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(f"[SQuality] _finish error  user={user_id}: {exc}")
        print(f"[SQuality] _finish error  user={user_id}: {exc}\n{tb}")
        await status.edit(
            f"<b>❌ Eʀʀᴏʀ:</b>\n<blockquote><code>{exc}</code></blockquote>"
        )


async def _sq_process(
    client:  Bot,
    message: Message,
    user_id: int,
    session: SQualitySession,
) -> None:
    print(f"[SQuality] _process called  user={user_id}  has_media={has_media(message)}")

    async with session.lock:

        if squality_sessions.get(user_id) is not session:
            print(f"[SQuality] session changed/gone  user={user_id}")
            return
        if session.finished:
            print(f"[SQuality] already finished  user={user_id}")
            return

        if not has_media(message):
            await message.reply(
                "⚠️ <b>Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ ғɪʟᴇ</b> (document, video, etc.) press to /cancel",
                quote=True,
            )
            return

        sources = extract_all_text(message)
        quality = None
        matched = None
        for src in sources:
            q = detect_quality(src)
            if q:
                quality = q
                matched = src
                break

        print(f"[SQuality] detection  user={user_id}  sources={sources}  result={quality}")
        logger.info(f"[SQuality] detection  user={user_id}  sources={sources}  result={quality}")

        if quality is None:
            preview = ", ".join(repr(s[:50]) for s in sources) if sources else "NONE FOUND"
            await message.reply(
                f"⚠️ <b>Uɴᴋɴᴏᴡɴ ǫᴜᴀʟɪᴛʏ.</b>\n"
                f"<b>Checked:</b> <code>{preview}</code>\n"
                f"<i>Need 480p / 720p / 1080p / HDRip / HD-Rip in filename or caption.</i>",
                quote=True,
            )
            return

        if quality in session.skipped:
            await message.reply(
                f"⚠️ <b>{QUALITY_DISPLAY[quality]}</b> ᴡᴀs sᴋɪᴘᴘᴇᴅ ɪɴ ᴛʜɪs sᴇssɪᴏɴ.\n"
                f"<i>Only send: {', '.join(QUALITY_DISPLAY[k] for k in session.required)}</i>",
                quote=True,
            )
            return

        if quality not in session.required:
            await message.reply(
                f"⚠️ <b>{QUALITY_DISPLAY[quality]}</b> ɪs ɴᴏᴛ ɪɴ ʀᴇǫᴜɪʀᴇᴅ ʟɪsᴛ.",
                quote=True,
            )
            return

        if quality in session.collected:
            await message.reply(
                f"⚠️ <b>{QUALITY_DISPLAY[quality]} ᴀʟʀᴇᴀᴅʏ ᴀᴅᴅᴇᴅ.</b>",
                quote=True,
            )
            return

        session.collected[quality] = message
        count = len(session.collected)
        msg = (
            f"[SQuality] accepted  user={user_id}  quality={quality}  "
            f"{count}/{len(session.required)}  from='{matched}'"
        )
        logger.info(msg); print(msg)

        progress_reply = await message.reply(
            _sq_build_progress(session.collected, session.required),
            quote=True,
        )
        session.progress_msgs.append(progress_reply)

        if count == len(session.required):
            session.finished = True

    if session.finished and squality_sessions.get(user_id) is session:
        await _sq_finish(client, session, user_id, message)


# ───────────────────────────── /squality handlers ─────────

@Bot.on_message(filters.command("squality") & filters.private & is_admin, group=-2)
async def squality_cmd(client: Bot, message: Message):
    user_id = message.from_user.id
    _sq_clear(user_id)
    session = SQualitySession()
    squality_sessions[user_id] = session

    msg = f"[SQuality] Session started  user={user_id}"
    logger.info(msg); print(msg)

    sent = await message.reply(
        "<b>Kᴏɴ ᴋᴏɴ sᴀ ǫᴜᴀʟɪᴛʏ sᴋɪᴘ ᴋᴀʀɴᴀ ʜᴀɪ?</b>\n\n"
        "✅ = Cᴏʟʟᴇᴄᴛ ᴋᴀʀᴇɢᴀ\n"
        "❌ = Sᴋɪᴘ ʜᴏ ᴊᴀʏᴇɢᴀ\n\n"
        "<i>Quality tap karo toggle karne ke liye, fir <b>Confirm</b> or /cancel dabao.</i>",
        reply_markup=_sq_build_skip_keyboard(session.skipped),
        quote=True,
    )
    session.select_msg = sent
    message.stop_propagation()


@Bot.on_callback_query(filters.regex(r"^sq(toggle_|confirm)") & is_admin, group=-1)
async def squality_callback(client: Bot, query: CallbackQuery):
    user_id = query.from_user.id
    print(f"[SQuality] CALLBACK ENTRY  user={user_id}  data={query.data}")

    session = squality_sessions.get(user_id)
    print(f"[SQuality] session_found={session is not None}  confirmed={session.confirmed if session else 'N/A'}")

    if not session:
        print(f"[SQuality] No session for user={user_id}")
        await query.answer("⚠️ Koi active /squality session nahi.", show_alert=True)
        return
    if session.confirmed:
        print(f"[SQuality] Session already confirmed  user={user_id}")
        await query.answer("✅ Session confirmed! Files bhejo.", show_alert=True)
        return

    data = query.data

    if data.startswith("sqtoggle_"):
        key = data[len("sqtoggle_"):]
        print(f"[SQuality] TOGGLE  user={user_id}  key={key}  skipped_before={set(session.skipped)}")
        if key in session.skipped:
            session.skipped.discard(key)
            print(f"[SQuality] Included {key}  skipped_now={set(session.skipped)}")
            await query.answer(f"✅ {QUALITY_DISPLAY[key]} include hoga")
        else:
            if len(session.skipped) >= len(QUALITY_ORDER) - 1:
                print(f"[SQuality] Cannot skip all qualities  user={user_id}")
                await query.answer(
                    "⚠️ Kam se kam ek quality include honi chahiye!",
                    show_alert=True,
                )
                return
            session.skipped.add(key)
            print(f"[SQuality] Skipped {key}  skipped_now={set(session.skipped)}")
            await query.answer(f"❌ {QUALITY_DISPLAY[key]} skip hoga")
        await query.edit_message_reply_markup(_sq_build_skip_keyboard(session.skipped))
        print(f"[SQuality] Keyboard updated  user={user_id}")

    elif data == "sqconfirm":
        print(f"[SQuality] CONFIRM pressed  user={user_id}")
        required = [k for k in QUALITY_ORDER if k not in session.skipped]
        session.required  = required
        session.confirmed = True
        print(f"[SQuality] required={required}  skipped={list(session.skipped)}")

        skipped_names  = [QUALITY_DISPLAY[k] for k in session.skipped] if session.skipped else ["Koi nahi (sab include)"]
        required_names = [QUALITY_DISPLAY[k] for k in required]

        text = (
            "<b>✅ Confirmed!</b>\n\n"
            f"<b>⏭ Skipped:</b> {', '.join(skipped_names)}\n"
            f"<b>📥 Required:</b> {', '.join(required_names)}\n\n"
            f"<i>Ab {len(required)} file{'s' if len(required) > 1 else ''} bhejo.</i>"
        )
        await query.edit_message_text(text, reply_markup=None)
        await query.answer("Session ready! Files bhejo ab. 📂")

        msg = f"[SQuality] Confirmed  user={user_id}  required={required}  skipped={list(session.skipped)}"
        logger.info(msg); print(msg)

    else:
        print(f"[SQuality] UNKNOWN callback data={data}  user={user_id}")


@Bot.on_message(filters.command("cancel") & filters.private & is_admin, group=-2)
async def squality_cancel(client: Bot, message: Message):
    user_id = message.from_user.id
    if user_id in squality_sessions:
        _sq_clear(user_id)
        print(f"[SQuality] Cancelled  user={user_id}")
        await message.reply("<b>✅ SQuality task cancel ho gaya.</b>", quote=True)
        message.stop_propagation()


@Bot.on_message(
    ~filters.command(_CMD_LIST) & filters.private & is_admin,
    group=-2,
)
async def squality_file_handler(client: Bot, message: Message):
    user_id = message.from_user.id
    print(f"[SQuality] HANDLER ENTRY  user={user_id}  session_active={user_id in squality_sessions}")

    if user_id not in squality_sessions:
        return

    session = squality_sessions[user_id]

    if not session.confirmed:
        await message.reply(
            "⚠️ Pehle quality selection <b>Confirm</b> karo.\n"
            "<i>(Upar diye buttons mein se toggle karo fir Confirm dabao.)</i>",
            quote=True,
        )
        message.stop_propagation()
        return

    try:
        await _sq_process(client, message, user_id, session)
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(f"[SQuality] handler error  user={user_id}: {exc}")
        print(f"[SQuality] handler error  user={user_id}: {exc}\n{tb}")
        try:
            await message.reply(f"<b>❌ Eʀʀᴏʀ:</b>\n<code>{exc}</code>", quote=True)
        except Exception:
            pass

    print(f"[SQuality] stopping propagation  user={user_id}")
    message.stop_propagation()
