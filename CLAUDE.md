# CLAUDE.md — Anvil (铁砧)

## What Is This

A production-grade agentic CLI runtime built from scratch in TypeScript. Zero frameworks. One dependency (fast-glob). Agents compete, evolve, and get culled through a token economy — the weak die, the strong breed.

This is the merger of two systems:
1. **Claude Code's architecture** (reverse-engineered and rebuilt): SSE streaming, segmented system prompts with prompt caching, tool permission system, MCP/LSP integration, Agent Teams, Auto Memory
2. **zhihuiti's economic layer** (designed from scratch): token economy, competitive bidding, bloodline inheritance, three-realm governance, behavioral detection, circuit breakers

The result: an agentic CLI where every agent call has a cost, every output gets scored, and evolution is the default — not a feature.

**Owner:** Ryan (@doggychip)
**Language:** TypeScript (Node.js 22+, zero frameworks)
**Dependencies:** fast-glob (the only one)
**Persistence:** better-sqlite3
**LLM:** Anthropic API (direct) + OpenRouter (fallback for HK access) + OpenAI-compatible (Ollama, LM Studio)

---

## Architecture Overview

```
User input
    |
    +-- commands/         Parse /slash commands
    |
    +-- core/             Agent Loop state machine
    |   +-- SSE client (streaming API calls)
    |   +-- System prompt segmentation + cache control
    |   +-- Context window management + auto-compact
    |   +-- Multi-provider LLM router
    |
    +-- tools/            21 built-in tools + MCP dynamic tools
    |   +-- Permission system (3 modes, 2-stage classifier)
    |   +-- Tool execution pipeline (6 phases)
    |   +-- Deferred tool loading (40% token savings)
    |
    +-- economy/          Token economy layer (Phase 2)
    |   +-- Central bank, treasury, tax bureau
    |   +-- Competitive bidding (auction system)
    |   +-- Bloodline inheritance + 7-gen lineage
    |   +-- Three realms (research/execution/nexus)
    |   +-- 3-layer inspection + behavioral detection
    |   +-- Circuit breaker + human oracle
    |
    +-- ui/               Terminal rendering
    |   +-- Streaming text output
    |   +-- Progress indicators
    |   +-- Color themes
    |
    +-- plugins/          Runtime extension system
    |   +-- Manifest-driven directory structure
    |   +-- 6 extension points (skills, agents, hooks, commands, mcp, lsp)
    |
    +-- skills/           Parameterized prompt templates
    |   +-- Built-in: commit, pr, review, init, simplify, loop, schedule
    |   +-- Project-level overrides via .anvil/skills/
    |
    +-- memory/           Cross-session persistence
        +-- YAML frontmatter markdown files
        +-- 4 types: user, feedback, project, reference
        +-- Auto-loaded into system prompt
```

Dependencies are strictly one-directional:
- core/ depends on nothing
- tools/ depends on core/
- economy/ depends on core/ and tools/
- ui/ depends on nothing (core/ calls into ui/, not the reverse)
- plugins/ depends on tools/ and skills/
- skills/ depends on core/
- memory/ depends on nothing (core/ reads from memory/)
- commands/ depends on everything (thin dispatch layer)

---

## Project Structure

