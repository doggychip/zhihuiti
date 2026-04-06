import { AgentLoop } from '../core/agent-loop.js';
import { Renderer } from '../ui/renderer.js';
import { Prompt } from '../ui/prompt.js';
import * as c from '../ui/colors.js';
import type { AnvilConfig, Message } from '../core/types.js';

/**
 * Interactive REPL mode: anvil chat
 * Multi-turn conversation with the agent.
 */
export async function chatCommand(config: AnvilConfig): Promise<void> {
  const renderer = new Renderer();
  const prompt = new Prompt();

  process.stderr.write(`\n${c.bold('Anvil')} ${c.muted('— interactive mode')}\n`);
  process.stderr.write(`${c.muted('Type your message. "exit" or Ctrl+C to quit.')}\n`);

  let messages: Message[] = [];

  // Handle Ctrl+C gracefully
  process.on('SIGINT', () => {
    renderer.endText();
    process.stderr.write(`\n${c.muted('Goodbye.')}\n`);
    prompt.close();
    process.exit(0);
  });

  while (true) {
    const input = await prompt.userInput();

    if (!input) continue;
    if (input === 'exit' || input === 'quit' || input === '/exit' || input === '/quit') {
      process.stderr.write(`${c.muted('Goodbye.')}\n`);
      break;
    }

    // Clear command
    if (input === '/clear') {
      messages = [];
      process.stderr.write(`${c.muted('Conversation cleared.')}\n`);
      continue;
    }

    renderer.loopStart();

    const loop = new AgentLoop({
      config,
      onText: (text) => renderer.text(text),
      onToolCall: (name, toolInput) => renderer.toolCall(name, toolInput),
      onPermissionRequest: async (name, toolInput) => {
        renderer.permissionPrompt(name, toolInput);
        const allowed = await prompt.confirm('');
        if (!allowed) renderer.permissionDenied(name);
        return allowed;
      },
    });

    try {
      let result;
      if (messages.length === 0) {
        result = await loop.run(input);
      } else {
        result = await loop.continueWith(messages, input);
      }

      messages = result.messages;
      renderer.loopEnd(result.iterations, result.usage);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      renderer.error(msg);
    }
  }

  prompt.close();
}
