#!/usr/bin/env python3
"""Discord dev bot — answers questions about zhihuiti backend AND Big Brain frontend.

Knowledge sources loaded on startup:
  1. ~/ryan-os/output/**/*.md    — Ryan's decisions, preferences, patterns
  2. ~/zhihuiti/CLAUDE.md        — backend architecture & conventions
  3. ~/pixel-perfect-replica-51aecdac/src/**/*.{ts,tsx} — Big Brain frontend

When someone messages in the dev channel, the bot searches the knowledge base
for relevant context, calls DeepSeek, and replies in-channel.

Env vars (from .env):
  DISCORD_DEV_BOT_TOKEN   — bot token
  DISCORD_DEV_CHANNEL_ID  — channel to listen in
  LLM_API_KEY             — DeepSeek API key
  LLM_BASE_URL            — DeepSeek base URL
  LLM_MODEL               — model name (default: deepseek-chat)
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import discord
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

BOT_TOKEN = os.environ.get("DISCORD_DEV_BOT_TOKEN", "")
CHANNEL_ID = int(os.environ.get("DISCORD_DEV_CHANNEL_ID", "0"))
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

KNOWLEDGE_DIR = Path.home() / "ryan-os" / "output"
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
FRONTEND_SRC = Path.home() / "pixel-perfect-replica-51aecdac" / "src"

# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------

# Each entry: {"name": str, "category": str, "content": str}
knowledge_base: list[dict[str, str]] = []


def load_knowledge():
    """Load all three knowledge sources."""
    knowledge_base.clear()

    # --- Source 1: CLAUDE.md (backend architecture) ---
    if CLAUDE_MD.exists():
        text = CLAUDE_MD.read_text(encoding="utf-8", errors="replace")
        knowledge_base.append({
            "name": "CLAUDE.md",
            "category": "backend",
            "content": text,
        })
        print(f"  [backend] CLAUDE.md ({len(text):,} chars)")
    else:
        print(f"  [backend] CLAUDE.md not found, skipping")

    # --- Source 2: ~/ryan-os/output/**/*.md (Ryan's decisions) ---
    ryan_count = 0
    if KNOWLEDGE_DIR.is_dir():
        for md_file in sorted(KNOWLEDGE_DIR.glob("**/*.md")):
            try:
                text = md_file.read_text(encoding="utf-8", errors="replace")
                knowledge_base.append({
                    "name": md_file.name,
                    "category": "ryan",
                    "content": text,
                })
                ryan_count += 1
            except Exception as e:
                print(f"  Warning: failed to read {md_file}: {e}")
        print(f"  [ryan] {ryan_count} files from {KNOWLEDGE_DIR}")
    else:
        print(f"  [ryan] {KNOWLEDGE_DIR} not found, skipping")

    # --- Source 3: Big Brain frontend .ts/.tsx files ---
    frontend_count = 0
    if FRONTEND_SRC.is_dir():
        for pattern in ("**/*.ts", "**/*.tsx"):
            for src_file in sorted(FRONTEND_SRC.glob(pattern)):
                try:
                    text = src_file.read_text(encoding="utf-8", errors="replace")
                    rel = src_file.relative_to(FRONTEND_SRC)
                    knowledge_base.append({
                        "name": f"frontend/{rel}",
                        "category": "frontend",
                        "content": text,
                    })
                    frontend_count += 1
                except Exception as e:
                    print(f"  Warning: failed to read {src_file}: {e}")
        print(f"  [frontend] {frontend_count} files from {FRONTEND_SRC}")
    else:
        print(f"  [frontend] {FRONTEND_SRC} not found, skipping")

    print(f"  Total: {len(knowledge_base)} documents loaded")


def search_knowledge(query: str, max_chunks: int = 8, max_chars: int = 8000) -> str:
    """Keyword search over the knowledge base with category boosting.

    Scores each document by how many query words appear in it.
    Boosts results if query mentions frontend/backend/connect keywords.
    Returns top matches concatenated (truncated to max_chars).
    """
    query_lower = query.lower()
    query_words = set(query_lower.split())
    if not query_words:
        return ""

    # Detect intent to boost relevant categories
    frontend_kw = {"frontend", "react", "component", "page", "ui", "tsx", "big brain", "bigbrain", "lovable"}
    backend_kw = {"backend", "api", "endpoint", "daemon", "trading", "orchestrat", "pipeline", "zhihuiti"}
    connect_kw = {"connect", "integrate", "wire", "hook up", "bridge", "between"}

    wants_frontend = any(w in query_lower for w in frontend_kw)
    wants_backend = any(w in query_lower for w in backend_kw)
    wants_connect = any(w in query_lower for w in connect_kw)

    scored: list[tuple[float, dict[str, str]]] = []
    for doc in knowledge_base:
        lower = doc["content"].lower()
        hits = sum(1 for w in query_words if w in lower)
        if hits == 0:
            continue

        score = hits / len(query_words)

        # Category boosting
        cat = doc["category"]
        if wants_frontend and cat == "frontend":
            score *= 1.5
        if wants_backend and cat == "backend":
            score *= 1.5
        if wants_connect:
            # When asking about connecting, boost both backend and frontend
            if cat in ("frontend", "backend"):
                score *= 1.3

        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)

    parts: list[str] = []
    total = 0
    for _score, doc in scored[:max_chunks]:
        snippet = doc["content"]
        if total + len(snippet) > max_chars:
            snippet = snippet[: max_chars - total]
        tag = doc["category"].upper()
        parts.append(f"--- [{tag}] {doc['name']} ---\n{snippet}")
        total += len(snippet)
        if total >= max_chars:
            break

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

http_client = httpx.AsyncClient(timeout=120)

SYSTEM_PROMPT = """\
You are the zhihuiti dev assistant, an expert on two codebases:

