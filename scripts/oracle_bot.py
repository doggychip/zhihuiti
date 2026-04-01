import discord, sqlite3, os, sys, json
from pathlib import Path
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

TOKEN = os.getenv("DISCORD_ORACLE_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_ORACLE_CHANNEL_ID", "0"))
DB_PATH = Path(__file__).parent.parent / "zhihuiti.db"

llm = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
)
MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

def get_system_context():
    ctx = ["You are Oracle, the intelligence layer of zhihuiti — Ryan's autonomous multi-agent system with token economics.",
           "Answer conversationally in the same language Ryan uses. Keep responses concise.\n"]

    if DB_PATH.exists():
        db = sqlite3.connect(str(DB_PATH))

        total = db.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        alive = db.execute("SELECT COUNT(*) FROM agents WHERE alive=1").fetchone()[0]
        ctx.append(f"AGENTS: {total} total, {alive} alive, {total-alive} dead")

        # Top 10 by score
        rows = db.execute("SELECT id, role, avg_score, budget, depth FROM agents WHERE alive=1 ORDER BY avg_score DESC LIMIT 10").fetchall()
        if rows:
            ctx.append("\nTOP 10 AGENTS:")
            for r in rows:
                ctx.append(f"  {r[0][:12]} | {r[1]} | score:{r[2]:.2f} | budget:{r[3]:.0f} | depth:{r[4]}")

        # By role
        roles = db.execute("SELECT role, COUNT(*) FROM agents WHERE alive=1 GROUP BY role ORDER BY COUNT(*) DESC").fetchall()
        if roles:
            ctx.append("\nAGENTS BY ROLE:")
            for r in roles:
                ctx.append(f"  {r[0]}: {r[1]}")

        # Economy
        econ = db.execute("SELECT entity, state FROM economy_state").fetchall()
        if econ:
            ctx.append("\nECONOMY:")
            for r in econ:
                ctx.append(f"  {r[0]}: {r[1][:200]}")

        # Recent tasks
        try:
            tasks = db.execute("SELECT id, status, score, created_at FROM tasks ORDER BY created_at DESC LIMIT 5").fetchall()
            if tasks:
                ctx.append("\nRECENT TASKS:")
                for t in tasks:
                    ctx.append(f"  {t[0][:12]} | {t[1]} | score:{t[2]} | {t[3]}")
        except:
            pass

        # Auctions
        try:
            auctions = db.execute("SELECT COUNT(*) FROM auctions").fetchone()[0]
            ctx.append(f"\nTOTAL AUCTIONS: {auctions}")
        except:
            pass

        # Predictions
        try:
            preds = db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
            ctx.append(f"TOTAL PREDICTIONS: {preds}")
        except:
            pass

        # Knowledge
        try:
            knowledge = db.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0]
            ctx.append(f"KNOWLEDGE CHUNKS: {knowledge}")
        except:
            pass

        # Collisions
        try:
            collisions = db.execute("SELECT COUNT(*) FROM collision_history").fetchone()[0]
            ctx.append(f"THEORY COLLISIONS: {collisions}")
        except:
            pass

        db.close()

    # Latest report
    reports_dir = Path(__file__).parent.parent / "reports"
    if reports_dir.exists():
        reports = sorted(reports_dir.glob("*.md"))
        if reports:
            latest = reports[-1].read_text()[:2000]
            ctx.append(f"\nLATEST REPORT ({reports[-1].name}):\n{latest}")

    return "\n".join(ctx)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

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
    print(f"MSG: {msg.author} | {msg.content}")
    try:
        system = get_system_context()
        resp = llm.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": msg.content}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        answer = resp.choices[0].message.content
        if len(answer) > 1900:
            answer = answer[:1900] + "..."
        await msg.channel.send(answer)
    except Exception as e:
        print(f"Error: {e}")
        await msg.channel.send(f"⚠️ Error: {str(e)[:200]}")

client.run(TOKEN)
