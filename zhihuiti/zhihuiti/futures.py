"""Futures / Staking system — agents bet on other agents' future performance.

Agents can stake tokens predicting that a target agent will achieve a minimum
average score over a specified number of future tasks.  If the target hits the
threshold the staker receives a 2x payout; otherwise the stake is forfeited.

Rules:
- Maximum stake: 30% of the staker's current budget
- Payout on success: 2x the staked amount
- Staking creates an Investment relationship between staker and target
- Stakes expire if the target is culled before completing enough tasks
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from zhihuiti.economy import Transaction, TransactionType

if TYPE_CHECKING:
    from zhihuiti.memory import Memory
    from zhihuiti.models import AgentState

console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_STAKE_RATIO = 0.30       # Staker can risk at most 30% of their budget
PAYOUT_MULTIPLIER = 2.0      # Winning stake returns 2x


class StakeStatus(str, Enum):
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    EXPIRED = "expired"


@dataclass
class Stake:
    """A futures bet placed by one agent on another's performance."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    staker_id: str = ""
    target_id: str = ""
    amount: float = 0.0
    predicted_score_min: float = 0.5
    duration_tasks: int = 5
    tasks_seen: int = 0
    status: StakeStatus = StakeStatus.ACTIVE
    payout: float = 0.0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


