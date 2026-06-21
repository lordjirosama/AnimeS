import time
import io
import calendar
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import numpy as np

# ──────────────────────────────────────────────────────────────
# DB helpers – imported from database.py
# ──────────────────────────────────────────────────────────────
from database import get_user_count, get_graph_data  # noqa: E402


# ──────────────────────────────────────────────────────────────
# Chart renderer
# ──────────────────────────────────────────────────────────────

DARK_BG    = "#0D1117"
PANEL_BG   = "#161B22"
ACCENT     = "#58A6FF"
ACCENT2    = "#3FB950"
GRID_CLR   = "#21262D"
TEXT_CLR   = "#E6EDF3"
SUB_CLR    = "#8B949E"
GRAD_TOP   = "#388BFD"
GRAD_BOT   = "#0D1117"


def _make_chart(x_labels: list, y_values: list,
                x_title: str, title: str) -> io.BytesIO:
    xs = np.arange(len(x_labels))

    fig, ax = plt.subplots(figsize=(12, 5.5), facecolor=DARK_BG)
    ax.set_facecolor(PANEL_BG)

    # ── gradient fill under the line ──
    ax.fill_between(xs, y_values, alpha=0.18, color=ACCENT)

    # ── main line ──
    ax.plot(xs, y_values, color=ACCENT, linewidth=2.5,
            solid_capstyle="round", zorder=3)

    # ── data-point dots ──
    ax.scatter(xs, y_values, color=ACCENT, s=50, zorder=4,
               edgecolors=DARK_BG, linewidths=1.5)

    # ── highlight peak ──
    peak_idx = int(np.argmax(y_values))
    ax.scatter([xs[peak_idx]], [y_values[peak_idx]],
               color=ACCENT2, s=90, zorder=5,
               edgecolors=DARK_BG, linewidths=1.5)
    ax.annotate(
        f"Peak: {y_values[peak_idx]:,}",
        xy=(xs[peak_idx], y_values[peak_idx]),
        xytext=(8, 10), textcoords="offset points",
        fontsize=8, color=ACCENT2, fontweight="bold",
        arrowprops=dict(arrowstyle="-", color=ACCENT2, lw=0.8),
    )

    # ── axes styling ──
    ax.set_xticks(xs)
    step = max(1, len(x_labels) // 12)
    tick_labels = [x_labels[i] if i % step == 0 else "" for i in range(len(x_labels))]
    ax.set_xticklabels(tick_labels, color=SUB_CLR, fontsize=8.5)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(
        lambda v, _: f"{int(v):,}"))
    ax.tick_params(colors=SUB_CLR, length=3)
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.grid(axis="y", color=GRID_CLR, linewidth=0.8, linestyle="--")
    ax.set_axisbelow(True)

    # ── labels ──
    ax.set_xlabel(x_title, color=SUB_CLR, fontsize=9, labelpad=6)
    ax.set_ylabel("Users", color=SUB_CLR, fontsize=9, labelpad=6)

    # ── title block ──
    fig.text(0.04, 0.97, title,
             color=TEXT_CLR, fontsize=13, fontweight="bold", va="top")
    fig.text(0.04, 0.91,
             f"Generated  {datetime.utcnow().strftime('%Y-%m-%d  %H:%M UTC')}",
             color=SUB_CLR, fontsize=8, va="top")

    # ── summary pill ──
    total = sum(y_values)
    avg   = total / len(y_values)
    summary = f"  Σ Total: {total:,}   |   Avg: {avg:,.1f}   |   Peak: {y_values[peak_idx]:,}  "
    fig.text(0.96, 0.97, summary,
             color=ACCENT, fontsize=8.5, va="top", ha="right",
             bbox=dict(boxstyle="round,pad=0.4", facecolor=GRID_CLR,
                       edgecolor=ACCENT, linewidth=0.8))

    fig.tight_layout(rect=[0, 0, 1, 0.88])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150,
                facecolor=DARK_BG, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ──────────────────────────────────────────────────────────────
# Keyboards
# ──────────────────────────────────────────────────────────────

def kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📊 Number", callback_data="stats_number"),
        InlineKeyboardButton("📈 Graph",  callback_data="stats_graph"),
    ], [
        InlineKeyboardButton("✖️ Close", callback_data="close"),
    ]])


def kb_graph() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Today", callback_data="graph_today"),
        InlineKeyboardButton("Week",  callback_data="graph_week"),
    ], [
        InlineKeyboardButton("Month", callback_data="graph_month"),
        InlineKeyboardButton("Year",  callback_data="graph_year"),
    ], [
        InlineKeyboardButton("◀️ Back", callback_data="stats_back"),
        InlineKeyboardButton("✖️ Close", callback_data="close"),
    ]])


def kb_back_close() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("◀️ Back",  callback_data="stats_back"),
        InlineKeyboardButton("✖️ Close", callback_data="close"),
    ]])


# ──────────────────────────────────────────────────────────────
# /status command
# ──────────────────────────────────────────────────────────────

async def cmd_status(client, message: Message):
    """Entry point – /status command for admins."""
    start = time.time()
    tmp   = await message.reply("<i>⏳ Processing...</i>")
    ping  = (time.time() - start) * 1000

    now   = datetime.utcnow()
    delta = now - client.uptime
    h, r  = divmod(int(delta.total_seconds()), 3600)
    m, s  = divmod(r, 60)
    uptime_str = f"{h}h {m}m {s}s"

    await tmp.edit(
        f"<b>🤖 Admin Control Panel</b>\n\n"
        f"<code>⏱ Uptime  : {uptime_str}</code>\n"
        f"<code>📡 Ping   : {ping:.2f} ms</code>\n\n"
        f"Choose a stats view below:",
        reply_markup=kb_main(),
    )


# ──────────────────────────────────────────────────────────────
# Callback handlers
# ──────────────────────────────────────────────────────────────

async def cb_stats(client, query: CallbackQuery):
    data = query.data

    # ── close ──
    if data == "close":
        await query.message.delete()
        return

    # ── back to main ──
    if data == "stats_back":
        await query.message.edit_text(
            "<b>📊 Admin Stats Panel</b>\n\nSelect a view:",
            reply_markup=kb_main(),
        )
        return

    # ── number overview ──
    if data == "stats_number":
        today   = await get_user_count("today")
        weekly  = await get_user_count("weekly")
        monthly = await get_user_count("monthly")
        mau     = await get_user_count("mau")
        yearly  = await get_user_count("yearly")
        total   = await get_user_count("all")

        text = (
            "<b>📊 Bot User Statistics</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Today</b>           : <code>{today:,}</code>\n"
            f"• <b>This Week</b>       : <code>{weekly:,}</code>\n"
            f"• <b>This Month</b>      : <code>{monthly:,}</code>\n"
            f"• <b>Monthly Active</b>  : <code>{mau:,}</code>\n"
            f"• <b>This Year</b>       : <code>{yearly:,}</code>\n"
            f"• <b>Total Registered</b>: <code>{total:,}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        await query.message.edit_text(text, reply_markup=kb_back_close())
        return

    # ── graph menu ──
    if data == "stats_graph":
        await query.message.edit_text(
            "<b>📈 Graph Mode</b>\n\nSelect a time range:",
            reply_markup=kb_graph(),
        )
        return

    # ── generate a graph ──
    if data.startswith("graph_"):
        period = data.split("_", 1)[1]           # today / week / month / year
        await query.answer("⏳ Generating chart…")

        x_labels, y_values, x_title, title = await get_graph_data(period)
        buf = _make_chart(x_labels, y_values, x_title, title)

        caption = (
            f"<b>📈 {title}</b>\n"
            f"<code>Total : {sum(y_values):,}  |  "
            f"Avg : {sum(y_values)/len(y_values):.1f}  |  "
            f"Peak : {max(y_values):,}</code>"
        )

        # Send as new photo and delete old message (inline edit doesn't support
        # switching from text → photo in every client version)
        await query.message.reply_photo(
            photo=buf,
            caption=caption,
            reply_markup=kb_graph(),
        )
        await query.message.delete()
        return

    await query.answer()
