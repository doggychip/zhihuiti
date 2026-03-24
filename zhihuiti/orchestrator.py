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
from zhihuiti.causal import CausalGraph, CausalReasoner, CausalValidator, load_arb_causal_data
from zhihuiti.circuit_breaker import CircuitBreaker
from zhihuiti.economy import Economy
from zhihuiti.judge import Judge
from zhihuiti.llm import LLM
from zhihuiti.memory import Memory
from zhihuiti.messaging import MessageBoard
from zhihuiti.models import AgentRole, Task, TaskStatus
from zhihuiti.arbitration import ArbitrationBureau
from zhihuiti.factory import Factory
from zhihuiti.futures import FuturesMarket
from zhihuiti.market import TradingMarket
from zhihuiti.prompts import get_prompt
from zhihuiti.realms import RealmManager
from zhihuiti.relationships import LendingSystem, RelationshipGraph, RelationType
from zhihuiti.retry import RetryProtocol, EscalationAction
from zhihuiti.rice import estimate_rice_scores
from zhihuiti.phase_gate import PhaseGate, GateMode

console = Console()


class Orchestrator:
    """Top-level controller that decomposes goals and manages the agent swarm."""

    def __init__(self, db_path: str = "zhihuiti.db", model: str | None = None,
                 tools_enabled: bool = False):
        self.llm = LLM(model=model)
        self.memory = Memory(db_path=db_path)
        self.economy = Economy(self.memory)
        self.bloodline = Bloodline(self.memory)
        self.realm_manager = RealmManager(self.memory)
        self.tools_enabled = tools_enabled

        # Tool executor (only created when tools are enabled)
        tool_executor = None
        if tools_enabled:
            from zhihuiti.tools import ToolExecutor
            tool_executor = ToolExecutor()
            console.print("  [dim]🔧 Tool execution enabled (gh, git read-only)[/dim]")

        self.agent_manager = AgentManager(
            self.llm, self.memory, self.economy, self.bloodline, self.realm_manager,
            tool_executor=tool_executor,
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
        self.messages = MessageBoard(self.memory)
        self.retry_protocol = RetryProtocol(max_retries=3)
        self.phase_gate = PhaseGate(mode=GateMode.SOFT)

        # Causal reasoning engine (因果推理)
        self.causal_graph = CausalGraph()
        self.causal_reasoner = CausalReasoner(self.llm, self.causal_graph)
        self.causal_validator = CausalValidator(self.llm, self.causal_graph)
        try:
            n_loaded = load_arb_causal_data(self.causal_graph)
            if n_loaded > 0:
                console.print(f"  [dim]因果图: {n_loaded} causal edges loaded[/dim]")
        except Exception:
            pass  # Non-critical: prediction-arb data may not be available

        self.tasks: dict[str, Task] = {}
        self.max_workers = 4
        self.max_retries = 1

        # Restore surviving agents from prior sessions into agent_manager
        for agent in self.bidding.pool.get_all_alive():
            if agent.id not in self.agent_manager.agents:
                self.agent_manager.agents[agent.id] = agent

        # Allocate initial realm budgets from treasury
        self.realm_manager.allocate_budgets(self.economy.treasury.balance * 0.5)

    def decompose_goal(self, goal: str) -> list[Task]:
        """Use the LLM to break a goal into subtasks with optional dependencies.

        The LLM is asked for ``id`` and ``depends_on`` per subtask.  When it
        doesn't provide them we fall back to a flat (independent) list.
        """
        from zhihuiti.dag import detect_cycle

        console.print(Panel(f"[bold]Goal:[/bold] {goal}", title="智慧体 Orchestrator"))

        # Cross-goal memory: inject prior similar goals as context
        prior_context = ""
        first_word = goal.split()[0] if goal.split() else ""
        prior_goals = self.memory.get_similar_goals(first_word, limit=2)
        if prior_goals:
            examples = "\n".join(
                f"- Goal: {g['goal'][:80]} → {g['task_count']} tasks, avg score {g['avg_score']:.2f}"
                for g in prior_goals
            )
            prior_context = f"\n\nPrior similar goals for reference:\n{examples}\n"
            console.print(f"  [dim]📚 Found {len(prior_goals)} prior goals as context[/dim]")

        subtasks_raw = self.llm.chat_json(
            system=get_prompt("orchestrator"),
            user=f"Decompose this goal into subtasks:\n\n{goal}{prior_context}",
            temperature=0.5,
        )

        if not isinstance(subtasks_raw, list):
            subtasks_raw = [subtasks_raw]

        # Build tasks, preserving the LLM-provided ``id`` for dependency wiring
        dag_id_to_task: dict[str, Task] = {}
        dag_deps: dict[str, list[str]] = {}
        tasks: list[Task] = []

        for i, st in enumerate(subtasks_raw):
            dag_id = st.get("id", f"t{i}")
            depends_on = st.get("depends_on", [])
            if not isinstance(depends_on, list):
                depends_on = []

            task = Task(
                description=st.get("description", str(st)),
                metadata={
                    "requested_role": st.get("role", "custom"),
                    "dag_id": dag_id,
                    "depends_on": depends_on,
                },
            )
            self.tasks[task.id] = task
            dag_id_to_task[dag_id] = task
            dag_deps[dag_id] = depends_on
            tasks.append(task)

        # Cycle check — fall back to flat if the LLM produced a cycle
        cycle = detect_cycle(dag_deps)
        if cycle:
            console.print(
                f"  [yellow]⚠ Dependency cycle detected ({' → '.join(cycle)}), "
                f"running flat[/yellow]"
            )
            for t in tasks:
                t.metadata["depends_on"] = []

        console.print(f"\n[bold]Decomposed into {len(tasks)} subtasks:[/bold]")
        for i, t in enumerate(tasks, 1):
            role = t.metadata.get("requested_role", "custom")
            deps = t.metadata.get("depends_on", [])
            dep_str = f" (after {', '.join(deps)})" if deps else ""
            console.print(f"  {i}. [{role}] {t.description}{dep_str}")
        console.print()

        return tasks

    def execute_goal(self, goal: str) -> dict:
        """Full pipeline: decompose → spawn → execute (DAG-parallel) → judge → evolve."""
        import uuid as _uuid
        from zhihuiti.dag import topological_waves

        tasks = self.decompose_goal(goal)
        results: list[dict] = []
        goal_id = _uuid.uuid4().hex[:12]
        _lock = threading.Lock()  # serialises shared-state mutations within this goal

        # Build the dependency waves
        dag_id_list = [t.metadata["dag_id"] for t in tasks]
        dag_deps = {t.metadata["dag_id"]: t.metadata.get("depends_on", []) for t in tasks}
        dag_id_to_task = {t.metadata["dag_id"]: t for t in tasks}

        try:
            waves = topological_waves(dag_id_list, dag_deps)
        except ValueError:
            # Should not happen (cycle already stripped in decompose), fallback
            waves = [dag_id_list]

        # Completed task outputs keyed by dag_id — fed as context to dependents
        completed_outputs: dict[str, str] = {}
        completed_lock = threading.Lock()

        def _run_task(task: Task) -> dict:
            role_name = task.metadata.get("requested_role", "custom")
            role = ROLE_MAP.get(role_name, AgentRole.CUSTOM)

            console.print(
                f"\n[bold cyan]▶ Executing:[/bold cyan] {task.description[:80]}..."
            )

            # ── Phase 1 (locked): auction — spawns agents, mutates economy ──
            with _lock:
                def _spawn_for_pool(r: AgentRole, budget: float):
                    config = self.agent_manager.get_best_config(r)
                    if config and self.tools_enabled:
                        config.tools_enabled = True
                    return self.agent_manager.spawn(role=r, depth=0, config=config, budget=budget)

                winner, auction = self.bidding.run_auction(
                    task_description=task.description,
                    role=role,
                    spawn_fn=_spawn_for_pool,
                )

                if winner:
                    agent = winner
                    if agent.id not in self.agent_manager.agents:
                        self.agent_manager.agents[agent.id] = agent
                else:
                    console.print("  [yellow]No auction winner, spawning directly[/yellow]")
                    config = self.agent_manager.get_best_config(role)
                    if config and self.tools_enabled:
                        config.tools_enabled = True
                    agent = self.agent_manager.spawn(
                        role=role, depth=0, config=config, budget=100.0,
                    )

            # ── Phase 2 (free): task execution — slow LLM I/O ──
            # Inject dependency context — prior task outputs from deps
            dep_ids = task.metadata.get("depends_on", [])
            if dep_ids:
                with completed_lock:
                    dep_context = "\n".join(
                        f"[{did}]: {completed_outputs.get(did, '(pending)')[:500]}"
                        for did in dep_ids
                        if did in completed_outputs
                    )
                if dep_context:
                    task.description = (
                        f"{task.description}\n\n"
                        f"Context from prior tasks:\n{dep_context}"
                    )

            # Inject messages from collaborating agents (A2A messaging)
            msg_context = self.messages.collect_context(agent, goal_id)
            if msg_context:
                task.description = f"{task.description}\n\n{msg_context}"

            output = self.agent_manager.execute_task(agent, task)

            # Store output so dependent tasks can read it
            dag_id = task.metadata.get("dag_id", task.id)
            with completed_lock:
                completed_outputs[dag_id] = output

            # Broadcast output to message board for other agents
            self.messages.broadcast(agent, output, goal_id)

            preview = output[:150].replace("\n", " ")
            console.print(
                f"  [dim]Output: {preview}...[/dim]"
                if len(output) > 150 else f"  [dim]Output: {preview}[/dim]"
            )

            # ── Phase 3 (locked): circuit-breaker + behavioural analysis ──
            with _lock:
                fuse_event = self.circuit_breaker.check(output, task.description, agent)
                if fuse_event and fuse_event.status.value != "overridden":
                    task.status = TaskStatus.FAILED
                    task.result = f"[REJECTED BY FUSE: {fuse_event.law_name}] {output[:200]}"
                    task.score = 0.0
                    agent.scores.append(0.0)
                    return {
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
                        "_fuse_event": fuse_event,
                    }

                deep = self.behavior.should_deep_analyze(agent)
                violations = self.behavior.analyze(output, task, agent, deep=deep)

            # ── Phase 4 (free): judge scoring — 3 more LLM calls ──
            score = self.judge.score_task(task, agent)
            # Capture inspection result for structured retry feedback
            _inspection_result = (
                self.judge.inspection.history[-1]
                if self.judge.inspection.history else None
            )

            # ── Phase 5 (locked): penalties, realm, reward, checkpoint ──
            with _lock:
                if violations:
                    penalty = self.behavior.get_score_penalty(agent)
                    old_score = score
                    score = max(0.0, score - penalty)
                    task.score = score
                    if agent.scores:
                        agent.scores[-1] = score
                    console.print(
                        f"  [yellow]Behavior penalty:[/yellow] -{penalty:.2f} "
                        f"(score: {old_score:.2f} -> {score:.2f})"
                    )

                self.realm_manager.on_task_complete(
                    agent, score, task.status.value == "completed",
                )

                budget_ref = [agent.budget]
                reward_info = self.economy.reward_agent(
                    agent.id, score, budget_ref,
                    task_complexity=1.0 + len(task.subtask_ids) * 0.3,
                )
                agent.budget = budget_ref[0]
                self.agent_manager.checkpoint_agent(agent)

                if reward_info["paid"]:
                    console.print(
                        f"  [green]💰 Reward:[/green] +{reward_info['net']:.1f} tokens "
                        f"(gross={reward_info['gross']:.1f}, tax={reward_info['tax']:.1f})"
                    )
                    repaid = self.lending.auto_repay(agent, reward_info["net"])
                    if repaid > 0:
                        self.rel_graph.record_transaction_rel(
                            agent.id, "loan_repayment", repaid,
                        )

                for subtask_id in task.subtask_ids:
                    for a in self.agent_manager.agents.values():
                        if subtask_id in [t for t in a.task_ids]:
                            self.judge.evaluate_agent(a)

                self.judge.evaluate_agent(agent)

            return {
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
                "_inspection_result": _inspection_result,
            }

        def _run_with_retry(task: Task) -> dict:
            """Run a task with structured retry and escalation protocol.

            On failure:
            1. Record structured QA feedback (what failed, why, which layer)
            2. Inject feedback into the task for the next attempt
            3. After max attempts, escalate (reassign/decompose/defer/accept)
            """
            original_desc = task.description
            result = _run_task(task)

            while result["status"] in ("fuse_tripped", "failed"):
                # Record failure with structured feedback
                retry_state = self.retry_protocol.record_failure(
                    task,
                    score=result.get("score", 0.0),
                    result=task.result,
                    inspection_result=result.get("_inspection_result"),
                    fuse_event=result.get("_fuse_event"),
                )

                if not self.retry_protocol.should_retry(task):
                    # Exhausted retries — escalate
                    action = self.retry_protocol.escalate(task)
                    if action == EscalationAction.ACCEPT:
                        # Use the best result we got
                        task.result = retry_state.best_result
                        task.score = retry_state.best_score
                        result["score"] = retry_state.best_score
                        result["status"] = "accepted_with_issues"
                    # For REASSIGN/DECOMPOSE/DEFER, the caller can inspect
                    # result["escalation"] to decide what to do
                    result["escalation"] = action.value
                    break

                attempt = retry_state.attempt + 1
                console.print(
                    f"\n  [yellow]⟳ Retry {attempt}/{self.retry_protocol.max_retries} "
                    f"(with QA feedback):[/yellow] {original_desc[:60]}..."
                )

                # Reset task state and inject QA feedback
                task.status = TaskStatus.PENDING
                task.result = ""
                task.score = None
                feedback = self.retry_protocol.get_retry_context(task)
                task.description = f"{original_desc}\n\n{feedback}" if feedback else original_desc

                result = _run_task(task)

            # Restore original description (remove injected feedback)
            task.description = original_desc
            return result

        # Execute wave-by-wave; tasks within a wave run in parallel
        max_w = self.max_workers
        for wave_idx, wave_ids in enumerate(waves):
            wave_tasks = [dag_id_to_task[did] for did in wave_ids]

            # RICE prioritization: order tasks within each wave by impact
            if len(wave_tasks) > 1:
                rice_scores = estimate_rice_scores(self.llm, wave_tasks, goal)
                rice_order = {s.task_id: i for i, s in enumerate(rice_scores)}
                wave_tasks.sort(key=lambda t: rice_order.get(t.id, 999))

            if len(waves) > 1:
                console.print(
                    f"\n[bold magenta]── Wave {wave_idx} "
                    f"({len(wave_tasks)} task{'s' if len(wave_tasks) != 1 else ''}) "
                    f"──[/bold magenta]"
                )

            wave_results: list[dict] = []
            if len(wave_tasks) > 1:
                with ThreadPoolExecutor(max_workers=min(len(wave_tasks), max_w)) as executor:
                    futures = {executor.submit(_run_with_retry, t): t for t in wave_tasks}
                    for future in as_completed(futures):
                        wave_results.append(future.result())
            else:
                wave_results.extend(_run_with_retry(t) for t in wave_tasks)

            results.extend(wave_results)

            # Phase gate: evaluate wave quality before proceeding to next wave
            if (
                getattr(self, 'phase_gate', None)
                and len(waves) > 1
                and wave_idx < len(waves) - 1
            ):
                gate_result = self.phase_gate.evaluate(wave_idx, wave_results)
                if not self.phase_gate.should_continue(gate_result):
                    console.print(
                        "\n  [bold red]Pipeline halted by phase gate.[/bold red] "
                        "Remaining waves skipped."
                    )
                    break

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
        if getattr(self, 'phase_gate', None) and self.phase_gate.history:
            self.phase_gate.print_report()
        if self.lending.active_loans:
            self.lending.print_report()
        if getattr(self, 'causal_validator', None) and self.causal_validator.history:
            self.causal_validator.print_report()
        if getattr(self, 'causal_graph', None) and self.causal_graph.edges:
            self.causal_graph.print_graph()

        # Save goal to history for cross-goal learning
        scores = [r["score"] for r in results if r["score"] > 0]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        summary = "; ".join(
            f"{r['role']}: {r['task'][:40]} ({r['score']:.2f})"
            for r in results
        )
        self.memory.save_goal(
            goal_id=goal_id,
            goal=goal,
            task_count=len(results),
            avg_score=avg_score,
            summary=summary[:500],
        )

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
