"""Orchestrator — decomposes goals, spawns agents, runs the loop."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from zhihuiti.agents import ROLE_MAP, AgentManager
from zhihuiti.behavior import BehaviorDetector
from zhihuiti.bidding import BiddingHouse
from zhihuiti.bloodline import Bloodline
from zhihuiti.circuit_breaker import CircuitBreaker
from zhihuiti.economy import Economy
from zhihuiti.judge import Judge
from zhihuiti.llm import LLM
from zhihuiti.memory import Memory
from zhihuiti.models import AgentRole, Task, TaskStatus
from zhihuiti.arbitration import ArbitrationBureau
from zhihuiti.factory import Factory
from zhihuiti.futures import FuturesMarket
from zhihuiti.market import TradingMarket
from zhihuiti.prompts import get_prompt
from zhihuiti.realms import RealmManager
from zhihuiti.relationships import LendingSystem, RelationshipGraph, RelationType

console = Console()


class Orchestrator:
    """Top-level controller that decomposes goals and manages the agent swarm."""

    def __init__(self, db_path: str = "zhihuiti.db", model: str | None = None):
        from zhihuiti.llm import DEFAULT_MODEL

        self.llm = LLM(model=model or DEFAULT_MODEL)
        self.memory = Memory(db_path=db_path)
        self.economy = Economy(self.memory)
        self.bloodline = Bloodline(self.memory)
        self.realm_manager = RealmManager(self.memory)
        self.agent_manager = AgentManager(
            self.llm, self.memory, self.economy, self.bloodline, self.realm_manager,
        )
        self.judge = Judge(self.llm, self.memory, self.agent_manager)
        self.circuit_breaker = CircuitBreaker(self.memory, interactive=True)
        self.behavior = BehaviorDetector(self.memory, self.llm)
        self.rel_graph = RelationshipGraph(self.memory)
        self.lending = LendingSystem(self.memory, self.rel_graph)
        self.arbitration = ArbitrationBureau(self.memory)
        self.market = TradingMarket(self.memory)
        self.futures = FuturesMarket(self.memory)
        self.factory = Factory(llm=self.llm, memory=self.memory)
        self.bidding = BiddingHouse(self.llm, self.memory, self.economy)
        self.tasks: dict[str, Task] = {}

        # Allocate initial realm budgets from treasury
        self.realm_manager.allocate_budgets(self.economy.treasury.balance * 0.5)

    def decompose_goal(self, goal: str) -> list[Task]:
        """Use the LLM to break a goal into subtasks."""
        console.print(Panel(f"[bold]Goal:[/bold] {goal}", title="智慧体 Orchestrator"))

        subtasks_raw = self.llm.chat_json(
            system=get_prompt("orchestrator"),
            user=f"Decompose this goal into subtasks:\n\n{goal}",
            temperature=0.5,
        )

        if not isinstance(subtasks_raw, list):
            subtasks_raw = [subtasks_raw]

        tasks = []
        for st in subtasks_raw:
            task = Task(
                description=st.get("description", str(st)),
                metadata={"requested_role": st.get("role", "custom")},
            )
            self.tasks[task.id] = task
            tasks.append(task)

        console.print(f"\n[bold]Decomposed into {len(tasks)} subtasks:[/bold]")
        for i, t in enumerate(tasks, 1):
            role = t.metadata.get("requested_role", "custom")
            console.print(f"  {i}. [{role}] {t.description}")
        console.print()

        return tasks

    def execute_goal(self, goal: str) -> dict:
        """Full pipeline: decompose → spawn → execute (with sub-agents) → judge → evolve."""
        tasks = self.decompose_goal(goal)
        results = []

        for task in tasks:
            role_name = task.metadata.get("requested_role", "custom")
            role = ROLE_MAP.get(role_name, AgentRole.CUSTOM)

            console.print(
                f"\n[bold cyan]▶ Executing:[/bold cyan] {task.description[:80]}..."
            )

            # Run auction — agents compete for the task
            def _spawn_for_pool(r: AgentRole, budget: float):
                config = self.agent_manager.get_best_config(r)
                return self.agent_manager.spawn(role=r, depth=0, config=config, budget=budget)

            winner, auction = self.bidding.run_auction(
                task_description=task.description,
                role=role,
                spawn_fn=_spawn_for_pool,
            )

            if winner:
                agent = winner
                # Also register in agent_manager if not already there
                if agent.id not in self.agent_manager.agents:
                    self.agent_manager.agents[agent.id] = agent
            else:
                # No bids — fallback to direct spawn
                console.print("  [yellow]No auction winner, spawning directly[/yellow]")
                config = self.agent_manager.get_best_config(role)
                agent = self.agent_manager.spawn(
                    role=role, depth=0, config=config, budget=100.0,
                )
            # execute_task now handles sub-agent delegation recursively
            output = self.agent_manager.execute_task(agent, task)

            preview = output[:150].replace("\n", " ")
            console.print(f"  [dim]Output: {preview}...[/dim]" if len(output) > 150 else f"  [dim]Output: {preview}[/dim]")

            # Circuit breaker check — iron laws before inspection
            fuse_event = self.circuit_breaker.check(output, task.description, agent)
            if fuse_event and fuse_event.status.value != "overridden":
                # Output rejected by circuit breaker
                task.status = TaskStatus.FAILED
                task.result = f"[REJECTED BY FUSE: {fuse_event.law_name}] {output[:200]}"
                task.score = 0.0
                agent.scores.append(0.0)
                results.append({
                    "task": task.description,
                    "agent_id": agent.id,
                    "role": role.value,
                    "score": 0.0,
                    "status": "fuse_tripped",
                    "alive": agent.alive,
                    "subtask_count": len(task.subtask_ids),
                    "reward": {"gross": 0, "tax": 0, "net": 0, "paid": False},
                    "bid": auction.winning_bid if auction.winning_bid else None,
                    "num_bids": len(auction.bids) if auction else 0,
                })
                continue

            # Behavioral detection — check for laziness, lying, scheming
            deep = self.behavior.should_deep_analyze(agent)
            violations = self.behavior.analyze(output, task, agent, deep=deep)

            # Judge scores the final (possibly synthesized) output via 3-layer inspection
            score = self.judge.score_task(task, agent)

            # Apply behavioral penalties to score
            if violations:
                penalty = self.behavior.get_score_penalty(agent)
                old_score = score
                score = max(0.0, score - penalty)
                task.score = score
                # Replace the last score in agent.scores with the penalized version
                if agent.scores:
                    agent.scores[-1] = score
                console.print(
                    f"  [yellow]Behavior penalty:[/yellow] -{penalty:.2f} "
                    f"(score: {old_score:.2f} -> {score:.2f})"
                )

            # Record in realm
            self.realm_manager.on_task_complete(
                agent, score, task.status.value == "completed",
            )

            # Pay the agent based on score
            budget_ref = [agent.budget]
            reward_info = self.economy.reward_agent(
                agent.id, score, budget_ref,
                task_complexity=1.0 + len(task.subtask_ids) * 0.3,
            )
            agent.budget = budget_ref[0]
            if reward_info["paid"]:
                console.print(
                    f"  [green]💰 Reward:[/green] +{reward_info['net']:.1f} tokens "
                    f"(gross={reward_info['gross']:.1f}, tax={reward_info['tax']:.1f})"
                )

                # Auto-repay outstanding loans from reward
                repaid = self.lending.auto_repay(agent, reward_info["net"])
                if repaid > 0:
                    self.rel_graph.record_transaction_rel(
                        agent.id, "loan_repayment", repaid,
                    )

            # Also score any sub-agents
            for subtask_id in task.subtask_ids:
                for a in self.agent_manager.agents.values():
                    if subtask_id in [t for t in a.task_ids]:
                        self.judge.evaluate_agent(a)

            # Evaluate parent agent for cull/promote
            self.judge.evaluate_agent(agent)

            results.append({
                "task": task.description,
                "agent_id": agent.id,
                "role": role.value,
                "score": score,
                "status": task.status.value,
                "alive": agent.alive,
                "subtask_count": len(task.subtask_ids),
                "reward": reward_info,
                "bid": auction.winning_bid if auction.winning_bid else None,
                "num_bids": len(auction.bids) if auction else 0,
            })

        # Print agent tree if any sub-agents were spawned
        has_subagents = any(r.get("subtask_count", 0) > 0 for r in results)
        if has_subagents:
            console.print()
            self.agent_manager.print_agent_tree()

        # Summary
        self._print_summary(results)

        # Realm, economy, and safety reports
        self.realm_manager.print_report(self.agent_manager.agents)
        self.economy.print_report()
        if self.circuit_breaker.events:
            self.circuit_breaker.print_report()
        if self.behavior.violations:
            self.behavior.print_report()
        if self.lending.active_loans:
            self.lending.print_report()

        return {
            "goal": goal,
            "tasks": results,
            "stats": self.memory.get_stats(),
            "economy": self.economy.get_report(),
        }

    def _print_summary(self, results: list[dict]) -> None:
        """Print a summary table of execution results."""
        console.print()
        table = Table(title="Execution Summary")
        table.add_column("Role", style="cyan")
        table.add_column("Task", max_width=35)
        table.add_column("Score", justify="center")
        table.add_column("Bid", justify="right")
        table.add_column("Reward", justify="right")
        table.add_column("Status", justify="center")

        for r in results:
            score = r["score"]
            score_style = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"
            status_style = "green" if r["status"] == "completed" else "red"
            alive_marker = "" if r["alive"] else " ☠"
            reward = r.get("reward", {})
            net = reward.get("net", 0)
            reward_str = f"+{net:.1f}" if net > 0 else "—"
            bid = r.get("bid")
            num_bids = r.get("num_bids", 0)
            bid_str = f"{bid:.1f} ({num_bids})" if bid else "direct"

            table.add_row(
                r["role"] + alive_marker,
                r["task"][:35],
                f"[{score_style}]{score:.2f}[/{score_style}]",
                bid_str,
                f"[green]{reward_str}[/green]" if net > 0 else reward_str,
                f"[{status_style}]{r['status']}[/{status_style}]",
            )

        console.print(table)

        stats = self.memory.get_stats()
        total_agents = len(self.agent_manager.agents)
        alive_agents = len(self.agent_manager.get_alive_agents())
        console.print(
            f"\n[dim]Session: {total_agents} agents spawned ({alive_agents} alive) | "
            f"Memory: {stats['total_tasks']} tasks, "
            f"{stats['gene_pool_size']} genes, "
            f"avg score: {stats['avg_task_score']:.3f}[/dim]\n"
        )

    def close(self) -> None:
        self.memory.close()
