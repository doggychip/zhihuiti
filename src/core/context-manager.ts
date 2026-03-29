import type { Message, ContentBlock } from './types.js';

/**
 * Token estimation and context window tracking.
 *
 * Uses chars/4 heuristic for fast estimation — accurate enough for
 * deciding when to compact. Actual token counts come from API usage events.
 */

export class ContextManager {
  private actualInputTokens = 0;
  private actualOutputTokens = 0;
  private cacheHits = 0;
  private cacheCreation = 0;

  constructor(
    private contextWindow: number,
    private compactThreshold: number,
  ) {}

  /** Estimate token count for the full messages array. */
  estimateTokens(messages: Message[]): number {
    let chars = 0;
    for (const msg of messages) {
      if (typeof msg.content === 'string') {
        chars += msg.content.length;
      } else {
        chars += this.estimateBlocks(msg.content);
      }
    }
    return Math.ceil(chars / 4);
  }

  /** Should we trigger compaction before the next API call? */
  shouldCompact(messages: Message[]): boolean {
    const estimated = this.estimateTokens(messages);
    return estimated > this.contextWindow * this.compactThreshold;
  }

  /** Update actual token counts from API usage events. */
  recordUsage(usage: {
    input_tokens: number;
    output_tokens: number;
    cache_read_input_tokens?: number;
    cache_creation_input_tokens?: number;
  }): void {
    this.actualInputTokens += usage.input_tokens;
    this.actualOutputTokens += usage.output_tokens;
    this.cacheHits += usage.cache_read_input_tokens ?? 0;
    this.cacheCreation += usage.cache_creation_input_tokens ?? 0;
  }

  getUsage() {
    return {
      inputTokens: this.actualInputTokens,
      outputTokens: this.actualOutputTokens,
      cacheHits: this.cacheHits,
      cacheCreation: this.cacheCreation,
    };
  }

  private estimateBlocks(blocks: ContentBlock[]): number {
    let chars = 0;
    for (const block of blocks) {
      if (block.type === 'text') {
        chars += block.text.length;
      } else if (block.type === 'tool_use') {
        chars += block.name.length + JSON.stringify(block.input).length;
      } else if (block.type === 'tool_result') {
        chars += block.content.length;
      }
    }
    return chars;
  }
}
