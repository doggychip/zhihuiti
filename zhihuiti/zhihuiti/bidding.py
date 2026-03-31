"""Bidding system (竞标) — agents compete for tasks, lowest qualified bid wins.

Modeled after 如老师's auction mechanism:
1. Task is posted with a price ceiling (max the system will pay)
2. Qualified agents submit bids (how much they'd charge)
3. Qualification: agent must have clean track record (no failures)
4. Lowest bid wins, saving token/compute costs
5. Winner gets the task; losers return to the pool

The bidding system maintains a persistent pool of agents that can be
reused across goals, unlike the previous spawn-per-task model.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from zhihuiti.models import AgentConfig, AgentRole, AgentState, Realm, ROLE_TO_REALM

if TYPE_CHECKING:
    from zhihuiti.economy import Economy
    from zhihuiti.llm import LLM
    from zhihuiti.memory import Memory

console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_BID = 3.0              # Floor bid to prevent race-to-zero
DEFAULT_PRICE_CEILING = 30.0  # Max the system pays for a standard task
MIN_QUALIFICATION_SCORE = 0.4  # Minimum avg score to qualify for bidding
MIN_TASKS_FOR_RECORD = 0    # How many past tasks needed to have a record
POOL_SIZE_PER_ROLE = 3      # How many agents to maintain per role in pool (override with --pool-size)


@dataclass
class Bid:
    """A single bid from an agent for a task."""
    agent_id: str
    amount: float
    confidence: float = 0.5   # Agent's self-assessed confidence (0-1)
    reason: str = ""


@dataclass
class Auction:
    """An auction for a single task."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_description: str = ""
    role: AgentRole = AgentRole.CUSTOM
    price_ceiling: float = DEFAULT_PRICE_CEILING
    bids: list[Bid] = field(default_factory=list)
    winner_id: str | None = None
    winning_bid: float | None = None
    disqualified: list[str] = field(default_factory=list)


class AgentPool:
    """Persistent pool of reusable agents, organized by role."""

    def __init__(self):
        self.agents: dict[str, AgentState] = {}  # id -> agent

    def add(self, agent: AgentState) -> None:
        self.agents[agent.id] = agent

    def get_by_role(self, role: AgentRole) -> list[AgentState]:
        return [
            a for a in self.agents.values()
            if a.config.role == role and a.alive
        ]

    def get_all_alive(self) -> list[AgentState]:
        return [a for a in self.agents.values() if a.alive]

    def get(self, agent_id: str) -> AgentState | None:
        return self.agents.get(agent_id)

    @property
    def size(self) -> int:
        return len([a for a in self.agents.values() if a.alive])


