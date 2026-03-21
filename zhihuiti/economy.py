"""Token economy system for zhihuiti."""
from __future__ import annotations

from typing import Optional

from .memory import Memory
from .models import AgentRole


GENESIS_SUPPLY = 10_000.0

SPAWN_COSTS: dict[str, float] = {
    AgentRole.orchestrator.value: 50.0,
    AgentRole.researcher.value: 20.0,
    AgentRole.analyst.value: 20.0,
    AgentRole.coder.value: 25.0,
    AgentRole.trader.value: 30.0,
    AgentRole.judge.value: 15.0,
    AgentRole.synthesizer.value: 20.0,
}
MERGE_COST = 40.0


class CentralBank:
    def __init__(self, memory: Memory):
        self._memory = memory
        self._supply: float = 0.0
        self._tax_rate: float = 0.05  # 5 %

    def bootstrap(self) -> None:
        """Mint genesis tokens if supply == 0."""
        if self._supply == 0.0:
            self.mint(GENESIS_SUPPLY, "genesis")

    def mint(self, amount: float, reason: str = "") -> None:
        self._supply += amount
        self._memory.save_economy_event("mint", amount, description=reason)

    def burn(self, amount: float, reason: str = "") -> None:
        burned = min(amount, self._supply)
        self._supply -= burned
        self._memory.save_economy_event("burn", burned, description=reason)

    @property
    def total_supply(self) -> float:
        return self._supply

    @property
    def tax_rate(self) -> float:
        return self._tax_rate

    def auto_adjust(self, treasury_balance: float) -> None:
        """Auto-adjust tax rate based on inflation proxy."""
        if self._supply > 0:
            ratio = treasury_balance / self._supply
            if ratio < 0.2:  # Treasury dangerously low → inflate
                self._tax_rate = min(self._tax_rate + 0.01, 0.20)
            elif ratio > 0.5:  # Too much hoarding → deflation risk
                self._tax_rate = max(self._tax_rate - 0.01, 0.01)


class Treasury:
    def __init__(self, memory: Memory):
        self._memory = memory
        self._balance: float = 0.0

    @property
    def balance(self) -> float:
        return self._balance

    def deposit(self, amount: float, reason: str = "") -> None:
        self._balance += amount
        self._memory.save_economy_event("treasury_deposit", amount, description=reason)

    def fund_spawn(self, agent_id: str, amount: float) -> bool:
        if self._balance < amount:
            return False
        self._balance -= amount
        self._memory.save_economy_event(
            "spawn_funding", amount, agent_id=agent_id, description="spawn"
        )
        return True

    def pay_reward(self, agent_id: str, amount: float) -> None:
        self._balance -= amount
        self._memory.save_economy_event(
            "reward", amount, agent_id=agent_id, description="task reward"
        )

    def collect_tax(self, agent_id: str, amount: float) -> None:
        self._balance += amount
        self._memory.save_economy_event(
            "tax", amount, agent_id=agent_id, description="tax collection"
        )


class Economy:
    """Facade composing CentralBank + Treasury."""

    def __init__(self, memory: Memory):
        self._memory = memory
        self.bank = CentralBank(memory)
        self.treasury = Treasury(memory)
        self._agent_balances: dict[str, float] = {}

    def bootstrap(self) -> None:
        """Initialize economy if not already done."""
        events = self._memory.get_economy_events(limit=1)
        if not events:
            self.bank.bootstrap()
            # Seed treasury with half of genesis supply
            seed = GENESIS_SUPPLY * 0.5
            self.bank.burn(seed, "treasury_seed")  # remove from free float
            self.treasury.deposit(seed, "genesis_treasury")

    def get_agent_balance(self, agent_id: str) -> float:
        return self._agent_balances.get(agent_id, 0.0)

    def set_agent_balance(self, agent_id: str, balance: float) -> None:
        self._agent_balances[agent_id] = balance

    def charge_spawn(self, agent_id: str, role: str) -> float:
        """Deduct spawn cost from treasury and assign to agent. Returns budget granted."""
        cost = SPAWN_COSTS.get(role, 20.0)
        funded = self.treasury.fund_spawn(agent_id, cost)
        if funded:
            self._agent_balances[agent_id] = cost
        else:
            # Mint extra if treasury dry
            self.bank.mint(cost * 2, "emergency_mint")
            self.treasury.deposit(cost * 2, "emergency")
            self.treasury.fund_spawn(agent_id, cost)
            self._agent_balances[agent_id] = cost
        self.bank.auto_adjust(self.treasury.balance)
        return cost

    def pay_task_reward(self, agent_id: str, score: float, base: float = 50.0) -> float:
        reward = score * base
        tax = reward * self.bank.tax_rate
        net = reward - tax
        self.treasury.pay_reward(agent_id, net)
        self.treasury.collect_tax(agent_id, tax)
        cur = self._agent_balances.get(agent_id, 0.0)
        self._agent_balances[agent_id] = cur + net
        return net

    def charge_task(self, agent_id: str, amount: float) -> None:
        """Deduct task execution cost from agent balance."""
        cur = self._agent_balances.get(agent_id, 0.0)
        self._agent_balances[agent_id] = max(0.0, cur - amount)
        self._memory.save_economy_event(
            "task_charge", amount, agent_id=agent_id, description="task execution"
        )

    def charge_merge(self, agent_id: str) -> float:
        """Charge merge/spawn cost for bloodline merge."""
        funded = self.treasury.fund_spawn(agent_id, MERGE_COST)
        if not funded:
            self.bank.mint(MERGE_COST * 2, "merge_mint")
            self.treasury.deposit(MERGE_COST * 2, "merge_emergency")
            self.treasury.fund_spawn(agent_id, MERGE_COST)
        self._agent_balances[agent_id] = MERGE_COST
        return MERGE_COST

    def burn_agent(self, agent_id: str, balance: float) -> None:
        """Burn remaining balance when agent is culled."""
        if balance > 0:
            self.bank.burn(balance, f"cull_burn:{agent_id}")
            self._agent_balances.pop(agent_id, None)
            self._memory.save_economy_event(
                "burn", balance, agent_id=agent_id, description="agent culled"
            )

    def penalize_agent(self, agent_id: str, amount: float) -> None:
        """Penalize agent by deducting tokens (collected as tax)."""
        cur = self._agent_balances.get(agent_id, 0.0)
        deducted = min(cur, amount)
        self._agent_balances[agent_id] = cur - deducted
        self.treasury.collect_tax(agent_id, deducted)

    def report(self) -> dict:
        return {
            "total_supply": self.bank.total_supply,
            "treasury_balance": self.treasury.balance,
            "tax_rate": self.bank.tax_rate,
            "num_agents_tracked": len(self._agent_balances),
        }