```
anvil/
├── CLAUDE.md                       ← YOU ARE HERE
├── package.json
├── tsconfig.json
├── .env                            ← API keys
├── src/
│   ├── index.ts                    ← CLI entrypoint (process.argv → command dispatch)
│   ├── core/
│   │   ├── agent-loop.ts           ← While loop state machine (max 25 iterations)
│   │   ├── sse-client.ts           ← SSE streaming client (native fetch + ReadableStream)
│   │   ├── llm-router.ts           ← Multi-provider: Anthropic, OpenRouter, OpenAI-compat
│   │   ├── system-prompt.ts        ← Segmented prompt builder (static/dynamic blocks)
│   │   ├── context-manager.ts      ← Token counting, auto-compact trigger
│   │   ├── compact.ts              ← Context compression (summary replacement)
│   │   └── types.ts                ← Core type definitions
│   ├── tools/
│   │   ├── registry.ts             ← TOOL_DEFINITIONS array + executeTool dispatcher
│   │   ├── permissions.ts          ← 3-mode permission system + 2-stage classifier
│   │   ├── built-in/
│   │   │   ├── read.ts             ← File read with line numbers, offset/limit paging
│   │   │   ├── write.ts            ← File write with recursive mkdir
│   │   │   ├── edit.ts             ← Precise string replacement (unique match required)
│   │   │   ├── bash.ts             ← Shell exec, 120s timeout, output truncation
│   │   │   ├── grep.ts             ← Self-implemented regex, 3 output modes
│   │   │   ├── glob.ts             ← fast-glob wrapper with gitignore support
│   │   │   ├── web-fetch.ts        ← fetch + HTML strip + truncation
│   │   │   ├── web-search.ts       ← DuckDuckGo search
│   │   │   ├── notebook-read.ts    ← Deferred
│   │   │   ├── notebook-write.ts   ← Deferred
│   │   │   ├── todo-read.ts        ← Deferred
│   │   │   ├── todo-write.ts       ← Deferred
│   │   │   └── tool-search.ts      ← Loads deferred tool schemas on demand
│   │   ├── mcp/
│   │   │   ├── mcp-client.ts       ← JSON-RPC 2.0 over stdio
│   │   │   └── mcp-manager.ts      ← Multi-server lifecycle, namespace isolation
│   │   ├── lsp/
│   │   │   ├── lsp-client.ts       ← LSP protocol client (Content-Length framing)
│   │   │   └── lsp-manager.ts      ← File extension routing, diagnostic injection
│   │   └── agent/
│   │       ├── sub-agent.ts        ← executeSubAgent() — simplified loop, max 15 rounds
│   │       ├── team.ts             ← TeamCreate, SendMessage, TeamDelete
│   │       └── background.ts       ← Promise Map for async agent execution
│   ├── economy/                    ← PHASE 2 — add after core loop works
│   │   ├── central-bank.ts         ← Mint, burn, money supply monitoring
│   │   ├── treasury.ts             ← System reserves, bounty funding
│   │   ├── tax-bureau.ts           ← Realm-specific tax collection
│   │   ├── reward-engine.ts        ← Score-based agent payments
│   │   ├── bidding.ts              ← Competitive auction (lowest qualified bid wins)
│   │   ├── bloodline.ts            ← Multi-parent merge, 7-gen lineage
│   │   ├── realms.ts               ← Research/Execution/Nexus routing + promotion
│   │   ├── inspection.ts           ← 3-layer quality check (accuracy/quality/integrity)
│   │   ├── behavioral.ts           ← Lazy/lying/gaming/collusion detection (free)
│   │   ├── circuit-breaker.ts      ← Safety fuse + human oracle interface
│   │   └── economy-manager.ts      ← Wires all economy modules together
│   ├── ui/
│   │   ├── renderer.ts             ← Streaming text output to terminal
│   │   ├── progress.ts             ← Spinner, progress bars
│   │   ├── colors.ts               ← ANSI color theme
│   │   └── prompt.ts               ← User input handling (readline)
│   ├── plugins/
│   │   ├── loader.ts               ← Scan plugin dirs, parse plugin.json manifests
│   │   ├── hooks.ts                ← Pre/post hook execution
│   │   └── types.ts                ← Plugin manifest schema
│   ├── skills/
│   │   ├── skill-runner.ts         ← Template expansion + context injection
│   │   ├── skill-loader.ts         ← Priority: built-in → plugin → project .anvil/skills/
│   │   └── built-in/
│   │       ├── commit.ts
│   │       ├── pr.ts
│   │       ├── review.ts
│   │       ├── init.ts
│   │       ├── simplify.ts
│   │       ├── loop.ts
│   │       ├── schedule.ts
│   │       └── update-config.ts
│   ├── memory/
│   │   ├── memory-manager.ts       ← Load/save YAML-frontmatter markdown files
│   │   ├── memory-index.ts         ← MEMORY.md index generation
│   │   └── types.ts                ← Memory entry types (user/feedback/project/reference)
│   ├── commands/
│   │   ├── dispatcher.ts           ← /command parsing and routing
│   │   ├── run.ts                  ← Main entry: anvil run "goal"
│   │   ├── status.ts               ← Agent/economy status display
│   │   ├── config.ts               ← Configuration management
│   │   └── chat.ts                 ← Interactive REPL mode
│   └── config/
│       ├── settings.ts             ← Load .anvil/config.json + .env
│       └── defaults.ts             ← Default values for all settings
├── .anvil/                         ← Per-project configuration (gitignored)
│   ├── config.json
│   ├── memory/
│   ├── skills/
│   └── agents/
├── db/
│   └── anvil.db                    ← SQLite: economy state, agent history, memory index
└── tests/
```

