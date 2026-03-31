import type { Message } from './types.js';
import { SSEClient } from './sse-client.js';
import type { ProviderConfig } from './types.js';

const COMPACT_PROMPT = `Summarize the conversation so far. Preserve:
- All file paths mentioned and their current state
- All decisions made and their rationale
- Current task progress and remaining steps
- Any errors encountered and how they were resolved
- Key code snippets or patterns discussed

Be thorough but concise. This summary replaces the full conversation history.`;

/**
 * Compress conversation history by summarizing it via an LLM call.
 * Returns a fresh 2-message array that replaces the entire history.
 */
export async function compactMessages(
  messages: Message[],
  provider: ProviderConfig,
): Promise<Message[]> {
  // Build a summary request — no tools, just a straight summary
  const client = new SSEClient(provider);

  const summaryMessages: Message[] = [
    ...messages,
    { role: 'user', content: COMPACT_PROMPT },
  ];

  let summary = '';
  for await (const event of client.stream({
    system: [{ type: 'text', text: 'You are a conversation summarizer. Produce a concise but complete summary.' }],
    messages: summaryMessages,
    tools: [],
    maxTokens: 4096,
  })) {
    if (event.type === 'content_block_delta' && event.delta) {
      const delta = event.delta as { type?: string; text?: string };
      if (delta.type === 'text_delta' && delta.text) {
        summary += delta.text;
      }
    }
  }

  if (!summary.trim()) {
    // Fallback: if summary fails, keep last few messages
    return messages.slice(-4);
  }

  return [
    { role: 'user', content: `[Context — conversation summary]\n${summary}` },
    { role: 'assistant', content: 'Understood. I have the full context from the summary. Continuing.' },
  ];
}