class BiddingHouse:
    """Manages auctions where agents compete for tasks.

    Flow:
    1. ensure_pool() — make sure we have enough agents per role
    2. open_auction() — post a task for bidding
    3. collect_bids() — qualified agents submit bids
    4. award() — lowest qualified bid wins
    """

    def __init__(self, llm: LLM, memory: Memory, economy: Economy | None = None):
        self.llm = llm
        self.memory = memory
        self.economy = economy
        self.pool = AgentPool()
        self.auctions: list[Auction] = []
        self._load_pool()

    def _load_pool(self) -> None:
        """Load surviving agents from memory into the pool."""
        rows = self.memory.conn.execute(
            "SELECT id, role, budget, depth, avg_score, config "
            "FROM agents WHERE alive = 1 ORDER BY avg_score DESC"
        ).fetchall()
        import json
        from zhihuiti.prompts import get_prompt

        for row in rows:
            role_str = row["role"]
            try:
                role = AgentRole(role_str)
            except ValueError:
                role = AgentRole.CUSTOM

            agent = AgentState(
                id=row["id"],
                config=AgentConfig(
                    role=role,
                    system_prompt=get_prompt(role_str),
                    budget=row["budget"],
                    temperature=0.7,
                ),
                budget=row["budget"],
                depth=row["depth"],
            )
            # Assign realm based on role (not persisted in DB)
            agent.realm = ROLE_TO_REALM.get(role, Realm.EXECUTION)
            # Reconstruct avg_score from stored value
            if row["avg_score"] and row["avg_score"] != 0.5:
                agent.scores = [row["avg_score"]]
            self.pool.add(agent)

    def ensure_pool(self, role: AgentRole, count: int = POOL_SIZE_PER_ROLE,
                    spawn_fn=None) -> list[AgentState]:
        """Ensure we have at least `count` alive agents of this role in the pool.

        spawn_fn: callable(role, budget) -> AgentState — used to spawn new agents
        """
        existing = self.pool.get_by_role(role)
        alive = [a for a in existing if a.alive]

        needed = count - len(alive)
        if needed <= 0:
            return alive

        if spawn_fn is None:
            return alive

        for _ in range(needed):
            agent = spawn_fn(role, 100.0)
            self.pool.add(agent)
            alive.append(agent)

        return alive

    def qualify(self, agent: AgentState) -> tuple[bool, str]:
        """Check if an agent qualifies to bid.

        Qualification rules (如老师's model):
        - Agent must be alive
        - Agent must have sufficient budget to cover MIN_BID
        - Agent must not have a history of failures (avg_score >= threshold)
        - Agent must not be bankrupt
        """
        if not agent.alive:
            return False, "agent is dead"

        if agent.budget < MIN_BID:
            return False, f"budget too low ({agent.budget:.1f} < {MIN_BID})"

        # Check historical track record
        history = self.memory.conn.execute(
            """SELECT COUNT(*) as total,
                      SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                      AVG(score) as avg_score
               FROM task_history
               WHERE agent_role = ?""",
            (agent.config.role.value,),
        ).fetchone()

        if history and history["total"] >= MIN_TASKS_FOR_RECORD:
            avg = history["avg_score"] or 0.5
            if avg < MIN_QUALIFICATION_SCORE:
                return False, f"avg score too low ({avg:.2f} < {MIN_QUALIFICATION_SCORE})"

        # Check this specific agent's score
        if agent.scores and agent.avg_score < MIN_QUALIFICATION_SCORE:
            return False, f"agent avg score too low ({agent.avg_score:.2f})"

        return True, "qualified"

    def open_auction(self, task_description: str, role: AgentRole,
                     price_ceiling: float = DEFAULT_PRICE_CEILING) -> Auction:
        """Open a new auction for a task."""
        auction = Auction(
            task_description=task_description,
            role=role,
            price_ceiling=price_ceiling,
        )
        self.auctions.append(auction)
        return auction

    def collect_bids(self, auction: Auction) -> list[Bid]:
        """Have all qualified agents of the right role submit bids.

        Each agent bids based on:
        - Their confidence in handling the task
        - Their current budget (agents with more budget can afford to bid lower)
        - Their track record (better agents may bid higher, knowing they'll score well)

        Uses LLM to generate bids for richer agent behavior.
        """
        candidates = self.pool.get_by_role(auction.role)

        if not candidates:
            console.print(f"  [yellow]No candidates for {auction.role.value}[/yellow]")
            return []

        for agent in candidates:
            qualified, reason = self.qualify(agent)
            if not qualified:
                auction.disqualified.append(agent.id)
                continue

            # Generate bid using agent's own judgment
            bid_amount = self._generate_bid(agent, auction)

            if bid_amount > auction.price_ceiling:
                auction.disqualified.append(agent.id)
                continue

            bid = Bid(
                agent_id=agent.id,
                amount=round(bid_amount, 2),
                confidence=min(1.0, agent.avg_score + 0.1),
            )
            auction.bids.append(bid)

        return auction.bids

    def _generate_bid(self, agent: AgentState, auction: Auction) -> float:
        """Calculate an agent's bid for a task.

        Bidding strategy:
        - Base: proportional to price ceiling
        - Discount for higher confidence (better agents bid lower, they know they'll earn rewards)
        - Premium for lower budget (desperate agents bid higher to survive)
        - Slight randomness to prevent ties
        """
        import random

        confidence = agent.avg_score if agent.scores else 0.5

        # Base bid: 50-80% of ceiling
        base = auction.price_ceiling * random.uniform(0.5, 0.8)

        # Confidence discount: better agents bid lower (they'll earn it back in rewards)
        confidence_factor = 1.0 - (confidence * 0.3)  # Up to 30% discount

        # Budget pressure: low budget agents bid higher
        budget_ratio = min(agent.budget / 100.0, 1.0)
        budget_factor = 1.0 + (1.0 - budget_ratio) * 0.2  # Up to 20% premium

        bid = base * confidence_factor * budget_factor

        # Clamp to valid range
        return max(MIN_BID, min(bid, auction.price_ceiling))

    def award(self, auction: Auction) -> tuple[AgentState | None, Bid | None]:
        """Award the task to the lowest bidder.

        Returns (winning_agent, winning_bid) or (None, None) if no bids.
        """
        if not auction.bids:
            return None, None

        # Sort by amount (lowest first), break ties by confidence (highest first)
        sorted_bids = sorted(auction.bids, key=lambda b: (b.amount, -b.confidence))
        winner_bid = sorted_bids[0]

        winner = self.pool.get(winner_bid.agent_id)
        if winner is None:
            return None, None

        auction.winner_id = winner.id
        auction.winning_bid = winner_bid.amount

        # Record the auction in memory
        self.memory.save_auction(
            auction_id=auction.id,
            task_description=auction.task_description,
            role=auction.role.value,
            price_ceiling=auction.price_ceiling,
            num_bids=len(auction.bids),
            winning_bid=winner_bid.amount,
            winner_id=winner.id,
            savings=auction.price_ceiling - winner_bid.amount,
        )

        return winner, winner_bid

    def run_auction(self, task_description: str, role: AgentRole,
                    price_ceiling: float = DEFAULT_PRICE_CEILING,
                    spawn_fn=None) -> tuple[AgentState | None, Auction]:
        """Full auction flow: ensure pool → open → bid → award.

        Returns (winning_agent, auction).
        """
        # Ensure we have candidates
        self.ensure_pool(role, count=POOL_SIZE_PER_ROLE, spawn_fn=spawn_fn)

        # Open auction
        auction = self.open_auction(task_description, role, price_ceiling)

        # Collect bids
        bids = self.collect_bids(auction)

        if not bids:
            console.print(
                f"  [yellow]⚠ No bids for:[/yellow] {task_description[:60]}..."
            )
            return None, auction

        # Award to lowest bidder
        winner, winning_bid = self.award(auction)

        if winner and winning_bid:
            savings = auction.price_ceiling - winning_bid.amount
            savings_pct = (savings / auction.price_ceiling * 100) if auction.price_ceiling > 0 else 0

            console.print(
                f"  [bold green]🏷 Auction:[/bold green] {len(bids)} bids, "
                f"winner={winner.config.role.value} [dim]{winner.id}[/dim] "
                f"bid={winning_bid.amount:.1f} "
                f"(saved {savings:.1f} tokens, {savings_pct:.0f}%)"
            )

            # Deduct bid amount from agent's budget (they're committing this cost)
            winner.deduct_budget(winning_bid.amount)
            if self.economy:
                self.economy.record_task_fee(winner.id, winning_bid.amount)

        return winner, auction

    def print_auction_history(self) -> None:
        """Print a table of past auctions."""
        rows = self.memory.conn.execute(
            """SELECT role, task_description, price_ceiling, num_bids,
                      winning_bid, savings, winner_id, created_at
               FROM auctions ORDER BY created_at DESC LIMIT 20"""
        ).fetchall()

        if not rows:
            console.print("[dim]No auctions yet.[/dim]")
            return

        table = Table(title="Auction History")
        table.add_column("Role", style="cyan")
        table.add_column("Task", max_width=35)
        table.add_column("Ceiling", justify="right")
        table.add_column("Bids", justify="center")
        table.add_column("Won at", justify="right")
        table.add_column("Saved", justify="right", style="green")

        for r in rows:
            savings_pct = (r["savings"] / r["price_ceiling"] * 100) if r["price_ceiling"] > 0 else 0
            table.add_row(
                r["role"],
                r["task_description"][:35],
                f"{r['price_ceiling']:.0f}",
                str(r["num_bids"]),
                f"{r['winning_bid']:.1f}",
                f"{r['savings']:.1f} ({savings_pct:.0f}%)",
            )

        console.print(table)

        # Summary stats
        totals = self.memory.conn.execute(
            """SELECT COUNT(*) as count, SUM(savings) as total_savings,
                      AVG(savings) as avg_savings,
                      AVG(winning_bid) as avg_bid
               FROM auctions"""
        ).fetchone()
        if totals and totals["count"] > 0:
            console.print(
                f"\n[dim]Total auctions: {totals['count']} | "
                f"Total saved: {totals['total_savings']:.1f} tokens | "
                f"Avg savings: {totals['avg_savings']:.1f} | "
                f"Avg winning bid: {totals['avg_bid']:.1f}[/dim]"
            )