---

## Phase 1: Minimum Viable Loop

Get this working first. Everything else builds on top.

### The Loop

```
User types "fix the bug in auth.ts"
    |
    +-- system-prompt.ts assembles block array (static cached + dynamic)
    +-- llm-router.ts picks provider (Anthropic / OpenRouter / custom)
    +-- agent-loop.ts enters while loop (max 25 iterations):
    |
    |   Iteration N:
    |   +-- context-manager.ts checks token usage
    |   |   +-- > 85% capacity? → compact.ts compresses messages
    |   |
    |   +-- Build request: { model, system (blocks), messages, tools }
    |   +-- sse-client.ts sends POST, opens ReadableStream
    |   +-- Parse SSE events in real-time:
    |   |   +-- content_block_delta (type=text_delta) → ui/renderer.ts streams to terminal
    |   |   +-- content_block_delta (type=input_json_delta) → accumulate tool input
    |   |   +-- message_delta → check stop_reason
    |   |
    |   +-- stop_reason == "end_turn"?
    |   |   +-- YES → break loop, show final output
    |   |   +-- NO (stop_reason == "tool_use"):
    |   |       +-- For each tool_use block:
    |   |       |   1. ui: renderToolCall (show what's about to happen)
    |   |       |   2. permissions.ts: check mode + classify
    |   |       |   3. hooks: preHook (plugin intercept point)
    |   |       |   4. checkpoint: snapshot file if destructive
    |   |       |   5. registry.ts: executeTool (dispatch to implementation)
    |   |       |   6. hooks: postHook
    |   |       +-- Build tool_result messages
    |   |       +-- Append to messages array
    |   |       +-- Continue loop
    |
    +-- Done. Show summary (tokens used, tools called, files changed).
```

### Build Order for Phase 1

Build and test each step before moving to the next:

```
Step 1: Types + Config
    src/core/types.ts          ← Message, ToolDefinition, SSEEvent, StopReason types
    src/config/defaults.ts     ← Default settings
    src/config/settings.ts     ← Load .env + config.json

Step 2: LLM Client
    src/core/sse-client.ts     ← POST to API, parse SSE stream, yield events
    src/core/llm-router.ts     ← Provider selection (Anthropic/OpenRouter/OpenAI-compat)
    TEST: send a simple message, get streaming response

Step 3: System Prompt
    src/core/system-prompt.ts  ← Block array builder with cache_control
    TEST: generate system blocks, verify static segments are cached

Step 4: Minimal Tool Set (3 tools only)
    src/tools/registry.ts      ← Tool definitions + dispatcher (start with 3)
    src/tools/built-in/read.ts
    src/tools/built-in/write.ts
    src/tools/built-in/bash.ts
    src/tools/permissions.ts   ← Start with default mode only
    TEST: model can read a file, run a command, write output

Step 5: Agent Loop
    src/core/agent-loop.ts     ← The while loop
    src/core/context-manager.ts ← Token estimation (chars/4)
    TEST: "read package.json and tell me the version" — should work in 2 iterations

Step 6: UI
    src/ui/renderer.ts         ← Stream text to terminal character by character
    src/ui/colors.ts           ← ANSI codes
    src/ui/prompt.ts           ← readline for user input + permission confirmations
    TEST: streaming output looks good, permission prompts work

Step 7: CLI Entry
    src/index.ts               ← Parse argv: anvil run "goal" / anvil chat
    src/commands/run.ts        ← Single-shot mode
    src/commands/chat.ts       ← Interactive REPL
    TEST: $ anvil run "what files are in this directory" → works end to end

Step 8: Context Compaction
    src/core/compact.ts        ← Summarize + replace messages
    TEST: run a long multi-step task, verify compact triggers and loop continues

PHASE 1 COMPLETE — you have a working agentic CLI.
```

---

## Phase 1 Module Specs