class FuturesMarket:
    """Manages agent-to-agent performance stakes.

    Flow:
    1. Staker places a bet on a target agent via ``place_stake()``
       - Tokens are deducted immediately (escrowed)
       - An Investment relationship is created
    2. After each round, ``evaluate_stakes()`` checks whether any active
       stakes have accumulated enough observed tasks to be settled.
    3. ``settle_stake()`` pays out 2x on success or forfeits the amount.
    """

    def __init__(self, memory: Memory):
        self.memory = memory
        self.stakes: list[Stake] = []

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def place_stake(
        self,
        staker: AgentState,
        target: AgentState,
        amount: float,
        predicted_score_min: float = 0.5,
        duration_tasks: int = 5,
    ) -> Stake | None:
        """Place a futures stake on *target*'s upcoming performance.

        Returns the new ``Stake`` on success, or ``None`` if the stake
        is rejected (insufficient budget, self-staking, etc.).
        """
        # --- validation ---------------------------------------------------
        if staker.id == target.id:
            console.print("  [red]Cannot stake on yourself.[/red]")
            return None

        max_allowed = staker.budget * MAX_STAKE_RATIO
        if amount > max_allowed:
            console.print(
                f"  [red]Stake {amount:.1f} exceeds 30% cap "
                f"({max_allowed:.1f}).[/red]"
            )
            return None

        if amount <= 0:
            console.print("  [red]Stake amount must be positive.[/red]")
            return None

        if not staker.deduct_budget(amount):
            console.print(
                f"  [red]Insufficient budget for stake "
                f"({staker.budget:.1f} < {amount:.1f}).[/red]"
            )
            return None

        # --- create stake -------------------------------------------------
        stake = Stake(
            staker_id=staker.id,
            target_id=target.id,
            amount=amount,
            predicted_score_min=predicted_score_min,
            duration_tasks=duration_tasks,
        )
        self.stakes.append(stake)

        # Persist escrow transaction
        self.memory.record_transaction(Transaction(
            tx_type=TransactionType.TRANSFER,
            from_entity=staker.id,
            to_entity="futures_escrow",
            amount=amount,
            memo=f"Stake {stake.id}: {amount:.1f} on {target.id[:8]}",
        ))
        self.memory.save_economy_state(f"stake_{stake.id}", {
            "id": stake.id,
            "staker_id": stake.staker_id,
            "target_id": stake.target_id,
            "amount": stake.amount,
            "predicted_score_min": stake.predicted_score_min,
            "duration_tasks": stake.duration_tasks,
            "tasks_seen": stake.tasks_seen,
            "status": stake.status.value,
            "payout": stake.payout,
            "created_at": stake.created_at,
        })

        # Investment relationship
        from zhihuiti.relationships import RelationshipGraph, RelationType
        graph = RelationshipGraph(self.memory)
        graph.add(
            RelationType.INVESTMENT, staker.id, target.id,
            metadata={
                "stake_id": stake.id,
                "amount": amount,
                "predicted_score_min": predicted_score_min,
            },
        )

        console.print(
            f"  [green]📈 Stake placed:[/green] {staker.id[:8]} → "
            f"{target.id[:8]}  {amount:.1f} tokens  "
            f"(need avg >= {predicted_score_min:.2f} over {duration_tasks} tasks)"
        )

        return stake

    def evaluate_stakes(
        self,
        agents: dict[str, AgentState],
        task_counts: dict[str, int] | None = None,
    ) -> list[Stake]:
        """Evaluate all active stakes and settle those that are ready.

        *task_counts* maps ``agent_id`` → number of new tasks completed
        since the last evaluation.  If ``None``, each active target is
        credited with one task (convenience for round-by-round calling).

        Returns a list of stakes that were settled this call.
        """
        settled: list[Stake] = []

        for stake in self.stakes:
            if stake.status != StakeStatus.ACTIVE:
                continue

            target = agents.get(stake.target_id)

            # Target culled / removed → expire the stake
            if target is None or not target.alive:
                stake.status = StakeStatus.EXPIRED
                stake.payout = 0.0
                self._persist_stake(stake)
                console.print(
                    f"  [yellow]⏰ Stake expired:[/yellow] {stake.id} "
                    f"(target {stake.target_id[:8]} no longer active)"
                )
                settled.append(stake)
                continue

            # Increment tasks seen
            new_tasks = (
                task_counts.get(stake.target_id, 0)
                if task_counts is not None
                else 1
            )
            stake.tasks_seen += new_tasks

            # Not enough tasks yet → skip
            if stake.tasks_seen < stake.duration_tasks:
                self._persist_stake(stake)
                continue

            # Ready to settle
            self.settle_stake(stake, target, agents)
            settled.append(stake)

        return settled

    def settle_stake(
        self,
        stake: Stake,
        target: AgentState,
        agents: dict[str, AgentState],
    ) -> None:
        """Settle a single stake based on the target's average score."""
        staker = agents.get(stake.staker_id)
        if staker is None:
            stake.status = StakeStatus.EXPIRED
            stake.payout = 0.0
            self._persist_stake(stake)
            return

        if target.avg_score >= stake.predicted_score_min:
            # --- WIN ---
            payout = stake.amount * PAYOUT_MULTIPLIER
            stake.status = StakeStatus.WON
            stake.payout = payout
            staker.budget += payout

            self.memory.record_transaction(Transaction(
                tx_type=TransactionType.TRANSFER,
                from_entity="futures_escrow",
                to_entity=staker.id,
                amount=payout,
                memo=f"Stake {stake.id} WON: 2x payout ({payout:.1f})",
            ))

            console.print(
                f"  [green]🎉 Stake WON:[/green] {stake.id}  "
                f"{staker.id[:8]} gets {payout:.1f} tokens  "
                f"(target avg {target.avg_score:.2f} >= {stake.predicted_score_min:.2f})"
            )
        else:
            # --- LOSE ---
            stake.status = StakeStatus.LOST
            stake.payout = 0.0

            self.memory.record_transaction(Transaction(
                tx_type=TransactionType.BURN,
                from_entity="futures_escrow",
                to_entity="treasury",
                amount=stake.amount,
                memo=f"Stake {stake.id} LOST: forfeited {stake.amount:.1f}",
            ))

            console.print(
                f"  [red]💸 Stake LOST:[/red] {stake.id}  "
                f"{staker.id[:8]} forfeits {stake.amount:.1f} tokens  "
                f"(target avg {target.avg_score:.2f} < {stake.predicted_score_min:.2f})"
            )

        self._persist_stake(stake)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_agent_stakes(self, agent_id: str) -> dict[str, list[Stake]]:
        """Return stakes where *agent_id* is the staker or the target.

        Returns ``{"placed": [...], "received": [...]}``.
        """
        placed = [s for s in self.stakes if s.staker_id == agent_id]
        received = [s for s in self.stakes if s.target_id == agent_id]
        return {"placed": placed, "received": received}

    def get_stats(self) -> dict:
        """Aggregate statistics across all stakes."""
        total = len(self.stakes)
        active = sum(1 for s in self.stakes if s.status == StakeStatus.ACTIVE)
        won = sum(1 for s in self.stakes if s.status == StakeStatus.WON)
        lost = sum(1 for s in self.stakes if s.status == StakeStatus.LOST)
        expired = sum(1 for s in self.stakes if s.status == StakeStatus.EXPIRED)
        total_staked = sum(s.amount for s in self.stakes)
        total_payouts = sum(s.payout for s in self.stakes)
        escrowed = sum(
            s.amount for s in self.stakes if s.status == StakeStatus.ACTIVE
        )
        return {
            "total_stakes": total,
            "active": active,
            "won": won,
            "lost": lost,
            "expired": expired,
            "total_staked": total_staked,
            "total_payouts": total_payouts,
            "escrowed": escrowed,
        }

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def print_report(self) -> None:
        """Print a summary panel of the futures market."""
        stats = self.get_stats()

        table = Table(title="Futures Market", show_header=False,
                      box=None, padding=(0, 2))
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total Stakes", str(stats["total_stakes"]))
        table.add_row("Active", f"[green]{stats['active']}[/green]")
        table.add_row("Won", f"[green]{stats['won']}[/green]")
        table.add_row("Lost", f"[red]{stats['lost']}[/red]")
        table.add_row("Expired", f"[yellow]{stats['expired']}[/yellow]")
        table.add_row("Total Staked", f"{stats['total_staked']:.1f}")
        table.add_row("Total Payouts", f"{stats['total_payouts']:.1f}")
        table.add_row("Escrowed", f"{stats['escrowed']:.1f}")

        console.print(Panel(table, title="📈 Futures / Staking"))

    def print_active_stakes(self) -> None:
        """Print a table of all currently active stakes."""
        active = [s for s in self.stakes if s.status == StakeStatus.ACTIVE]
        if not active:
            console.print("  [dim]No active stakes.[/dim]")
            return

        table = Table(title="Active Stakes")
        table.add_column("ID", style="dim")
        table.add_column("Staker", style="dim")
        table.add_column("Target", style="dim")
        table.add_column("Amount", justify="right")
        table.add_column("Min Score", justify="right")
        table.add_column("Progress", justify="center")
        table.add_column("Created", style="dim")

        for s in active:
            progress = f"{s.tasks_seen}/{s.duration_tasks}"
            created = s.created_at[:10] if len(s.created_at) >= 10 else s.created_at
            table.add_row(
                s.id, s.staker_id[:8], s.target_id[:8],
                f"{s.amount:.1f}", f"{s.predicted_score_min:.2f}",
                progress, created,
            )

        console.print(table)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _persist_stake(self, stake: Stake) -> None:
        """Persist stake state to the economy store."""
        self.memory.save_economy_state(f"stake_{stake.id}", {
            "id": stake.id,
            "staker_id": stake.staker_id,
            "target_id": stake.target_id,
            "amount": stake.amount,
            "predicted_score_min": stake.predicted_score_min,
            "duration_tasks": stake.duration_tasks,
            "tasks_seen": stake.tasks_seen,
            "status": stake.status.value,
            "payout": stake.payout,
            "created_at": stake.created_at,
        })
