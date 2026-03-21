"""Agent runtime — spawning, execution, budget management, sub-agent delegation."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from rich.console import Console
from rich.tree import Tree

from zhihuiti.models import AgentConfig, AgentRole, AgentState, Task, TaskStatus
from zhihuiti.prompts import SYNTHESIS_INSTRUCTIONS, TOOL_INSTRUCTIONS, get_prompt

if TYPE_CHECKING:
    from zhihuiti.bloodline import Bloodline
    from zhihuiti.economy import Economy
    from zhihuiti.llm import LLM
    from zhihuiti.memory import Memory
    from zhihuiti.realms import RealmManager
    from zhihuiti.tools import ToolExecutor

console = Console()

MAX_DEPTH = 3
TASK_COST = 5.0  # Budget units per task execution
SYNTHESIS_COST = 3.0  # Budget for the synthesis step

ROLE_MAP = {
    "researcher": AgentRole.RESEARCHER,
    "analyst": AgentRole.ANALYST,
    "coder": AgentRole.CODER,
    "trader": AgentRole.TRADER,
    "alphaarena_trader": AgentRole.ALPHAARENA_TRADER,
    "custom": AgentRole.CUSTOM,
}


def _parse_delegation(response: str) -> list[dict] | None:
    """Try to parse a delegation request from agent output.

    Returns a list of subtask dicts if the agent requested delegation,
    or None if the agent responded directly.
    """
    stripped = response.strip()

    # Try to parse as JSON
    # Strip markdown fences if present
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None

    # Check for delegation format: {"action": "delegate", "subtasks": [...]}
    if isinstance(data, dict) and data.get("action") == "delegate":
        subtasks = data.get("subtasks", [])
        if isinstance(subtasks, list) and len(subtasks) > 0:
            return subtasks

    return None


def _parse_tool_request(response: str) -> str | None:
    """Try to parse a tool-use request from agent output.

    Returns the command string if the agent requested a tool,
    or None if no tool request.
    """
    stripped = response.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None

    if isinstance(data, dict) and data.get("action") == "tool":
        command = data.get("command", "")
        if command:
            return command

    return None


class AgentManager:
    """Manages the lifecycle of all agents, including recursive sub-agent spawning."""

    def __init__(self, llm: LLM, memory: Memory, economy: Economy | None = None,
                 bloodline: Bloodline | None = None,
                 realm_manager: RealmManager | None = None,
                 tool_executor: ToolExecutor | None = None):
        self.llm = llm
        self.memory = memory
        self.economy = economy
        self.bloodline = bloodline
        self.realm_manager = realm_manager
        self.tool_executor = tool_executor
        self.agents: dict[str, AgentState] = {}

    def spawn(
        self,
        role: AgentRole,
        depth: int = 0,
        parent_id: str | None = None,
        config: AgentConfig | None = None,
        budget: float = 100.0,
    ) -> AgentState:
        """Spawn a new agent, respecting depth limits."""
        if depth > MAX_DEPTH:
            raise ValueError(f"Cannot spawn agent: depth {depth} exceeds max {MAX_DEPTH}")

        if config is None:
            config = AgentConfig(
                role=role,
                system_prompt=get_prompt(role.value),
                budget=budget,
                gene_id=uuid.uuid4().hex[:12],
            )

        # Fund from treasury if economy is active
        if self.economy:
            if not self.economy.fund_spawn(budget):
                raise ValueError("Treasury cannot fund agent spawn")

        agent = AgentState(
            config=config,
            budget=budget,
            depth=depth,
            parent_agent_id=parent_id,
        )
        self.agents[agent.id] = agent

        self.memory.save_agent(
            agent_id=agent.id,
            role=role.value,
            budget=budget,
            depth=depth,
            avg_score=0.5,
            alive=True,
            parent_agent_id=parent_id,
        )

        # Register in bloodline lineage
        if self.bloodline:
            self.bloodline.register(config, agent_id=agent.id)

        # Assign to realm
        if self.realm_manager:
            self.realm_manager.on_agent_spawn(agent)

        indent = "  " * (depth + 1)
        gen_str = f" gen-{config.generation}" if config.generation > 0 else ""
        realm_str = f" {agent.realm.value}" if hasattr(agent, 'realm') else ""
        console.print(
            f"{indent}[green]↳ Spawned[/green] {role.value} agent "
            f"[dim]{agent.id}[/dim] (depth={depth}, budget={budget:.0f}{gen_str}{realm_str})"
        )
        return agent

    def execute_task(self, agent: AgentState, task: Task) -> str:
        """Execute a task with optional tool-use loop and sub-agent delegation."""
        from zhihuiti.tools import TOOL_COST, MAX_TOOL_CALLS, ToolExecutionError

        if not agent.alive:
            raise ValueError(f"Agent {agent.id} is dead")

        if not agent.deduct_budget(TASK_COST):
            console.print(f"  [red]✗[/red] Agent {agent.id} out of budget")
            agent.alive = False
            task.status = TaskStatus.FAILED
            task.result = "Agent ran out of budget"
            return task.result

        # Record the fee in the economy
        if self.economy:
            self.economy.record_task_fee(agent.id, TASK_COST)

        task.status = TaskStatus.RUNNING
        task.assigned_agent_id = agent.id

        # Build context from past successes
        past = self.memory.get_similar_successes(agent.config.role.value)
        context = ""
        if past:
            examples = "\n".join(
                f"- Task: {p['task_description'][:80]} → Score: {p['score']}"
                for p in past[:2]
            )
            context = f"\n\nPast successful approaches:\n{examples}\n"

        # Add depth context so agent knows if it can delegate
        can_delegate = agent.depth < MAX_DEPTH
        depth_note = ""
        if not can_delegate:
            depth_note = (
                "\n\nNOTE: You are at maximum depth and CANNOT delegate to sub-agents. "
                "You must handle this task directly."
            )

        # Build system prompt — append tool instructions if tools are enabled
        system_prompt = agent.config.system_prompt
        tools_active = agent.config.tools_enabled and self.tool_executor is not None
        if tools_active:
            system_prompt += TOOL_INSTRUCTIONS

        prompt = f"Task: {task.description}{context}{depth_note}"
        tool_history = ""  # accumulated tool call/result pairs
        tool_calls = 0

        # ── Agentic loop: LLM → (tool → LLM)* → final answer ──
        while True:
            try:
                raw_response = self.llm.chat(
                    system=system_prompt,
                    user=prompt + tool_history,
                    temperature=agent.config.temperature,
                    model=agent.config.model,
                )
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.result = f"Error: {e}"
                self._save_task(task, agent)
                return task.result

            # Check for tool request
            if tools_active and tool_calls < MAX_TOOL_CALLS:
                tool_command = _parse_tool_request(raw_response)
                if tool_command:
                    tool_calls += 1
                    if not agent.deduct_budget(TOOL_COST):
                        tool_history += (
                            f"\n\n[Tool {tool_calls}: {tool_command}]\n"
                            f"[Error: insufficient budget for tool call]\n"
                        )
                        continue

                    try:
                        result = self.tool_executor.execute(tool_command)
                        output = result.stdout or result.stderr or "(no output)"
                        tool_history += (
                            f"\n\n[Tool {tool_calls}: {tool_command}]\n"
                            f"[Output ({result.return_code}):\n{output}\n]\n"
                        )
                    except ToolExecutionError as e:
                        tool_history += (
                            f"\n\n[Tool {tool_calls}: {tool_command}]\n"
                            f"[Blocked: {e}]\n"
                        )

                    console.print(
                        f"  [dim]🔧 Tool call {tool_calls}/{MAX_TOOL_CALLS}[/dim]"
                    )
                    continue  # loop back for agent to process the result

            # Not a tool request — check for delegation or return as final answer
            subtask_requests = None
            if can_delegate:
                subtask_requests = _parse_delegation(raw_response)

            if subtask_requests:
                result = self._execute_delegation(agent, task, subtask_requests)
            else:
                result = raw_response

            break

        task.status = TaskStatus.COMPLETED
        task.result = result
        self._save_task(task, agent)
        return result

    def _execute_delegation(
        self, parent: AgentState, parent_task: Task, subtask_requests: list[dict]
    ) -> str:
        """Spawn sub-agents for delegated subtasks, then synthesize results."""
        indent = "  " * (parent.depth + 1)
        console.print(
            f"\n{indent}[bold magenta]⑂ Delegating[/bold magenta] "
            f"{len(subtask_requests)} subtasks from {parent.config.role.value} "
            f"[dim]{parent.id}[/dim] (depth {parent.depth} → {parent.depth + 1})"
        )

        sub_results: list[dict] = []

        for i, req in enumerate(subtask_requests):
            description = req.get("description", str(req))
            role_name = req.get("role", "custom")
            role = ROLE_MAP.get(role_name, AgentRole.CUSTOM)

            # Create subtask
            subtask = Task(
                description=description,
                parent_task_id=parent_task.id,
                metadata={"requested_role": role_name, "parent_agent_id": parent.id},
            )
            parent_task.subtask_ids.append(subtask.id)

            # Budget for sub-agent: split parent's remaining budget
            sub_budget = min(parent.budget * 0.4, 50.0)

            # Try gene pool config
            config = self.get_best_config(role)

            # Spawn sub-agent
            sub_agent = self.spawn(
                role=role,
                depth=parent.depth + 1,
                parent_id=parent.id,
                config=config,
                budget=sub_budget,
            )

            # Execute (this recurses if the sub-agent also delegates)
            sub_indent = "  " * (parent.depth + 2)
            console.print(
                f"\n{sub_indent}[cyan]▶ Sub-task {i+1}/{len(subtask_requests)}:[/cyan] "
                f"{description[:70]}..."
            )
            output = self.execute_task(sub_agent, subtask)

            preview = output[:120].replace("\n", " ")
            console.print(f"{sub_indent}[dim]→ {preview}...[/dim]" if len(output) > 120 else f"{sub_indent}[dim]→ {preview}[/dim]")

            sub_results.append({
                "role": role_name,
                "task": description,
                "result": output,
                "agent_id": sub_agent.id,
            })

        # Synthesis: parent agent combines sub-agent outputs
        return self._synthesize(parent, parent_task, sub_results)

    def _synthesize(
        self, agent: AgentState, task: Task, sub_results: list[dict]
    ) -> str:
        """Have the parent agent synthesize sub-agent results into a final output."""
        if not agent.deduct_budget(SYNTHESIS_COST):
            # Out of budget for synthesis — just concatenate
            return "\n\n---\n\n".join(
                f"[{r['role']}] {r['task']}:\n{r['result']}" for r in sub_results
            )

        indent = "  " * (agent.depth + 1)
        console.print(
            f"\n{indent}[bold yellow]⊕ Synthesizing[/bold yellow] "
            f"{len(sub_results)} sub-results for {agent.config.role.value} "
            f"[dim]{agent.id}[/dim]"
        )

        # Build synthesis prompt
        results_text = "\n\n".join(
            f"--- Sub-agent ({r['role']}) ---\n"
            f"Task: {r['task']}\n"
            f"Result:\n{r['result'][:2000]}"
            for r in sub_results
        )

        prompt = (
            f"{SYNTHESIS_INSTRUCTIONS}"
            f"Original task: {task.description}\n\n"
            f"Sub-agent results:\n{results_text}"
        )

        try:
            synthesis = self.llm.chat(
                system=agent.config.system_prompt,
                user=prompt,
                temperature=agent.config.temperature,
                model=agent.config.model,
            )
            return synthesis
        except Exception as e:
            # Fallback: concatenate results
            console.print(f"{indent}[yellow]⚠ Synthesis failed:[/yellow] {e}")
            return "\n\n---\n\n".join(
                f"[{r['role']}] {r['task']}:\n{r['result']}" for r in sub_results
            )

    def _save_task(self, task: Task, agent: AgentState) -> None:
        self.memory.save_task(
            task_id=task.id,
            description=task.description,
            status=task.status.value,
            result=task.result,
            agent_id=agent.id,
            parent_task_id=task.parent_task_id,
        )

    def checkpoint_agent(self, agent: AgentState) -> None:
        """Persist the agent's current budget and avg_score to DB mid-session."""
        self.memory.save_agent(
            agent_id=agent.id,
            role=agent.config.role.value,
            budget=agent.budget,
            depth=agent.depth,
            avg_score=agent.avg_score,
            alive=agent.alive,
            parent_agent_id=agent.parent_agent_id,
        )

    def cull_agent(self, agent: AgentState) -> None:
        """Kill an underperforming agent and burn its remaining tokens."""
        # Burn remaining budget
        if self.economy and agent.budget > 0:
            self.economy.burn_agent_balance(agent.id, agent.budget)
            console.print(
                f"  [red]🔥 Burned[/red] {agent.budget:.1f} tokens from agent "
                f"[dim]{agent.id}[/dim]"
            )

        agent.alive = False
        agent.budget = 0.0
        self.memory.save_agent(
            agent_id=agent.id,
            role=agent.config.role.value,
            budget=agent.budget,
            depth=agent.depth,
            avg_score=agent.avg_score,
            alive=False,
            parent_agent_id=agent.parent_agent_id,
        )

        # Mark gene dead in bloodline
        if self.bloodline and agent.config.gene_id:
            self.bloodline.mark_dead(agent.config.gene_id, agent.avg_score)

        # Update realm lifecycle
        if self.realm_manager:
            self.realm_manager.on_agent_cull(agent)

        console.print(
            f"  [red]☠ Culled[/red] {agent.config.role.value} agent "
            f"[dim]{agent.id}[/dim] (avg_score={agent.avg_score:.2f})"
        )

    def promote_to_gene_pool(self, agent: AgentState) -> None:
        """Save a high-performing agent's config to the gene pool.

        Agents promoted here earn a model upgrade: their descendants will use
        the LLM's premium_model instead of the default.
        """
        gene_id = agent.config.gene_id or uuid.uuid4().hex[:12]

        # Upgrade model tier for this gene
        premium = getattr(self.llm, "premium_model", None)
        if premium and agent.config.model != premium:
            agent.config.model = premium
            console.print(
                f"  [bold yellow]⬆ Model upgrade:[/bold yellow] "
                f"{agent.config.role.value} [dim]{agent.id}[/dim] → {premium}"
            )

        self.memory.save_to_gene_pool(
            gene_id=gene_id,
            role=agent.config.role.value,
            system_prompt=agent.config.system_prompt,
            temperature=agent.config.temperature,
            avg_score=agent.avg_score,
            parent_gene_id=agent.config.parent_gene_id,
            model=agent.config.model,
        )

        # Update bloodline score
        if self.bloodline and agent.config.gene_id:
            self.bloodline.update_score(agent.config.gene_id, agent.avg_score)

        console.print(
            f"  [yellow]★ Promoted[/yellow] {agent.config.role.value} agent "
            f"[dim]{agent.id}[/dim] to gene pool (score={agent.avg_score:.2f})"
        )

    def get_best_config(self, role: AgentRole) -> AgentConfig | None:
        """Get the best config for a role — tries breeding first, falls back to gene pool."""
        # Try breeding from bloodline (needs 2+ parents)
        if self.bloodline:
            bred = self.bloodline.breed_from_pool(role)
            if bred:
                return bred

        # Fallback: single-parent mutation from gene pool
        genes = self.memory.get_best_genes(role.value, limit=1)
        if not genes:
            return None

        best = genes[0]
        config = AgentConfig(
            role=role,
            system_prompt=best["system_prompt"],
            temperature=best["temperature"],
            gene_id=best["gene_id"],
            model=best.get("model"),  # inherit model tier from gene
        )
        return config.mutate("inherited from gene pool")

    def get_alive_agents(self) -> list[AgentState]:
        return [a for a in self.agents.values() if a.alive]

    def print_agent_tree(self) -> None:
        """Print a tree visualization of all agents and their parent-child relationships."""
        roots = [a for a in self.agents.values() if a.parent_agent_id is None]
        if not roots:
            console.print("[dim]No agents spawned yet.[/dim]")
            return

        tree = Tree("[bold]Agent Swarm[/bold]")
        for root in roots:
            self._add_to_tree(tree, root)
        console.print(tree)

    def _add_to_tree(self, parent_tree: Tree, agent: AgentState) -> None:
        status = "[green]●[/green]" if agent.alive else "[red]●[/red]"
        score_str = f"{agent.avg_score:.2f}" if agent.scores else "—"
        label = (
            f"{status} {agent.config.role.value} [dim]{agent.id}[/dim] "
            f"score={score_str} budget={agent.budget:.0f}"
        )
        branch = parent_tree.add(label)

        # Find children
        children = [a for a in self.agents.values() if a.parent_agent_id == agent.id]
        for child in children:
            self._add_to_tree(branch, child)