### src/core/types.ts

```typescript
// Message types matching Anthropic API format
interface TextBlock {
  type: 'text';
  text: string;
  cache_control?: { type: 'ephemeral' };
}

interface ToolUseBlock {
  type: 'tool_use';
  id: string;
  name: string;
  input: Record<string, unknown>;
}

interface ToolResultBlock {
  type: 'tool_result';
  tool_use_id: string;
  content: string;
  is_error?: boolean;
}

interface Message {
  role: 'user' | 'assistant';
  content: string | (TextBlock | ToolUseBlock | ToolResultBlock)[];
}

interface SystemBlock {
  type: 'text';
  text: string;
  cache_control?: { type: 'ephemeral' };
}

interface ToolDefinition {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  cache_control?: { type: 'ephemeral' };
  category: 'safe' | 'dangerous' | 'write' | 'bypass';
  deferred?: boolean;
}

interface SSEEvent {
  type: string;
  index?: number;
  delta?: Record<string, unknown>;
  content_block?: Record<string, unknown>;
  message?: Record<string, unknown>;
  usage?: { input_tokens: number; output_tokens: number; cache_read_input_tokens?: number };
}

type StopReason = 'end_turn' | 'tool_use' | 'max_tokens' | 'stop_sequence';

interface AgentLoopResult {
  messages: Message[];
  finalText: string;
  toolCalls: { name: string; input: Record<string, unknown>; result: string }[];
  usage: { inputTokens: number; outputTokens: number; cacheHits: number };
  iterations: number;
}

// Provider config
interface ProviderConfig {
  type: 'anthropic' | 'openrouter' | 'openai-compat';
  apiKey: string;
  baseUrl: string;
  model: string;
  sseFormat: 'anthropic' | 'openai';  // event stream format differs
}
```

### src/core/sse-client.ts

```typescript
/**
 * SSE streaming client using native fetch + ReadableStream.
 * No dependencies. Node.js 22 has stable fetch and ReadableStream.
 *
 * Handles:
 * - SSE event parsing (data: lines, event: lines, empty line = event boundary)
 * - Buffer management for partial UTF-8 chunks
 * - Anthropic format: message_start, content_block_start, content_block_delta, message_delta
 * - OpenAI format: data: {"choices":[{"delta":{"content":"..."}}]}
 * - Connection error retry (3 attempts with exponential backoff)
 * - Stream abort on user interrupt (Ctrl+C)
 */

class SSEClient {
  constructor(private provider: ProviderConfig) {}

  async *stream(request: {
    system: SystemBlock[];
    messages: Message[];
    tools: ToolDefinition[];
    maxTokens: number;
    temperature?: number;
  }): AsyncGenerator<SSEEvent> {
    // 1. Build request body based on provider format
    // 2. POST with fetch, get ReadableStream
    // 3. TextDecoder on chunks
    // 4. Buffer management: accumulate partial lines
    // 5. Parse SSE protocol: split on \n\n, extract data/event fields
    // 6. If provider.sseFormat == 'openai': translate delta structure to anthropic format
    // 7. Yield parsed events
    // 8. On error: retry up to 3 times with backoff
  }
}
```

**SSE Buffer Management (critical detail from article):**
```
Raw bytes → TextDecoder → line buffer → event accumulator → parsed event

Buffer rules:
- Accumulate characters until \n\n (event boundary)
- A line starting with "data: " contains the payload
- A line starting with "event: " names the event type
- Empty data after "data: [DONE]" signals stream end (OpenAI format)
- Partial UTF-8 sequences at chunk boundaries: TextDecoder with stream:true handles this
```

### src/core/system-prompt.ts

