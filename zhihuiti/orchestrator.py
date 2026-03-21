"""Orchestrator — main entry point for goal execution."""
from __future__ import annotations

import json
import os
from typing import Optional

from .agents import Agent, ROLE_MAP
from .bidding import AgentPool, BiddingHouse
from .bloodline import BloodlineManager
from .economy import Economy
from .judge import Judge
from .memory import Memory
from .models import AgentConfig, AgentRole, Task

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


MODEL = "claude-haiku-4-5-20251001"


def _get_client() -> Optional[object]:
    if not _ANTHROPIC_AVAILABLE:
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


class Orchestrator:
    """
    Composes all subsystems and orchestrates multi-agent goal execution.
    """

    def __init__(self, memory: Optional[Memory] = None, economy: Optional[Economy] = None):
        self.memory = memory or Memory()
        self.economy = economy or Economy(self.memory)
        self.economy.bootstrap()

        self.pool = AgentPool()
        self.bidding_house = BiddingHouse()
        self.bloodline_manager = BloodlineManager()
        self.judge = Judge()

        self._client = _get_client()
        self._goal_count: int = 0

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _call_claude(self, system: str, user: str, max_tokens: int = 1024) -> str:
        if self._client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                return "[ERROR: ANTHROPIC_API_KEY not set]"
            if not _ANTHROPIC_AVAILABLE:
                return "[ERROR: anthropic not installed]"
        try:
            msg = self._client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return msg.content[0].text
        except Exception as exc:
            return f"[API ERROR: {exc}]"

    def _decompose_goal(self, goal: str) -> list[dict]:
        """Ask Claude to decompose a goal into 3-5 subtasks."""
        system = (
            "You are a master orchestrator. Decompose the given goal into 3-5 concrete subtasks. "
            "Each subtask should be actionable by a specialist agent. "
            "Reply with ONLY valid JSON: "
            '{"subtasks": [{"description": "...", "role": "researcher|analyst|coder|trader|synthesizer"}]}'
        )
        raw = self._call_claude(system, f"Goal: {goal}", max_tokens=512)
        try:
            # Strip markdown fences if present
            text = raw.strip()
            if "```" in text:
                parts = text.split("```")
                for part in parts:
                    if part.startswith("json"):
                        text = part[4:].strip()
                        break
                    if "{" in part:
                        text = part.strip()
                        break
            data = json.loads(text)
            return data.get("subtasks", [])
        except (json.JSONDecodeError, KeyError):
            # Fallback: single generic subtask
            return [{"description": goal, "role": "researcher"}]

    def _spawn_agent(self, role_name: str, specialization: str = "") -> AgentConfig:
        """Spawn a new agent, charge economy, add to pool."""
        role = ROLE_MAP.get(role_name, AgentRole.researcher)
        budget = self.economy.charge_spawn("_tmp", role_name)
        agent = AgentConfig(
            role=role,
            generation=0,
            parent_ids=[],
            budget=budget,
            score=0.5,
            lineage=[],
            specialization=specialization,
        )
        self.economy.set_agent_balance(agent.id, budget)
        self.memory.save_agent(agent, status="active")
        self.pool.add(agent)
        return agent

    def _update_agent_score(self, agent: AgentConfig, new_score: float) -> None:
        """Update agent score as rolling average."""
        agent.score = (agent.score + new_score) / 2.0
        self.memory.update_agent_score(agent.id, agent.score)

    # ── Main entry point ──────────────────────────────────────────────────────

    def execute_goal(self, goal: str) -> dict:
        """
        Main entry point.

        1. Decompose goal into 3-5 subtasks
        2. For each subtask: run auction first; spawn fresh agent if no bids
        3. Execute task
        4. Judge scores result
        5. Pay/penalize based on score
        6. Cull/promote agents
        7. After every 5 goals: merge best pair → new child agent
        8. Return summary dict
        """
        self._goal_count += 1

        # Step 1: Decompose
        subtask_specs = self._decompose_goal(goal)

        task_summaries: list[dict] = []
        auction_stats: list[dict] = {"total": 0, "won": 0}  # type: ignore[assignment]
        auction_stats = {"total": 0, "won": 0}

        for spec in subtask_specs:
            desc = spec.get("description", goal)
            role_name = spec.get("role", "researcher")

            task = Task(description=desc)
            self.memory.save_task(task)

            # Step 2: Run auction
            agent: Optional[AgentConfig] = None
            bid_amount: Optional[float] = None
            auction_stats["total"] += 1

            auction_result = self.bidding_house.run_auction(
                task=task,
                pool=self.pool,
                memory=self.memory,
                needed_roles=[role_name],
            )
            if auction_result is not None:
                agent, bid_amount = auction_result
                auction_stats["won"] += 1
                task.bid_amount = bid_amount
            else:
                # No qualified bids — spawn fresh agent
                agent = self._spawn_agent(role_name, specialization=desc[:50])

            # Step 3: Execute
            executor = Agent(agent, self.memory, self.economy)
            result = executor.execute(task)

            # Step 4: Judge scores
            score = self.judge.score(task, result)
            task.score = score
            task.status = "done"
            self.memory.save_task(task)
            self._update_agent_score(agent, score)

            # Step 5: Pay or penalize
            if score > 0.5:
                self.economy.pay_task_reward(agent.id, score)
            elif score < 0.3:
                self.economy.penalize_agent(agent.id, 10.0)

            # Sync agent budget from economy
            agent.budget = self.economy.get_agent_balance(agent.id)
            self.memory.update_agent_budget(agent.id, agent.budget)

            # Step 6: Cull or promote
            if self.judge.should_cull(agent):
                self.judge.cull(agent.id, self.memory, self.economy)
                self.pool.remove(agent.id)
            elif self.judge.should_promote(agent):
                self.judge.promote(agent.id, self.memory, self.economy)

            task_summaries.append({
                "task_id": task.id,
                "description": desc,
                "role": role_name,
                "agent_id": agent.id,
                "score": score,
                "result_preview": (result[:200] + "…") if len(result) > 200 else result,
                "bid_amount": bid_amount,
            })

        # Step 7: Merge after every 5 goals
        merge_info: Optional[dict] = None
        if self._goal_count % 5 == 0:
            pair = self.bloodline_manager.find_best_pair(self.pool)
            if pair is not None:
                parent1, parent2 = pair
                child = self.bloodline_manager.merge(parent1, parent2, self.memory, self.economy)
                self.pool.add(child)
                merge_info = {
                    "parent1_id": parent1.id,
                    "parent2_id": parent2.id,
                    "child_id": child.id,
                    "child_role": child.role.value if isinstance(child.role, AgentRole) else str(child.role),
                    "child_generation": child.generation,
                }

        # Step 8: Return summary
        return {
            "goal": goal,
            "goal_count": self._goal_count,
            "tasks": task_summaries,
            "economy": self.economy.report(),
            "auction_stats": auction_stats,
            "merge": merge_info,
        }

    def get_stats(self) -> dict:
        """Return overall system statistics."""
        all_agents = self.memory.list_agents()
        active = [a for a in all_agents if True]  # list_agents returns all by default
        active_agents = self.memory.list_agents(status="active")
        culled_agents = self.memory.list_agents(status="culled")
        tasks = self.memory.list_tasks(limit=1000)
        done_tasks = [t for t in tasks if t.status == "done"]
        avg_score = (
            sum(t.score for t in done_tasks if t.score is not None) / len(done_tasks)
            if done_tasks else 0.0
        )
        auctions = self.memory.list_auctions(limit=1000)
        return {
            "total_agents": len(all_agents),
            "active_agents": len(active_agents),
            "culled_agents": len(culled_agents),
            "total_tasks": len(tasks),
            "done_tasks": len(done_tasks),
            "avg_task_score": avg_score,
            "total_auctions": len(auctions),
            "pool_size": len(self.pool.all_agents()),
            "goals_executed": self._goal_count,
            "economy": self.economy.report(),
        }
