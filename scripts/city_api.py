"""Flask-based read-only API for the zhihuiti city snapshot.

Serves agent, task, economy, and transaction data from a SQLite snapshot.
Designed for Zeabur deployment with gunicorn.
"""

import json
import os
import sqlite3

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = os.environ.get("ZHIHUITI_DB", "/app/zhihuiti.db")

# On startup, force the DB out of WAL mode to avoid disk I/O errors
# in container overlay filesystems after restarts.
def _init_db():
    if not os.path.exists(DB_PATH):
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.close()
        # Remove leftover WAL/SHM files
        for suffix in ("-wal", "-shm"):
            path = DB_PATH + suffix
            if os.path.exists(path):
                os.remove(path)
    except Exception as e:
        print(f"[init_db] Warning: {e}")

_init_db()


def get_db():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/health")
def health():
    """Health check with DB diagnostics."""
    import traceback
    diag = {
        "status": "ok",
        "service": "zhihuiti-city",
        "db_path": DB_PATH,
        "db_exists": os.path.exists(DB_PATH),
    }
    if os.path.exists(DB_PATH):
        diag["db_size_mb"] = round(os.path.getsize(DB_PATH) / 1048576, 2)
    # Try opening DB
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        diag["tables"] = tables
        count = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        diag["agent_count"] = count
        conn.close()
    except Exception as e:
        diag["status"] = "error"
        diag["db_error"] = str(e)
        diag["db_traceback"] = traceback.format_exc()
    # Check /app/data too
    diag["app_data_exists"] = os.path.isdir("/app/data")
    if os.path.isdir("/app/data"):
        try:
            diag["app_data_contents"] = os.listdir("/app/data")
        except Exception:
            pass
    diag["app_contents"] = os.listdir("/app")
    return jsonify(diag)


@app.route("/api/stats")
def stats():
    """Combined stats: agent counts, task counts, economy overview."""
    db = get_db()
    try:
        agents = db.execute("SELECT COUNT(*) as total, SUM(alive) as alive FROM agents").fetchone()
        tasks = db.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed, "
            "SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed "
            "FROM tasks"
        ).fetchone()
        tx_count = db.execute("SELECT COUNT(*) as c FROM transactions").fetchone()["c"]

        # Economy state
        economy = {}
        for row in db.execute("SELECT entity, state, updated_at FROM economy_state"):
            try:
                economy[row["entity"]] = json.loads(row["state"])
            except (json.JSONDecodeError, TypeError):
                economy[row["entity"]] = row["state"]

        # Role breakdown
        roles = db.execute(
            "SELECT role, COUNT(*) as count, SUM(alive) as alive, "
            "ROUND(AVG(avg_score), 3) as avg_score "
            "FROM agents GROUP BY role"
        ).fetchall()

        return jsonify({
            "agents": {
                "total": agents["total"],
                "alive": int(agents["alive"] or 0),
            },
            "tasks": {
                "total": tasks["total"],
                "completed": int(tasks["completed"] or 0),
                "failed": int(tasks["failed"] or 0),
            },
            "transactions": tx_count,
            "roles": [dict(r) for r in roles],
            "economy": economy,
        })
    finally:
        db.close()


@app.route("/api/agents")
def agents():
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, role, budget, depth, avg_score, alive, created_at FROM agents ORDER BY created_at DESC"
        ).fetchall()
        return jsonify({"agents": [dict(r) for r in rows], "count": len(rows)})
    finally:
        db.close()


@app.route("/api/tasks")
def tasks():
    limit = request.args.get("limit", 50, type=int)
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, description, assigned_agent_id, status, score, created_at "
            "FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return jsonify({"tasks": [dict(r) for r in rows], "count": len(rows)})
    finally:
        db.close()


@app.route("/api/transactions")
def transactions():
    limit = request.args.get("limit", 50, type=int)
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, tx_type, from_entity, to_entity, amount, memo, created_at "
            "FROM transactions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return jsonify({"transactions": [dict(r) for r in rows], "count": len(rows)})
    finally:
        db.close()


@app.route("/api/think", methods=["POST"])
def think():
    """Generate an AI thought for an agent. Uses Claude API if ANTHROPIC_API_KEY is set."""
    import random

    data = request.get_json(silent=True) or {}
    role = data.get("role", "coder")
    agent_id = data.get("agent_id", "unknown")
    score = data.get("score", 0.5)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return jsonify({"thought": None})  # client falls back to local thoughts

    try:
        import urllib.request

        prompt = (
            f"You are a {role} AI agent (id: {agent_id[:6]}, score: {score:.2f}) "
            f"in a competitive multi-agent economy. In ONE short sentence (under 20 words), "
            f"say what you're thinking about doing right now. Be specific to your role. "
            f"Be creative and varied. No quotes."
        )
        body = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 60,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            result = json.loads(resp.read())
            text = result["content"][0]["text"].strip()
            return jsonify({"thought": text})
    except Exception:
        return jsonify({"thought": None})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
