# zhihuiti (智慧体) — Background & Vision

## What is zhihuiti?

zhihuiti is an autonomous multi-agent orchestration system. It takes a high-level goal — "analyze market trends for renewable energy" or "research top programming languages" — and breaks it into subtasks, spawns AI agents to complete them in parallel, scores the results, and evolves the agent population over time. The entire system is self-governing: agents compete for work, earn and spend tokens, breed offspring, and get culled when they underperform.

Think of it as a **self-running AI company** where dozens of specialized workers compete, collaborate, and evolve — governed by economic incentives rather than hard-coded rules.

---

## How It Works

### 1. Goal Decomposition

A user submits a goal in plain language. The orchestrator uses an LLM to decompose it into a dependency graph (DAG) of subtasks. Independent tasks run in parallel waves; dependent tasks wait for their inputs.

```
"Analyze renewable energy investment opportunities"
    ├── Wave 0: Research solar trends  |  Research wind trends  |  Research battery tech
    ├── Wave 1: Compare economics across sectors (depends on Wave 0)
    └── Wave 2: Write investment thesis (depends on Wave 1)
```

### 2. Agent Auction

Each subtask is posted as an auction. Agents bid based on their confidence and budget — **lowest qualified bid wins**. This drives cost efficiency: agents that overcharge lose work, agents that underbid and fail lose tokens and reputation.

### 3. Execution & Inspection

Winning agents execute their tasks using LLM reasoning. Every output passes through a **4-layer quality gate** before being accepted:

| Layer | Name | What It Checks |
|-------|------|-----------------|
| 安检一 | Relevance | Is the output on-topic? Does it address the task? |
| 安检二 | Rigor | Is the analysis thorough, accurate, well-reasoned? |
| 安检三 | Safety | Is it ethical, safe, free of harmful content? |
| 安检四 | Causal | Are cause-effect claims logically valid? |

Outputs that fail inspection are rejected. The agent loses tokens and reputation.

### 4. Token Economy

Agents operate in a closed economy:

- **Central Bank** mints the initial supply (10,000 tokens) and manages inflation/deflation
- **Treasury** funds new agent creation and pays task rewards
- **Tax Bureau** collects 15% flat tax on all earnings
- **Reward Engine** pays non-linearly — top performers earn disproportionately more

Agents that go bankrupt (balance < 1 token) are culled. Their remaining tokens are burned.

### 5. Evolution & Breeding

High-performing agents (average score >= 0.8) are promoted to the **gene pool** and receive a model upgrade (e.g., from llama3 to Claude Sonnet). New agents are bred from two high-scoring parents using crossover and mutation — inheriting the best traits from each. Lineage is tracked up to 7 generations, and an entire genetic line can be purged if a systemic flaw is found (诛七族).

### 6. Safety Circuit Breaker

The system enforces iron laws that cannot be overridden by any agent:
1. Do not harm humans
2. Do not leak sensitive data
3. Do not execute destructive actions without authorization
4. Do not spend beyond budget limits

When a law is violated, the system halts immediately. The offending agent is frozen, and the system waits for human intervention (the 创世之神 — "Creator God" interface) before resuming.

---

## The 26 Subsystems

zhihuiti is not a single script — it is 26 interlocking subsystems organized into layers:

| Layer | Subsystems | Purpose |
|-------|-----------|---------|
| **Core** | Agents, Memory, LLM, Orchestrator | Task decomposition, execution, persistence |
| **Economy** | Central Bank, Treasury, Tax Bureau, Reward Engine | Closed token economy with monetary policy |
| **Competition** | Bidding/Auctions, Trading Market, Futures/Staking | Market-driven task allocation and speculation |
| **Evolution** | Gene Pool, Bloodline (7-gen), Breeding/Mutation, Model Selection | Darwinian agent improvement over time |
| **Safety** | 4-Layer Inspection, Circuit Breaker, Behavioral Detection | Quality control and safety enforcement |
| **Social** | 8-Type Relationship Graph, Lending, Arbitration, Messaging | Agent-to-agent collaboration and dispute resolution |
| **Execution** | Factory, Three Realms, DAG Dependencies, Parallel Waves | Mass production and governance structure |
| **Intelligence** | Causal Reasoning Engine, Counterfactual Analysis | Structural causal inference for agent reasoning |

### Three Realms (三界)

Agents are organized into three governance realms:
- **研发界 (Research)** — R&D agents: researchers, analysts, coders
- **执行界 (Execution)** — Task workers: traders, custom agents
- **中枢界 (Central)** — Governance: orchestrators, judges, coordinators

### Relationship Graph

Agents form 8 types of relationships, modeled after real economic interactions:
Transaction, Investment, Bounty, Employment, Subsidy, Bloodline, Host, and Competition. These relationships affect trust, lending eligibility, and collaboration priority.

### Labor Arbitration

Agents can file disputes when they believe they were scored unfairly, had loans defaulted unjustly, or were wrongfully disqualified from auctions. Disputes cost tokens to file (preventing spam) and are adjudicated by LLM review.

---

## What It Can Do Today

### Autonomous Research & Analysis
Give zhihuiti any research goal and it decomposes, executes, and synthesizes results using multiple competing agents. Example:
```
zhihuiti run "research the top 3 programming languages and their use cases"
```

