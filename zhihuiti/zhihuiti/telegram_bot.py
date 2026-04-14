"""Telegram bot — pushes East×West wisdom content to Stella daily.

Setup:
  1. Talk to @BotFather on Telegram → create bot → get token
  2. Set env var: TELEGRAM_BOT_TOKEN=your-token
  3. Set env var: TELEGRAM_CHAT_ID=stella's-chat-id
     (Stella messages the bot, then check /api/telegram/updates to get her chat_id)
  4. Content auto-pushes on each auto-evolve cycle

Endpoints:
  GET  /api/telegram/status    — bot status and config
  POST /api/telegram/send      — manually send content to Stella
  GET  /api/telegram/updates   — check recent messages (to find chat_id)
"""

from __future__ import annotations

import json
import os
import threading
import time

import httpx


TELEGRAM_API = "https://api.telegram.org/bot{token}"


def _get_token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


def _get_chat_id() -> str:
    return os.environ.get("TELEGRAM_CHAT_ID", "")


def is_configured() -> bool:
    return bool(_get_token() and _get_chat_id())


def send_message(text: str, chat_id: str = "", parse_mode: str = "HTML") -> dict:
    """Send a message via Telegram bot API."""
    token = _get_token()
    chat_id = chat_id or _get_chat_id()
    if not token or not chat_id:
        return {"error": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set"}

    url = f"{TELEGRAM_API.format(token=token)}/sendMessage"
    try:
        resp = httpx.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }, timeout=15)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def get_updates() -> list[dict]:
    """Get recent messages sent to the bot (to find chat_id)."""
    token = _get_token()
    if not token:
        return []
    url = f"{TELEGRAM_API.format(token=token)}/getUpdates"
    try:
        resp = httpx.get(url, timeout=10)
        data = resp.json()
        return data.get("result", [])
    except Exception:
        return []


def get_bot_info() -> dict:
    """Get bot info (name, username)."""
    token = _get_token()
    if not token:
        return {"error": "no token"}
    url = f"{TELEGRAM_API.format(token=token)}/getMe"
    try:
        resp = httpx.get(url, timeout=10)
        return resp.json().get("result", {})
    except Exception as e:
        return {"error": str(e)}


def format_content_for_telegram(piece: dict) -> str:
    """Format a ContentPiece dict into a beautiful Telegram message."""
    title = piece.get("title", "")
    body = piece.get("body", "")
    west = piece.get("west_topic", "")
    east = piece.get("east_topic", "")
    cross = piece.get("cross_insight", "")
    videos = piece.get("video_recommendations", [])

    # Truncate body for Telegram (max ~4000 chars)
    if len(body) > 3000:
        body = body[:3000] + "..."

    msg = f"✨ <b>{title}</b>\n\n"
    msg += f"🔬 <i>{west}</i>\n"
    msg += f"🧘 <i>{east}</i>\n\n"
    msg += f"{body}\n\n"

    if cross:
        msg += f"💡 <b>Key Insight:</b> {cross}\n\n"

    if videos:
        msg += "🎬 <b>推荐视频 Videos:</b>\n"
        for v in videos[:3]:
            search = v.get("search_query", v.get("title", ""))
            desc = v.get("description", "")
            msg += f"  • {desc} → 搜索: <code>{search}</code>\n"

    msg += "\n— Stella's Wisdom Feed 🪷"
    return msg


def push_latest_content() -> dict:
    """Push the most recent unpushed content to Stella via Telegram."""
    if not is_configured():
        return {"status": "not_configured"}

    try:
        from zhihuiti.content_agent import get_feed
        feed = get_feed(limit=1)
        if not feed:
            return {"status": "no_content"}

        piece = feed[0]
        msg = format_content_for_telegram(piece)
        result = send_message(msg)

        return {
            "status": "sent",
            "content_id": piece.get("id", ""),
            "title": piece.get("title", ""),
            "telegram_result": result,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def push_content_piece(piece: dict) -> dict:
    """Push a specific content piece to Telegram."""
    if not is_configured():
        return {"status": "not_configured"}

    msg = format_content_for_telegram(piece)
    result = send_message(msg)
    return {"status": "sent", "telegram_result": result}
