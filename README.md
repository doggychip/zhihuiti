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

## Human-approved video workflows

`zhihuiti.video_factory.VideoFactory` provides a durable state machine for agent-assisted video production. It enforces sequential production stages, explicit human gates, claim/asset/compliance/QC artifacts, and SHA-256 approval binding so a changed render or script cannot reuse an old approval. See the [Macro Alpha–style blueprint](docs/macro-alpha-agent-video-blueprint.md) for the full operating model.

```bash
zhihuiti video create rates-explained "Why rates stayed higher"
zhihuiti video advance 2026-08-15-rates-explained pitched --actor scout-1
zhihuiti video status 2026-08-15-rates-explained
# After verified artifacts and QC exist:
zhihuiti video approve-release 2026-08-15-rates-explained --reviewer ryan
```

Image batches are resumable and cost-free by default. First plan the batch,
then generate a small approval set before authorizing the full manifest:

```bash
zhihuiti video images episodes/ep001_v4/shots.json --output episodes/ep001_v4/images
export OPENAI_API_KEY=sk-...
zhihuiti video images episodes/ep001_v4/shots.json --output episodes/ep001_v4/images --limit 3 --execute
# After visual approval, rerun without --limit; the first three files are skipped.
zhihuiti video images episodes/ep001_v4/shots.json --output episodes/ep001_v4/images --execute
```

The generator fails closed when another process holds the output lock, when it
finds an iCloud/Finder conflict copy such as `shot_001 2.png`, or when an
existing file is an unreadable cloud placeholder rather than valid image
bytes. Resolve those files manually or choose a new authoritative output
directory; the command never guesses which agent's image should win.

Inspect one existing folder or run a non-billing pass across the whole episode
root:

```bash
zhihuiti video doctor /path/to/episodes/ep001_v4
zhihuiti video daily /path/to/episodes
# Only after the report is correct and OPENAI_API_KEY is available:
zhihuiti video daily /path/to/episodes --execute-images
```

### Daily automation on macOS

Use the operating-system scheduler rather than leaving a chat session open.
First run the exact command manually. Then save the following as
`~/Library/LaunchAgents/com.zhihuiti.video-daily.plist`, replacing the three
absolute paths. Keep the API key in the working directory's `.env` file with
owner-only permissions (`chmod 600 .env`); do not put it in the plist.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.zhihuiti.video-daily</string>
  <key>ProgramArguments</key><array>
    <string>/ABSOLUTE/PATH/TO/zhihuiti</string>
    <string>video</string><string>daily</string>
    <string>/ABSOLUTE/PATH/TO/episodes</string>
    <string>--execute-images</string>
  </array>
  <key>WorkingDirectory</key><string>/ABSOLUTE/PATH/TO/project</string>
  <key>StartCalendarInterval</key><dict>
    <key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key><string>/tmp/zhihuiti-video.log</string>
  <key>StandardErrorPath</key><string>/tmp/zhihuiti-video-error.log</string>
</dict></plist>
```

```bash
plutil -lint ~/Library/LaunchAgents/com.zhihuiti.video-daily.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.zhihuiti.video-daily.plist
launchctl kickstart -k gui/$(id -u)/com.zhihuiti.video-daily
tail -f /tmp/zhihuiti-video.log /tmp/zhihuiti-video-error.log
```

The daily command currently automates episode discovery, retirement filtering,
image planning/generation, resumption, collision protection, and render-readiness
reporting. Narration and final rendering remain external commands until their
contracts are added to this repository; release approval and publication remain
intentional human gates.

The prioritized implementation sequence for closing that gap is documented in
[Video factory: next build plan](docs/video-factory-next-build.md). The next
vertical slice is an idempotent `video assemble` command built around the real
narration, exposure, caption, and render contracts—not another speculative
episode schema.

Create the canonical multi-agent ownership and dependency plan for an existing
episode with:

```bash
zhihuiti video architect /path/to/episodes/ep001_v4
```

This writes `agent-plan.json` with specialized creative agents, deterministic
production workers, two explicit human gates, parallel execution waves, paid
task markers, and single-writer artifact contracts. It is an auditable plan;
it does not claim an artifact is complete merely because an agent returned
text, and it never grants publishing authority to a research or writing agent.

Evaluate the ready execution wave without making changes:

```bash
zhihuiti video run-plan /path/to/episodes/ep001_v4/agent-plan.json
```

The resumable executor validates existing outputs, hashes completed artifacts,
enforces dependencies, paid-task budgets, and explicit human gates, and writes
`agent-run.json`. `--execute` only runs task handlers that have been registered;
unimplemented narration/render integrations fail as `handler_required` rather
than being reported as successful.

Run the configured multi-model team with explicit model IDs:

```bash
export OPENROUTER_API_KEY=...
export VIDEO_CLAUDE_MODEL=anthropic/your-approved-claude-model
export VIDEO_GEMINI_MODEL=google/your-approved-gemini-model
export OPENAI_API_KEY=...                  # needed only for the image worker
export VIDEO_IMAGE_MODEL=your-approved-openai-image-model

zhihuiti video run-plan /path/to/episode/agent-plan.json \
  --execute --multi-model-team --workers 4 --paid-budget 1
```

The router assigns primary-source discovery and analysis to Gemini, editorial
architecture/counter-thesis/script/verification/scene planning to Claude, and
manifest image generation to the OpenAI-compatible image worker. Exposure,
captions, FFmpeg rendering, and QC remain deterministic handler slots and stop
as `handler_required` until the real local commands are registered. Model IDs
are configuration, not hard-coded aliases, so an upstream model change cannot
silently alter production behavior.

### Use the video factory from Claude

Claude Desktop can use the safe planning and inspection surface through the
existing local MCP server. Add a local server entry to Claude Desktop's MCP
configuration, replacing both absolute paths:

```json
{
  "mcpServers": {
    "zhihuiti-video": {
      "command": "/ABSOLUTE/PATH/TO/python",
      "args": ["-m", "zhihuiti.mcp_server"],
      "env": {
        "PYTHONPATH": "/ABSOLUTE/PATH/TO/zhihuiti/zhihuiti"
      }
    }
  }
}
```

Restart Claude Desktop after saving the configuration. Claude will see four
video tools: architect an episode, inspect one episode, plan the daily sweep,
and inspect plan readiness. These MCP tools deliberately cannot spend image
credits, approve a human gate, execute production handlers, upload, or publish.
Keep paid execution and approval in the CLI until a narrower authenticated MCP
permission layer is implemented.

Example requests to Claude:

```text
Inspect /Users/rcheung/.../王利杰/ep001_v4 and list every render blocker.
Create the multi-agent plan for /Users/rcheung/.../王利杰/ep002.
Run a cost-free daily readiness plan across /Users/rcheung/.../王利杰.
Show which tasks are ready or human-gated in ep001_v4/agent-plan.json.
```

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
```

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