1. **zhihuiti** (Python backend) — trading intelligence pipeline with orchestrator, \
LLM agents, knowledge extraction, circuit breaker, daemon mode, and REST API.
2. **Big Brain** (React/TypeScript frontend) — the UI for zhihuiti, built with \
Vite + React + shadcn/ui + Tailwind.

You also know Ryan's preferences and decision patterns from his notes.

Your job:
- Answer questions about either codebase using the provided context.
- When asked how to connect frontend ↔ backend, suggest concrete integration \
approaches (API endpoints, data flow, component structure).
- Be concise and direct. Use code examples when helpful.
- If the context doesn't contain relevant info, say so and answer from general knowledge.
- Respond in the same language as the question.\
"""


LLM_MAX_RETRIES = 3
LLM_RETRY_BACKOFF = 2  # seconds


async def ask_llm(question: str, context: str) -> str:
    """Call DeepSeek with the question and retrieved context.

    Retries up to LLM_MAX_RETRIES times with LLM_RETRY_BACKOFF second intervals
    on connection/timeout errors. Raises on exhaustion.
    """
    user_msg = question
    if context:
        user_msg = f"Knowledge base context:\n{context}\n\n---\nQuestion: {question}"

    url = LLM_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    last_exc: Exception | None = None
    for attempt in range(LLM_MAX_RETRIES):
        try:
            resp = await http_client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.TimeoutException) as e:
            last_exc = e
            if attempt < LLM_MAX_RETRIES - 1:
                await asyncio.sleep(LLM_RETRY_BACKOFF * (attempt + 1))

    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Daily digest (早报)
# ---------------------------------------------------------------------------

OPEN_QUESTIONS_PATH = Path.home() / "ryan-os" / "output" / "context" / "open_questions.md"

DIGEST_SYSTEM_PROMPT = """\
You are Spark, the zhihuiti dev bot. Summarize the following git log into a concise \
Chinese-language changelog grouped by area (backend, frontend, infra, etc.). \
Keep each bullet to one line. If there are no commits, say 无变更.\
"""


def _git_log_since_yesterday() -> str:
    """Run git log --since='1 day ago' on ~/zhihuiti."""
    try:
        result = subprocess.run(
            ["git", "log", "--since=1 day ago", "--oneline", "--no-merges"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.stdout.strip() or "无变更"
    except Exception as e:
        return f"(git error: {e})"


def _read_open_questions() -> str:
    """Read open_questions.md and extract unresolved items."""
    if not OPEN_QUESTIONS_PATH.exists():
        return "无待解决项"

    try:
        text = OPEN_QUESTIONS_PATH.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            return "无待解决项"
        # Extract unchecked items (- [ ] lines)
        unchecked = [
            line.strip()
            for line in text.splitlines()
            if line.strip().startswith("- [ ]")
        ]
        if unchecked:
            return "\n".join(unchecked)
        # No checkbox format — return the whole file (truncated)
        return text[:1500]
    except Exception as e:
        return f"(read error: {e})"


async def _summarize_git_log(raw_log: str) -> str:
    """Use the LLM to summarize the raw git log."""
    if raw_log == "无变更" or raw_log.startswith("(git error"):
        return raw_log

    url = LLM_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": DIGEST_SYSTEM_PROMPT},
            {"role": "user", "content": raw_log},
        ],
        "temperature": 0.3,
        "max_tokens": 800,
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = await http_client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        # Fallback: just return the raw log
        return raw_log


async def post_daily_digest():
    """Build and post the morning digest to #zhihuiti-dev."""
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print("[digest] Channel not found, skipping digest")
        return

    raw_log = _git_log_since_yesterday()
    summary = await _summarize_git_log(raw_log)
    open_qs = _read_open_questions()

    digest = (
        "☀️ 早报\n\n"
        f"**昨日变更:**\n{summary}\n\n"
        f"**待解决:**\n{open_qs}"
    )

    # Discord 2000 char limit
    if len(digest) > 2000:
        digest = digest[:1997] + "..."

    await channel.send(digest)
    print(f"[digest] Posted morning digest ({len(digest)} chars)")


