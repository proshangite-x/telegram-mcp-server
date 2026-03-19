"""
Telegram MCP Server
====================
A high-performance MCP (Model Context Protocol) server that exposes Telegram Bot API
functionality as tools for LLM agents (Cursor, Claude Desktop, etc.).

Tools provided:
  Messaging:   send_message, reply_to_message, edit_message, delete_message
  Files/Media: send_document, send_photo, send_video, download_file, get_file_link
  Management:  create_group, create_channel, add_member, kick_member, pin_message
  Information: get_me, get_updates, get_chat_id

Requires:
  - TELEGRAM_BOT_TOKEN  (env var or .env file)
  - DEFAULT_CHAT_ID     (optional, used as fallback when chat_id is omitted)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import aiohttp
import telegram
import telegram.error
from telegram import ReplyParameters
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("telegram-mcp")

TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
DEFAULT_CHAT_ID: str | None = os.getenv("DEFAULT_CHAT_ID")

# Telegram Bot API file‑size limits (bytes)
BOT_API_UPLOAD_WARN = 50 * 1024 * 1024      # 50 MB – standard bot API limit
BOT_API_UPLOAD_HARD = 2000 * 1024 * 1024     # ~2 GB – absolute maximum

AIOHTTP_TIMEOUT = aiohttp.ClientTimeout(total=30)

# ──────────────────────────────────────────────────────────────────────────────
# FastMCP server instance
# ──────────────────────────────────────────────────────────────────────────────

mcp = FastMCP(
    "Telegram MCP Server",
    dependencies=[
        "python-telegram-bot",
        "python-dotenv",
        "aiohttp",
    ],
)

# ──────────────────────────────────────────────────────────────────────────────
# Lazy bot singleton
# ──────────────────────────────────────────────────────────────────────────────

_bot: telegram.Bot | None = None


def _get_bot() -> telegram.Bot:
    """Return the shared Bot instance, creating it on first call."""
    global _bot
    if _bot is None:
        if not TELEGRAM_BOT_TOKEN:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN is not set. "
                "Add it to your .env file or export it as an environment variable."
            )
        _bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        logger.info("Bot instance created (token …%s)", TELEGRAM_BOT_TOKEN[-6:])
    return _bot


def _resolve_chat_id(chat_id: str | None) -> str:
    """Return *chat_id* if given, otherwise fall back to DEFAULT_CHAT_ID."""
    cid = chat_id or DEFAULT_CHAT_ID
    if not cid:
        raise ValueError(
            "No chat_id provided and DEFAULT_CHAT_ID is not set. "
            "Pass chat_id explicitly or set DEFAULT_CHAT_ID in your .env file."
        )
    return cid


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _ok(data: Any) -> str:
    """Wrap a successful result as JSON."""
    return json.dumps({"ok": True, "result": data}, ensure_ascii=False, default=str)


def _err(message: str) -> str:
    """Wrap an error result as JSON."""
    return json.dumps({"ok": False, "error": message}, ensure_ascii=False)


def _validate_file(path_str: str, label: str = "File") -> Path:
    """Validate that a local file exists and return its Path object."""
    p = Path(path_str).resolve()
    if not p.exists():
        raise FileNotFoundError(f"{label} not found: {p}")
    if not p.is_file():
        raise ValueError(f"{label} path is not a file: {p}")
    return p


def _check_file_size(path: Path) -> str | None:
    """Return a warning string if file exceeds safe upload limits, else None."""
    size = path.stat().st_size
    if size > BOT_API_UPLOAD_HARD:
        raise ValueError(
            f"File size ({size / (1024**3):.2f} GB) exceeds Telegram's 2 GB hard limit."
        )
    if size > BOT_API_UPLOAD_WARN:
        return (
            f"⚠️ File is {size / (1024**2):.1f} MB — exceeds 50 MB standard Bot API limit. "
            "Upload may fail unless you run a local Telegram Bot API server."
        )
    return None


async def _handle_telegram_error(e: Exception) -> str:
    """Convert Telegram / network exceptions to user‑friendly JSON errors."""
    if isinstance(e, telegram.error.RetryAfter):
        return _err(f"Rate limited by Telegram. Retry after {e.retry_after} seconds.")
    if isinstance(e, telegram.error.TimedOut):
        return _err("Request timed out. Telegram servers may be slow — try again.")
    if isinstance(e, telegram.error.BadRequest):
        return _err(f"Bad request: {e.message}")
    if isinstance(e, telegram.error.Forbidden):
        return _err(f"Forbidden: {e.message}. Check bot permissions for this chat.")
    if isinstance(e, telegram.error.TelegramError):
        return _err(f"Telegram error: {e.message}")
    if isinstance(e, (FileNotFoundError, ValueError, RuntimeError)):
        return _err(str(e))
    return _err(f"Unexpected error: {type(e).__name__}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  1. MESSAGING & INTERACTION TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def send_message(
    text: str,
    chat_id: str | None = None,
    parse_mode: str = "HTML",
) -> str:
    """Send a text message to a Telegram chat.

    Args:
        text: The message content. Supports HTML formatting by default
              (e.g. <b>bold</b>, <i>italic</i>, <code>code</code>).
        chat_id: Target chat/group/channel ID. Omit to use DEFAULT_CHAT_ID.
        parse_mode: Formatting mode — "HTML" (default), "MarkdownV2", or "".
                    Use "" (empty string) to send raw unformatted text.

    Returns:
        JSON with the sent message details (message_id, date, chat info).
    """
    logger.info("send_message → chat=%s, parse_mode=%s", chat_id, parse_mode)
    try:
        bot = _get_bot()
        cid = _resolve_chat_id(chat_id)
        pm = parse_mode if parse_mode else None
        msg = await bot.send_message(chat_id=cid, text=text, parse_mode=pm)
        return _ok({
            "message_id": msg.message_id,
            "chat_id": msg.chat.id,
            "date": msg.date.isoformat(),
            "text": msg.text,
        })
    except Exception as e:
        return await _handle_telegram_error(e)


@mcp.tool()
async def reply_to_message(
    text: str,
    message_id: int,
    chat_id: str | None = None,
    parse_mode: str = "HTML",
) -> str:
    """Reply to a specific message in a Telegram chat.

    Args:
        text: Reply content. Supports HTML formatting by default.
        message_id: The message ID to reply to.
        chat_id: Target chat ID. Omit to use DEFAULT_CHAT_ID.
        parse_mode: "HTML" (default), "MarkdownV2", or "" for plain text.

    Returns:
        JSON with the sent reply details.
    """
    logger.info("reply_to_message → chat=%s, reply_to=%d", chat_id, message_id)
    try:
        bot = _get_bot()
        cid = _resolve_chat_id(chat_id)
        pm = parse_mode if parse_mode else None
        msg = await bot.send_message(
            chat_id=cid,
            text=text,
            reply_parameters=ReplyParameters(message_id=message_id),
            parse_mode=pm,
        )
        return _ok({
            "message_id": msg.message_id,
            "chat_id": msg.chat.id,
            "date": msg.date.isoformat(),
            "text": msg.text,
            "reply_to_message_id": message_id,
        })
    except Exception as e:
        return await _handle_telegram_error(e)


@mcp.tool()
async def edit_message(
    text: str,
    message_id: int,
    chat_id: str | None = None,
    parse_mode: str = "HTML",
) -> str:
    """Edit a message previously sent by the bot.

    Args:
        text: New text content for the message.
        message_id: The ID of the message to edit (must be a bot message).
        chat_id: Chat where the message is. Omit to use DEFAULT_CHAT_ID.
        parse_mode: "HTML" (default), "MarkdownV2", or "" for plain text.

    Returns:
        JSON with the edited message details.
    """
    logger.info("edit_message → chat=%s, msg=%d", chat_id, message_id)
    try:
        bot = _get_bot()
        cid = _resolve_chat_id(chat_id)
        pm = parse_mode if parse_mode else None
        msg = await bot.edit_message_text(
            chat_id=cid,
            message_id=message_id,
            text=text,
            parse_mode=pm,
        )
        return _ok({
            "message_id": msg.message_id,
            "chat_id": msg.chat.id,
            "text": msg.text,
        })
    except Exception as e:
        return await _handle_telegram_error(e)


@mcp.tool()
async def delete_message(
    message_id: int,
    chat_id: str | None = None,
) -> str:
    """Delete a message from a chat.

    Args:
        message_id: The ID of the message to delete.
        chat_id: Chat where the message is. Omit to use DEFAULT_CHAT_ID.

    Returns:
        JSON confirming deletion.

    Note:
        Bots can only delete messages they sent, or any message in groups/channels
        where the bot has delete-message admin permission.
    """
    logger.info("delete_message → chat=%s, msg=%d", chat_id, message_id)
    try:
        bot = _get_bot()
        cid = _resolve_chat_id(chat_id)
        result = await bot.delete_message(chat_id=cid, message_id=message_id)
        return _ok({"deleted": result, "message_id": message_id})
    except Exception as e:
        return await _handle_telegram_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  2. FILE & MEDIA TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def send_document(
    file_path: str,
    chat_id: str | None = None,
    caption: str | None = None,
    parse_mode: str = "HTML",
) -> str:
    """Send a document/file to a Telegram chat.

    Supports any file type up to ~2 GB (standard Bot API: 50 MB without local server).
    The file path must be a valid absolute or relative path on the local machine.

    Args:
        file_path: Local path to the file to send.
        chat_id: Target chat ID. Omit to use DEFAULT_CHAT_ID.
        caption: Optional caption for the document (supports HTML by default).
        parse_mode: Formatting for the caption — "HTML" (default), "MarkdownV2", or "".

    Returns:
        JSON with document details (file_id, file_name, file_size).
    """
    logger.info("send_document → chat=%s, file=%s", chat_id, file_path)
    try:
        bot = _get_bot()
        cid = _resolve_chat_id(chat_id)
        path = _validate_file(file_path, "Document")
        warning = _check_file_size(path)
        pm = parse_mode if parse_mode else None

        with open(path, "rb") as f:
            msg = await bot.send_document(
                chat_id=cid,
                document=f,
                caption=caption,
                parse_mode=pm,
                filename=path.name,
            )

        result: dict[str, Any] = {
            "message_id": msg.message_id,
            "file_id": msg.document.file_id,
            "file_name": msg.document.file_name,
            "file_size": msg.document.file_size,
        }
        if warning:
            result["warning"] = warning
        return _ok(result)
    except Exception as e:
        return await _handle_telegram_error(e)


@mcp.tool()
async def send_photo(
    photo_path: str,
    chat_id: str | None = None,
    caption: str | None = None,
    parse_mode: str = "HTML",
) -> str:
    """Send a photo to a Telegram chat.

    Supported formats: JPEG, PNG, GIF (non‑animated), BMP, WebP.
    The photo will be compressed by Telegram. For uncompressed, use send_document.

    Args:
        photo_path: Local path to the image file.
        chat_id: Target chat ID. Omit to use DEFAULT_CHAT_ID.
        caption: Optional caption (supports HTML by default).
        parse_mode: Formatting for the caption.

    Returns:
        JSON with photo details (file_id, width, height).
    """
    logger.info("send_photo → chat=%s, file=%s", chat_id, photo_path)
    try:
        bot = _get_bot()
        cid = _resolve_chat_id(chat_id)
        path = _validate_file(photo_path, "Photo")
        warning = _check_file_size(path)
        pm = parse_mode if parse_mode else None

        with open(path, "rb") as f:
            msg = await bot.send_photo(
                chat_id=cid,
                photo=f,
                caption=caption,
                parse_mode=pm,
            )

        largest = msg.photo[-1]  # Telegram returns multiple sizes; last is largest
        result: dict[str, Any] = {
            "message_id": msg.message_id,
            "file_id": largest.file_id,
            "width": largest.width,
            "height": largest.height,
            "file_size": largest.file_size,
        }
        if warning:
            result["warning"] = warning
        return _ok(result)
    except Exception as e:
        return await _handle_telegram_error(e)


@mcp.tool()
async def send_video(
    video_path: str,
    chat_id: str | None = None,
    caption: str | None = None,
    parse_mode: str = "HTML",
) -> str:
    """Send a video to a Telegram chat.

    Supported formats: MP4 (preferred), other formats may not play inline.
    Standard Bot API limit: 50 MB. With local Bot API server: up to 2 GB.

    Args:
        video_path: Local path to the video file.
        chat_id: Target chat ID. Omit to use DEFAULT_CHAT_ID.
        caption: Optional caption (supports HTML by default).
        parse_mode: Formatting for the caption.

    Returns:
        JSON with video details (file_id, duration, width, height).
    """
    logger.info("send_video → chat=%s, file=%s", chat_id, video_path)
    try:
        bot = _get_bot()
        cid = _resolve_chat_id(chat_id)
        path = _validate_file(video_path, "Video")
        warning = _check_file_size(path)
        pm = parse_mode if parse_mode else None

        with open(path, "rb") as f:
            msg = await bot.send_video(
                chat_id=cid,
                video=f,
                caption=caption,
                parse_mode=pm,
            )

        result: dict[str, Any] = {
            "message_id": msg.message_id,
            "file_id": msg.video.file_id,
            "duration": msg.video.duration,
            "width": msg.video.width,
            "height": msg.video.height,
            "file_size": msg.video.file_size,
        }
        if warning:
            result["warning"] = warning
        return _ok(result)
    except Exception as e:
        return await _handle_telegram_error(e)


@mcp.tool()
async def download_file(
    file_id: str,
    destination_path: str,
) -> str:
    """Download a file from Telegram to the local machine.

    Use this to save files, photos, or documents that were sent to the bot.
    The file_id can be obtained from get_updates or from a previous send_* result.

    Args:
        file_id: Telegram file ID (obtained from messages or get_updates).
        destination_path: Local path where the file should be saved.
                          The parent directory must exist.

    Returns:
        JSON with the saved file path and size.
    """
    logger.info("download_file → file_id=%s, dest=%s", file_id, destination_path)
    try:
        bot = _get_bot()
        dest = Path(destination_path).resolve()

        # Validate destination directory exists
        if not dest.parent.exists():
            raise FileNotFoundError(
                f"Destination directory does not exist: {dest.parent}"
            )

        tg_file = await bot.get_file(file_id)
        await tg_file.download_to_drive(custom_path=str(dest))

        return _ok({
            "saved_to": str(dest),
            "file_size": dest.stat().st_size,
            "telegram_file_path": tg_file.file_path,
        })
    except Exception as e:
        return await _handle_telegram_error(e)


@mcp.tool()
async def get_file_link(file_id: str) -> str:
    """Get a direct download URL for a file stored on Telegram.

    The link is temporary and typically valid for about 1 hour.

    Args:
        file_id: Telegram file ID from a message or get_updates result.

    Returns:
        JSON with the direct download URL and file path on Telegram servers.
    """
    logger.info("get_file_link → file_id=%s", file_id)
    try:
        bot = _get_bot()
        tg_file = await bot.get_file(file_id)
        return _ok({
            "file_id": file_id,
            "file_path": tg_file.file_path,
            "download_url": tg_file.file_path
            if tg_file.file_path.startswith("http")
            else f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{tg_file.file_path}",
        })
    except Exception as e:
        return await _handle_telegram_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  3. MANAGEMENT & AUTOMATION TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def create_group(
    title: str,
    user_ids: list[int] | None = None,
) -> str:
    """Attempt to create a new Telegram group.

    ⚠️  LIMITATION: The standard Telegram Bot API does NOT support group creation.
    This tool attempts the call via the raw HTTP API but will likely return an error.
    To create groups programmatically, consider using a user‑bot library (e.g. Telethon).

    Args:
        title: Name of the new group.
        user_ids: Optional list of user IDs to invite into the group.

    Returns:
        JSON with group details on success, or an informative error explaining the limitation.
    """
    logger.warning("create_group → title=%s (Bot API does not support this)", title)
    try:
        if not TELEGRAM_BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set.")

        # Attempt via raw HTTP — this will fail with current Bot API versions
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/createNewChat"
        payload: dict[str, Any] = {"title": title}
        if user_ids:
            payload["user_ids"] = user_ids

        async with aiohttp.ClientSession(timeout=AIOHTTP_TIMEOUT) as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()

        if data.get("ok"):
            return _ok(data.get("result"))

        return _err(
            f"Telegram API returned: {data.get('description', 'Unknown error')}. "
            "Note: The standard Bot API does NOT support group creation. "
            "Use a user‑bot library like Telethon/Pyrogram for this feature."
        )
    except aiohttp.ClientError as e:
        return _err(f"Network error: {e}")
    except Exception as e:
        return await _handle_telegram_error(e)


@mcp.tool()
async def create_channel(
    title: str,
    description: str = "",
) -> str:
    """Attempt to create a new Telegram channel.

    ⚠️  LIMITATION: The standard Telegram Bot API does NOT support channel creation.
    This tool exists for forward‑compatibility and will return an informative error.
    Ideal for personal logs/storage once supported, or via user‑bot (MTProto) approach.

    Args:
        title: Channel title.
        description: Optional channel description.

    Returns:
        JSON with channel details on success, or an error explaining the limitation.
    """
    logger.warning("create_channel → title=%s (Bot API does not support this)", title)
    try:
        if not TELEGRAM_BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set.")

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/createChannel"
        payload = {"title": title, "description": description}

        async with aiohttp.ClientSession(timeout=AIOHTTP_TIMEOUT) as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()

        if data.get("ok"):
            return _ok(data.get("result"))

        return _err(
            f"Telegram API returned: {data.get('description', 'Unknown error')}. "
            "Note: The standard Bot API does NOT support channel creation. "
            "Use a user‑bot library like Telethon/Pyrogram for this feature."
        )
    except aiohttp.ClientError as e:
        return _err(f"Network error: {e}")
    except Exception as e:
        return await _handle_telegram_error(e)


@mcp.tool()
async def add_member(
    user_id: int,
    chat_id: str | None = None,
) -> str:
    """Add a user to a group or channel by creating an invite link.

    Since bots cannot directly add users, this creates a one‑time invite link
    that can be shared with the user to join.

    Args:
        user_id: The Telegram user ID (used for context; the invite link is for anyone).
        chat_id: Group/channel ID. Omit to use DEFAULT_CHAT_ID.

    Returns:
        JSON with the generated invite link.
    """
    logger.info("add_member → chat=%s, user=%d", chat_id, user_id)
    try:
        bot = _get_bot()
        cid = _resolve_chat_id(chat_id)
        invite = await bot.create_chat_invite_link(
            chat_id=cid,
            member_limit=1,
            name=f"Invite for user {user_id}",
        )
        return _ok({
            "invite_link": invite.invite_link,
            "for_user_id": user_id,
            "chat_id": cid,
            "member_limit": 1,
        })
    except Exception as e:
        return await _handle_telegram_error(e)


@mcp.tool()
async def kick_member(
    user_id: int,
    chat_id: str | None = None,
) -> str:
    """Remove (ban) a user from a group or channel.

    The bot must be an admin with "Ban Users" permission.

    Args:
        user_id: Telegram user ID to remove.
        chat_id: Group/channel ID. Omit to use DEFAULT_CHAT_ID.

    Returns:
        JSON confirming the ban.
    """
    logger.info("kick_member → chat=%s, user=%d", chat_id, user_id)
    try:
        bot = _get_bot()
        cid = _resolve_chat_id(chat_id)
        result = await bot.ban_chat_member(chat_id=cid, user_id=user_id)
        return _ok({
            "banned": result,
            "user_id": user_id,
            "chat_id": cid,
        })
    except Exception as e:
        return await _handle_telegram_error(e)


@mcp.tool()
async def pin_message(
    message_id: int,
    chat_id: str | None = None,
    disable_notification: bool = False,
) -> str:
    """Pin a message in a chat.

    The bot must be an admin with "Pin Messages" permission in groups/channels.

    Args:
        message_id: The ID of the message to pin.
        chat_id: Chat where the message is. Omit to use DEFAULT_CHAT_ID.
        disable_notification: If True, members won't receive a notification about the pin.

    Returns:
        JSON confirming the pin action.
    """
    logger.info("pin_message → chat=%s, msg=%d", chat_id, message_id)
    try:
        bot = _get_bot()
        cid = _resolve_chat_id(chat_id)
        result = await bot.pin_chat_message(
            chat_id=cid,
            message_id=message_id,
            disable_notification=disable_notification,
        )
        return _ok({
            "pinned": result,
            "message_id": message_id,
            "chat_id": cid,
        })
    except Exception as e:
        return await _handle_telegram_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  4. INFORMATION & MONITORING TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def get_me() -> str:
    """Get information about the bot itself.

    Returns:
        JSON with bot username, ID, display name, and capability flags.
    """
    logger.info("get_me")
    try:
        bot = _get_bot()
        me = await bot.get_me()
        return _ok({
            "id": me.id,
            "is_bot": me.is_bot,
            "first_name": me.first_name,
            "username": me.username,
            "can_join_groups": me.can_join_groups,
            "can_read_all_group_messages": me.can_read_all_group_messages,
            "supports_inline_queries": me.supports_inline_queries,
        })
    except Exception as e:
        return await _handle_telegram_error(e)


@mcp.tool()
async def get_updates(
    limit: int = 10,
    offset: int | None = None,
) -> str:
    """Fetch recent incoming messages and events.

    This retrieves updates (messages, edited messages, etc.) from the bot's queue.
    Useful for checking what messages the bot has received.

    Args:
        limit: Maximum number of updates to return (1–100, default 10).
        offset: Identifier of the first update to return.
                Use the update_id of the last processed update + 1 to avoid duplicates.

    Returns:
        JSON with a list of recent updates, each containing message details.
    """
    logger.info("get_updates → limit=%d, offset=%s", limit, offset)
    try:
        bot = _get_bot()
        updates = await bot.get_updates(
            limit=min(max(limit, 1), 100),
            offset=offset,
        )

        results = []
        for u in updates:
            entry: dict[str, Any] = {"update_id": u.update_id}
            msg = u.message or u.edited_message or u.channel_post
            if msg:
                entry["message"] = {
                    "message_id": msg.message_id,
                    "chat_id": msg.chat.id,
                    "chat_title": msg.chat.title or msg.chat.first_name,
                    "chat_type": msg.chat.type,
                    "date": msg.date.isoformat(),
                    "text": msg.text,
                }
                if msg.from_user:
                    entry["message"]["from"] = {
                        "id": msg.from_user.id,
                        "name": msg.from_user.full_name,
                        "username": msg.from_user.username,
                    }
                # Include file info if present
                if msg.document:
                    entry["message"]["document"] = {
                        "file_id": msg.document.file_id,
                        "file_name": msg.document.file_name,
                        "file_size": msg.document.file_size,
                        "mime_type": msg.document.mime_type,
                    }
                if msg.photo:
                    largest = msg.photo[-1]
                    entry["message"]["photo"] = {
                        "file_id": largest.file_id,
                        "width": largest.width,
                        "height": largest.height,
                    }
                if msg.video:
                    entry["message"]["video"] = {
                        "file_id": msg.video.file_id,
                        "duration": msg.video.duration,
                        "file_size": msg.video.file_size,
                    }
            results.append(entry)

        return _ok({"count": len(results), "updates": results})
    except Exception as e:
        return await _handle_telegram_error(e)


@mcp.tool()
async def get_chat_id(query: str) -> str:
    """Look up a chat/group/channel ID by searching recent updates.

    Searches through recent bot updates for chats whose title or username
    matches the query (case‑insensitive substring match).

    Args:
        query: Search term — matches against chat title, username, or first name.

    Returns:
        JSON with matching chat IDs and their details.

    Tip:
        The bot must have received at least one message from the target chat
        for it to appear in the search results.
    """
    logger.info("get_chat_id → query=%s", query)
    try:
        bot = _get_bot()
        updates = await bot.get_updates(limit=100)

        seen: dict[int, dict[str, Any]] = {}
        q = query.lower()

        for u in updates:
            msg = u.message or u.edited_message or u.channel_post
            if not msg:
                continue
            chat = msg.chat
            chat_id_val = chat.id
            if chat_id_val in seen:
                continue

            title = (chat.title or "").lower()
            first = (chat.first_name or "").lower()
            uname = (chat.username or "").lower()

            if q in title or q in first or q in uname:
                seen[chat_id_val] = {
                    "chat_id": chat_id_val,
                    "type": chat.type,
                    "title": chat.title or chat.first_name,
                    "username": chat.username,
                }

        matches = list(seen.values())
        return _ok({
            "query": query,
            "count": len(matches),
            "matches": matches,
        })
    except Exception as e:
        return await _handle_telegram_error(e)


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    """Run the MCP server with stdio transport."""
    logger.info("Starting Telegram MCP Server …")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
