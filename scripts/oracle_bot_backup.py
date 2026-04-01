import discord
import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_ORACLE_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_ORACLE_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

DB_PATH = Path(__file__).parent.parent / "zhihuiti.db"

@client.event
async def on_ready():
    print(f"Oracle connected as {client.user}")
    ch = client.get_channel(CHANNEL_ID)
    if ch:
        await ch.send("🔮 Oracle online")

@client.event
async def on_message(msg):
    if msg.author.bot or msg.channel.id != CHANNEL_ID:
        return
    content = msg.content.strip().lower()

    if content == "!status":
        reports = sorted(Path("reports").glob("*.md"))
        if reports:
            text = reports[-1].read_text()[:1500]
            await msg.channel.send(f"📊 Latest report:\n```\n{text}\n```")
        else:
            await msg.channel.send("No reports yet.")

    elif content == "!agents":
        if not DB_PATH.exists():
            await msg.channel.send("DB not found.")
            return
        db = sqlite3.connect(str(DB_PATH))
        rows = db.execute("SELECT name, role, realm, total_score, tasks_completed, generation FROM agents WHERE alive=1 ORDER BY total_score DESC LIMIT 10").fetchall()
        db.close()
        if rows:
            lines = ["🏆 Top 10 Agents:"]
            for r in rows:
                lines.append(f"`{r[0]}` | {r[1]} | {r[2]} | score:{r[3]:.2f} | tasks:{r[4]} | gen:{r[5]}")
            await msg.channel.send("\n".join(lines))
        else:
            await msg.channel.send("No agents found.")

    elif content == "!economy":
        if not DB_PATH.exists():
            await msg.channel.send("DB not found.")
            return
        db = sqlite3.connect(str(DB_PATH))
        rows = db.execute("SELECT key, value FROM economy_state").fetchall()
        db.close()
        if rows:
            lines = ["💰 Economy:"]
            for r in rows:
                lines.append(f"  {r[0]}: {r[1]}")
            await msg.channel.send("\n".join(lines))
        else:
            await msg.channel.send("No economy data.")

    elif content == "!help":
        await msg.channel.send("🔮 Commands:\n`!status` — latest daemon report\n`!agents` — top 10 agents\n`!economy` — treasury & money supply\n`!help` — this message")

client.run(TOKEN)