# ---------------------------------------------------------------------------
# Discord bot
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


scheduler = AsyncIOScheduler()


@client.event
async def on_ready():
    print(f"Dev bot connected as {client.user}")
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        print(f"  Listening in #{channel.name}")
    else:
        print(f"  Warning: channel {CHANNEL_ID} not found (bot may lack access)")

    # Schedule daily digest at 09:00 HKT (UTC+8 → 01:00 UTC)
    if not scheduler.running:
        scheduler.add_job(
            post_daily_digest,
            CronTrigger(hour=1, minute=0, timezone="UTC"),
            id="daily_digest",
            replace_existing=True,
        )
        scheduler.start()
        print("  Digest scheduled: daily at 09:00 HKT")


@client.event
async def on_message(message: discord.Message):
    # Ignore bots
    if message.author.bot:
        return

    # Only respond in the configured channel
    if message.channel.id != CHANNEL_ID:
        return

    question = message.content.strip()
    if not question:
        return

    async with message.channel.typing():
        try:
            context = search_knowledge(question)
            answer = await ask_llm(question, context)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.TimeoutException):
            answer = "⚠️ LLM connection failed, try again in a minute."
        except Exception as e:
            answer = f"Error: {e}"

    # Discord has a 2000 char limit
    if len(answer) > 2000:
        answer = answer[:1997] + "..."

    await message.reply(answer)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not BOT_TOKEN:
        print("Error: DISCORD_DEV_BOT_TOKEN not set in .env")
        sys.exit(1)
    if not CHANNEL_ID:
        print("Error: DISCORD_DEV_CHANNEL_ID not set in .env")
        sys.exit(1)
    if not LLM_API_KEY:
        print("Error: LLM_API_KEY not set in .env")
        sys.exit(1)

    print("Loading knowledge base...")
    load_knowledge()

    print(f"Starting dev bot (model: {LLM_MODEL})...")
    client.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
