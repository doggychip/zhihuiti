"""Three Realms system (三界) — organizational governance for agents.

Modeled after 如老师's three-realm architecture:

研发界 (Research Realm)
  - Develops new products and technologies
  - Houses: researcher, analyst, coder agents
  - Focus: innovation, R&D, technical excellence

执行界 (Execution Realm)
  - Task distribution and execution
  - Houses: trader, custom agents
  - Focus: getting things done, operational efficiency

中枢界 (Central Realm)
  - Management and coordination (the "government")
  - Houses: orchestrator, judge agents
  - Focus: oversight, quality control, resource allocation

Each realm maintains its own agent pool and budget allocation.
Agents within a realm can be: active / frozen / bankrupt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from zhihuiti.models import (
    AgentLifeState,
    AgentRole,
    AgentState,
    Realm,
    ROLE_TO_REALM,
    Task,
)

if TYPE_CHECKING:
    from zhihuiti.memory import Memory

console = Console()

# Budget allocation ratios per realm (must sum to 1.0)
REALM_BUDGET_RATIO: dict[Realm, float] = {
    Realm.RESEARCH: 0.50,    # 50% — R&D gets the most funding
    Realm.EXECUTION: 0.35,   # 35% — execution is the workhorse
    Realm.CENTRAL: 0.15,     # 15% — governance is lean
}

# Realm display names
REALM_NAMES: dict[Realm, str] = {
    Realm.RESEARCH: "研发界 Research",
    Realm.EXECUTION: "执行界 Execution",
    Realm.CENTRAL: "中枢界 Central",
}

REALM_ICONS: dict[Realm, str] = {
    Realm.RESEARCH: "🔬",
    Realm.EXECUTION: "⚡",
    Realm.CENTRAL: "🏛",
}

# Freeze threshold: agents below this score get frozen instead of culled
FREEZE_THRESHOLD = 0.25
# Bankruptcy threshold: agents below this budget are bankrupt
BANKRUPTCY_BUDGET = 1.0


@dataclass
class RealmState:
    """Runtime state for a single realm."""
    realm: Realm
    budget_allocated: float = 0.0
    budget_spent: float = 0.0
    agents_spawned: int = 0
    agents_active: int = 0
    agents_frozen: int = 0
    agents_bankrupt: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_score: float = 0.0
    score_count: int = 0

    @property
    def avg_score(self) -> float:
        return self.total_score / self.score_count if self.score_count > 0 else 0.0

    @property
    def budget_remaining(self) -> float:
        return max(0.0, self.budget_allocated - self.budget_spent)


class RealmManager:
    """Manages the three realms — routing, budget allocation, agent lifecycle."""

    def __init__(self, memory: Memory):
        self.memory = memory
        self.realms: dict[Realm, RealmState] = {
            r: RealmState(realm=r) for r in Realm
        }
        self._load_state()

    def _load_state(self) -> None:
        """Restore realm states from database."""
        for realm in Realm:
            state = self.memory.get_economy_state(f"realm_{realm.value}")
            if state:
                rs = self.realms[realm]
                rs.budget_allocated = state.get("budget_allocated", 0.0)
                rs.budget_spent = state.get("budget_spent", 0.0)
                rs.agents_spawned = state.get("agents_spawned", 0)
                rs.agents_active = state.get("agents_active", 0)
                rs.agents_frozen = state.get("agents_frozen", 0)
                rs.agents_bankrupt = state.get("agents_bankrupt", 0)
                rs.tasks_completed = state.get("tasks_completed", 0)
                rs.tasks_failed = state.get("tasks_failed", 0)
                rs.total_score = state.get("total_score", 0.0)
                rs.score_count = state.get("score_count", 0)

    def _save_state(self, realm: Realm) -> None:
        rs = self.realms[realm]
        self.memory.save_economy_state(f"realm_{realm.value}", {
            "budget_allocated": rs.budget_allocated,
            "budget_spent": rs.budget_spent,
            "agents_spawned": rs.agents_spawned,
            "agents_active": rs.agents_active,
            "agents_frozen": rs.agents_frozen,
            "agents_bankrupt": rs.agents_bankrupt,
            "tasks_completed": rs.tasks_completed,
            "tasks_failed": rs.tasks_failed,
            "total_score": rs.total_score,
            "score_count": rs.score_count,
        })

    def reconcile_counts(self, agents: dict) -> None:
        """Recompute agent counts from live agent objects.

        This fixes drift between RealmState counters and reality,
        which happens when agents are removed without going through
        the full freeze/bankrupt/cull lifecycle methods.

        Args:
            agents: dict of agent_id -> AgentState from agent_manager.
        """
        for realm in Realm:
            rs = self.realms[realm]
            realm_agents = [a for a in agents.values() if a.realm == realm]
            rs.agents_active = len([
                a for a in realm_agents
                if a.life_state == AgentLifeState.ACTIVE
            ])
            rs.agents_frozen = len([
                a for a in realm_agents
                if a.life_state == AgentLifeState.FROZEN
            ])
            rs.agents_bankrupt = len([
                a for a in realm_agents
                if a.life_state == AgentLifeState.BANKRUPT
            ])
            self._save_state(realm)

    # ------------------------------------------------------------------
    # Budget allocation
    # ------------------------------------------------------------------

    def allocate_budgets(self, total_budget: float,
                         attention: dict[str, float] | None = None,
                         reset: bool = False) -> None:
        """Distribute budget across realms according to ratios.

        Args:
            total_budget: Total budget to distribute.
            attention: Optional override ratios from theory config.
                       Dict with keys 'research', 'execution', 'central'.
                       If None, uses default REALM_BUDGET_RATIO.
        """
        if attention:
            ratios = {
                Realm.RESEARCH: attention.get("research", 0.50),
                Realm.EXECUTION: attention.get("execution", 0.35),
                Realm.CENTRAL: attention.get("central", 0.15),
            }
        else:
            ratios = REALM_BUDGET_RATIO

        for realm, ratio in ratios.items():
            allocation = total_budget * ratio
            if reset:
                self.realms[realm].budget_allocated = allocation
                self.realms[realm].budget_spent = 0.0
            else:
                self.realms[realm].budget_allocated += allocation
            self._save_state(realm)

        console.print(
            f"  [bold]Budget allocated:[/bold] "
            + " | ".join(
                f"{REALM_ICONS[r]} {REALM_NAMES[r]}: {self.realms[r].budget_allocated:.0f}"
                for r in Realm
            )
        )

    # ------------------------------------------------------------------
    # Realm assignment
    # ------------------------------------------------------------------

    def assign_realm(self, role: AgentRole) -> Realm:
        """Determine which realm an agent belongs to based on its role."""
        return ROLE_TO_REALM.get(role, Realm.EXECUTION)

    def replenish_spawn_quota(
        self,
        role: AgentRole,
        budget: float,
        *,
        treasury_available: float,
    ) -> float:
        """Expand spawn quota for one Treasury-backed scheduled spawn.

        Realm quota is an administrative limit, not a separate token balance.
        The population rotator may expand it only after the shared Treasury can
        fund the complete spawn. Other spawn paths remain bounded by quota.

        Returns the amount of quota added.
        """
        if not math.isfinite(budget) or budget <= 0:
            raise ValueError("Scheduled spawn budget must be a positive finite number")
        if not math.isfinite(treasury_available) or treasury_available < 0:
            raise ValueError("Treasury availability must be a non-negative finite number")
        if treasury_available < budget:
            raise ValueError(
                "Treasury cannot back scheduled realm quota replenishment: "
                f"{treasury_available:.1f} available, {budget:.1f} required"
            )

        realm = self.assign_realm(role)
        state = self.realms[realm]
        required = state.budget_spent + budget
        added = max(0.0, required - state.budget_allocated)
        if added:
            state.budget_allocated += added
            self._save_state(realm)
        return added

    def route_task(self, task: Task) -> Realm:
        """Route a task to the appropriate realm based on the requested role."""
        role_name = task.metadata.get("requested_role", "custom")
        try:
            role = AgentRole(role_name)
        except ValueError:
            role = AgentRole.CUSTOM
        return self.assign_realm(role)

    # ------------------------------------------------------------------
    # Agent lifecycle within realms
    # ------------------------------------------------------------------

    def on_agent_spawn(self, agent: AgentState) -> None:
        """Register an agent spawn in its realm."""
        realm = self.assign_realm(agent.config.role)
        if self.realms[realm].budget_remaining < agent.budget:
            raise ValueError(
                f"{realm.value} realm spawn quota exhausted: "
                f"{self.realms[realm].budget_remaining:.1f} remaining"
            )
        agent.realm = realm
        agent.life_state = AgentLifeState.ACTIVE

        rs = self.realms[realm]
        rs.agents_spawned += 1
        rs.agents_active += 1
        rs.budget_spent += agent.budget
        self._save_state(realm)

    def on_task_complete(self, agent: AgentState, score: float, success: bool) -> None:
        """Record task completion in the agent's realm."""
        rs = self.realms[agent.realm]
        if success:
            rs.tasks_completed += 1
        else:
            rs.tasks_failed += 1
        rs.total_score += score
        rs.score_count += 1
        self._save_state(agent.realm)

    def freeze_agent(self, agent: AgentState) -> None:
        """Freeze an agent — preserve in sandbox but make inactive.

        Frozen agents keep their config/genes but don't take tasks.
        They can be thawed later if needed.
        """
        if agent.life_state == AgentLifeState.FROZEN:
            return

        old_state = agent.life_state
        agent.life_state = AgentLifeState.FROZEN
        agent.alive = False  # Not available for tasks

        rs = self.realms[agent.realm]
        if old_state == AgentLifeState.ACTIVE:
            rs.agents_active = max(0, rs.agents_active - 1)
        rs.agents_frozen += 1
        self._save_state(agent.realm)

        console.print(
            f"  [blue]❄ Frozen[/blue] {agent.config.role.value} agent "
            f"[dim]{agent.id}[/dim] in {REALM_NAMES[agent.realm]}"
        )

    def thaw_agent(self, agent: AgentState) -> None:
        """Thaw a frozen agent — reactivate it."""
        if agent.life_state != AgentLifeState.FROZEN:
            return

        agent.life_state = AgentLifeState.ACTIVE
        agent.alive = True

        rs = self.realms[agent.realm]
        rs.agents_frozen = max(0, rs.agents_frozen - 1)
        rs.agents_active += 1
        self._save_state(agent.realm)

        console.print(
            f"  [green]🔥 Thawed[/green] {agent.config.role.value} agent "
            f"[dim]{agent.id}[/dim] in {REALM_NAMES[agent.realm]}"
        )

    def bankrupt_agent(self, agent: AgentState) -> None:
        """Mark an agent as bankrupt."""
        if agent.life_state == AgentLifeState.BANKRUPT:
            return

        old_state = agent.life_state
        agent.life_state = AgentLifeState.BANKRUPT
        agent.alive = False

        rs = self.realms[agent.realm]
        if old_state == AgentLifeState.ACTIVE:
            rs.agents_active = max(0, rs.agents_active - 1)
        elif old_state == AgentLifeState.FROZEN:
            rs.agents_frozen = max(0, rs.agents_frozen - 1)
        rs.agents_bankrupt += 1
        self._save_state(agent.realm)

        console.print(
            f"  [red]💸 Bankrupt[/red] {agent.config.role.value} agent "
            f"[dim]{agent.id}[/dim] in {REALM_NAMES[agent.realm]}"
        )

    def on_agent_cull(
        self,
        agent: AgentState,
        *,
        unused_budget: float | None = None,
        quota_release: float | None = None,
    ) -> None:
        """Handle agent culling — decide between freeze and bankrupt.

        Very low scorers get frozen (preserved but inactive).
        Zero-budget agents get bankrupted.

        ``unused_budget`` is burned by ``AgentManager``. ``quota_release`` is
        capped at the agent's original reservation, so task rewards cannot
        over-release quota. Neither value refunds tokens to Treasury.
        """
        rs = self.realms[agent.realm]
        remaining = agent.budget if unused_budget is None else max(0.0, unused_budget)
        released = remaining if quota_release is None else max(0.0, quota_release)
        if released:
            rs.budget_spent = max(0.0, rs.budget_spent - released)
            self._save_state(agent.realm)

        if remaining <= BANKRUPTCY_BUDGET:
            self.bankrupt_agent(agent)
        else:
            self.freeze_agent(agent)

    def get_active_agents_in_realm(self, realm: Realm,
                                   agents: dict[str, AgentState]) -> list[AgentState]:
        """Get all active agents in a specific realm."""
        return [
            a for a in agents.values()
            if a.realm == realm and a.life_state == AgentLifeState.ACTIVE and a.alive
        ]

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def print_report(self, agents: dict[str, AgentState] | None = None) -> None:
        """Print a comprehensive three-realm report."""
        table = Table(title="三界 Three Realms", show_lines=True)
        table.add_column("Realm", style="bold", min_width=20)
        table.add_column("Active", justify="center", style="green")
        table.add_column("Frozen", justify="center", style="blue")
        table.add_column("Bankrupt", justify="center", style="red")
        table.add_column("Tasks Done", justify="center")
        table.add_column("Avg Score", justify="center")
        table.add_column("Budget", justify="right")

        for realm in Realm:
            rs = self.realms[realm]
            icon = REALM_ICONS[realm]
            name = REALM_NAMES[realm]

            # If we have live agent data, count from it
            if agents:
                realm_agents = [a for a in agents.values() if a.realm == realm]
                active = len([a for a in realm_agents if a.life_state == AgentLifeState.ACTIVE])
                frozen = len([a for a in realm_agents if a.life_state == AgentLifeState.FROZEN])
                bankrupt = len([a for a in realm_agents if a.life_state == AgentLifeState.BANKRUPT])
            else:
                active = rs.agents_active
                frozen = rs.agents_frozen
                bankrupt = rs.agents_bankrupt

            avg = f"{rs.avg_score:.2f}" if rs.score_count > 0 else "—"
            budget_str = f"{rs.budget_remaining:.0f}/{rs.budget_allocated:.0f}"

            table.add_row(
                f"{icon} {name}",
                str(active),
                str(frozen),
                str(bankrupt),
                str(rs.tasks_completed),
                avg,
                budget_str,
            )

        console.print(Panel(table))

    def print_realm_detail(self, realm: Realm,
                           agents: dict[str, AgentState]) -> None:
        """Print detailed info for a single realm."""
        rs = self.realms[realm]
        icon = REALM_ICONS[realm]
        name = REALM_NAMES[realm]

        realm_agents = [a for a in agents.values() if a.realm == realm]
        if not realm_agents:
            console.print(f"  [dim]{icon} {name}: No agents[/dim]")
            return

        table = Table(title=f"{icon} {name}")
        table.add_column("ID", style="dim")
        table.add_column("Role", style="cyan")
        table.add_column("State", justify="center")
        table.add_column("Budget", justify="right")
        table.add_column("Score", justify="center")
        table.add_column("Gen", justify="center")

        state_styles = {
            AgentLifeState.ACTIVE: "[green]active[/green]",
            AgentLifeState.FROZEN: "[blue]frozen[/blue]",
            AgentLifeState.BANKRUPT: "[red]bankrupt[/red]",
        }

        for a in sorted(realm_agents, key=lambda x: (-x.alive, x.config.role.value)):
            score_str = f"{a.avg_score:.2f}" if a.scores else "—"
            gen = a.config.generation
            table.add_row(
                a.id,
                a.config.role.value,
                state_styles.get(a.life_state, str(a.life_state)),
                f"{a.budget:.1f}",
                score_str,
                str(gen),
            )

        console.print(table)
        console.print(
            f"  [dim]Budget: {rs.budget_remaining:.0f} remaining / "
            f"{rs.budget_allocated:.0f} allocated | "
            f"Tasks: {rs.tasks_completed} done, {rs.tasks_failed} failed[/dim]"
        )
