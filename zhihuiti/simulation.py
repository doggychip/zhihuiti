"""Evolutionary simulation — the epoch loop that ties economy, market, bidding, and bloodline together.

Each epoch:
1. Generate tasks
2. Each agent makes an LLM decision (concurrent via ThreadPoolExecutor)
3. Run auctions
4. Run market matching (including breeding rights)
5. Score, reward, deduct maintenance cost
6. Natural selection: cull bankrupts, breed top performers
7. Record stats to SQLite

The genome defines HARD CONSTRAINTS on the agent's action space.
The LLM reasons WITHIN those constraints.
"""

from __future__ import annotations

import json
import random
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console

from zhihuiti.bidding import BiddingHouse
from zhihuiti.bloodline import Bloodline
from zhihuiti.economy import BANKRUPTCY_THRESHOLD, Economy
from zhihuiti.genome import (
    StrategyGenome,
    classify_archetype,
    crossover,
    mutate,
    random_genome,
)
from zhihuiti.market import TradingMarket, TradeRecord
from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentRole, AgentState, Realm, ROLE_TO_REALM

console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAINTENANCE_COST = 5.0            # Tokens deducted per agent per epoch
EVOLVED_BANKRUPTCY = 10.0         # Higher threshold for evolutionary sim
POPULATION_FLOOR = 10             # Emergency spawn if below this
TASK_ROLES = [AgentRole.CODER, AgentRole.RESEARCHER, AgentRole.ANALYST, AgentRole.TRADER]


@dataclass
class SimulationConfig:
    population_size: int = 50
    epochs: int = 500
    model: str = "haiku"
    max_cost_usd: float = 25.0
    concurrency: int = 5
    db_path: str = "zhihuiti_evolution.db"


@dataclass
class AgentDecision:
    action: str = "skip"           # bid, market, breed, skip
    params: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    model_used: str = "haiku"


@dataclass
class EpochStats:
    epoch: int = 0
    population: int = 0
    avg_fitness: float = 0.0
    money_supply: float = 0.0
    gini: float = 0.0
    archetype_counts: dict[str, int] = field(default_factory=dict)
    culled: int = 0
    born: int = 0
    trades: int = 0
    cost_usd: float = 0.0


class EvolutionarySimulation:
    """Runs the evolutionary economy simulation."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.memory = Memory(config.db_path)
        self.economy = Economy(self.memory)
        self.market = TradingMarket(self.memory)
        self.bloodline = Bloodline(self.memory)
        self.agents: dict[str, AgentState] = {}
        self.epoch = 0
        self.total_cost_usd = 0.0
        self._llm = None
        self._bidding_house: BiddingHouse | None = None

        # Register breeding rights settlement callback
        self.market.on_trade_settled = self._on_trade_settled

    def _get_llm(self):
        if self._llm is None:
            from zhihuiti.llm import LLM
            self._llm = LLM()
        return self._llm

    def _get_bidding_house(self) -> BiddingHouse:
        if self._bidding_house is None:
            self._bidding_house = BiddingHouse(
                self._get_llm(), self.memory, self.economy,
            )
        return self._bidding_house

    # ------------------------------------------------------------------
    # Population initialization
    # ------------------------------------------------------------------

    def initialize_population(self) -> None:
        """Spawn initial population with random genomes."""
        for _ in range(self.config.population_size):
            self._spawn_agent(random_genome())

    def _spawn_agent(self, genome: StrategyGenome,
                     role: AgentRole | None = None) -> AgentState:
        """Create a new agent with the given genome."""
        if role is None:
            role = random.choice(TASK_ROLES)

        config = AgentConfig(
            role=role,
            system_prompt=f"You are a {role.value} agent in an evolutionary economy.",
            budget=100.0,
            genome=genome,
            gene_id=uuid.uuid4().hex[:12],
            generation=0,
        )

        agent = AgentState(
            config=config,
            budget=100.0,
            realm=ROLE_TO_REALM.get(role, Realm.EXECUTION),
        )

        # Fund from treasury
        self.economy.fund_spawn()
        self.agents[agent.id] = agent
        return agent

    # ------------------------------------------------------------------
    # Task generation
    # ------------------------------------------------------------------

    def _generate_tasks(self, epoch: int) -> list[dict]:
        """Generate 10-20 random tasks with varying roles and complexity."""
        num_tasks = random.randint(10, 20)
        tasks = []
        for _ in range(num_tasks):
            role = random.choice(TASK_ROLES)
            complexity = random.uniform(0.5, 2.0)
            ceiling = 15.0 + complexity * 15.0  # 22.5 - 45.0
            tasks.append({
                "id": uuid.uuid4().hex[:12],
                "role": role,
                "complexity": round(complexity, 2),
                "price_ceiling": round(ceiling, 2),
                "description": f"{role.value} task (complexity {complexity:.1f})",
            })
        return tasks

    # ------------------------------------------------------------------
    # Agent decision (LLM call with genome constraints)
    # ------------------------------------------------------------------

    def _build_prompt(self, agent: AgentState, tasks: list[dict],
                      market_prices: dict[str, float | None]) -> str:
        """Build the decision prompt for an agent."""
        genome = agent.config.genome
        assert genome is not None

        # Apply genome hard constraints to filter available actions
        available_actions = ["skip"]

        # Filter tasks by risk tolerance
        eligible_tasks = []
        for t in tasks:
            if t["complexity"] > 1.5 and genome.risk_tolerance < 0.3:
                continue  # Hard task filtered for risk-averse agents
            if t["role"] != agent.config.role and genome.specialization > 0.7:
                continue  # Specialist only bids on matching tasks
            eligible_tasks.append(t)

        if eligible_tasks:
            available_actions.insert(0, "bid")

        if genome.cooperation_bias >= 0.3:
            available_actions.append("market")

        if genome.breeding_investment >= 0.3:
            available_actions.append("breed")

        task_list = "\n".join(
            f"  - {t['id']}: {t['description']} (ceiling {t['price_ceiling']:.1f}t)"
            for t in eligible_tasks[:5]  # Show top 5 to limit tokens
        ) or "  (no eligible tasks this epoch)"

        market_str = "\n".join(
            f"  - {role}: {price:.1f}t" if price else f"  - {role}: no trades yet"
            for role, price in sorted(market_prices.items())
        ) or "  (no market data)"

        actions_str = ", ".join(available_actions)

        prompt = f"""You are agent {agent.id[:8]}, a {agent.config.role.value} in generation {agent.config.generation}.

