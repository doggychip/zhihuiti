"""Discord Oracle — human-in-the-loop via Discord reactions.

Runs a discord.py bot in a background thread. When the circuit breaker
trips, sends an embed to the configured channel with ✅ ❌ 🔨 reactions,
waits for the creator's reaction, and returns the decision.
"""

from __future__ import annotations

import asyncio
import os
import threading
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from zhihuiti.circuit_breaker import FuseEvent

console = Console()

# Reaction → decision mapping
REACTION_MAP = {
    "✅": "approve",
    "❌": "reject",
    "🔨": "purge",
}

DECISION_TIMEOUT = 30 * 60  # 30 minutes


class DiscordOracle:
    """Discord bot for human oracle intervention.

    Connects to Discord in a background thread on ``start()``.
    Call ``ask(event)`` from any thread to send an embed and block
    until the creator reacts or timeout expires.
    """

    def __init__(self) -> None:
        self.token = os.environ.get("DISCORD_ORACLE_TOKEN", "")
        self.guild_id = int(os.environ.get("DISCORD_GUILD_ID", "0"))
        self.channel_id = int(os.environ.get("DISCORD_ORACLE_CHANNEL_ID", "0"))
        self.user_id = int(os.environ.get("DISCORD_RYAN_USER_ID", "0"))

        self._bot = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    @property
    def available(self) -> bool:
        """True if all required env vars are set."""
        return bool(self.token and self.guild_id and self.channel_id and self.user_id)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Connect the bot to Discord in a background daemon thread."""
        if not self.available:
            console.print("  [dim]Discord oracle: missing env vars, skipping.[/dim]")
            return

        import discord

        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True

        bot = discord.Client(intents=intents)

        @bot.event
        async def on_ready():
            console.print(f"  [green]Discord oracle connected as {bot.user}[/green]")
            self._ready.set()

        self._bot = bot

        def _run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(bot.start(self.token))

        self._thread = threading.Thread(target=_run, daemon=True, name="discord-oracle")
        self._thread.start()

        # Wait up to 30s for the bot to be ready
        if not self._ready.wait(timeout=30):
            console.print("  [yellow]Discord oracle: timed out waiting for connection.[/yellow]")

    def stop(self) -> None:
        """Disconnect the bot gracefully."""
        if self._bot and self._loop and not self._loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(self._bot.close(), self._loop)
            try:
                future.result(timeout=10)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Ask the human oracle
    # ------------------------------------------------------------------

    def ask(self, event: FuseEvent) -> str:
        """Send a fuse event to Discord and wait for a reaction.

        Returns one of: ``"approve"``, ``"reject"``, ``"purge"``.
        Defaults to ``"reject"`` on timeout or error.
        """
        if not self._bot or not self._loop or self._loop.is_closed():
            return "reject"

        future = asyncio.run_coroutine_threadsafe(
            self._ask_async(event), self._loop,
        )
        try:
            return future.result(timeout=DECISION_TIMEOUT + 30)
        except Exception as exc:
            console.print(f"  [yellow]Discord oracle error: {exc}[/yellow]")
            return "reject"

    async def _ask_async(self, event: FuseEvent) -> str:
        import discord

        channel = self._bot.get_channel(self.channel_id)
        if channel is None:
            try:
                channel = await self._bot.fetch_channel(self.channel_id)
            except Exception:
                console.print("  [yellow]Discord oracle: channel not found.[/yellow]")
                return "reject"

        # Build embed
        severity_color = {
            "emergency": discord.Color.red(),
            "halt": discord.Color.orange(),
            "warning": discord.Color.yellow(),
        }
        color = severity_color.get(event.severity.value, discord.Color.greyple())

        snippet = (event.output_snippet[:300] + "…") if len(event.output_snippet) > 300 else event.output_snippet

        embed = discord.Embed(
            title="🚨 熔断 CIRCUIT BREAKER",
            description=f"**{event.reason}**",
            color=color,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Law", value=event.law_name, inline=True)
        embed.add_field(name="Severity", value=event.severity.value.upper(), inline=True)
        embed.add_field(name="Agent", value=event.agent_id, inline=True)
        embed.add_field(name="Task", value=event.task_description[:200] or "—", inline=False)
        embed.add_field(name="Output", value=f"```\n{snippet}\n```", inline=False)
        embed.add_field(
            name="Actions",
            value="✅ Approve  ·  ❌ Reject  ·  🔨 Purge",
            inline=False,
        )
        embed.set_footer(text=f"Fuse ID: {event.id} | Timeout: 30 min → auto-reject")

        # Send with ping
        ping = f"<@{self.user_id}>"
        msg = await channel.send(content=ping, embed=embed)

        # Add reactions
        for emoji in REACTION_MAP:
            await msg.add_reaction(emoji)

        # Wait for the creator's reaction
        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return (
                user.id == self.user_id
                and reaction.message.id == msg.id
                and str(reaction.emoji) in REACTION_MAP
            )

        try:
            reaction, _ = await self._bot.wait_for(
                "reaction_add", check=check, timeout=DECISION_TIMEOUT,
            )
            decision = REACTION_MAP[str(reaction.emoji)]
        except asyncio.TimeoutError:
            decision = "reject"
            await msg.reply("⏰ Timeout — auto-rejected.")

        # Reply with result
        result_text = {
            "approve": "✅ Approved — system resuming.",
            "reject": "❌ Rejected — agent remains frozen.",
            "purge": "🔨 Purge ordered — 诛七族.",
        }
        await msg.reply(result_text.get(decision, decision))

        return decision


# Module-level singleton
_oracle: DiscordOracle | None = None


def get_discord_oracle() -> DiscordOracle:
    """Get or create the module-level singleton."""
    global _oracle
    if _oracle is None:
        _oracle = DiscordOracle()
    return _oracle
