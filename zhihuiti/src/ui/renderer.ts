import * as c from './colors.js';

/**
 * Terminal renderer for streaming agent output.
 *
 * Writes directly to stdout/stderr — stdout for user-facing content,
 * stderr for status/diagnostic info (per coding standards).
 */

export class Renderer {
  private inTextBlock = false;

  /** Stream a text delta to stdout. */
  text(chunk: string): void {
    if (!this.inTextBlock) {
      this.inTextBlock = true;
      process.stdout.write('\n');
    }
    process.stdout.write(chunk);
  }

  /** End the current text block with a newline. */
  endText(): void {
    if (this.inTextBlock) {
      process.stdout.write('\n');
      this.inTextBlock = false;
    }
  }

  /** Display a tool call before execution. */
  toolCall(name: string, input: Record<string, unknown>): void {
    this.endText();
    const summary = this.summarizeToolInput(name, input);
    process.stderr.write(`\n  ${c.toolName(name)} ${c.muted(summary)}\n`);
  }

  /** Display a tool result (truncated). */
  toolResult(name: string, result: string, isError: boolean): void {
    if (isError) {
      process.stderr.write(`  ${c.error('✗')} ${c.toolName(name)} ${c.error(truncate(result, 200))}\n`);
    } else {
      const preview = truncate(result, 120);
      process.stderr.write(`  ${c.success('✓')} ${c.toolName(name)} ${c.muted(preview)}\n`);
    }
  }

  /** Display a permission prompt. */
  permissionPrompt(name: string, input: Record<string, unknown>): void {
    this.endText();
    const summary = this.summarizeToolInput(name, input);
    process.stderr.write(`\n  ${c.warn('?')} ${c.toolName(name)} ${c.muted(summary)}\n`);
    process.stderr.write(`    ${c.warn('Allow?')} ${c.muted('[y/n]')} `);
  }

  /** Display permission denied. */
  permissionDenied(name: string): void {
    process.stderr.write(`  ${c.error('✗')} ${c.toolName(name)} ${c.muted('denied')}\n`);
  }

  /** Display loop start banner. */
  loopStart(): void {
    process.stderr.write(`\n${c.muted('─'.repeat(60))}\n`);
  }

  /** Display loop end summary. */
  loopEnd(iterations: number, usage: {
    inputTokens: number;
    outputTokens: number;
    cacheHits: number;
  }): void {
    this.endText();
    process.stderr.write(`\n${c.muted('─'.repeat(60))}\n`);

    const parts: string[] = [
      `${iterations} iteration${iterations !== 1 ? 's' : ''}`,
      `${formatTokens(usage.inputTokens)} in`,
      `${formatTokens(usage.outputTokens)} out`,
    ];
    if (usage.cacheHits > 0) {
      parts.push(`${formatTokens(usage.cacheHits)} cached`);
    }
    process.stderr.write(`${c.muted(parts.join(' · '))}\n`);
  }

  /** Display an error. */
  error(msg: string): void {
    this.endText();
    process.stderr.write(`\n${c.error('Error:')} ${msg}\n`);
  }

  /** Display an info message. */
  info(msg: string): void {
    process.stderr.write(`${c.info(msg)}\n`);
  }

  private summarizeToolInput(name: string, input: Record<string, unknown>): string {
    switch (name) {
      case 'Read':
        return String(input.file_path ?? '');
      case 'Write':
        return String(input.file_path ?? '');
      case 'Edit':
        return String(input.file_path ?? '');
      case 'Bash':
        return truncate(String(input.command ?? ''), 80);
      case 'Grep':
        return `/${String(input.pattern ?? '')}/`;
      case 'Glob':
        return String(input.pattern ?? '');
      default: {
        const keys = Object.keys(input);
        if (keys.length === 0) return '';
        const first = input[keys[0]];
        return truncate(String(first ?? ''), 60);
      }
    }
  }
}

function truncate(str: string, max: number): string {
  const oneLine = str.replace(/\n/g, ' ').trim();
  if (oneLine.length <= max) return oneLine;
  return oneLine.slice(0, max - 1) + '…';
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}