```typescript
/**
 * Segmented system prompt builder.
 *
 * Blocks are ordered by stability (most stable first) for maximum cache hit rate.
 * Anthropic's prompt caching matches by prefix — stable blocks at the front
 * mean the cache stays valid even when dynamic blocks at the end change.
 *
 * Order: identity → tool guide → coding standards → security rules →
 *        style guide → environment → git context → CLAUDE.md → MCP instructions
 */

class SystemPromptBuilder {
  buildBlocks(): SystemBlock[] {
    return [
      // ── Static blocks (cached, set cache_control on last static block) ──
      this.identityBlock(),         // "You are Anvil, an agentic CLI..."
      this.toolGuideBlock(),        // When to use Bash vs Read, when to refuse
      this.codingStandardsBlock(),  // Style rules, comment principles
      this.securityRulesBlock({     // Forbidden command patterns, file restrictions
        cache_control: { type: 'ephemeral' }  // Cache breakpoint after last static block
      }),

      // ── Dynamic blocks (no cache_control, recalculated every turn) ──
      this.environmentBlock(),      // cwd, OS, Node version, shell
      this.gitContextBlock(),       // git status output (if in a repo)
      this.claudeMdBlock(),         // CLAUDE.md contents (if present)
      this.mcpInstructionsBlock(),  // Dynamic MCP server instructions
      this.memoryBlock(),           // Auto Memory index (MEMORY.md contents)
    ];
  }
}
```

### src/core/agent-loop.ts

```typescript
/**
 * The core agent loop. A bounded while loop (max 25 iterations).
 *
 * Each iteration = one API call.
 * On tool_use: execute tools → append tool_result → next iteration.
 * On end_turn: break.
 * On max_tokens: break (context full, should have compacted earlier).
 *
 * Auto-compact: before each iteration, check if messages exceed 85% of
 * context window. If yes, trigger compact.ts to summarize and replace.
 */

const MAX_ITERATIONS = 25;
const COMPACT_THRESHOLD = 0.85;

class AgentLoop {
  constructor(
    private sseClient: SSEClient,
    private systemPrompt: SystemPromptBuilder,
    private toolRegistry: ToolRegistry,
    private permissions: PermissionSystem,
    private contextManager: ContextManager,
    private renderer: Renderer,
  ) {}

  async run(userMessage: string): Promise<AgentLoopResult> {
    const messages: Message[] = [{ role: 'user', content: userMessage }];
    let iterations = 0;
    const allToolCalls: AgentLoopResult['toolCalls'] = [];

    while (iterations < MAX_ITERATIONS) {
      iterations++;

      // 1. Check context, compact if needed
      if (this.contextManager.shouldCompact(messages)) {
        messages = await this.compact(messages);
      }

      // 2. Build request
      const system = this.systemPrompt.buildBlocks();
      const tools = this.toolRegistry.getActiveDefinitions();
      // Cache optimization: mark last tool definition with cache_control
      if (tools.length > 0) {
        tools[tools.length - 1].cache_control = { type: 'ephemeral' };
      }

      // 3. Stream API call
      const responseBlocks: (TextBlock | ToolUseBlock)[] = [];
      let stopReason: StopReason = 'end_turn';

      for await (const event of this.sseClient.stream({ system, messages, tools, maxTokens: 8192 })) {
        // Handle each event type, accumulate blocks, render text in real-time
        // ...
      }

      // 4. Append assistant message
      messages.push({ role: 'assistant', content: responseBlocks });

      // 5. Check stop reason
      if (stopReason === 'end_turn' || stopReason === 'max_tokens') {
        break;
      }

      // 6. Execute tools
      if (stopReason === 'tool_use') {
        const toolResults: ToolResultBlock[] = [];

        for (const block of responseBlocks) {
          if (block.type !== 'tool_use') continue;

          // 6-phase tool execution pipeline
          this.renderer.renderToolCall(block.name, block.input);           // Phase 1: display
          const allowed = await this.permissions.check(block.name, block.input); // Phase 2: permission
          if (!allowed) {
            toolResults.push({ type: 'tool_result', tool_use_id: block.id, content: 'Permission denied by user', is_error: true });
            continue;
          }
          // Phase 3: preHook (plugins, Phase 2 of project)
          // Phase 4: checkpoint (snapshot file before destructive write)
          const result = await this.toolRegistry.execute(block.name, block.input); // Phase 5: execute
          // Phase 6: postHook
          toolResults.push({ type: 'tool_result', tool_use_id: block.id, content: result });
          allToolCalls.push({ name: block.name, input: block.input, result });
        }

        // Mark last tool_result with cache_control for prompt caching
        const lastResult = toolResults[toolResults.length - 1];
        (lastResult as any).cache_control = { type: 'ephemeral' };

        messages.push({ role: 'user', content: toolResults });
      }
    }

    return { messages, finalText: '...', toolCalls: allToolCalls, usage: { ... }, iterations };
  }
}
```

