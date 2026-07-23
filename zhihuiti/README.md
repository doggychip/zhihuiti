# 智慧体 zhihuiti

Autonomous multi-agent orchestration system inspired by 如老师's governance architecture.

Agents compete, collaborate, evolve, and self-govern through an internal token economy. Goals are decomposed into dependency-aware subtasks, auctioned to the best agents, executed in parallel waves, and scored through 3-layer inspection.

## Quick Start

```bash
# Requires Python 3.9+ and Ollama running locally
ollama serve &
ollama pull llama3

pip install -e .

# Single goal
zhihuiti run "research the top 3 programming languages and their use cases"

# Interactive REPL
zhihuiti repl
```

### Cloud LLM (OpenRouter)

```bash
export OPENROUTER_API_KEY=sk-or-...
zhihuiti run "analyze market trends for renewable energy"
```

## Architecture

```
Goal → Orchestrator → DAG Decomposition → Parallel Waves
                           ↓
            ┌──────────────┼──────────────┐
         Wave 0         Wave 1         Wave 2
        (parallel)     (parallel)     (parallel)
            ↓              ↓              ↓
         Auction        Auction        Auction
            ↓              ↓              ↓
       Execute Task   Execute Task   Execute Task
            ↓              ↓              ↓
       3-Layer Score  3-Layer Score  3-Layer Score
            ↓              ↓              ↓
       Reward / Cull  Reward / Cull  Reward / Cull
```

### 26 Subsystems

