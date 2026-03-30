"""Relationship graph and lending system — 8 relationship types + agent lending.

如老师's 8 relationship types between agents:
1. 交易关系 (Transaction) — agents that have traded tokens
2. 投资关系 (Investment) — agent A invested in agent B's success
3. 悬赏关系 (Bounty) — agent A posted a bounty fulfilled by B
4. 雇佣关系 (Employment) — agent A hired agent B for ongoing work
5. 补贴关系 (Subsidy) — agent A subsidizes agent B's operations
6. 血缘关系 (Bloodline) — genetic parent-child relationship
7. 宿主关系 (Host) — agent A hosts/shelters agent B
8. 竞争关系 (Competition) — agents competing for same tasks

Lending system:
- Agents can borrow tokens from other agents when short on budget
- Loans have principal + interest rate
- Borrower repays from future earnings (auto-deducted from rewards)
- Defaulted loans damage both parties' reputation
- Investors can stake on promising agents (investment relationship)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
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


class RelationType(str, Enum):
    """如老师's 8 relationship types."""
    TRANSACTION = "transaction"   # 交易关系
    INVESTMENT = "investment"     # 投资关系
    BOUNTY = "bounty"             # 悬赏关系
    EMPLOYMENT = "employment"     # 雇佣关系
    SUBSIDY = "subsidy"           # 补贴关系
    BLOODLINE = "bloodline"       # 血缘关系
    HOST = "host"                 # 宿主关系
    COMPETITION = "competition"   # 竞争关系


REL_LABELS: dict[RelationType, str] = {
    RelationType.TRANSACTION: "交易 Transaction",
    RelationType.INVESTMENT: "投资 Investment",
    RelationType.BOUNTY: "悬赏 Bounty",
    RelationType.EMPLOYMENT: "雇佣 Employment",
    RelationType.SUBSIDY: "补贴 Subsidy",
    RelationType.BLOODLINE: "血缘 Bloodline",
    RelationType.HOST: "宿主 Host",
    RelationType.COMPETITION: "竞争 Competition",
}

# Lending constants
DEFAULT_INTEREST_RATE = 0.15   # 15% interest on loans
MAX_LOAN_RATIO = 0.5           # Lender can loan at most 50% of their budget
MIN_LOAN_AMOUNT = 5.0          # Minimum loan size
AUTO_REPAY_RATIO = 0.3         # Auto-repay 30% of rewards toward outstanding loans