YOUR GENOME (these define your personality):
- Bid aggression: {genome.bid_aggression:.2f} ({"aggressive" if genome.bid_aggression > 0.6 else "conservative"})
- Risk tolerance: {genome.risk_tolerance:.2f}
- Cooperation bias: {genome.cooperation_bias:.2f}
- Specialization: {genome.specialization:.2f} ({"specialist" if genome.specialization > 0.7 else "generalist"})

YOUR STATE:
- Budget: {agent.budget:.1f} tokens
- Fitness: {agent.fitness:.2f}
- Maintenance cost: {MAINTENANCE_COST:.0f} tokens/epoch

AVAILABLE TASKS:
{task_list}

MARKET PRICES:
{market_str}

Available actions: {actions_str}

Respond in JSON: {{"action": "bid|market|breed|skip", "params": {{}}, "reasoning": "..."}}
For bid: {{"action": "bid", "params": {{"task_id": "...", "amount": 12.5}}, "reasoning": "..."}}
For skip: {{"action": "skip", "params": {{}}, "reasoning": "..."}}"""

        return prompt

    def _parse_llm_response(self, response: str) -> AgentDecision:
        """Parse LLM JSON response into AgentDecision."""
        try:
            # Try to extract JSON from response
            text = response.strip()
            # Handle markdown code blocks
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            data = json.loads(text)
            return AgentDecision(
                action=data.get("action", "skip"),
                params=data.get("params", {}),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, KeyError, IndexError):
            return AgentDecision(action="skip", reasoning="JSON parse failed")

    def _genome_heuristic(self, agent: AgentState,
                          tasks: list[dict]) -> AgentDecision:
        """Fallback decision using genome parameters only (no LLM)."""
        genome = agent.config.genome
        if genome is None:
            return AgentDecision(action="skip", reasoning="no genome")

        # Filter eligible tasks
        eligible = [
            t for t in tasks
            if not (t["complexity"] > 1.5 and genome.risk_tolerance < 0.3)
            and not (t["role"] != agent.config.role and genome.specialization > 0.7)
        ]

        if eligible and genome.bid_aggression > 0.5:
            task = eligible[0]
            # Bid based on aggression
            bid_ratio = 0.5 + (1.0 - genome.bid_aggression) * 0.3
            amount = task["price_ceiling"] * bid_ratio
            return AgentDecision(
                action="bid",
                params={"task_id": task["id"], "amount": round(amount, 2)},
                reasoning="genome heuristic: aggression > 0.5, bidding",
            )

        return AgentDecision(action="skip", reasoning="genome heuristic: skipping")

    def _agent_decision(self, agent: AgentState, tasks: list[dict],
                        market_prices: dict[str, float | None]) -> AgentDecision:
        """Get agent decision via LLM (with genome constraints) or heuristic fallback."""
        genome = agent.config.genome
        if genome is None:
            return self._genome_heuristic(agent, tasks)

        # Model routing: Sonnet for high-stakes decisions
        model = self.config.model
        breeding_available = any(
            TradingMarket.is_breeding_right(o.service_role)
            for o in self.market.orders
            if o.status.value == "open"
        )
        if (genome.breeding_investment > 0.6 and breeding_available) or agent.budget > 200:
            model = "sonnet"

        prompt = self._build_prompt(agent, tasks, market_prices)

        try:
            llm = self._get_llm()
            response = llm.chat(prompt)

            # Estimate cost (rough: ~500 input + ~100 output tokens)
            est_cost = 0.000225 if model == "haiku" else 0.003
            self.total_cost_usd += est_cost

            decision = self._parse_llm_response(response)
            decision.model_used = model
            return decision

        except Exception:
            return self._genome_heuristic(agent, tasks)

    # ------------------------------------------------------------------
    # Scoring and fitness
    # ------------------------------------------------------------------

    def _score_task(self, agent: AgentState, task: dict) -> float:
        """Score task completion based on role match and genome specialization."""
        genome = agent.config.genome
        role_match = 1.0 if agent.config.role == task["role"] else 0.5
        spec_bonus = (genome.specialization * 0.3) if genome else 0.0
        noise = random.uniform(0.85, 1.15)
        return min(1.0, max(0.0, role_match * (1.0 + spec_bonus) * noise * 0.8))

    def _update_fitness(self, agent: AgentState, task_score: float,
                        budget_start: float) -> None:
        """Update agent fitness using blended score with EMA."""
        budget_delta = (agent.budget - budget_start) / 100.0  # Normalize
        budget_delta = max(-1.0, min(1.0, budget_delta))

        epoch_fitness = 0.7 * task_score + 0.3 * budget_delta
        agent.fitness = 0.8 * agent.fitness + 0.2 * epoch_fitness

    # ------------------------------------------------------------------
    # Natural selection
    # ------------------------------------------------------------------

    def _natural_selection(self) -> tuple[list[str], list[str]]:
        """Cull bankrupts, breed top performers, maintain population floor."""
        culled_ids = []
        born_ids = []

        # Cull agents below threshold
        for agent_id, agent in list(self.agents.items()):
            if agent.budget < EVOLVED_BANKRUPTCY and agent.alive:
                agent.alive = False
                agent.life_state = agent.life_state  # Keep enum type
                self.economy.burn_agent_balance(agent_id, agent.budget)
                agent.budget = 0.0
                culled_ids.append(agent_id)

        # Remove dead agents from active dict
        alive_agents = {k: v for k, v in self.agents.items() if v.alive}

        # Breed top 20% by fitness
        if len(alive_agents) >= 2:
            sorted_agents = sorted(
                alive_agents.values(), key=lambda a: a.fitness, reverse=True,
            )
            top_count = max(2, len(sorted_agents) // 5)
            top_agents = sorted_agents[:top_count]

            # Breed pairs
            for i in range(0, len(top_agents) - 1, 2):
                parent_a = top_agents[i]
                parent_b = top_agents[i + 1]

                result = self.bloodline.breed(
                    parent_a.config, parent_b.config,
                    score_a=parent_a.fitness, score_b=parent_b.fitness,
                )

                child = AgentState(
                    config=result.child_config,
                    budget=100.0,
                    realm=ROLE_TO_REALM.get(result.child_config.role, Realm.EXECUTION),
                )
                self.economy.fund_spawn()
                self.agents[child.id] = child
                born_ids.append(child.id)

        # Population floor: emergency spawn
        alive_count = sum(1 for a in self.agents.values() if a.alive)
        while alive_count < POPULATION_FLOOR:
            agent = self._spawn_agent(random_genome())
            born_ids.append(agent.id)
            alive_count += 1

        return culled_ids, born_ids

    # ------------------------------------------------------------------
    # Breeding rights settlement
    # ------------------------------------------------------------------

    def _on_trade_settled(self, trade: TradeRecord) -> None:
        """Handle breeding rights trade settlement."""
        if not TradingMarket.is_breeding_right(trade.service_role):
            return

        buyer = self.agents.get(trade.buyer_id)
        seller = self.agents.get(trade.seller_id)

        if not buyer or not seller or not buyer.alive or not seller.alive:
            return

        if buyer.config.genome and seller.config.genome:
            result = self.bloodline.breed(
                buyer.config, seller.config,
                score_a=buyer.fitness, score_b=seller.fitness,
            )
            child = AgentState(
                config=result.child_config,
                budget=100.0,
                realm=ROLE_TO_REALM.get(result.child_config.role, Realm.EXECUTION),
            )
            self.economy.fund_spawn()
            self.agents[child.id] = child

    # ------------------------------------------------------------------
    # Gini coefficient
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_gini(budgets: list[float]) -> float:
        """Calculate Gini coefficient of wealth distribution."""
        if not budgets or len(budgets) < 2:
            return 0.0
        sorted_b = sorted(budgets)
        n = len(sorted_b)
        total = sum(sorted_b)
        if total == 0:
            return 0.0
        cumulative = sum((2 * i - n + 1) * b for i, b in enumerate(sorted_b))
        return cumulative / (n * total)

    # ------------------------------------------------------------------
    # Epoch loop
    # ------------------------------------------------------------------

    def run_epoch(self) -> EpochStats:
        """Run a single epoch of the evolutionary simulation."""
        self.epoch += 1
        alive_agents = {k: v for k, v in self.agents.items() if v.alive}

        # Record starting budgets for fitness calculation
        budget_starts = {k: v.budget for k, v in alive_agents.items()}

        # 1. Generate tasks
        tasks = self._generate_tasks(self.epoch)

        # 2. Agent decisions (concurrent LLM calls)
        market_prices = {
            role.value: self.market.get_market_price(role.value)
            for role in TASK_ROLES
        }

        decisions: dict[str, AgentDecision] = {}
        with ThreadPoolExecutor(max_workers=self.config.concurrency) as executor:
            futures = {
                executor.submit(
                    self._agent_decision, agent, tasks, market_prices
                ): agent_id
                for agent_id, agent in alive_agents.items()
            }
            for future in as_completed(futures):
                agent_id = futures[future]
                try:
                    decisions[agent_id] = future.result(timeout=10)
                except Exception:
                    decisions[agent_id] = self._genome_heuristic(
                        alive_agents[agent_id], tasks,
                    )

        # 3. Execute auctions
        bid_decisions = {
            k: v for k, v in decisions.items() if v.action == "bid"
        }
        task_scores: dict[str, float] = {}

        for task in tasks:
            # Find bids for this task
            task_bids = []
            for agent_id, decision in bid_decisions.items():
                if decision.params.get("task_id") == task["id"]:
                    agent = alive_agents.get(agent_id)
                    if agent and agent.budget >= decision.params.get("amount", 0):
                        task_bids.append((agent_id, decision.params.get("amount", 0)))

            if task_bids:
                # Lowest bid wins
                winner_id, bid_amount = min(task_bids, key=lambda x: x[1])
                winner = alive_agents[winner_id]

                # Deduct bid cost
                winner.budget -= bid_amount

                # Score the task
                score = self._score_task(winner, task)
                task_scores[winner_id] = score

                # Reward via economy
                self.economy.reward_agent(
                    winner_id, score, [winner.budget],
                    task_complexity=task["complexity"],
                )
                # Budget was updated via the mutable list ref
                winner.budget = [winner.budget][0] if isinstance(winner.budget, list) else winner.budget

        # 4. Execute market trades
        trade_count = 0
        market_decisions = {
            k: v for k, v in decisions.items() if v.action == "market"
        }
        for agent_id, decision in market_decisions.items():
            agent = alive_agents.get(agent_id)
            if not agent:
                continue
            from zhihuiti.market import OrderType
            side = decision.params.get("side", "buy")
            order_type = OrderType.BUY if side == "buy" else OrderType.SELL
            self.market.place_order(
                agent, order_type,
                decision.params.get("service_role", agent.config.role.value),
                decision.params.get("price", 10.0),
            )

        trades = self.market.run_matching(alive_agents)
        trade_count += len(trades)

        # 5. Deduct maintenance cost and update fitness
        for agent_id, agent in alive_agents.items():
            agent.budget -= MAINTENANCE_COST
            score = task_scores.get(agent_id, 0.0)
            self._update_fitness(agent, score, budget_starts[agent_id])

        # 6. Natural selection
        culled_ids, born_ids = self._natural_selection()

        # 7. Record epoch stats
        alive_agents = {k: v for k, v in self.agents.items() if v.alive}
        budgets = [a.budget for a in alive_agents.values()]
        archetypes: dict[str, int] = {}
        for a in alive_agents.values():
            if a.config.genome:
                archetype = classify_archetype(a.config.genome)
                archetypes[archetype] = archetypes.get(archetype, 0) + 1

        stats = EpochStats(
            epoch=self.epoch,
            population=len(alive_agents),
            avg_fitness=sum(a.fitness for a in alive_agents.values()) / max(len(alive_agents), 1),
            money_supply=self.economy.central_bank.money_supply,
            gini=self._calculate_gini(budgets),
            archetype_counts=archetypes,
            culled=len(culled_ids),
            born=len(born_ids),
            trades=trade_count,
            cost_usd=self.total_cost_usd,
        )

        # Save to SQLite
        self.memory.save_epoch_stats(
            self.epoch, stats.population, stats.avg_fitness,
            stats.money_supply, stats.gini, stats.archetype_counts,
        )

        # Save decisions and genome snapshots
        for agent_id, decision in decisions.items():
            self.memory.save_agent_decision(
                uuid.uuid4().hex[:12], self.epoch, agent_id,
                decision.action, decision.params, decision.reasoning,
                decision.model_used,
            )

        for agent_id, agent in alive_agents.items():
            if agent.config.genome:
                self.memory.save_genome_snapshot(
                    uuid.uuid4().hex[:12], self.epoch, agent_id,
                    agent.config.gene_id or "", agent.config.genome.to_dict(),
                    classify_archetype(agent.config.genome), agent.fitness,
                )

        # Inflation check
        self.economy.central_bank.check_inflation(self.economy.treasury)

        console.print(
            f"  [bold]Epoch {self.epoch}:[/bold] "
            f"pop={stats.population} fit={stats.avg_fitness:.2f} "
            f"culled={stats.culled} born={stats.born} "
            f"trades={stats.trades} cost=${stats.cost_usd:.2f}"
        )

        return stats

    def run(self, n_epochs: int | None = None) -> list[EpochStats]:
        """Run multiple epochs of the simulation."""
        epochs = n_epochs or self.config.epochs
        all_stats: list[EpochStats] = []

        self.initialize_population()

        for _ in range(epochs):
            # Check cost cap
            if self.total_cost_usd >= self.config.max_cost_usd:
                console.print(
                    f"[yellow]Simulation stopped: cost cap reached "
                    f"(${self.total_cost_usd:.2f} >= ${self.config.max_cost_usd:.2f})[/yellow]"
                )
                break

            stats = self.run_epoch()
            all_stats.append(stats)

        return all_stats


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="zhihuiti evolutionary simulation")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--population", type=int, default=20)
    parser.add_argument("--model", type=str, default="haiku")
    parser.add_argument("--max-cost", type=float, default=10.0)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--db", type=str, default="zhihuiti_evolution.db")
    args = parser.parse_args()

    config = SimulationConfig(
        population_size=args.population,
        epochs=args.epochs,
        model=args.model,
        max_cost_usd=args.max_cost,
        concurrency=args.concurrency,
        db_path=args.db,
    )

    console.print(f"[bold]zhihuiti Evolution[/bold] — {args.epochs} epochs, {args.population} agents")
    sim = EvolutionarySimulation(config)
    stats = sim.run()

    if stats:
        final = stats[-1]
        console.print(f"\n[bold green]Simulation complete.[/bold green]")
        console.print(f"  Final population: {final.population}")
        console.print(f"  Avg fitness: {final.avg_fitness:.3f}")
        console.print(f"  Total cost: ${sim.total_cost_usd:.2f}")
        console.print(f"  Archetypes: {final.archetype_counts}")

    # Generate dashboard
    try:
        from zhihuiti.evolution_dashboard import generate_report
        generate_report(sim.memory, "zhihuiti_evolution_report.html")
        console.print(f"  Dashboard: zhihuiti_evolution_report.html")
    except ImportError:
        console.print("  [dim]Dashboard generation requires plotly[/dim]")


if __name__ == "__main__":
    main()
