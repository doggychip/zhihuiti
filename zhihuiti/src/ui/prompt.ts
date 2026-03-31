import { createInterface, type Interface } from 'node:readline';
import * as c from './colors.js';

/**
 * User input handling via readline.
 * Provides single-line prompts and yes/no confirmations.
 */

export class Prompt {
  private rl: Interface | null = null;

  private getRL(): Interface {
    if (!this.rl) {
      this.rl = createInterface({
        input: process.stdin,
        output: process.stderr, // prompts go to stderr, stdout is for agent output
        terminal: process.stdin.isTTY ?? false,
      });
    }
    return this.rl;
  }

  /** Prompt user for text input. */
  async ask(prompt: string): Promise<string> {
    return new Promise((resolve) => {
      this.getRL().question(prompt, (answer) => {
        resolve(answer.trim());
      });
    });
  }

  /** Prompt user for yes/no confirmation. */
  async confirm(question: string): Promise<boolean> {
    const answer = await this.ask(`${question} ${c.muted('[y/n]')} `);
    return answer.toLowerCase().startsWith('y');
  }

  /** Prompt for the main user input in chat mode. */
  async userInput(): Promise<string> {
    const answer = await this.ask(`\n${c.bold(c.blue('anvil'))}${c.muted(' >')} `);
    return answer;
  }

  /** Close the readline interface. */
  close(): void {
    if (this.rl) {
      this.rl.close();
      this.rl = null;
    }
  }
}
