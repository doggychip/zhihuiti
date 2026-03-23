"""Token economy system — Central Bank, Treasury, Taxation.

Modeled after 如老师's governance architecture:
- CentralBank: mints and burns tokens, controls money supply
- Treasury: manages fiscal policy, holds reserves
- TaxBureau: collects taxes on agent earnings
- RewardEngine: calculates payouts based on task scores
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from zhihuiti.memory import Memory

console = Console()


# ---------------------------------------------------------------------------
# Constants — tunable economic parameters
# ---------------------------------------------------------------------------

INITIAL_MONEY_SUPPLY = 10_000.0   # Total tokens minted at genesis
AGENT_STARTING_BUDGET = 100.0     # Default budget for a new agent
MIN_REWARD = 2.0                  # Floor reward even for low scores
MAX_REWARD = 50.0                 # Ceiling reward for perfect scores
TAX_RATE = 0.15                   # 15% flat tax on all earnings
BANKRUPTCY_THRESHOLD = 1.0        # Agent is bankrupt below this balance
INFLATION_CHECK_INTERVAL = 20     # Re-evaluate money supply every N transactions
TARGET_VELOCITY = 0.6             # Target ratio of circulating / total supply


class TransactionType(str, Enum):
    MINT = "mint"               # Central bank creates new tokens
    BURN = "burn"               # Tokens destroyed (culled agent's remaining budget)
    REWARD = "reward"           # Agent earns tokens for task completion
    TAX = "tax"                 # Tax deducted from earnings
    SPAWN_COST = "spawn_cost"   # Cost to spawn a new agent
    TASK_FEE = "task_fee"       # Fee deducted when agent starts a task
    TRANSFER = "transfer"       # Agent-to-agent transfer (future: lending)


@dataclass
class Transaction:
    """A single economic event."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    tx_type: TransactionType = TransactionType.TRANSFER
    from_entity: str = ""       # "central_bank", "treasury", or agent_id
    to_entity: str = ""         # "central_bank", "treasury", or agent_id
    amount: float = 0.0
    memo: str = ""


class CentralBank:
    """Controls money supply through minting and burning.

    The central bank is the only entity that can create or destroy tokens.
    It monitors the money supply and adjusts via inflation/deflation.
    """

    def __init__(self, memory: Memory):
        self.memory = memory
        self.total_minted = 0.0
        self.total_burned = 0.0
        self.transaction_count = 0
        self._load_state()

    def _load_state(self) -> None:
        """Restore state from database."""
        state = self.memory.get_economy_state("central_bank")
        if state:
            self.total_minted = state.get("total_minted", 0.0)
            self.total_burned = state.get("total_burned", 0.0)
            self.transaction_count = state.get("transaction_count", 0)

    def _save_state(self) -> None:
        self.memory.save_economy_state("central_bank", {
            "total_minted": self.total_minted,
            "total_burned": self.total_burned,
            "transaction_count": self.transaction_count,
        })

    @property
    def money_supply(self) -> float:
        """Net tokens in circulation."""
        return self.total_minted - self.total_burned

    def mint(self, amount: float, recipient: str, memo: str = "") -> Transaction:
        """Create new tokens and assign them to a recipient."""
        tx = Transaction(
            tx_type=TransactionType.MINT,
            from_entity="central_bank",
            to_entity=recipient,
            amount=amount,
            memo=memo or f"Minted {amount:.1f} tokens",
        )
        self.total_minted += amount
        self.transaction_count += 1
        self.memory.record_transaction(tx)
        self._save_state()
        return tx

    def burn(self, amount: float, source: str, memo: str = "") -> Transaction:
        """Destroy tokens, removing them from circulation."""
        tx = Transaction(
            tx_type=TransactionType.BURN,
            from_entity=source,
            to_entity="central_bank",
            amount=amount,
            memo=memo or f"Burned {amount:.1f} tokens",
        )
        self.total_burned += amount
        self.transaction_count += 1
        self.memory.record_transaction(tx)
        self._save_state()
        return tx

    def genesis(self) -> None:
        """Initial minting — bootstrap the economy."""
        if self.total_minted > 0:
            return  # Already initialized
        self.mint(INITIAL_MONEY_SUPPLY, "treasury", "Genesis mint")
        console.print(
            f"  [bold green]🏦 Genesis:[/bold green] Minted {INITIAL_MONEY_SUPPLY:.0f} "
            f"tokens into Treasury"
        )

    def check_inflation(self, treasury: Treasury) -> None:
        """Periodically check if money supply needs adjustment."""
        if self.transaction_count % INFLATION_CHECK_INTERVAL != 0:
            return
        if self.money_supply <= 0:
            return

        velocity = 1.0 - (treasury.balance / max(self.money_supply, 1.0))

        if velocity < TARGET_VELOCITY * 0.7:
            # Too much money hoarded — burn some from treasury
            burn_amount = min(treasury.balance * 0.1, self.money_supply * 0.05)
            if burn_amount > 1.0:
                treasury.balance -= burn_amount
                self.burn(burn_amount, "treasury", "Deflationary burn")
                console.print(
                    f"  [dim]🏦 Deflation: burned {burn_amount:.1f} tokens "
                    f"(velocity={velocity:.2f})[/dim]"
                )
        elif velocity > TARGET_VELOCITY * 1.3:
            # Economy running hot — mint more
            mint_amount = self.money_supply * 0.05
            treasury.balance += mint_amount
            self.mint(mint_amount, "treasury", "Inflationary mint")
            console.print(
                f"  [dim]🏦 Inflation: minted {mint_amount:.1f} tokens "
                f"(velocity={velocity:.2f})[/dim]"
            )