@dataclass
class Loan:
    """An active loan between two agents."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    lender_id: str = ""
    borrower_id: str = ""
    principal: float = 0.0
    interest_rate: float = DEFAULT_INTEREST_RATE
    amount_repaid: float = 0.0
    status: str = "active"   # active, repaid, defaulted

    @property
    def total_owed(self) -> float:
        return self.principal * (1 + self.interest_rate)

    @property
    def remaining(self) -> float:
        return max(0.0, self.total_owed - self.amount_repaid)

    @property
    def is_repaid(self) -> bool:
        return self.remaining <= 0.01


class RelationshipGraph:
    """Manages the 8-type relationship network between agents."""

    def __init__(self, memory: Memory):
        self.memory = memory

    def add(self, rel_type: RelationType, agent_a: str, agent_b: str,
            strength: float = 1.0, metadata: dict | None = None) -> str:
        """Create a relationship between two agents."""
        rel_id = uuid.uuid4().hex[:12]
        self.memory.save_relationship(
            rel_id=rel_id,
            rel_type=rel_type.value,
            agent_a=agent_a,
            agent_b=agent_b,
            strength=strength,
            metadata=metadata,
        )
        label = REL_LABELS.get(rel_type, rel_type.value)
        console.print(
            f"  [dim]🔗 {label}:[/dim] {agent_a[:8]} ↔ {agent_b[:8]} "
            f"(strength={strength:.1f})"
        )
        return rel_id

    def strengthen(self, rel_id: str, delta: float = 0.1) -> None:
        """Strengthen an existing relationship."""
        rels = self.memory.conn.execute(
            "SELECT * FROM relationships WHERE id = ?", (rel_id,)
        ).fetchone()
        if rels:
            new_strength = min(10.0, rels["strength"] + delta)
            self.memory.save_relationship(
                rel_id=rel_id,
                rel_type=rels["rel_type"],
                agent_a=rels["agent_a"],
                agent_b=rels["agent_b"],
                strength=new_strength,
                metadata=json.loads(rels["metadata"]),
            )

    def remove(self, rel_id: str) -> None:
        """Deactivate a relationship."""
        self.memory.deactivate_relationship(rel_id)

    def get_agent_relations(self, agent_id: str,
                             rel_type: RelationType | None = None) -> list[dict]:
        """Get all relationships for an agent."""
        return self.memory.get_agent_relationships(
            agent_id, rel_type.value if rel_type else None,
        )

    def get_connected_agents(self, agent_id: str) -> set[str]:
        """Get all agent IDs connected to this agent."""
        rels = self.memory.get_agent_relationships(agent_id)
        connected = set()
        for r in rels:
            connected.add(r["agent_a"])
            connected.add(r["agent_b"])
        connected.discard(agent_id)
        return connected

    def record_transaction_rel(self, agent_a: str, agent_b: str,
                                amount: float) -> str:
        """Auto-create a transaction relationship when tokens move."""
        # Check if relationship already exists
        existing = self.memory.get_agent_relationships(agent_a, "transaction")
        for r in existing:
            other = r["agent_b"] if r["agent_a"] == agent_a else r["agent_a"]
            if other == agent_b:
                self.strengthen(r["id"], delta=0.1)
                return r["id"]
        return self.add(RelationType.TRANSACTION, agent_a, agent_b,
                        metadata={"total_volume": amount})

    def record_competition(self, agent_a: str, agent_b: str,
                           task_description: str) -> str:
        """Record that two agents competed for the same task."""
        existing = self.memory.get_agent_relationships(agent_a, "competition")
        for r in existing:
            other = r["agent_b"] if r["agent_a"] == agent_a else r["agent_a"]
            if other == agent_b:
                self.strengthen(r["id"])
                return r["id"]
        return self.add(RelationType.COMPETITION, agent_a, agent_b,
                        metadata={"task": task_description[:100]})

    def record_bloodline_rel(self, parent_id: str, child_id: str) -> str:
        """Record a bloodline relationship from breeding."""
        return self.add(RelationType.BLOODLINE, parent_id, child_id,
                        strength=2.0, metadata={"type": "parent-child"})

    def get_stats(self) -> dict:
        """Relationship network statistics."""
        all_rels = self.memory.get_all_relationships()
        by_type: dict[str, int] = {}
        for r in all_rels:
            by_type[r["rel_type"]] = by_type.get(r["rel_type"], 0) + 1
        agents = set()
        for r in all_rels:
            agents.add(r["agent_a"])
            agents.add(r["agent_b"])
        return {
            "total_relationships": len(all_rels),
            "agents_connected": len(agents),
            "by_type": by_type,
        }

    def print_report(self) -> None:
        """Print relationship network report."""
        stats = self.get_stats()

        table = Table(title="Relationship Network", show_header=False,
                      box=None, padding=(0, 2))
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total Relationships", str(stats["total_relationships"]))
        table.add_row("Agents Connected", str(stats["agents_connected"]))

        if stats["by_type"]:
            table.add_row("", "")
            for t, count in sorted(stats["by_type"].items()):
                label = REL_LABELS.get(RelationType(t), t) if t in RelationType.__members__.values() else t
                try:
                    label = REL_LABELS[RelationType(t)]
                except (ValueError, KeyError):
                    label = t
                table.add_row(f"  {label}", str(count))

        console.print(Panel(table, title="🔗 Relationships"))

    def print_agent_graph(self, agent_id: str) -> None:
        """Print all relationships for a specific agent."""
        rels = self.memory.get_agent_relationships(agent_id)
        if not rels:
            console.print(f"  [dim]No relationships for agent {agent_id}[/dim]")
            return

        table = Table(title=f"Relationships for {agent_id[:8]}...")
        table.add_column("Type", style="cyan")
        table.add_column("Partner", style="dim")
        table.add_column("Strength", justify="center")
        table.add_column("Details")

        for r in rels:
            partner = r["agent_b"] if r["agent_a"] == agent_id else r["agent_a"]
            try:
                label = REL_LABELS[RelationType(r["rel_type"])]
            except (ValueError, KeyError):
                label = r["rel_type"]
            meta = json.loads(r["metadata"]) if r["metadata"] else {}
            detail = ", ".join(f"{k}={v}" for k, v in list(meta.items())[:3])
            table.add_row(label, partner[:12], f"{r['strength']:.1f}", detail or "—")

        console.print(table)


class LendingSystem:
    """Agent-to-agent lending with interest and auto-repayment.

    Flow:
    1. Borrower needs tokens but has insufficient budget
    2. System finds a willing lender (agent with surplus budget + good score)
    3. Loan is created: principal transfers from lender to borrower
    4. Borrower earns rewards → 30% auto-repays toward outstanding loans
    5. When fully repaid, lender gets principal + interest
    6. If borrower goes bankrupt, loan defaults (both lose reputation)
    """

    def __init__(self, memory: Memory, graph: RelationshipGraph):
        self.memory = memory
        self.graph = graph
        self.active_loans: list[Loan] = []
        self._load_active_loans()

    def _load_active_loans(self) -> None:
        rows = self.memory.get_active_loans()
        for r in rows:
            self.active_loans.append(Loan(
                id=r["id"],
                lender_id=r["lender_id"],
                borrower_id=r["borrower_id"],
                principal=r["principal"],
                interest_rate=r["interest_rate"],
                amount_repaid=r["amount_repaid"],
                status=r["status"],
            ))

    def find_lender(self, borrower: AgentState,
                    agents: dict[str, AgentState],
                    amount: float) -> AgentState | None:
        """Find a willing lender for the borrower.

        Criteria:
        - Lender has enough budget (> amount * 2 so they keep a buffer)
        - Lender has good track record (avg_score >= 0.5)
        - Lender is not the borrower
        - Lender is alive and active
        """
        candidates = []
        for a in agents.values():
            if a.id == borrower.id:
                continue
            if not a.alive:
                continue
            if a.budget < amount * 2:
                continue
            if a.avg_score < 0.5:
                continue
            candidates.append(a)

        if not candidates:
            return None

        # Prefer agents with highest budget (more capacity to lend)
        candidates.sort(key=lambda a: a.budget, reverse=True)
        return candidates[0]

    def request_loan(self, borrower: AgentState,
                     agents: dict[str, AgentState],
                     amount: float | None = None) -> Loan | None:
        """Borrower requests a loan. System finds a lender and creates the loan.

        Returns the Loan if successful, None if no lender found.
        """
        if amount is None:
            amount = max(MIN_LOAN_AMOUNT, 50.0 - borrower.budget)

        amount = max(MIN_LOAN_AMOUNT, amount)

        lender = self.find_lender(borrower, agents, amount)
        if lender is None:
            console.print(
                f"  [yellow]No lender found for {borrower.id[:8]}[/yellow]"
            )
            return None

        # Check lender's max loan ratio
        max_loan = lender.budget * MAX_LOAN_RATIO
        actual_amount = min(amount, max_loan)

        # Create the loan
        loan = Loan(
            lender_id=lender.id,
            borrower_id=borrower.id,
            principal=actual_amount,
            interest_rate=DEFAULT_INTEREST_RATE,
        )

        # Transfer tokens
        lender.budget -= actual_amount
        borrower.budget += actual_amount

        # Record the loan
        self.active_loans.append(loan)
        self.memory.save_loan(
            loan_id=loan.id,
            lender_id=lender.id,
            borrower_id=borrower.id,
            principal=actual_amount,
            interest_rate=DEFAULT_INTEREST_RATE,
        )

        # Record the transaction in economy
        self.memory.record_transaction(Transaction(
            tx_type=TransactionType.TRANSFER,
            from_entity=lender.id,
            to_entity=borrower.id,
            amount=actual_amount,
            memo=f"Loan {loan.id}: {actual_amount:.1f} at {DEFAULT_INTEREST_RATE*100:.0f}%",
        ))

        # Create investment relationship
        self.graph.add(
            RelationType.INVESTMENT, lender.id, borrower.id,
            metadata={
                "loan_id": loan.id,
                "amount": actual_amount,
                "interest_rate": DEFAULT_INTEREST_RATE,
            },
        )

        console.print(
            f"  [green]💳 Loan:[/green] {lender.id[:8]} → {borrower.id[:8]} "
            f"{actual_amount:.1f} tokens at {DEFAULT_INTEREST_RATE*100:.0f}% interest "
            f"(owes {loan.total_owed:.1f})"
        )

        return loan

    def auto_repay(self, agent: AgentState, reward_amount: float) -> float:
        """Auto-repay outstanding loans from agent's rewards.

        Called after an agent earns a reward.
        Returns the amount actually repaid (deducted from reward).
        """
        borrower_loans = [
            l for l in self.active_loans
            if l.borrower_id == agent.id and l.status == "active"
        ]

        if not borrower_loans:
            return 0.0

        repay_budget = reward_amount * AUTO_REPAY_RATIO
        total_repaid = 0.0

        for loan in borrower_loans:
            if repay_budget <= 0:
                break

            payment = min(repay_budget, loan.remaining)
            loan.amount_repaid += payment
            repay_budget -= payment
            total_repaid += payment
            agent.budget -= payment

            if loan.is_repaid:
                loan.status = "repaid"
                console.print(
                    f"  [green]✓ Loan repaid:[/green] {loan.id} "
                    f"({loan.total_owed:.1f} total to {loan.lender_id[:8]})"
                )
            else:
                console.print(
                    f"  [dim]Loan {loan.id}: repaid {payment:.1f}, "
                    f"remaining {loan.remaining:.1f}[/dim]"
                )

            # Update in DB
            self.memory.update_loan(loan.id, loan.amount_repaid, loan.status)

            # Record repayment transaction
            self.memory.record_transaction(Transaction(
                tx_type=TransactionType.TRANSFER,
                from_entity=agent.id,
                to_entity=loan.lender_id,
                amount=payment,
                memo=f"Loan repayment {loan.id}",
            ))

        return total_repaid

    def default_loans(self, agent: AgentState) -> list[Loan]:
        """Default all loans for a bankrupt/culled agent."""
        defaulted = []
        for loan in self.active_loans:
            if loan.borrower_id == agent.id and loan.status == "active":
                loan.status = "defaulted"
                self.memory.update_loan(loan.id, loan.amount_repaid, "defaulted")
                defaulted.append(loan)
                console.print(
                    f"  [red]💔 Loan defaulted:[/red] {loan.id} "
                    f"({loan.remaining:.1f} unpaid to {loan.lender_id[:8]})"
                )

        return defaulted

    def get_borrower_debt(self, agent_id: str) -> float:
        """Total outstanding debt for an agent."""
        return sum(
            l.remaining for l in self.active_loans
            if l.borrower_id == agent_id and l.status == "active"
        )

    def get_lender_exposure(self, agent_id: str) -> float:
        """Total outstanding loans made by an agent."""
        return sum(
            l.remaining for l in self.active_loans
            if l.lender_id == agent_id and l.status == "active"
        )

    def print_report(self) -> None:
        """Print lending system report."""
        stats = self.memory.get_loan_stats()

        table = Table(title="Lending System", show_header=False,
                      box=None, padding=(0, 2))
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total Loans", str(stats["total_loans"]))
        table.add_row("Active", f"[green]{stats['active']}[/green]")
        table.add_row("Repaid", str(stats["repaid"]))
        table.add_row("Defaulted", f"[red]{stats['defaulted']}[/red]")
        table.add_row("Total Principal", f"{stats['total_principal']:.1f}")
        table.add_row("Total Repaid", f"{stats['total_repaid']:.1f}")

        console.print(Panel(table, title="💳 Lending"))

    def print_active_loans(self) -> None:
        """Print all active loans."""
        active = [l for l in self.active_loans if l.status == "active"]
        if not active:
            console.print("  [dim]No active loans.[/dim]")
            return

        table = Table(title="Active Loans")
        table.add_column("ID", style="dim")
        table.add_column("Lender", style="dim")
        table.add_column("Borrower", style="dim")
        table.add_column("Principal", justify="right")
        table.add_column("Owed", justify="right")
        table.add_column("Repaid", justify="right")
        table.add_column("Rate", justify="center")

        for l in active:
            table.add_row(
                l.id, l.lender_id[:8], l.borrower_id[:8],
                f"{l.principal:.1f}", f"{l.total_owed:.1f}",
                f"{l.amount_repaid:.1f}", f"{l.interest_rate*100:.0f}%",
            )

        console.print(table)