| Layer | Systems |
|-------|---------|
| **Core** | Agents, Memory (SQLite), LLM (Ollama/OpenRouter), Orchestrator |
| **Economy** | Central Bank, Treasury, Tax Bureau (15%), Reward Engine |
| **Competition** | Bidding/Auctions (竞标), Trading Market, Futures/Staking |
| **Evolution** | Gene Pool, Bloodline (7-gen tracing), Breeding/Mutation, Per-agent Model Selection |
| **Safety** | 3-layer Inspection (三层安检), Circuit Breaker (熔断), Behavioral Detection |
| **Social** | 8-type Relationship Graph (如老师's model), Lending, Arbitration, Agent-to-Agent Messaging |
| **Execution** | Factory (血汗工厂), Three Realms (三界), DAG Dependencies, Parallel Waves, Retry |
| **Persistence** | Persistent Agent Pool, Cross-goal Memory, Web Dashboard |

### Three Realms (三界)

- **研发界 Research** — R&D agents (researcher, analyst, coder)
- **执行界 Execution** — task execution agents (trader, custom)
- **中枢界 Central** — governance agents (orchestrator, judge)

### Token Economy

Agents operate in a closed economy with minted tokens:
- **Central Bank** mints initial supply (10,000 tokens) and manages inflation/deflation
- **Treasury** funds agent spawning and pays rewards
- **Tax Bureau** collects 15% flat tax on all earnings
- **Reward Engine** pays agents based on score (non-linear: high scores disproportionately rewarded)
- Agents that go bankrupt are culled; remaining tokens are burned

### Bidding System (竞标)

Tasks are posted as auctions. Agents bid based on confidence and budget. Lowest qualified bid wins — this drives cost efficiency while maintaining quality through post-hoc scoring.

### Gene Pool & Evolution

- High-scoring agents (avg >= 0.8) are **promoted** to the gene pool with a model upgrade
- New agents are **bred** from two high-scoring parents (crossover + mutation)
- Lineage is tracked up to 7 generations (诛七族 — purge a gene and all descendants)
- Promoted agents inherit the **premium model** (e.g., llama3 → llama3.1, sonnet → opus)

### DAG Execution

The orchestrator decomposes goals into subtasks with explicit dependencies:
```
research → analyze → report
              ↘ visualize ↗
```
Independent tasks run in parallel within waves. Dependent tasks receive prior outputs as context.

### Agent Messaging

Agents broadcast findings after completing tasks. Subsequent agents in the same goal pick up these messages as context — enabling collaboration beyond explicit DAG edges.

### Cross-goal Memory

Completed goals are saved to history. When a similar goal is run later, prior results are injected as context for decomposition, helping the system learn from experience.

## CLI

```bash
zhihuiti run GOAL [OPTIONS]     # Execute a single goal
zhihuiti repl [OPTIONS]         # Interactive mode
zhihuiti stats                  # Memory statistics
zhihuiti economy                # Economy report
zhihuiti auctions               # Auction history
zhihuiti bloodline              # Lineage stats
zhihuiti ancestry GENE_ID       # Trace 7-gen ancestry
zhihuiti purge GENE_ID          # 诛七族 — purge gene + descendants
zhihuiti realms                 # Three Realms status
zhihuiti inspection             # 3-layer inspection stats
zhihuiti dashboard              # Launch web dashboard
zhihuiti polymarket watch       # Paper-copy configured leader wallets
zhihuiti polymarket status      # Show virtual portfolio and audit counts
zhihuiti polymarket replay FILE # Deterministically replay a JSON fixture
```

### Polymarket paper copy trader

This subsystem is deterministic and isolated from the orchestrator, agents,
AlphaArena, and all model calls. It uses only Polymarket's public Data and CLOB
APIs. It has no private-key, authentication, or live-order configuration.

Set `POLYMARKET_LEADER_WALLETS` to comma-separated proxy wallet addresses, then:

```bash
export POLYMARKET_LEADER_WALLETS=0x0123456789abcdef0123456789abcdef01234567
export POLYMARKET_DB=polymarket-paper.db
zhihuiti polymarket watch --copy-ratio 0.10 --slippage 0.03
zhihuiti polymarket status
```

CLI flags override the `POLYMARKET_*` settings documented in `.env.example`.
Each source observation, acceptance or rejection, book snapshot fill, fee,
cash movement, position, cursor, and settlement is persisted in the dedicated
SQLite ledger. `replay` consumes a recorded object with `trades`, `books`, and
`markets` maps and performs no network requests.

Paper results have important limitations:

- The public trade feed has second-level timestamps and no fill/log ID. The
  copier overlaps polling windows and fingerprints observations, but truly
  identical same-second trades are only distinguishable by occurrence order.
- The follower sees a current book after polling plus configured simulated
  latency. It cannot reconstruct the historical depth or reproduce the
  leader's reported fill price.
- Public books expose aggregated depth, not queue priority. The simulator
  assumes an immediate taker, sorts levels itself, applies the current public
  fee schedule, and records conservative partial fills within the slippage cap.
- API indexing lag, polling latency, closed books, and later market resolution
  can all differ from live execution. This is an auditable simulation, not a
  profitability claim or an order-routing system.

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--db` | `zhihuiti.db` | SQLite database path |
| `--model` | `llama3` | LLM model name |
| `--workers` | `4` | Max parallel workers per wave |
| `--premium-model` | `llama3.1` | Premium model for promoted agents |
| `--retries` | `1` | Retry failed tasks (0 = no retries) |

### REPL Commands

`stats`, `genes`, `economy`, `auctions`, `pool`, `bloodline`, `ancestry <id>`, `purge <id>`, `realms`, `realm <name>`, `inspection`, `fuse`, `laws`, `behavior`, `relations`, `loans`, `market`, `futures`, `arbitration`, `factory`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | Use OpenRouter cloud LLM (absence = Ollama) |
| `OLLAMA_HOST` | Ollama URL (default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | Default Ollama model (default: `llama3`) |
| `LLM_MODEL` | Override model for any backend |
| `LLM_PREMIUM_MODEL` | Premium model for promoted agents |

## Web Dashboard

```bash
zhihuiti dashboard --port 8377
```

Dark-themed single-page dashboard showing all 18 system cards with 10-second auto-refresh. Also serves JSON at `/api/data`.

## K-Dense BYOK Integration

zhihuiti can serve as a multi-agent backend for [K-Dense BYOK](https://github.com/K-Dense-AI/k-dense-byok), letting Kady delegate complex tasks to zhihuiti's agent swarm.

### Option 1: MCP Toolset (recommended)

Add to `kady_agent/mcps.py` in your k-dense-byok project:

```python
from kady_bridge import zhihuiti_mcp
all_mcps.append(zhihuiti_mcp)
```

This starts zhihuiti as a subprocess MCP server. Kady gets 4 tools: `zhihuiti_execute_goal`, `zhihuiti_execute_task`, `zhihuiti_list_agents`, `zhihuiti_system_status`.

### Option 2: HTTP API

```bash
# Start the API server
zhihuiti serve --port 8377

# Submit goals
curl -X POST http://localhost:8377/api/goals -H 'Content-Type: application/json' \
  -d '{"goal": "research the top 3 programming languages"}'

# Poll results
curl http://localhost:8377/api/goals/<id>

# List agents
curl http://localhost:8377/api/agents
```

### Option 3: Direct function tool

```python
from kady_bridge import delegate_to_zhihuiti
result = delegate_to_zhihuiti("analyze market trends for renewable energy")
```

### Setup

1. `pip install -e /path/to/zhihuiti`
2. Copy `kady_bridge.py` into your k-dense-byok project
3. Set `OPENROUTER_API_KEY` (shared between both systems)

## Tests

```bash
pip install pytest
python -m pytest -q          # 353 tests, ~8s
```

All tests use in-memory SQLite and stub LLMs — no network or API keys required.

## License

MIT
