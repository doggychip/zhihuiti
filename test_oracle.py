"""Quick test: connect Oracle bot, send a message, disconnect."""

import asyncio
import os
import sys
from pathlib import Path

# Load .env
for line in Path(".env").read_text().splitlines():
    line = line.strip()
    if line and "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

import discord

TOKEN = os.environ["DISCORD_ORACLE_TOKEN"]
CHANNEL_ID = int(os.environ["DISCORD_ORACLE_CHANNEL_ID"])

print(f"Token: {TOKEN[:10]}...{TOKEN[-6:]}")
print(f"Channel: {CHANNEL_ID}")
sys.stdout.flush()

intents = discord.Intents.default()
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Connected as {client.user}", flush=True)
    try:
        channel = client.get_channel(CHANNEL_ID) or await client.fetch_channel(CHANNEL_ID)
        await channel.send("🔮 Oracle bot online")
        print(f"Message sent to #{channel.name}", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)
    await client.close()


async def main():
    try:
        async with asyncio.timeout(20):
            await client.start(TOKEN)
    except TimeoutError:
        print("Timed out connecting to Discord", flush=True)
        await client.close()
    except discord.LoginFailure as e:
        print(f"Login failed: {e}", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)

asyncio.run(main())
print("Done.", flush=True)