class Treasury:
    """Fiscal authority — holds reserves, funds agent spawning."""

    def __init__(self, memory: Memory):
        self.memory = memory
        self.balance = 0.0
        self.total_taxes_collected = 0.0
        self.total_rewards_paid = 0.0
        self.total_spawn_costs = 0.0
        self._load_state()

    def _load_state(self) -> None:
        state = self.memory.get_economy_state("treasury")
        if state:
            self.balance = state.get("balance", 0.0)
            self.total_taxes_collected = state.get("total_taxes_collected", 0.0)
            self.total_rewards_paid = state.get("total_rewards_paid", 0.0)
            self.total_spawn_costs = state.get("total_spawn_costs", 0.0)

    def _save_state(self) -> None:
        self.memory.save_economy_state("treasury", {
            "balance": self.balance,
            "total_taxes_collected": self.total_taxes_collected,
            "total_rewards_paid": self.total_rewards_paid,
            "total_spawn_costs": self.total_spawn_costs,
        })

    def fund_agent_spawn(self, amount: float) -> bool:
        """Allocate budget from treasury to spawn an agent."""
        if self.balance < amount:
            return False
        self.balance -= amount
        self.total_spawn_costs += amount
        self._save_state()
        return True

    def collect_tax(self, amount: float) -> None:
        """Receive tax revenue."""
        self.balance += amount
        self.total_taxes_collected += amount
        self._save_state()

    def pay_reward(self, amount: float) -> bool:
        """Pay out a reward from treasury reserves."""
        if self.balance < amount:
            return False
        self.balance -= amount
        self.total_rewards_paid += amount
        self._save_state()
        return True


class TaxBureau:
    """Collects taxes on agent earnings."""

    def __init__(self, treasury: Treasury, memory: Memory):
        self.treasury = treasury
        self.memory = memory
        self.rate = TAX_RATE

    def tax_earning(self, gross_amount: float, agent_id: str) -> tuple[float, float]:
        """Calculate and collect tax on an earning.

        Returns (net_amount, tax_amount).
        """
        tax = gross_amount * self.rate
        net = gross_amount - tax
        self.treasury.collect_tax(tax)

        self.memory.record_transaction(Transaction(
            tx_type=TransactionType.TAX,
            from_entity=agent_id,
            to_entity="treasury",
            amount=tax,
            memo=f"Tax on {gross_amount:.1f} earning ({self.rate*100:.0f}%)",
        ))

        return net, tax


class RewardEngine:
    """Calculates rewards for task completion based on score."""

    def __init__(
        self,
        central_bank: CentralBank,
        treasury: Treasury,
        tax_bureau: TaxBureau,
        memory: Memory,
    ):
        self.central_bank = central_bank
        self.treasury = treasury
        self.tax_bureau = tax_bureau
        self.memory = memory

    def calculate_reward(self, score: float, task_complexity: float = 1.0) -> float:
        """Calculate gross reward based on score and complexity.

        score: 0.0 to 1.0
        task_complexity: multiplier (1.0 = normal, 2.0 = complex)
        """
        if score <= 0.0:
            return 0.0

        # Non-linear reward curve: reward = MIN + (MAX - MIN) * score^1.5
        # This means high scores are disproportionately rewarded
        reward = MIN_REWARD + (MAX_REWARD - MIN_REWARD) * (score ** 1.5)
        reward *= task_complexity
        return round(reward, 2)

    def pay_agent(self, agent_id: str, score: float, agent_budget_ref: list,
                  task_complexity: float = 1.0) -> dict:
        """Full reward cycle: calculate → tax → pay → record.

        agent_budget_ref: mutable [budget_value] so we can update the agent's budget
        Returns dict with reward details.
        """
        gross = self.calculate_reward(score, task_complexity)

        if gross <= 0:
            return {"gross": 0, "tax": 0, "net": 0, "paid": False}

        # Check treasury can cover it
        if not self.treasury.pay_reward(gross):
            # Treasury short — mint more
            shortfall = gross - self.treasury.balance
            self.central_bank.mint(
                shortfall * 2,  # Mint double the shortfall as buffer
                "treasury",
                "Emergency mint for reward payment",
            )
            self.treasury.balance += shortfall * 2
            self.treasury.pay_reward(gross)

        # Tax the earning
        net, tax = self.tax_bureau.tax_earning(gross, agent_id)

        # Credit the agent
        agent_budget_ref[0] += net

        # Record the reward transaction
        self.memory.record_transaction(Transaction(
            tx_type=TransactionType.REWARD,
            from_entity="treasury",
            to_entity=agent_id,
            amount=net,
            memo=f"Reward: score={score:.2f}, gross={gross:.1f}, tax={tax:.1f}",
        ))

        # Check inflation
        self.central_bank.check_inflation(self.treasury)

        return {"gross": gross, "tax": tax, "net": net, "paid": True}


