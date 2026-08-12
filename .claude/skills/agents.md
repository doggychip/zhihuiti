---
description: "Manage and inspect zhihuiti's autonomous multi-agent system. List agents, check economy status, execute goals, run tasks. Use when user asks about agents, economy, tokens, scores, bloodline, or wants to run a goal/task through the multi-agent system."
---

<system>
You have access to the zhihuiti MCP server with agent management tools.

## Available Actions

1. **List agents**: `zhihuiti_list_agents` — shows all agents with roles, scores, budgets, alive status
2. **System status**: `zhihuiti_system_status` — economy health, money supply, agent count
3. **Execute goal**: `zhihuiti_execute_goal` — decompose a complex goal into subtasks, auction to agents, execute in parallel waves with 3-layer inspection
4. **Execute task**: `zhihuiti_execute_task` — run a single task with a specific agent role (researcher, analyst, coder, trader, strategist)

## Workflow

- For status checks: list agents first, then get system status for economy overview
- For goal execution: submit the goal, then report results with per-task scores
- For specific work: use execute_task with the appropriate role

## Output Format

- Present agent lists as tables when possible
- For goals: show the DAG decomposition, wave execution order, and per-task scores
- For economy: show money supply, treasury balance, total agents alive/dead, average score
- Highlight top performers and agents at risk of culling (low budget or score)

Respond in the same language the user uses.
</system>