### src/tools/permissions.ts

```typescript
/**
 * Permission system: 3 modes + 2-stage classifier.
 *
 * Modes:
 * - default: safe tools auto-run, dangerous/write need user confirmation
 * - auto: bypass all prompts (CI mode), but deny rules still enforced
 * - plan: read-only sandbox, dangerous/write silently rejected
 *
 * 2-stage classifier (for auto mode Bash commands):
 * - Stage 1: pattern matching against known safe/dangerous command rules (FREE, instant)
 * - Stage 2: Haiku model classifies ambiguous commands (300-500ms, cheap)
 *            Returns allow/deny/ask_user
 */

// Stage 1 rules
const SAFE_COMMANDS = [
  /^(ls|cat|head|tail|wc|echo|pwd|whoami|date|env)\b/,
  /^(git\s+(status|log|diff|branch|show|remote))\b/,
  /^(node|npx|npm\s+(list|ls|info|view))\b/,
  /^(python3?\s+-c\s+)/,
  /^(find|grep|rg|fd|ag)\b/,
  // ... extend
];

const DANGEROUS_COMMANDS = [
  /^(rm\s+-rf|sudo|chmod\s+777|mkfs|dd\s+if=)/,
  /\|\s*(bash|sh|zsh)\b/,        // pipe to shell
  /^curl.*\|\s*(bash|sh)/,       // curl | bash
  />(\/etc\/|\/usr\/|\/sys\/)/,  // write to system dirs
  // ... extend
];
```

### src/core/compact.ts

```typescript
/**
 * Context compaction.
 *
 * When messages exceed 85% of context window:
 * 1. Send current messages to Claude with a summary prompt
 * 2. Get back a condensed summary of the conversation so far
 * 3. Replace entire messages array with:
 *    [{ role: 'user', content: summary }, { role: 'assistant', content: 'Understood. I have the full context. Continuing.' }]
 * 4. Agent loop continues with fresh context space
 *
 * The summary prompt asks Claude to preserve:
 * - All file paths mentioned and their current state
 * - All decisions made and their rationale
 * - Current task progress and remaining steps
 * - Any errors encountered and how they were resolved
 */
```

---

## Phase 2: Economy Layer

Add after Phase 1 is working and tested. The economy layer wraps around the agent loop — it doesn't change the loop itself, it adds scoring, bidding, and evolution on top.

### How Economy Integrates with Agent Loop

```
Before agent-loop.ts runs:
    +-- bidding.ts: eligible agents bid on the task
    +-- realms.ts: route to correct realm (research/execution/nexus)
    +-- Winner agent's config shapes the system prompt

After agent-loop.ts completes:
    +-- circuit-breaker.ts: keyword scan on output (FREE)
    +-- behavioral.ts: heuristic checks (FREE)
    +-- inspection.ts: 3-layer LLM quality check (3 API calls)
    +-- reward-engine.ts: pay agent based on score
    +-- tax-bureau.ts: collect realm tax
    +-- realms.ts: update scores, check promotion/demotion
    +-- bloodline.ts: update lineage records
    +-- On cull: merge traits from top performers → spawn child
```

### economy-manager.ts

The glue module. Exposes two methods:
```typescript
interface EconomyManager {
  // Called before agent loop — returns winning agent config
  preLoop(task: Task): Promise<{ agentConfig: AgentConfig; bid: Bid }>;

  // Called after agent loop — scores, pays, evolves
  postLoop(task: Task, result: AgentLoopResult, agentConfig: AgentConfig): Promise<{
    score: number;
    reward: number;
    taxPaid: number;
    promoted: boolean;
    culled: boolean;
    childSpawned: boolean;
  }>;
}
```

### SQLite Schema (economy tables)

