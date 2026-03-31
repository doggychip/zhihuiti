import { execSync } from 'node:child_process';
import { readFileSync, existsSync } from 'node:fs';
import { resolve, basename } from 'node:path';
import type { SystemBlock } from './types.js';

/**
 * Segmented system prompt builder.
 *
 * Blocks ordered by stability (most stable first) for maximum prompt cache hit rate.
 * Anthropic caching matches by prefix — stable blocks at the front mean the cache
 * stays valid even when dynamic blocks at the end change.
 *
 * Order: identity → tool guide → coding standards → security rules →
 *        environment → git context → CLAUDE.md → memory
 */

export class SystemPromptBuilder {
  constructor(private projectDir: string = process.cwd()) {}

  buildBlocks(): SystemBlock[] {
    const blocks: SystemBlock[] = [];

    // ── Static blocks (stable across turns, cached) ──
    blocks.push(this.block(IDENTITY));
    blocks.push(this.block(TOOL_GUIDE));
    blocks.push(this.block(CODING_STANDARDS));
    // Last static block gets cache_control
    blocks.push(this.block(SECURITY_RULES, true));

    // ── Dynamic blocks (change between turns, not cached) ──
    blocks.push(this.block(this.environmentText()));

    const gitCtx = this.gitContextText();
    if (gitCtx) blocks.push(this.block(gitCtx));

    const claudeMd = this.claudeMdText();
    if (claudeMd) blocks.push(this.block(claudeMd));

    const memory = this.memoryText();
    if (memory) blocks.push(this.block(memory));

    return blocks;
  }

  private block(text: string, cache = false): SystemBlock {
    const b: SystemBlock = { type: 'text', text };
    if (cache) b.cache_control = { type: 'ephemeral' };
    return b;
  }

  // ── Dynamic block builders ──

  private environmentText(): string {
    const cwd = this.projectDir;
    const platform = process.platform;
    const nodeVersion = process.version;
    const shell = process.env['SHELL'] || 'unknown';

    return `# Environment
- Working directory: ${cwd}
- Platform: ${platform}
- Node.js: ${nodeVersion}
- Shell: ${shell}`;
  }

  private gitContextText(): string | null {
    try {
      const status = execSync('git status --short', {
        cwd: this.projectDir,
        encoding: 'utf-8',
        timeout: 5000,
        stdio: ['pipe', 'pipe', 'pipe'],
      }).trim();

      const branch = execSync('git branch --show-current', {
        cwd: this.projectDir,
        encoding: 'utf-8',
        timeout: 5000,
        stdio: ['pipe', 'pipe', 'pipe'],
      }).trim();

      const log = execSync('git log --oneline -5', {
        cwd: this.projectDir,
        encoding: 'utf-8',
        timeout: 5000,
        stdio: ['pipe', 'pipe', 'pipe'],
      }).trim();

      let text = `# Git Context\nBranch: ${branch}`;
      if (status) {
        text += `\n\nStatus:\n${status}`;
      } else {
        text += '\n\nStatus: clean';
      }
      if (log) {
        text += `\n\nRecent commits:\n${log}`;
      }
      return text;
    } catch {
      return null; // not a git repo
    }
  }

  private claudeMdText(): string | null {
    // Search upward: project dir → parent → … → root
    let dir = this.projectDir;
    const checked = new Set<string>();

    while (true) {
      if (checked.has(dir)) break;
      checked.add(dir);

      const candidate = resolve(dir, 'CLAUDE.md');
      if (existsSync(candidate)) {
        try {
          const content = readFileSync(candidate, 'utf-8');
          if (content.trim()) {
            return `# Project Instructions (${basename(dir)}/CLAUDE.md)\n${content}`;
          }
        } catch {
          // permission error etc — skip
        }
      }

      const parent = resolve(dir, '..');
      if (parent === dir) break; // reached root
      dir = parent;
    }
    return null;
  }

  private memoryText(): string | null {
    const memoryIndex = resolve(this.projectDir, '.anvil', 'memory', 'MEMORY.md');
    if (!existsSync(memoryIndex)) return null;

    try {
      const content = readFileSync(memoryIndex, 'utf-8').trim();
      if (!content) return null;
      // Truncate at 200 lines as specified
      const lines = content.split('\n');
      const truncated = lines.slice(0, 200).join('\n');
      return `# Memory\n${truncated}`;
    } catch {
      return null;
    }
  }
}

// ── Static prompt segments ──

const IDENTITY = `You are Anvil (铁砧), a production-grade agentic CLI built from scratch in TypeScript.

You help users with software engineering tasks: fixing bugs, adding features, refactoring code, explaining systems, and more. You operate through an iterative loop — reading files, running commands, editing code, and verifying results until the task is complete.

Be direct and concise. Lead with the answer or action. Skip filler words and unnecessary preamble. If you can say it in one sentence, don't use three.`;

const TOOL_GUIDE = `# Tool Usage Guide

Use the right tool for each job:
- Read files: use the Read tool (not cat/head/tail via Bash)
- Edit files: use the Edit tool (not sed/awk via Bash)
- Create files: use the Write tool (not echo/heredoc via Bash)
- Search by filename: use the Glob tool (not find/ls)
- Search file contents: use the Grep tool (not grep/rg via Bash)
- Shell commands: use Bash only for system operations that require execution

When multiple tool calls are independent, make them in parallel.
Read a file before editing it. Understand existing code before suggesting modifications.
Do not create files unless absolutely necessary — prefer editing existing ones.`;

const CODING_STANDARDS = `# Coding Standards

- Go straight to the point. Try the simplest approach first.
- Don't add features, refactor code, or make improvements beyond what was asked.
- Don't add error handling for scenarios that can't happen. Trust internal code.
- Don't create helpers or abstractions for one-time operations.
- Don't add docstrings, comments, or type annotations to code you didn't change.
- Three similar lines of code is better than a premature abstraction.
- Only add comments where the logic isn't self-evident.
- Be careful not to introduce security vulnerabilities (XSS, SQL injection, command injection, etc).`;

const SECURITY_RULES = `# Security Rules

Never execute commands that could cause irreversible damage without user confirmation:
- No rm -rf on important directories
- No force pushes to shared branches
- No dropping database tables
- No modifying system files (/etc, /usr, /sys)

Refuse to execute:
- curl | bash (piping remote scripts to shell)
- Commands that exfiltrate data to external servers
- Commands that modify SSH keys or credentials

For destructive operations, always explain what will happen and ask for confirmation first.`;
