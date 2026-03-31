#!/usr/bin/env node

import { loadConfig } from './config/settings.js';
import { runCommand } from './commands/run.js';
import { chatCommand } from './commands/chat.js';
import * as c from './ui/colors.js';

const VERSION = '0.1.0';

function printUsage(): void {
  process.stderr.write(`
${c.bold('Anvil')} ${c.muted(`v${VERSION}`)} — agentic CLI runtime

${c.label('Usage:')}
  anvil run <goal>       Run a single task, then exit
  anvil chat             Interactive REPL mode
  anvil --help           Show this help
  anvil --version        Show version

${c.label('Options:')}
  --auto                 Auto-approve all tool calls (CI mode)
  --plan                 Read-only mode (no writes)

${c.label('Examples:')}
  anvil run "read package.json and list the dependencies"
  anvil run "fix the type error in src/index.ts"
  anvil chat
`);
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    printUsage();
    return;
  }

  if (args.includes('--version') || args.includes('-v')) {
    process.stdout.write(`${VERSION}\n`);
    return;
  }

  // Load config
  const config = loadConfig();

  // Parse flags
  if (args.includes('--auto')) {
    config.permissionMode = 'auto';
  }
  if (args.includes('--plan')) {
    config.permissionMode = 'plan';
  }

  // Strip flags from args
  const positional = args.filter(a => !a.startsWith('--'));
  const command = positional[0];

  // Validate API key
  if (!config.provider.apiKey) {
    process.stderr.write(c.error('No API key configured.') + '\n');
    process.stderr.write(`Set ${c.bold('ANTHROPIC_API_KEY')} in .env or environment.\n`);
    process.exitCode = 1;
    return;
  }

  switch (command) {
    case 'run': {
      const goal = positional.slice(1).join(' ');
      if (!goal) {
        process.stderr.write(c.error('Missing goal.') + '\n');
        process.stderr.write(`Usage: ${c.muted('anvil run "your task here"')}\n`);
        process.exitCode = 1;
        return;
      }
      await runCommand(goal, config);
      break;
    }

    case 'chat': {
      await chatCommand(config);
      break;
    }

    default: {
      // If no command keyword, treat entire positional as a goal (shorthand)
      const goal = positional.join(' ');
      if (goal) {
        await runCommand(goal, config);
      } else {
        printUsage();
      }
      break;
    }
  }
}

main().catch((err) => {
  process.stderr.write(`Fatal: ${err instanceof Error ? err.message : String(err)}\n`);
  process.exitCode = 1;
});