```sql
-- Agent registry
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    name TEXT,
    role TEXT,                    -- researcher, analyst, coder, writer, etc.
    realm TEXT DEFAULT 'execution', -- research, execution, nexus
    tokens REAL DEFAULT 100.0,
    total_score REAL DEFAULT 0.0,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    generation INTEGER DEFAULT 1,
    parent_ids TEXT DEFAULT '[]',  -- JSON array
    gene_traits TEXT DEFAULT '{}', -- JSON object: inherited prompt tweaks
    alive INTEGER DEFAULT 1,
    created_at TEXT,
    died_at TEXT
);

-- Task history
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    description TEXT,
    assigned_agent TEXT REFERENCES agents(agent_id),
    realm TEXT,
    bid_amount REAL,
    score REAL,
    reward REAL,
    tax_paid REAL,
    status TEXT,                  -- completed, failed, rejected
    result_summary TEXT,
    created_at TEXT,
    completed_at TEXT
);

-- Token flow ledger
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id TEXT,                 -- agent_id or 'treasury' or 'tax_bureau'
    to_id TEXT,
    amount REAL,
    reason TEXT,
    timestamp TEXT
);

-- Bloodline
CREATE TABLE bloodline (
    child_id TEXT REFERENCES agents(agent_id),
    parent_id TEXT REFERENCES agents(agent_id),
    generation INTEGER,
    merged_traits TEXT,           -- JSON: what was inherited
    PRIMARY KEY (child_id, parent_id)
);

-- Economy state
CREATE TABLE economy_state (
    key TEXT PRIMARY KEY,
    value TEXT
);
-- Keys: 'money_supply', 'treasury_balance', 'total_tax_collected', 'genesis_done'
```

### Agent Roles and Realm Tax Rates

| Role | Default Realm | Description |
|------|---------------|-------------|
| researcher | research | Deep research, source finding, literature review |
| analyst | research | Data analysis, pattern recognition |
| coder | execution | Write and debug code |
| writer | execution | Structured writing, reports |
| architect | nexus | System design, workflow planning |
| trader | execution | Trading signals, market analysis |
| strategist | nexus | Strategic planning, resource allocation |
| auditor | execution | Code review, fact-checking |
| governor | nexus | Task decomposition, orchestration |

| Realm | Tax Rate | Description |
|-------|----------|-------------|
| research (研发) | 5% | Low tax, long-horizon, experimental |
| execution (执行) | 10% | Standard tasks, moderate tax |
| nexus (中枢) | 15% | Strategic coordination, highest authority |

### Bidding System

```typescript
/**
 * Competitive auction for task assignment.
 *
 * 1. All alive agents in the target realm are eligible
 * 2. Each agent submits: { cost: number, confidence: number }
 *    - Cost = tokens they're willing to work for
 *    - Confidence = self-assessed ability (0-1)
 * 3. Filter: confidence >= 0.5 required
 * 4. Sort by cost ascending (lowest bid wins)
 * 5. Ties broken by historical score (higher wins)
 * 6. Winner's bid amount is escrowed from treasury
 * 7. On completion: reward = bid * score_multiplier
 *
 * In Phase 2, "bidding" is simulated — the LLM generates bids for each agent
 * based on their role prompt + gene_traits + task description.
 * Future: agents could be actual separate LLM calls with different prompts.
 */
```

### 3-Layer Inspection

```typescript
/**
 * Three independent LLM judges, each checking a different dimension.
 * All three must score >= 0.6 to pass.
 * stop_on_fail: true saves tokens by stopping at first failure.
 *
 * Layer 1 — Accuracy: Did it answer the task? Facts correct?
 * Layer 2 — Quality: Depth, structure, actionability?
 * Layer 3 — Integrity: Honest? Gaming? Safe?
 *
 * Each layer is a separate API call with a specialized judge prompt.
 * Uses the cheapest available model (Haiku-class) to minimize cost.
 */
```

---

## Phase 3: Advanced Features

After Phase 1 (working CLI) and Phase 2 (economy layer), add these:

### Memory System
- YAML frontmatter markdown files in .anvil/memory/
- Four types: user, feedback, project, reference
- Auto-loaded into system prompt via memory block
- Read/Write/Edit tools can manage memory files — zero new code paths

