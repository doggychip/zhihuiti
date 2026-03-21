"""SQLite-based memory system for agent learning."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class Memory:
    """Persistent memory store using SQLite."""

    def __init__(self, db_path: str = "zhihuiti.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                parent_task_id TEXT,
                assigned_agent_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                result TEXT DEFAULT '',
                score REAL,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                budget REAL NOT NULL DEFAULT 100.0,
                depth INTEGER NOT NULL DEFAULT 0,
                parent_agent_id TEXT,
                avg_score REAL DEFAULT 0.5,
                alive INTEGER DEFAULT 1,
                config TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS gene_pool (
                gene_id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                temperature REAL DEFAULT 0.7,
                avg_score REAL NOT NULL,
                parent_gene_id TEXT,
                mutation_notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_description TEXT NOT NULL,
                agent_role TEXT NOT NULL,
                result TEXT,
                score REAL,
                success INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS economy_state (
                entity TEXT PRIMARY KEY,
                state TEXT NOT NULL DEFAULT '{}',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                tx_type TEXT NOT NULL,
                from_entity TEXT NOT NULL,
                to_entity TEXT NOT NULL,
                amount REAL NOT NULL,
                memo TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS auctions (
                id TEXT PRIMARY KEY,
                task_description TEXT NOT NULL,
                role TEXT NOT NULL,
                price_ceiling REAL NOT NULL,
                num_bids INTEGER NOT NULL DEFAULT 0,
                winning_bid REAL,
                winner_id TEXT,
                savings REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS lineage (
                gene_id TEXT PRIMARY KEY,
                parent_a_gene TEXT,
                parent_b_gene TEXT,
                role TEXT NOT NULL,
                generation INTEGER NOT NULL DEFAULT 0,
                avg_score REAL DEFAULT 0.0,
                alive INTEGER DEFAULT 1,
                agent_id TEXT,
                system_prompt_hash TEXT DEFAULT '',
                temperature REAL DEFAULT 0.7,
                mutation_notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                rel_type TEXT NOT NULL,
                agent_a TEXT NOT NULL,
                agent_b TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                metadata TEXT DEFAULT '{}',
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS loans (
                id TEXT PRIMARY KEY,
                lender_id TEXT NOT NULL,
                borrower_id TEXT NOT NULL,
                principal REAL NOT NULL,
                interest_rate REAL NOT NULL DEFAULT 0.1,
                amount_repaid REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                due_at TIMESTAMP
            );
        """)
        self.conn.commit()

    def save_task(self, task_id: str, description: str, status: str,
                  result: str = "", score: float | None = None,
                  agent_id: str | None = None, parent_task_id: str | None = None,
                  metadata: dict | None = None) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO tasks
               (id, description, parent_task_id, assigned_agent_id, status, result, score, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, description, parent_task_id, agent_id, status,
             result, score, json.dumps(metadata or {})),
        )
        self.conn.commit()

    def save_agent(self, agent_id: str, role: str, budget: float,
                   depth: int, avg_score: float, alive: bool,
                   parent_agent_id: str | None = None,
                   config: dict | None = None) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO agents
               (id, role, budget, depth, parent_agent_id, avg_score, alive, config)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (agent_id, role, budget, depth, parent_agent_id,
             avg_score, int(alive), json.dumps(config or {})),
        )
        self.conn.commit()

    def save_to_gene_pool(self, gene_id: str, role: str, system_prompt: str,
                          temperature: float, avg_score: float,
                          parent_gene_id: str | None = None,
                          mutation_notes: str = "") -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO gene_pool
               (gene_id, role, system_prompt, temperature, avg_score,
                parent_gene_id, mutation_notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (gene_id, role, system_prompt, temperature, avg_score,
             parent_gene_id, mutation_notes),
        )
        self.conn.commit()

    def get_best_genes(self, role: str, limit: int = 5) -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM gene_pool
               WHERE role = ?
               ORDER BY avg_score DESC
               LIMIT ?""",
            (role, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def record_task_history(self, description: str, agent_role: str,
                           result: str, score: float) -> None:
        self.conn.execute(
            """INSERT INTO task_history
               (task_description, agent_role, result, score, success)
               VALUES (?, ?, ?, ?, ?)""",
            (description, agent_role, result, score, int(score >= 0.5)),
        )
        self.conn.commit()

    def get_similar_successes(self, role: str, limit: int = 3) -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM task_history
               WHERE agent_role = ? AND success = 1
               ORDER BY score DESC
               LIMIT ?""",
            (role, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Relationship methods ---

    def save_relationship(self, rel_id: str, rel_type: str, agent_a: str,
                          agent_b: str, strength: float = 1.0,
                          metadata: dict | None = None, active: bool = True) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO relationships
               (id, rel_type, agent_a, agent_b, strength, metadata, active, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (rel_id, rel_type, agent_a, agent_b, strength,
             json.dumps(metadata or {}), int(active)),
        )
        self.conn.commit()

    def get_agent_relationships(self, agent_id: str,
                                 rel_type: str | None = None) -> list[dict]:
        if rel_type:
            rows = self.conn.execute(
                """SELECT * FROM relationships
                   WHERE (agent_a = ? OR agent_b = ?) AND rel_type = ? AND active = 1
                   ORDER BY updated_at DESC""",
                (agent_id, agent_id, rel_type),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT * FROM relationships
                   WHERE (agent_a = ? OR agent_b = ?) AND active = 1
                   ORDER BY updated_at DESC""",
                (agent_id, agent_id),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_all_relationships(self, rel_type: str | None = None,
                               active_only: bool = True) -> list[dict]:
        query = "SELECT * FROM relationships"
        conditions = []
        params: list = []
        if active_only:
            conditions.append("active = 1")
        if rel_type:
            conditions.append("rel_type = ?")
            params.append(rel_type)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY updated_at DESC"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def deactivate_relationship(self, rel_id: str) -> None:
        self.conn.execute(
            "UPDATE relationships SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (rel_id,),
        )
        self.conn.commit()

    # --- Loan methods ---

    def save_loan(self, loan_id: str, lender_id: str, borrower_id: str,
                  principal: float, interest_rate: float, status: str = "active",
                  amount_repaid: float = 0.0) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO loans
               (id, lender_id, borrower_id, principal, interest_rate, amount_repaid, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (loan_id, lender_id, borrower_id, principal, interest_rate, amount_repaid, status),
        )
        self.conn.commit()

    def get_agent_loans(self, agent_id: str, role: str = "any") -> list[dict]:
        """Get loans where agent is lender or borrower (or both)."""
        if role == "lender":
            rows = self.conn.execute(
                "SELECT * FROM loans WHERE lender_id = ? ORDER BY created_at DESC",
                (agent_id,),
            ).fetchall()
        elif role == "borrower":
            rows = self.conn.execute(
                "SELECT * FROM loans WHERE borrower_id = ? ORDER BY created_at DESC",
                (agent_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT * FROM loans WHERE lender_id = ? OR borrower_id = ?
                   ORDER BY created_at DESC""",
                (agent_id, agent_id),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_active_loans(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM loans WHERE status = 'active' ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def update_loan(self, loan_id: str, amount_repaid: float, status: str) -> None:
        self.conn.execute(
            "UPDATE loans SET amount_repaid = ?, status = ? WHERE id = ?",
            (amount_repaid, status, loan_id),
        )
        self.conn.commit()

    def get_loan_stats(self) -> dict:
        row = self.conn.execute(
            """SELECT COUNT(*) as total,
                      SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
                      SUM(CASE WHEN status = 'repaid' THEN 1 ELSE 0 END) as repaid,
                      SUM(CASE WHEN status = 'defaulted' THEN 1 ELSE 0 END) as defaulted,
                      COALESCE(SUM(principal), 0) as total_principal,
                      COALESCE(SUM(amount_repaid), 0) as total_repaid
               FROM loans"""
        ).fetchone()
        return {
            "total_loans": row["total"],
            "active": row["active"],
            "repaid": row["repaid"],
            "defaulted": row["defaulted"],
            "total_principal": round(row["total_principal"], 2),
            "total_repaid": round(row["total_repaid"], 2),
        }

    # --- Economy methods ---

    def save_economy_state(self, entity: str, state: dict) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO economy_state (entity, state, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)""",
            (entity, json.dumps(state)),
        )
        self.conn.commit()

    def get_economy_state(self, entity: str) -> dict | None:
        row = self.conn.execute(
            "SELECT state FROM economy_state WHERE entity = ?", (entity,)
        ).fetchone()
        if row:
            return json.loads(row["state"])
        return None

    def record_transaction(self, tx) -> None:
        """Record a Transaction object."""
        self.conn.execute(
            """INSERT INTO transactions (id, tx_type, from_entity, to_entity, amount, memo)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (tx.id, tx.tx_type.value if hasattr(tx.tx_type, 'value') else tx.tx_type,
             tx.from_entity, tx.to_entity, tx.amount, tx.memo),
        )
        self.conn.commit()

    def get_agent_transactions(self, agent_id: str, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM transactions
               WHERE from_entity = ? OR to_entity = ?
               ORDER BY created_at DESC LIMIT ?""",
            (agent_id, agent_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_transaction_summary(self) -> dict:
        """Aggregate transaction stats."""
        rows = self.conn.execute(
            """SELECT tx_type, COUNT(*) as count, SUM(amount) as total
               FROM transactions GROUP BY tx_type"""
        ).fetchall()
        return {r["tx_type"]: {"count": r["count"], "total": round(r["total"], 2)} for r in rows}

    # --- Auction methods ---

    def save_auction(self, auction_id: str, task_description: str, role: str,
                     price_ceiling: float, num_bids: int, winning_bid: float,
                     winner_id: str, savings: float) -> None:
        self.conn.execute(
            """INSERT INTO auctions
               (id, task_description, role, price_ceiling, num_bids,
                winning_bid, winner_id, savings)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (auction_id, task_description, role, price_ceiling,
             num_bids, winning_bid, winner_id, savings),
        )
        self.conn.commit()

    def get_auction_stats(self) -> dict:
        row = self.conn.execute(
            """SELECT COUNT(*) as count, COALESCE(SUM(savings), 0) as total_savings,
                      COALESCE(AVG(savings), 0) as avg_savings,
                      COALESCE(AVG(winning_bid), 0) as avg_bid,
                      COALESCE(AVG(num_bids), 0) as avg_bids
               FROM auctions"""
        ).fetchone()
        return {
            "total_auctions": row["count"],
            "total_savings": round(row["total_savings"], 2),
            "avg_savings": round(row["avg_savings"], 2),
            "avg_winning_bid": round(row["avg_bid"], 2),
            "avg_bids_per_auction": round(row["avg_bids"], 1),
        }

    # --- Lineage/Bloodline methods ---

    def save_lineage(self, gene_id: str, role: str, generation: int,
                     parent_a_gene: str | None = None, parent_b_gene: str | None = None,
                     avg_score: float = 0.0, alive: bool = True,
                     agent_id: str | None = None, temperature: float = 0.7,
                     mutation_notes: str = "") -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO lineage
               (gene_id, parent_a_gene, parent_b_gene, role, generation,
                avg_score, alive, agent_id, temperature, mutation_notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (gene_id, parent_a_gene, parent_b_gene, role, generation,
             avg_score, int(alive), agent_id, temperature, mutation_notes),
        )
        self.conn.commit()

    def update_lineage_score(self, gene_id: str, avg_score: float, alive: bool) -> None:
        self.conn.execute(
            "UPDATE lineage SET avg_score = ?, alive = ? WHERE gene_id = ?",
            (avg_score, int(alive), gene_id),
        )
        self.conn.commit()

    def get_lineage_ancestors(self, gene_id: str, max_depth: int = 7) -> list[dict]:
        """Trace ancestry up to max_depth generations. BFS traversal."""
        ancestors = []
        queue = [gene_id]
        visited = set()
        depth = 0

        while queue and depth < max_depth:
            next_queue = []
            for gid in queue:
                if gid in visited or gid is None:
                    continue
                visited.add(gid)
                row = self.conn.execute(
                    "SELECT * FROM lineage WHERE gene_id = ?", (gid,)
                ).fetchone()
                if row:
                    record = dict(row)
                    record["trace_depth"] = depth
                    ancestors.append(record)
                    if row["parent_a_gene"]:
                        next_queue.append(row["parent_a_gene"])
                    if row["parent_b_gene"]:
                        next_queue.append(row["parent_b_gene"])
            queue = next_queue
            depth += 1

        return ancestors

    def get_lineage_descendants(self, gene_id: str, max_depth: int = 7) -> list[dict]:
        """Find all descendants of a gene (for 诛七族)."""
        descendants = []
        queue = [gene_id]
        visited = set()
        depth = 0

        while queue and depth < max_depth:
            next_queue = []
            for gid in queue:
                if gid in visited or gid is None:
                    continue
                visited.add(gid)
                rows = self.conn.execute(
                    """SELECT * FROM lineage
                       WHERE parent_a_gene = ? OR parent_b_gene = ?""",
                    (gid, gid),
                ).fetchall()
                for row in rows:
                    record = dict(row)
                    record["trace_depth"] = depth + 1
                    descendants.append(record)
                    next_queue.append(row["gene_id"])
            queue = next_queue
            depth += 1

        return descendants

    def get_top_lineage_genes(self, role: str, limit: int = 5) -> list[dict]:
        """Get highest-scoring alive genes for breeding."""
        rows = self.conn.execute(
            """SELECT * FROM lineage
               WHERE role = ? AND alive = 1
               ORDER BY avg_score DESC LIMIT ?""",
            (role, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_lineage_stats(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) as c FROM lineage").fetchone()["c"]
        alive = self.conn.execute("SELECT COUNT(*) as c FROM lineage WHERE alive = 1").fetchone()["c"]
        max_gen = self.conn.execute("SELECT MAX(generation) as m FROM lineage").fetchone()["m"] or 0
        avg_score = self.conn.execute(
            "SELECT AVG(avg_score) as a FROM lineage WHERE alive = 1"
        ).fetchone()["a"]
        return {
            "total_genes": total,
            "alive_genes": alive,
            "max_generation": max_gen,
            "avg_score": round(avg_score or 0.0, 3),
        }

    def get_stats(self) -> dict:
        tasks = self.conn.execute("SELECT COUNT(*) as c FROM tasks").fetchone()["c"]
        agents = self.conn.execute("SELECT COUNT(*) as c FROM agents").fetchone()["c"]
        genes = self.conn.execute("SELECT COUNT(*) as c FROM gene_pool").fetchone()["c"]
        avg = self.conn.execute(
            "SELECT AVG(score) as a FROM task_history WHERE score IS NOT NULL"
        ).fetchone()["a"]
        return {
            "total_tasks": tasks,
            "total_agents": agents,
            "gene_pool_size": genes,
            "avg_task_score": round(avg or 0.0, 3),
        }

    def close(self) -> None:
        self.conn.close()
