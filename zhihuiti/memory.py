"""SQLite persistence layer for zhihuiti."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import AgentConfig, AgentRole, Task


DB_PATH = Path.home() / ".zhihuiti" / "memory.db"


def _now() -> str:
    return datetime.utcnow().isoformat()


class Memory:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            generation INTEGER NOT NULL DEFAULT 0,
            budget REAL NOT NULL DEFAULT 100.0,
            score REAL NOT NULL DEFAULT 0.5,
            parent_ids TEXT NOT NULL DEFAULT '[]',
            lineage TEXT NOT NULL DEFAULT '[]',
            specialization TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            assigned_agent_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            result TEXT,
            score REAL,
            bid_amount REAL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS economy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            amount REAL NOT NULL,
            agent_id TEXT,
            timestamp TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS auctions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            winner_agent_id TEXT,
            winning_bid REAL,
            num_bidders INTEGER NOT NULL DEFAULT 0,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bloodlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent1_id TEXT,
            parent2_id TEXT,
            child_id TEXT NOT NULL,
            generation INTEGER NOT NULL DEFAULT 0,
            timestamp TEXT NOT NULL
        );
        """)
        self._conn.commit()

    # ── Agent methods ────────────────────────────────────────────────────────

    def save_agent(self, agent: AgentConfig, status: str = "active") -> None:
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO agents (id, role, generation, budget, score, parent_ids, lineage,
                                specialization, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                role=excluded.role,
                generation=excluded.generation,
                budget=excluded.budget,
                score=excluded.score,
                parent_ids=excluded.parent_ids,
                lineage=excluded.lineage,
                specialization=excluded.specialization,
                status=excluded.status
        """, (
            agent.id,
            agent.role.value if isinstance(agent.role, AgentRole) else agent.role,
            agent.generation,
            agent.budget,
            agent.score,
            json.dumps(agent.parent_ids),
            json.dumps(agent.lineage),
            agent.specialization,
            _now(),
            status,
        ))
        self._conn.commit()

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_agent(row)

    def list_agents(
        self,
        status: Optional[str] = None,
        role: Optional[str] = None,
    ) -> list[AgentConfig]:
        query = "SELECT * FROM agents WHERE 1=1"
        params: list = []
        if status:
            query += " AND status=?"
            params.append(status)
        if role:
            query += " AND role=?"
            params.append(role)
        query += " ORDER BY created_at DESC"
        cur = self._conn.cursor()
        rows = cur.execute(query, params).fetchall()
        return [self._row_to_agent(r) for r in rows]

    def update_agent_status(self, agent_id: str, status: str) -> None:
        self._conn.execute(
            "UPDATE agents SET status=? WHERE id=?", (status, agent_id)
        )
        self._conn.commit()

    def update_agent_budget(self, agent_id: str, budget: float) -> None:
        self._conn.execute(
            "UPDATE agents SET budget=? WHERE id=?", (budget, agent_id)
        )
        self._conn.commit()

    def update_agent_score(self, agent_id: str, score: float) -> None:
        self._conn.execute(
            "UPDATE agents SET score=? WHERE id=?", (score, agent_id)
        )
        self._conn.commit()

    @staticmethod
    def _row_to_agent(row: sqlite3.Row) -> AgentConfig:
        return AgentConfig(
            id=row["id"],
            role=AgentRole(row["role"]),
            generation=row["generation"],
            budget=row["budget"],
            score=row["score"],
            parent_ids=json.loads(row["parent_ids"]),
            lineage=json.loads(row["lineage"]),
            specialization=row["specialization"],
        )

    # ── Task methods ─────────────────────────────────────────────────────────

    def save_task(self, task: Task) -> None:
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO tasks (id, description, assigned_agent_id, status, result,
                               score, bid_amount, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                assigned_agent_id=excluded.assigned_agent_id,
                status=excluded.status,
                result=excluded.result,
                score=excluded.score,
                bid_amount=excluded.bid_amount
        """, (
            task.id,
            task.description,
            task.assigned_agent_id,
            task.status,
            task.result,
            task.score,
            task.bid_amount,
            _now(),
        ))
        self._conn.commit()

    def get_task(self, task_id: str) -> Optional[Task]:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_task(row)

    def list_tasks(self, limit: int = 50) -> list[Task]:
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_task(r) for r in rows]

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            description=row["description"],
            assigned_agent_id=row["assigned_agent_id"],
            status=row["status"],
            result=row["result"],
            score=row["score"],
            bid_amount=row["bid_amount"],
        )

    # ── Economy methods ───────────────────────────────────────────────────────

    def save_economy_event(
        self,
        event_type: str,
        amount: float,
        agent_id: Optional[str] = None,
        description: str = "",
    ) -> None:
        self._conn.execute(
            """INSERT INTO economy (event_type, amount, agent_id, timestamp, description)
               VALUES (?, ?, ?, ?, ?)""",
            (event_type, amount, agent_id, _now(), description),
        )
        self._conn.commit()

    def get_economy_events(self, limit: int = 100) -> list[dict]:
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT * FROM economy ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Auction methods ───────────────────────────────────────────────────────

    def save_auction(
        self,
        task_id: str,
        winner_agent_id: Optional[str],
        winning_bid: Optional[float],
        num_bidders: int,
    ) -> None:
        self._conn.execute(
            """INSERT INTO auctions (task_id, winner_agent_id, winning_bid, num_bidders, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (task_id, winner_agent_id, winning_bid, num_bidders, _now()),
        )
        self._conn.commit()

    def list_auctions(self, limit: int = 50) -> list[dict]:
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT * FROM auctions ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Bloodline methods ─────────────────────────────────────────────────────

    def save_bloodline_event(
        self,
        child_id: str,
        generation: int,
        parent1_id: Optional[str] = None,
        parent2_id: Optional[str] = None,
    ) -> None:
        self._conn.execute(
            """INSERT INTO bloodlines (parent1_id, parent2_id, child_id, generation, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (parent1_id, parent2_id, child_id, generation, _now()),
        )
        self._conn.commit()

    def get_agent_lineage(self, agent_id: str) -> list[str]:
        """Return lineage list stored in agents table."""
        agent = self.get_agent(agent_id)
        if agent is None:
            return []
        return agent.lineage

    def close(self) -> None:
        self._conn.close()
