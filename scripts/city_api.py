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

DB_PATH = os.environ.get("ZHIHUITI_DB", "/app/data/zhihuiti.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "zhihuiti-city"})


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
