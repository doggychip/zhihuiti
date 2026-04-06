import type { PermissionMode, ToolCategory } from '../core/types.js';

export type PermissionResult = 'allow' | 'deny' | 'ask_user';

/**
 * 3-mode permission system with 2-stage Bash classifier.
 *
 * Modes:
 * - default: safe tools auto-run, write/dangerous need user confirmation
 * - auto: bypass all prompts (CI mode), but deny rules still enforced
 * - plan: read-only sandbox, write/dangerous silently rejected
 */

export function checkPermission(
  mode: PermissionMode,
  toolName: string,
  category: ToolCategory,
  input: Record<string, unknown>,
): PermissionResult {
  // Plan mode: read-only
  if (mode === 'plan') {
    if (category === 'safe') return 'allow';
    return 'deny';
  }

  // Safe tools always run
  if (category === 'safe') return 'allow';

  // Auto mode: run everything except hard-denied patterns
  if (mode === 'auto') {
    if (toolName === 'Bash') {
      const command = (input.command as string) || '';
      if (isDangerousCommand(command)) return 'deny';
    }
    return 'allow';
  }

  // Default mode: safe auto-runs, everything else asks
  if (toolName === 'Bash') {
    const command = (input.command as string) || '';
    // Stage 1: pattern matching
    if (isDangerousCommand(command)) return 'deny';
    if (isSafeCommand(command)) return 'allow';
    // Ambiguous → ask user
    return 'ask_user';
  }

  // Write/dangerous tools need confirmation in default mode
  return 'ask_user';
}

// ── Stage 1: Pattern-based classifier (free, instant) ──

const SAFE_PATTERNS = [
  /^(ls|cat|head|tail|wc|echo|pwd|whoami|date)\b/,
  /^(git\s+(status|log|diff|branch|show|remote|rev-parse))\b/,
  /^(node|npx)\s/,
  /^npm\s+(list|ls|info|view|outdated|why)\b/,
  /^(python3?|ruby|perl)\s+-c\s/,
  /^(find|grep|rg|fd|ag|tree|file|which|type|man)\b/,
  /^(env|printenv|uname|arch|hostname|id|groups)\b/,
  /^(tsc|eslint|prettier|jest|vitest|mocha)\s/,
  /^(docker\s+(ps|images|logs|inspect))\b/,
  /^(curl|wget)\s.*--head\b/,
  /^(wc|sort|uniq|cut|tr|tee|xargs|seq|yes)\b/,
];

const DANGEROUS_PATTERNS = [
  /^rm\s+(-rf|--recursive)\s+\//,     // rm -rf /anywhere
  /^sudo\b/,                           // sudo anything
  /^chmod\s+777/,                      // world-writable
  /^(mkfs|fdisk|dd\s+if=)/,           // disk operations
  /\|\s*(bash|sh|zsh)\b/,             // pipe to shell
  /^curl.*\|\s*(bash|sh)/,            // curl | bash
  />(\/etc\/|\/usr\/|\/sys\/)/,        // write to system dirs
  /^(shutdown|reboot|halt|init\s+0)/,  // system control
  /^kill\s+-9\s+1\b/,                 // kill init
  /--force\s+push|push\s+--force/,    // git force push
  /\bgit\s+push\s+.*--force/,
  /\bgit\s+reset\s+--hard/,           // destructive git
  /\bgit\s+clean\s+-f/,
];

function isSafeCommand(command: string): boolean {
  const trimmed = command.trim();
  return SAFE_PATTERNS.some(p => p.test(trimmed));
}

function isDangerousCommand(command: string): boolean {
  const trimmed = command.trim();
  return DANGEROUS_PATTERNS.some(p => p.test(trimmed));
}
