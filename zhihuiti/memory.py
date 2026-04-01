"""SQLite-based memory system for agent learning."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


class Memory:
    """Persistent memory store using SQLite."""

    def __init__(self, db_path: str = "zhihuiti.db"):
        self.db_path = Path(db_path)
        # check_same_thread=False allows the connection to be shared across
        # threads; _write_lock serializes all writes for correctness.
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # WAL mode allows concurrent reads while writes are serialized
        self.conn.execute("PRAGMA journal_mode=WAL")
        # RLock (reentrant) serialises ALL connection access across threads.
        self._lock = threading.RLock()
        self._init_tables()

    # ------------------------------------------------------------------
    # Thread-safe query helpers
    # ------------------------------------------------------------------

    def _query(self, sql: str, params=()) -> list:
        """Execute a SELECT and return all rows, holding the lock."""
        with self._lock:
            return self.conn.execute(sql, params).fetchall()

    def _query_one(self, sql: str, params=()):
        """Execute a SELECT and return one row, holding the lock."""
        with self._lock:
            return self.conn.execute(sql, params).fetchone()

    def _init_tables(self) -> None:
        # Migrate existing DBs that predate the model column
        try:
            self.conn.execute("ALTER TABLE gene_pool ADD COLUMN model TEXT DEFAULT NULL")
            self.conn.commit()
        except Exception:
            pass  # Column already exists

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
                model TEXT DEFAULT NULL,
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

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                sender_id TEXT NOT NULL,
                receiver_id TEXT,
                goal_id TEXT,
                content TEXT NOT NULL,
                read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS goal_history (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                task_count INTEGER DEFAULT 0,
                avg_score REAL DEFAULT 0.0,
                summary TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS monitors (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                interval_seconds INTEGER NOT NULL,
                last_run TIMESTAMP,
                next_run TIMESTAMP,
                enabled INTEGER DEFAULT 1,
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

            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                goal_id TEXT,
                phase TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]',
                data TEXT NOT NULL DEFAULT '{}',
                parent_snapshot_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_goal ON snapshots(goal_id);
            CREATE INDEX IF NOT EXISTS idx_snapshots_phase ON snapshots(phase);

            -- Brain Intelligence: Collision history for metacognition
            CREATE TABLE IF NOT EXISTS collision_history (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                domain TEXT DEFAULT '',
                theory_a TEXT NOT NULL,
                theory_b TEXT NOT NULL,
                score_a REAL NOT NULL,
                score_b REAL NOT NULL,
                winner TEXT NOT NULL,
                tasks_a INTEGER DEFAULT 0,
                tasks_b INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Brain Intelligence: Regime preferences learned from collisions
            CREATE TABLE IF NOT EXISTS regime_preferences (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                theory TEXT NOT NULL,
                win_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                avg_score REAL DEFAULT 0.0,
                confidence REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Brain Intelligence: Consolidated knowledge (memory compression)
            CREATE TABLE IF NOT EXISTS consolidated_knowledge (
                id TEXT PRIMARY KEY,
                principle TEXT NOT NULL,
                domain TEXT DEFAULT '',
                evidence_count INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0.5,
                source_goals TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Brain Intelligence: Persistent causal edges across runs
            CREATE TABLE IF NOT EXISTS causal_knowledge (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                edge_type TEXT NOT NULL DEFAULT 'causes',
                strength TEXT NOT NULL DEFAULT 'weak',
                confidence REAL DEFAULT 0.5,
                evidence TEXT DEFAULT '{}',
                domain TEXT DEFAULT '',
                observation_count INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Brain Intelligence: Prediction error tracking
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                goal_id TEXT DEFAULT '',
                predicted_score REAL NOT NULL,
                predicted_outcome TEXT DEFAULT '',
                actual_score REAL,
                actual_outcome TEXT DEFAULT '',
                prediction_error REAL,
                causal_update TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            );

            -- Knowledge Base: ingested knowledge chunks
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL,
                chunk_type TEXT NOT NULL DEFAULT 'text',
                tags TEXT DEFAULT '[]',
                confidence REAL DEFAULT 0.5,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source ON knowledge_chunks(source);
            CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_type ON knowledge_chunks(chunk_type);

            CREATE TABLE IF NOT EXISTS epoch_stats (
                epoch INTEGER PRIMARY KEY,
                population INTEGER,
                avg_fitness REAL,
                money_supply REAL,
                gini REAL,
                archetype_counts TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_decisions (
                id TEXT PRIMARY KEY,
                epoch INTEGER,
                agent_id TEXT,
                action TEXT,
                params TEXT DEFAULT '{}',
                reasoning TEXT DEFAULT '',
                model_used TEXT DEFAULT 'haiku',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_agent_decisions_epoch ON agent_decisions(epoch);
            CREATE INDEX IF NOT EXISTS idx_agent_decisions_agent ON agent_decisions(epoch, agent_id);

            CREATE TABLE IF NOT EXISTS genome_snapshots (
                id TEXT PRIMARY KEY,
                epoch INTEGER,
                agent_id TEXT,
                gene_id TEXT,
                genome TEXT DEFAULT '{}',
                archetype TEXT DEFAULT '',
                fitness REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_genome_snapshots_epoch ON genome_snapshots(epoch);
            CREATE INDEX IF NOT EXISTS idx_genome_snapshots_agent ON genome_snapshots(epoch, agent_id);
        """)
        self.conn.commit()

    def save_task(self, task_id: str, description: str, status: str,
                  result: str = "", score: float | None = None,
                  agent_id: str | None = None, parent_task_id: str | None = None,
                  metadata: dict | None = None) -> None:
        with self._lock:
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
        with self._lock:
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
                          mutation_notes: str = "",
                          model: str | None = None) -> None:
        with self._lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO gene_pool
                   (gene_id, role, system_prompt, temperature, avg_score,
                    parent_gene_id, mutation_notes, model)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (gene_id, role, system_prompt, temperature, avg_score,
                 parent_gene_id, mutation_notes, model),
            )
            self.conn.commit()

    def get_best_genes(self, role: str, limit: int = 5) -> list[dict]:
        rows = self._query(
            "SELECT * FROM gene_pool WHERE role = ? ORDER BY avg_score DESC LIMIT ?",
            (role, limit),
        )
        return [dict(r) for r in rows]

    # --- Messaging methods ---

    def save_message(self, msg_id: str, sender_id: str, content: str,
                     receiver_id: str | None = None,
                     goal_id: str | None = None) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT INTO messages (id, sender_id, receiver_id, goal_id, content) VALUES (?, ?, ?, ?, ?)",
                (msg_id, sender_id, receiver_id, goal_id, content),
            )
            self.conn.commit()

    def get_unread_messages(self, receiver_id: str | None = None,
                            goal_id: str | None = None,
                            limit: int = 10) -> list[dict]:
        if receiver_id:
            rows = self._query(
                "SELECT * FROM messages WHERE (receiver_id = ? OR receiver_id IS NULL) AND read = 0 ORDER BY created_at DESC LIMIT ?",
                (receiver_id, limit),
            )
        elif goal_id:
            rows = self._query(
                "SELECT * FROM messages WHERE goal_id = ? AND read = 0 ORDER BY created_at DESC LIMIT ?",
                (goal_id, limit),
            )
        else:
            rows = self._query(
                "SELECT * FROM messages WHERE read = 0 ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return [dict(r) for r in rows]

    def mark_messages_read(self, msg_ids: list[str]) -> None:
        if not msg_ids:
            return
        placeholders = ",".join("?" for _ in msg_ids)
        with self._lock:
            self.conn.execute(
                f"UPDATE messages SET read = 1 WHERE id IN ({placeholders})",
                msg_ids,
            )
            self.conn.commit()

    # --- Goal history methods ---

    def save_goal(self, goal_id: str, goal: str, task_count: int,
                  avg_score: float, summary: str) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO goal_history (id, goal, task_count, avg_score, summary) VALUES (?, ?, ?, ?, ?)",
                (goal_id, goal, task_count, avg_score, summary),
            )
            self.conn.commit()

    def get_similar_goals(self, keywords: str, limit: int = 3) -> list[dict]:
        """Search past goals by keyword matching."""
        rows = self._query(
            "SELECT * FROM goal_history WHERE goal LIKE ? ORDER BY avg_score DESC LIMIT ?",
            (f"%{keywords[:50]}%", limit),
        )
        return [dict(r) for r in rows]

    def get_recent_goals(self, limit: int = 5) -> list[dict]:
        rows = self._query(
            "SELECT * FROM goal_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    # --- Monitor methods ---

    def save_monitor(self, monitor_id: str, goal: str, interval_seconds: int,
                     next_run: str | None = None) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO monitors (id, goal, interval_seconds, next_run) VALUES (?, ?, ?, ?)",
                (monitor_id, goal, interval_seconds, next_run),
            )
            self.conn.commit()

    def get_due_monitors(self) -> list[dict]:
        rows = self._query(
            "SELECT * FROM monitors WHERE enabled = 1 AND (next_run IS NULL OR next_run <= datetime('now'))"
        )
        return [dict(r) for r in rows]

    def update_monitor_run(self, monitor_id: str, last_run: str, next_run: str) -> None:
        with self._lock:
            self.conn.execute(
                "UPDATE monitors SET last_run = ?, next_run = ? WHERE id = ?",
                (last_run, next_run, monitor_id),
            )
            self.conn.commit()

    def list_monitors(self) -> list[dict]:
        rows = self._query("SELECT * FROM monitors ORDER BY created_at DESC")
        return [dict(r) for r in rows]

    def toggle_monitor(self, monitor_id: str, enabled: bool) -> None:
        with self._lock:
            self.conn.execute(
                "UPDATE monitors SET enabled = ? WHERE id = ?",
                (int(enabled), monitor_id),
            )
            self.conn.commit()

    def delete_monitor(self, monitor_id: str) -> None:
        with self._lock:
            self.conn.execute("DELETE FROM monitors WHERE id = ?", (monitor_id,))
            self.conn.commit()

    def record_task_history(self, description: str, agent_role: str,
                           result: str, score: float) -> None:
        with self._lock:
            self.conn.execute(
                """INSERT INTO task_history
                   (task_description, agent_role, result, score, success)
                   VALUES (?, ?, ?, ?, ?)""",
                (description, agent_role, result, score, int(score >= 0.5)),
            )
            self.conn.commit()

    def get_similar_successes(self, role: str, limit: int = 3) -> list[dict]:
        rows = self._query(
            "SELECT * FROM task_history WHERE agent_role = ? AND success = 1 ORDER BY score DESC LIMIT ?",
            (role, limit),
        )
        return [dict(r) for r in rows]

    # --- Relationship methods ---

    def save_relationship(self, rel_id: str, rel_type: str, agent_a: str,
                          agent_b: str, strength: float = 1.0,
                          metadata: dict | None = None, active: bool = True) -> None:
        with self._lock:
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
            rows = self._query(
                "SELECT * FROM relationships WHERE (agent_a = ? OR agent_b = ?) AND rel_type = ? AND active = 1 ORDER BY updated_at DESC",
                (agent_id, agent_id, rel_type),
            )
        else:
            rows = self._query(
                "SELECT * FROM relationships WHERE (agent_a = ? OR agent_b = ?) AND active = 1 ORDER BY updated_at DESC",
                (agent_id, agent_id),
            )
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
        rows = self._query(query, params)
        return [dict(r) for r in rows]

    def deactivate_relationship(self, rel_id: str) -> None:
        with self._lock:
            self.conn.execute(
                "UPDATE relationships SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (rel_id,),
            )
            self.conn.commit()

    # --- Loan methods ---

    def save_loan(self, loan_id: str, lender_id: str, borrower_id: str,
                  principal: float, interest_rate: float, status: str = "active",
                  amount_repaid: float = 0.0) -> None:
        with self._lock:
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
            rows = self._query("SELECT * FROM loans WHERE lender_id = ? ORDER BY created_at DESC", (agent_id,))
        elif role == "borrower":
            rows = self._query("SELECT * FROM loans WHERE borrower_id = ? ORDER BY created_at DESC", (agent_id,))
        else:
            rows = self._query("SELECT * FROM loans WHERE lender_id = ? OR borrower_id = ? ORDER BY created_at DESC", (agent_id, agent_id))
        return [dict(r) for r in rows]

    def get_active_loans(self) -> list[dict]:
        rows = self._query("SELECT * FROM loans WHERE status = 'active' ORDER BY created_at DESC")
        return [dict(r) for r in rows]

    def update_loan(self, loan_id: str, amount_repaid: float, status: str) -> None:
        with self._lock:
            self.conn.execute(
                "UPDATE loans SET amount_repaid = ?, status = ? WHERE id = ?",
                (amount_repaid, status, loan_id),
            )
            self.conn.commit()

    def get_loan_stats(self) -> dict:
        row = self._query_one(
            """SELECT COUNT(*) as total,
                      COALESCE(SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END), 0) as active,
                      COALESCE(SUM(CASE WHEN status = 'repaid' THEN 1 ELSE 0 END), 0) as repaid,
                      COALESCE(SUM(CASE WHEN status = 'defaulted' THEN 1 ELSE 0 END), 0) as defaulted,
                      COALESCE(SUM(principal), 0) as total_principal,
                      COALESCE(SUM(amount_repaid), 0) as total_repaid
               FROM loans"""
        )
        return {
            "total_loans": row["total"],
            "active": row["active"] or 0,
            "repaid": row["repaid"] or 0,
            "defaulted": row["defaulted"] or 0,
            "total_principal": round(row["total_principal"] or 0, 2),
            "total_repaid": round(row["total_repaid"] or 0, 2),
        }

    # --- Economy methods ---

    def save_economy_state(self, entity: str, state: dict) -> None:
        with self._lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO economy_state (entity, state, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)""",
                (entity, json.dumps(state)),
            )
            self.conn.commit()

    def get_economy_state(self, entity: str) -> dict | None:
        row = self._query_one("SELECT state FROM economy_state WHERE entity = ?", (entity,))
        if row:
            return json.loads(row["state"])
        return None

    def record_transaction(self, tx) -> None:
        """Record a Transaction object."""
        with self._lock:
            self.conn.execute(
                """INSERT INTO transactions (id, tx_type, from_entity, to_entity, amount, memo)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (tx.id, tx.tx_type.value if hasattr(tx.tx_type, 'value') else tx.tx_type,
                 tx.from_entity, tx.to_entity, tx.amount, tx.memo),
            )
            self.conn.commit()

    def get_agent_transactions(self, agent_id: str, limit: int = 20) -> list[dict]:
        rows = self._query(
            "SELECT * FROM transactions WHERE from_entity = ? OR to_entity = ? ORDER BY created_at DESC LIMIT ?",
            (agent_id, agent_id, limit),
        )
        return [dict(r) for r in rows]

    def get_transaction_summary(self) -> dict:
        """Aggregate transaction stats."""
        rows = self._query("SELECT tx_type, COUNT(*) as count, SUM(amount) as total FROM transactions GROUP BY tx_type")
        return {r["tx_type"]: {"count": r["count"], "total": round(r["total"], 2)} for r in rows}

    # --- Evolution simulation methods ---

    def save_epoch_stats(self, epoch: int, population: int, avg_fitness: float,
                         money_supply: float, gini: float,
                         archetype_counts: dict) -> None:
        with self._lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO epoch_stats
                   (epoch, population, avg_fitness, money_supply, gini, archetype_counts)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (epoch, population, avg_fitness, money_supply, gini,
                 json.dumps(archetype_counts)),
            )
            self.conn.commit()

    def save_agent_decision(self, decision_id: str, epoch: int, agent_id: str,
                            action: str, params: dict, reasoning: str,
                            model_used: str = "haiku") -> None:
        with self._lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO agent_decisions
                   (id, epoch, agent_id, action, params, reasoning, model_used)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (decision_id, epoch, agent_id, action, json.dumps(params),
                 reasoning, model_used),
            )
            self.conn.commit()

    def save_genome_snapshot(self, snapshot_id: str, epoch: int, agent_id: str,
                             gene_id: str, genome: dict, archetype: str,
                             fitness: float) -> None:
        with self._lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO genome_snapshots
                   (id, epoch, agent_id, gene_id, genome, archetype, fitness)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (snapshot_id, epoch, agent_id, gene_id, json.dumps(genome),
                 archetype, fitness),
            )
            self.conn.commit()

    def get_epoch_stats(self, limit: int = 100) -> list[dict]:
        rows = self._query(
            "SELECT * FROM epoch_stats ORDER BY epoch DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]

    def get_agent_decisions_for_epoch(self, epoch: int) -> list[dict]:
        rows = self._query(
            "SELECT * FROM agent_decisions WHERE epoch = ? ORDER BY agent_id",
            (epoch,))
        return [dict(r) for r in rows]

    def get_genome_snapshots_for_epoch(self, epoch: int) -> list[dict]:
        rows = self._query(
            "SELECT * FROM genome_snapshots WHERE epoch = ? ORDER BY agent_id",
            (epoch,))
        return [dict(r) for r in rows]

    # --- Auction methods ---

    def save_auction(self, auction_id: str, task_description: str, role: str,
                     price_ceiling: float, num_bids: int, winning_bid: float,
                     winner_id: str, savings: float) -> None:
        with self._lock:
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
        row = self._query_one(
            """SELECT COUNT(*) as count, COALESCE(SUM(savings), 0) as total_savings,
                      COALESCE(AVG(savings), 0) as avg_savings,
                      COALESCE(AVG(winning_bid), 0) as avg_bid,
                      COALESCE(AVG(num_bids), 0) as avg_bids
               FROM auctions"""
        )
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
        with self._lock:
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
        with self._lock:
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
                row = self._query_one("SELECT * FROM lineage WHERE gene_id = ?", (gid,))
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
                rows = self._query(
                    "SELECT * FROM lineage WHERE parent_a_gene = ? OR parent_b_gene = ?",
                    (gid, gid),
                )
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
        rows = self._query(
            "SELECT * FROM lineage WHERE role = ? AND alive = 1 ORDER BY avg_score DESC LIMIT ?",
            (role, limit),
        )
        return [dict(r) for r in rows]

    def get_lineage_stats(self) -> dict:
        total = self._query_one("SELECT COUNT(*) as c FROM lineage")["c"]
        alive = self._query_one("SELECT COUNT(*) as c FROM lineage WHERE alive = 1")["c"]
        max_gen = self._query_one("SELECT MAX(generation) as m FROM lineage")["m"] or 0
        avg_score = self._query_one("SELECT AVG(avg_score) as a FROM lineage WHERE alive = 1")["a"]
        return {
            "total_genes": total,
            "alive_genes": alive,
            "max_generation": max_gen,
            "avg_score": round(avg_score or 0.0, 3),
        }

    def get_stats(self) -> dict:
        tasks = self._query_one("SELECT COUNT(*) as c FROM tasks")["c"]
        agents = self._query_one("SELECT COUNT(*) as c FROM agents")["c"]
        genes = self._query_one("SELECT COUNT(*) as c FROM gene_pool")["c"]
        avg = self._query_one("SELECT AVG(score) as a FROM task_history WHERE score IS NOT NULL")["a"]
        return {
            "total_tasks": tasks,
            "total_agents": agents,
            "gene_pool_size": genes,
            "avg_task_score": round(avg or 0.0, 3),
        }

    # ------------------------------------------------------------------
    # Versioned state: checkpoint / rollback / recall / search
    # ------------------------------------------------------------------

    def checkpoint(
        self,
        phase: str,
        goal_id: str | None = None,
        tags: list[str] | None = None,
        include: list[str] | None = None,
    ) -> str:
        """Snapshot current state and return the snapshot ID.

        ``include`` controls which tables are captured.  Defaults to the
        core state tables: agents, economy_state, tasks, gene_pool.
        Append-only audit tables (transactions, task_history, auctions)
        are excluded by default since they don't need rollback.

        Each snapshot records its predecessor (``parent_snapshot_id``) so
        you can walk the checkpoint chain for a goal.
        """
        tables = include or ["agents", "economy_state", "tasks", "gene_pool"]
        data: dict[str, list[dict]] = {}
        for table in tables:
            rows = self._query(f"SELECT * FROM {table}")  # noqa: S608
            data[table] = [dict(r) for r in rows]

        snapshot_id = uuid.uuid4().hex[:12]

        # Find the most recent snapshot for this goal to set parent
        parent_id = None
        if goal_id:
            parent = self._query_one(
                "SELECT id FROM snapshots WHERE goal_id = ? ORDER BY rowid DESC LIMIT 1",
                (goal_id,),
            )
            if parent:
                parent_id = parent["id"]

        with self._lock:
            self.conn.execute(
                """INSERT INTO snapshots
                   (id, goal_id, phase, tags, data, parent_snapshot_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    snapshot_id,
                    goal_id,
                    phase,
                    json.dumps(tags or []),
                    json.dumps(data),
                    parent_id,
                ),
            )
            self.conn.commit()

        return snapshot_id

    def rollback(self, snapshot_id: str) -> dict:
        """Restore state from a snapshot.

        Replaces all rows in the captured tables with the snapshot data.
        Returns the restored data dict so callers can inspect what changed.
        """
        row = self._query_one(
            "SELECT data FROM snapshots WHERE id = ?", (snapshot_id,)
        )
        if not row:
            raise ValueError(f"Snapshot {snapshot_id} not found")

        data: dict[str, list[dict]] = json.loads(row["data"])

        with self._lock:
            for table, rows in data.items():
                if not rows:
                    self.conn.execute(f"DELETE FROM {table}")  # noqa: S608
                    continue
                self.conn.execute(f"DELETE FROM {table}")  # noqa: S608
                cols = list(rows[0].keys())
                placeholders = ",".join("?" for _ in cols)
                col_names = ",".join(cols)
                for r in rows:
                    self.conn.execute(
                        f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})",  # noqa: S608
                        tuple(r[c] for c in cols),
                    )
            self.conn.commit()

        return data

    def recall(
        self,
        goal_id: str | None = None,
        phase: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """Retrieve recent snapshots, optionally filtered by goal or phase."""
        conditions: list[str] = []
        params: list = []
        if goal_id:
            conditions.append("goal_id = ?")
            params.append(goal_id)
        if phase:
            conditions.append("phase = ?")
            params.append(phase)

        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        rows = self._query(
            f"SELECT id, goal_id, phase, tags, parent_snapshot_id, created_at "
            f"FROM snapshots{where} ORDER BY created_at DESC LIMIT ?",
            params,
        )
        return [dict(r) for r in rows]

    def search_snapshots(self, tags: list[str], limit: int = 10) -> list[dict]:
        """Find snapshots that match ANY of the given tags."""
        conditions = " OR ".join("tags LIKE ?" for _ in tags)
        params = [f"%{t}%" for t in tags]
        params.append(limit)  # type: ignore[arg-type]
        rows = self._query(
            f"SELECT id, goal_id, phase, tags, parent_snapshot_id, created_at "
            f"FROM snapshots WHERE ({conditions}) ORDER BY created_at DESC LIMIT ?",
            params,
        )
        return [dict(r) for r in rows]

    def get_snapshot_data(self, snapshot_id: str) -> dict | None:
        """Return the full data payload of a snapshot."""
        row = self._query_one(
            "SELECT data FROM snapshots WHERE id = ?", (snapshot_id,)
        )
        if row:
            return json.loads(row["data"])
        return None

    def get_snapshot_chain(self, snapshot_id: str, max_depth: int = 10) -> list[dict]:
        """Walk the parent chain from a snapshot back to the root."""
        chain: list[dict] = []
        current_id: str | None = snapshot_id
        depth = 0
        while current_id and depth < max_depth:
            row = self._query_one(
                "SELECT id, goal_id, phase, tags, parent_snapshot_id, created_at "
                "FROM snapshots WHERE id = ?",
                (current_id,),
            )
            if not row:
                break
            chain.append(dict(row))
            current_id = row["parent_snapshot_id"]
            depth += 1
        return chain

    # Brain Intelligence: Collision history & regime preferences
    # ------------------------------------------------------------------

    def save_collision(self, collision_id: str, goal: str, domain: str,
                       theory_a: str, theory_b: str, score_a: float,
                       score_b: float, winner: str, tasks_a: int = 0,
                       tasks_b: int = 0, metadata: dict | None = None) -> None:
        with self._lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO collision_history
                   (id, goal, domain, theory_a, theory_b, score_a, score_b,
                    winner, tasks_a, tasks_b, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (collision_id, goal, domain, theory_a, theory_b, score_a,
                 score_b, winner, tasks_a, tasks_b, json.dumps(metadata or {})),
            )
            self.conn.commit()

    def get_collision_history(self, domain: str | None = None,
                              limit: int = 50) -> list[dict]:
        if domain:
            rows = self._query(
                "SELECT * FROM collision_history WHERE domain = ? ORDER BY created_at DESC LIMIT ?",
                (domain, limit),
            )
        else:
            rows = self._query(
                "SELECT * FROM collision_history ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return [dict(r) for r in rows]

    def save_regime_preference(self, pref_id: str, domain: str, theory: str,
                                win_count: int, total_count: int,
                                avg_score: float, confidence: float) -> None:
        with self._lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO regime_preferences
                   (id, domain, theory, win_count, total_count, avg_score,
                    confidence, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (pref_id, domain, theory, win_count, total_count,
                 avg_score, confidence),
            )
            self.conn.commit()

    def get_regime_preference(self, domain: str) -> dict | None:
        row = self._query_one(
            "SELECT * FROM regime_preferences WHERE domain = ? ORDER BY confidence DESC LIMIT 1",
            (domain,),
        )
        return dict(row) if row else None

    def get_all_regime_preferences(self) -> list[dict]:
        rows = self._query(
            "SELECT * FROM regime_preferences ORDER BY confidence DESC"
        )
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Brain Intelligence: Memory consolidation
    # ------------------------------------------------------------------

    def save_consolidated_knowledge(self, knowledge_id: str, principle: str,
                                     domain: str, evidence_count: int,
                                     confidence: float,
                                     source_goals: list[str] | None = None) -> None:
        with self._lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO consolidated_knowledge
                   (id, principle, domain, evidence_count, confidence,
                    source_goals, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (knowledge_id, principle, domain, evidence_count, confidence,
                 json.dumps(source_goals or [])),
            )
            self.conn.commit()

    def get_consolidated_knowledge(self, domain: str | None = None,
                                    limit: int = 20) -> list[dict]:
        if domain:
            rows = self._query(
                "SELECT * FROM consolidated_knowledge WHERE domain = ? ORDER BY confidence DESC LIMIT ?",
                (domain, limit),
            )
        else:
            rows = self._query(
                "SELECT * FROM consolidated_knowledge ORDER BY confidence DESC LIMIT ?",
                (limit,),
            )
        return [dict(r) for r in rows]

    def get_stale_goals(self, max_age_days: int = 30, limit: int = 50) -> list[dict]:
        """Get old goal history entries for consolidation."""
        rows = self._query(
            """SELECT * FROM goal_history
               WHERE created_at < datetime('now', ?)
               ORDER BY created_at ASC LIMIT ?""",
            (f"-{max_age_days} days", limit),
        )
        return [dict(r) for r in rows]

    def get_old_task_history(self, max_age_days: int = 30,
                             limit: int = 100) -> list[dict]:
        """Get old task history for consolidation."""
        rows = self._query(
            """SELECT * FROM task_history
               WHERE created_at < datetime('now', ?)
               ORDER BY created_at ASC LIMIT ?""",
            (f"-{max_age_days} days", limit),
        )
        return [dict(r) for r in rows]

    def purge_old_task_history(self, max_age_days: int = 30) -> int:
        """Delete old task history entries after consolidation."""
        with self._lock:
            cursor = self.conn.execute(
                "DELETE FROM task_history WHERE created_at < datetime('now', ?)",
                (f"-{max_age_days} days",),
            )
            self.conn.commit()
            return cursor.rowcount

    # ------------------------------------------------------------------
    # Brain Intelligence: Persistent causal knowledge
    # ------------------------------------------------------------------

    def save_causal_knowledge(self, edge_id: str, source: str, target: str,
                               edge_type: str, strength: str, confidence: float,
                               evidence: dict | None = None, domain: str = "",
                               observation_count: int = 1) -> None:
        with self._lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO causal_knowledge
                   (id, source, target, edge_type, strength, confidence,
                    evidence, domain, observation_count, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (edge_id, source, target, edge_type, strength, confidence,
                 json.dumps(evidence or {}), domain, observation_count),
            )
            self.conn.commit()

    def get_causal_knowledge(self, domain: str | None = None,
                              min_confidence: float = 0.0) -> list[dict]:
        if domain:
            rows = self._query(
                """SELECT * FROM causal_knowledge
                   WHERE domain = ? AND confidence >= ?
                   ORDER BY confidence DESC""",
                (domain, min_confidence),
            )
        else:
            rows = self._query(
                """SELECT * FROM causal_knowledge
                   WHERE confidence >= ?
                   ORDER BY confidence DESC""",
                (min_confidence,),
            )
        return [dict(r) for r in rows]

    def find_causal_edge(self, source: str, target: str,
                          domain: str = "") -> dict | None:
        row = self._query_one(
            "SELECT * FROM causal_knowledge WHERE source = ? AND target = ? AND domain = ?",
            (source, target, domain),
        )
        return dict(row) if row else None

    def increment_causal_observation(self, edge_id: str,
                                      new_confidence: float) -> None:
        with self._lock:
            self.conn.execute(
                """UPDATE causal_knowledge
                   SET observation_count = observation_count + 1,
                       confidence = ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (new_confidence, edge_id),
            )
            self.conn.commit()

    # ------------------------------------------------------------------
    # Brain Intelligence: Prediction error tracking
    # ------------------------------------------------------------------

    def save_prediction(self, pred_id: str, agent_id: str, task_id: str,
                        predicted_score: float, predicted_outcome: str = "",
                        goal_id: str = "") -> None:
        with self._lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO predictions
                   (id, agent_id, task_id, goal_id, predicted_score,
                    predicted_outcome)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (pred_id, agent_id, task_id, goal_id, predicted_score,
                 predicted_outcome),
            )
            self.conn.commit()

    def resolve_prediction(self, pred_id: str, actual_score: float,
                           actual_outcome: str = "",
                           prediction_error: float = 0.0,
                           causal_update: dict | None = None) -> None:
        with self._lock:
            self.conn.execute(
                """UPDATE predictions
                   SET actual_score = ?, actual_outcome = ?,
                       prediction_error = ?, causal_update = ?,
                       resolved_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (actual_score, actual_outcome, prediction_error,
                 json.dumps(causal_update or {}), pred_id),
            )
            self.conn.commit()

    def get_agent_predictions(self, agent_id: str, resolved: bool = True,
                               limit: int = 20) -> list[dict]:
        if resolved:
            rows = self._query(
                """SELECT * FROM predictions
                   WHERE agent_id = ? AND resolved_at IS NOT NULL
                   ORDER BY resolved_at DESC LIMIT ?""",
                (agent_id, limit),
            )
        else:
            rows = self._query(
                """SELECT * FROM predictions
                   WHERE agent_id = ? AND resolved_at IS NULL
                   ORDER BY created_at DESC LIMIT ?""",
                (agent_id, limit),
            )
        return [dict(r) for r in rows]

    def get_prediction_stats(self) -> dict:
        total = self._query_one("SELECT COUNT(*) as c FROM predictions")["c"]
        resolved = self._query_one(
            "SELECT COUNT(*) as c FROM predictions WHERE resolved_at IS NOT NULL"
        )["c"]
        avg_error = self._query_one(
            "SELECT AVG(ABS(prediction_error)) as a FROM predictions WHERE prediction_error IS NOT NULL"
        )["a"]
        return {
            "total_predictions": total,
            "resolved": resolved,
            "pending": total - resolved,
            "avg_absolute_error": round(avg_error or 0.0, 4),
        }

    def close(self) -> None:
        self.conn.close()
