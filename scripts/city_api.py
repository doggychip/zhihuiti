"""
zhihuiti City API — read-only Flask API serving agent/economy data from zhihuiti.db
"""

import json
import os
import sqlite3

from flask import Flask, g, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = os.environ.get("ZHIHUITI_DB", os.path.join(os.path.dirname(__file__), "..", "zhihuiti.db"))


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/api/agents")
def agents():
    """All agents with their current state."""
    db = get_db()
    rows = db.execute(
        "SELECT id, role, budget, depth, parent_agent_id, avg_score, alive, config, created_at FROM agents ORDER BY created_at DESC"
    ).fetchall()
    return jsonify([
        {
            "id": r["id"],
            "role": r["role"],
            "budget": r["budget"],
            "depth": r["depth"],
            "parent_agent_id": r["parent_agent_id"],
            "avg_score": r["avg_score"],
            "alive": bool(r["alive"]),
            "config": json.loads(r["config"] or "{}"),
            "created_at": r["created_at"],
        }
        for r in rows
    ])


@app.route("/api/agents/top")
def agents_top():
    """Top 10 agents by avg_score (alive only)."""
    db = get_db()
    rows = db.execute(
        "SELECT id, role, budget, avg_score, created_at FROM agents WHERE alive = 1 ORDER BY avg_score DESC LIMIT 10"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/economy")
def economy():
    """Economy state + recent transactions."""
    db = get_db()
    state_rows = db.execute("SELECT entity, state, updated_at FROM economy_state").fetchall()
    tx_rows = db.execute(
        "SELECT id, tx_type, from_entity, to_entity, amount, memo, created_at FROM transactions ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    return jsonify({
        "state": [
            {"entity": r["entity"], "state": json.loads(r["state"] or "{}"), "updated_at": r["updated_at"]}
            for r in state_rows
        ],
        "recent_transactions": [dict(r) for r in tx_rows],
    })


@app.route("/api/stats")
def stats():
    """High-level stats dashboard."""
    db = get_db()
    agent_count = db.execute("SELECT COUNT(*) as c FROM agents").fetchone()["c"]
    alive_count = db.execute("SELECT COUNT(*) as c FROM agents WHERE alive = 1").fetchone()["c"]
    tx_count = db.execute("SELECT COUNT(*) as c FROM transactions").fetchone()["c"]
    task_count = db.execute("SELECT COUNT(*) as c FROM tasks").fetchone()["c"]
    task_done = db.execute("SELECT COUNT(*) as c FROM tasks WHERE status = 'done'").fetchone()["c"]
    avg_score = db.execute("SELECT AVG(avg_score) as a FROM agents WHERE alive = 1").fetchone()["a"]
    total_budget = db.execute("SELECT SUM(budget) as s FROM agents WHERE alive = 1").fetchone()["s"]
    tx_volume = db.execute("SELECT SUM(amount) as s FROM transactions").fetchone()["s"]

    return jsonify({
        "agents": {"total": agent_count, "alive": alive_count, "avg_score": round(avg_score or 0, 3)},
        "economy": {"total_budget": round(total_budget or 0, 2), "transaction_count": tx_count, "transaction_volume": round(tx_volume or 0, 2)},
        "tasks": {"total": task_count, "completed": task_done},
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