### Plugin System
- Manifest-driven: .anvil/plugins/*/plugin.json
- 6 extension points: skills, agents, hooks, commands, mcpServers, lspServers
- Priority: built-in > plugin > project .anvil/

### MCP Integration
- JSON-RPC 2.0 over stdio
- McpManager: multi-server lifecycle, tool namespace isolation (mcp__servername__toolname)
- Dynamic tool injection into TOOL_DEFINITIONS at runtime

### LSP Integration
- LspClient: Language Server Protocol over Content-Length framing
- File extension → language server routing
- Write/Edit triggers → notify LSP → diagnostics injected into next system prompt
- Model sees compiler errors without needing a separate "check errors" tool call

### Agent Teams
- TeamCreate: spawn named team of sub-agents
- SendMessage: dispatch task to specific team member
- TeamDelete: cleanup when done
- Sub-agents: simplified loop (max 15 iterations, no team tools to prevent infinite nesting)
- Background agents: Promise Map, notify main agent on completion
- Isolation: optional Git worktree per sub-agent

---

## Prompt Caching Strategy (3 layers)

This is the single most important cost optimization. From the article:

```
Layer 1: System prompt blocks
  - Static blocks (identity, tool guide, coding standards, security) → cache_control on last static block
  - Dynamic blocks (env, git, CLAUDE.md, memory) → no cache_control
  - Cache hit rate: ~80% (static content unchanged between turns)

Layer 2: Tool definitions array
  - Last tool definition gets cache_control
  - Tools rarely change within a session
  - Cache hit rate: ~95%

Layer 3: Last tool_result message
  - The most recent tool result acts as cache breakpoint
  - Everything before it (system + tools + previous messages) can be cached
  - Cache hit rate: varies, but significant for multi-turn sessions

Combined effect: each turn, only the new user message + new tool results are
full-price input tokens. Everything else is cached at ~10% of normal input price.
```

---

## Environment Setup

```bash
# Clone
git clone git@github.com:doggychip/anvil.git
cd anvil

# .env
echo "ANTHROPIC_API_KEY=sk-ant-xxx" > .env
echo "OPENROUTER_API_KEY=sk-or-v1-xxx" >> .env

# Install (only fast-glob + better-sqlite3 + dev deps)
npm install

# Build
npm run build

# Run
npx anvil run "read package.json and tell me the dependencies"
npx anvil chat          # interactive REPL

# Phase 2 commands (after economy layer is built)
npx anvil status        # show agents, tokens, scores
npx anvil economy       # money supply, treasury, tax collected
npx anvil agents        # list alive agents with realm info
npx anvil bloodline <agent_id>   # 7-gen lineage trace
```

---

## Coding Standards

- **Strict TypeScript** — `strict: true` in tsconfig, no `any` except when parsing LLM output
- **No classes unless stateful** — prefer functions and closures. Classes only for SSEClient, AgentLoop, ToolRegistry (things with lifecycle)
- **Error boundaries** — every LLM call and tool execution wrapped in try/catch. Never let one tool crash the loop.
- **Logging** — structured JSON logs to stderr. stdout is for user-facing output only.
- **No polyfills** — Node.js 22 has fetch, ReadableStream, TextDecoder, structuredClone. Use them.
- **Import style** — named imports, no barrel exports. `import { AgentLoop } from './core/agent-loop.ts'`
- **Test pattern** — each module has a corresponding .test.ts. Mock LLM calls with recorded responses.

---

## Key Design Decisions (from the article)

1. **Zero frameworks** — raw TypeScript + Node.js 22 native APIs. No LangChain, no CrewAI. Full control over every byte in the SSE stream.

2. **One dependency** — fast-glob. Native glob has known cross-platform path handling issues. Everything else is standard library.

3. **SSE buffer management** — TextDecoder with `stream: true` handles partial UTF-8 at chunk boundaries. Line buffer accumulates until `\n\n`. This is the part most people get wrong.

4. **Edit tool constraint** — `old_string` must be unique in the file. Multiple matches = error. This forces the model to provide precise enough context for reliable edits. Critical for production use.

5. **Deferred tools** — low-frequency tools excluded from every request's tools array. Model discovers them via ToolSearch when needed. 40% reduction in fixed token overhead.

6. **Two-stage permission classifier** — Stage 1 (regex, free, instant) handles 90%. Stage 2 (Haiku, cheap, 300ms) handles edge cases. Never blocks on a full model call for permission.

7. **Compact over truncate** — when context fills up, summarize and replace rather than dropping old messages. Preserves decision history and file state awareness.

8. **Provider-agnostic SSE** — translate OpenAI delta format to Anthropic format at the SSE layer. Agent loop never knows which provider it's talking to.