class Economy:
    """Unified facade for the entire economic system."""

    def __init__(self, memory: Memory):
        self.memory = memory
        self.central_bank = CentralBank(memory)
        self.treasury = Treasury(memory)
        self.tax_bureau = TaxBureau(self.treasury, memory)
        self.reward_engine = RewardEngine(
            self.central_bank, self.treasury, self.tax_bureau, memory,
        )
        # Bootstrap if needed
        self.central_bank.genesis()
        # Load treasury balance from genesis mint
        if self.treasury.balance == 0 and self.central_bank.total_minted > 0:
            self.treasury.balance = INITIAL_MONEY_SUPPLY
            self.treasury._save_state()

    def fund_spawn(self, budget: float = AGENT_STARTING_BUDGET) -> bool:
        """Allocate budget from treasury for a new agent."""
        success = self.treasury.fund_agent_spawn(budget)
        if not success:
            # Auto-mint if treasury is depleted
            self.central_bank.mint(budget * 2, "treasury", "Mint for agent spawn")
            self.treasury.balance += budget * 2
            success = self.treasury.fund_agent_spawn(budget)
        return success

    def reward_agent(self, agent_id: str, score: float,
                     agent_budget_ref: list, task_complexity: float = 1.0) -> dict:
        """Pay an agent for completed work."""
        return self.reward_engine.pay_agent(
            agent_id, score, agent_budget_ref, task_complexity,
        )

    def burn_agent_balance(self, agent_id: str, remaining_budget: float) -> None:
        """When an agent is culled, burn its remaining tokens."""
        if remaining_budget > 0:
            self.central_bank.burn(
                remaining_budget, agent_id,
                f"Culled agent {agent_id} — budget burned",
            )

    def record_task_fee(self, agent_id: str, amount: float) -> None:
        """Record a task execution fee."""
        self.memory.record_transaction(Transaction(
            tx_type=TransactionType.TASK_FEE,
            from_entity=agent_id,
            to_entity="system",
            amount=amount,
            memo=f"Task fee: {amount:.1f}",
        ))

    def get_report(self) -> dict:
        """Full economic report."""
        return {
            "money_supply": round(self.central_bank.money_supply, 2),
            "total_minted": round(self.central_bank.total_minted, 2),
            "total_burned": round(self.central_bank.total_burned, 2),
            "treasury_balance": round(self.treasury.balance, 2),
            "total_taxes_collected": round(self.treasury.total_taxes_collected, 2),
            "total_rewards_paid": round(self.treasury.total_rewards_paid, 2),
            "total_spawn_costs": round(self.treasury.total_spawn_costs, 2),
            "transactions": self.central_bank.transaction_count,
            "tax_rate": f"{self.tax_bureau.rate * 100:.0f}%",
        }

    def print_report(self) -> None:
        """Pretty-print the economic report."""
        report = self.get_report()

        table = Table(title="Economy Report", show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Money Supply", f"{report['money_supply']:.0f}")
        table.add_row("  Minted", f"+{report['total_minted']:.0f}")
        table.add_row("  Burned", f"-{report['total_burned']:.0f}")
        table.add_row("", "")
        table.add_row("Treasury Balance", f"{report['treasury_balance']:.0f}")
        table.add_row("  Taxes Collected", f"+{report['total_taxes_collected']:.0f}")
        table.add_row("  Rewards Paid", f"-{report['total_rewards_paid']:.0f}")
        table.add_row("  Spawn Costs", f"-{report['total_spawn_costs']:.0f}")
        table.add_row("", "")
        table.add_row("Tax Rate", report['tax_rate'])
        table.add_row("Transactions", str(report['transactions']))

        console.print(Panel(table, title="🏦 zhihuiti Economy"))
