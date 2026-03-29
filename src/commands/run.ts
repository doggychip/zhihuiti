import { AgentLoop } from '../core/agent-loop.js';
import { Renderer } from '../ui/renderer.js';
import { Prompt } from '../ui/prompt.js';
import type { AnvilConfig } from '../core/types.js';

/**
 * Single-shot mode: anvil run "goal"
 * Runs the agent loop once with the given goal, then exits.
 */
export async function runCommand(goal: string, config: AnvilConfig): Promise<void> {
  const renderer = new Renderer();
  const prompt = new Prompt();

  renderer.loopStart();

  const loop = new AgentLoop({
    config,
    onText: (text) => renderer.text(text),
    onToolCall: (name, input) => renderer.toolCall(name, input),
    onPermissionRequest: async (name, input) => {
      renderer.permissionPrompt(name, input);
      const allowed = await prompt.confirm('');
      if (!allowed) renderer.permissionDenied(name);
      return allowed;
    },
  });

  try {
    const result = await loop.run(goal);
    renderer.loopEnd(result.iterations, result.usage);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    renderer.error(msg);
    process.exitCode = 1;
  } finally {
    prompt.close();
  }
}