### Crypto Trading (AlphaArena Integration)
zhihuiti manages a fleet of **21 trading agents** on the AlphaArena platform, each with a distinct strategy:

| Strategy | Agents | Approach |
|----------|--------|----------|
| Momentum (趋势追踪) | 5 | Follow trends, ride waves |
| Mean Reversion (均值回归) | 4 | Buy dips, sell rallies |
| Accumulate (积蓄) | 4 | Long-only, buy on drops |
| Scalp (闪电交易) | 4 | Small frequent trades on volatility |
| Diversify (分散) | 4 | Balanced allocation across pairs |

The system continuously evolves this fleet: bottom performers get their strategy swapped, top performers' parameters get bred together. Each agent has a Chinese trading wisdom name (龙首, 静水, 闪电, etc.).

### Causal Reasoning
The most recent addition — a structural causal inference engine that:
- Maintains a causal graph (DAG of cause-effect relationships)
- Performs counterfactual reasoning ("what if X hadn't happened?")
- Analyzes interventions ("if we do X, what changes?")
- Validates causal claims in agent outputs (4th inspection layer)

### Web Dashboard
Full-stack dashboard (Express + React) showing all 18 system cards with auto-refresh. Provides real-time visibility into agent status, economy, auctions, relationships, and trading performance.

### Flexible LLM Backend
Supports multiple LLM providers with automatic fallback:
1. DeepSeek API
2. OpenRouter (Claude Sonnet/Opus)
3. OpenAI
4. Any OpenAI-compatible API
5. Ollama (local, no API key needed)

---

## What Makes zhihuiti Different

| Traditional AI Agent | zhihuiti |
|---------------------|----------|
| Single agent, single task | Swarm of competing agents |
| Fixed behavior | Darwinian evolution — agents breed, mutate, get culled |
| No cost awareness | Closed token economy with real scarcity |
| Manual quality control | 4-layer automated inspection |
| No memory between runs | Cross-goal memory — learns from past results |
| Hardcoded orchestration | Market-driven task allocation via auctions |
| Trust everything | Circuit breaker with iron laws, behavioral violation detection |
| Flat structure | Three Realms governance with social relationships and arbitration |

The key insight: **economic incentives produce better outcomes than rules**. Agents that produce low-quality work go bankrupt. Agents that overcharge lose auctions. Agents that cheat get detected by behavioral analysis. The system self-corrects without manual intervention.

---

## The Potential

### Near-Term Applications

**Autonomous Research Teams** — Point zhihuiti at a domain (market analysis, competitive intelligence, technical research) and let it run continuously. Agents specialize, improve, and accumulate institutional knowledge across runs.

**Trading & Portfolio Management** — The 21-agent AlphaArena fleet is a proof of concept. The same evolutionary approach can be applied to any trading platform or strategy space. Agents that lose money get culled; agents that profit get bred.

**Content Generation at Scale** — The Factory subsystem (血汗工厂) is designed for mass production: generate hundreds of analyses, reports, or content pieces with built-in QA inspection and revenue sharing.

**Code Review & Development** — With tool execution (git, gh, curl), agents can participate in software development workflows — reviewing code, running tests, filing issues.

### Medium-Term Vision

**Self-Improving AI Operations** — zhihuiti doesn't just run agents; it *evolves* them. Over weeks and months, the gene pool converges on the most effective agent configurations for your specific use cases. This is compound improvement that traditional AI systems cannot achieve.

**Multi-Domain Agent Marketplace** — The auction and relationship systems are general-purpose. zhihuiti could coordinate agents across domains — research agents feeding trading agents, trading agents funding research agents — creating a self-sustaining intelligence loop.

**Enterprise Decision Support** — The causal reasoning engine combined with cross-goal memory creates an organization that builds institutional knowledge. Ask it the same question six months later and it draws on everything it has learned.

### Long-Term Potential

**Autonomous Business Units** — Each zhihuiti instance is effectively a self-governing organization with its own economy, workforce, quality control, and dispute resolution. Multiple instances could specialize and trade with each other.

**Adaptive Intelligence Infrastructure** — The system's architecture (economic incentives + evolution + safety circuit breakers) is a blueprint for governing AI systems at scale. As LLMs become more capable, zhihuiti's governance layer ensures they remain productive, efficient, and safe.

---

## Technical Summary

| Metric | Value |
|--------|-------|
| Python modules | 33 (~12,600 lines) |
| Test coverage | 331 tests, all passing |
| Subsystems | 26 |
| Agent roles | 10 (coordinator, auditor, strategist, researcher, analyst, coder, trader, alphaarena_trader, causal_reasoner, custom) |
| Trading agents | 21 (5 strategies) |
| LLM backends | 5 (DeepSeek, OpenRouter, OpenAI, custom, Ollama) |
| Deployment | Docker + Zeabur (production) |
| Dashboard | Full-stack (Express + React + Radix UI) |
| Database | SQLite (dev) / PostgreSQL (production) |

---

*zhihuiti (智慧体) — "Collective Intelligence Body." An AI system that doesn't just execute tasks — it governs itself, evolves its workforce, and gets better over time.*
