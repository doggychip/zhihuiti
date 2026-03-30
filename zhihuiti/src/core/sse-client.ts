import type {
  ProviderConfig,
  SystemBlock,
  Message,
  ToolDefinition,
  SSEEvent,
} from './types.js';

export interface StreamRequest {
  system: SystemBlock[];
  messages: Message[];
  tools: ToolDefinition[];
  maxTokens: number;
  temperature?: number;
}

const MAX_RETRIES = 5;
const BACKOFF_SECONDS = [2, 4, 8, 16, 32];

export class SSEClient {
  constructor(private provider: ProviderConfig) {}

  async *stream(request: StreamRequest): AsyncGenerator<SSEEvent> {
    const { url, headers, body } = this.buildRequest(request);

    let lastError: Error | null = null;
    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      if (attempt === 0) {
        // Initial delay — some providers (DeepSeek) need a moment before accepting streams
        await new Promise(r => setTimeout(r, 1000));
      }
      try {
        let gotMessageDelta = false;
        for await (const event of this.doStream(url, headers, body)) {
          if (event.type === 'message_delta') gotMessageDelta = true;
          yield event;
        }
        if (!gotMessageDelta) {
          throw new Error('Stream ended without delivering a message_delta event');
        }
        return; // success — exit
      } catch (err) {
        lastError = err instanceof Error ? err : new Error(String(err));
        process.stderr.write(
          `[sse-client] Attempt ${attempt + 1}/${MAX_RETRIES} failed: ${lastError.message}\n`
        );
        // Only retry on network/server errors, not 4xx
        if (lastError.message.includes('status 4')) throw lastError;
        if (attempt < MAX_RETRIES - 1) {
          const delay = BACKOFF_SECONDS[attempt] * 1000;
          process.stderr.write(
            `[sse-client] Retrying in ${BACKOFF_SECONDS[attempt]}s...\n`
          );
          await new Promise(r => setTimeout(r, delay));
        }
      }
    }
    throw lastError ?? new Error('SSE stream failed after retries');
  }

  private async *doStream(
    url: string,
    headers: Record<string, string>,
    body: string,
  ): AsyncGenerator<SSEEvent> {
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body,
    });

    if (!response.ok) {
      const text = await response.text().catch(() => '');
      throw new Error(`API request failed with status ${response.status}: ${text}`);
    }

    if (!response.body) {
      throw new Error('Response body is null — streaming not supported');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8', { fatal: false });
    let lineBuffer = '';

    // SSE accumulator
    let eventType = '';
    let dataLines: string[] = [];

    try {
      while (true) {
        let readResult: ReadableStreamReadResult<Uint8Array>;
        try {
          readResult = await reader.read();
        } catch (readErr) {
          // Stream body read failed — always throw so outer retry loop handles it
          const msg = readErr instanceof Error ? readErr.message : String(readErr);
          process.stderr.write(`[sse-client] Stream read error: ${msg}\n`);
          throw readErr;
        }
        const { done, value } = readResult;
        if (done) break;

        // Decode chunk — stream: true handles partial UTF-8 sequences
        lineBuffer += decoder.decode(value, { stream: true });

        // Process complete lines
        const lines = lineBuffer.split('\n');
        // Last element may be incomplete — keep in buffer
        lineBuffer = lines.pop() ?? '';

        for (const rawLine of lines) {
          const line = rawLine.trimEnd(); // strip \r if present

          if (line === '') {
            // Empty line = event boundary
            if (dataLines.length > 0) {
              const dataStr = dataLines.join('\n');
              dataLines = [];

              if (dataStr === '[DONE]') return;

              const event = this.parseEvent(eventType, dataStr);
              if (event) yield event;
              eventType = '';
            }
            continue;
          }

          if (line.startsWith('event: ')) {
            eventType = line.slice(7);
          } else if (line.startsWith('data: ')) {
            dataLines.push(line.slice(6));
          }
          // Ignore other SSE fields (id:, retry:, comments)
        }
      }

      // Flush any remaining buffered data
      if (lineBuffer.trim()) {
        lineBuffer += '\n\n';
        // Process remaining
        const remaining = lineBuffer.split('\n');
        for (const rawLine of remaining) {
          const line = rawLine.trimEnd();
          if (line === '' && dataLines.length > 0) {
            const dataStr = dataLines.join('\n');
            dataLines = [];
            if (dataStr === '[DONE]') return;
            const event = this.parseEvent(eventType, dataStr);
            if (event) yield event;
            eventType = '';
          } else if (line.startsWith('event: ')) {
            eventType = line.slice(7);
          } else if (line.startsWith('data: ')) {
            dataLines.push(line.slice(6));
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  private parseEvent(eventType: string, dataStr: string): SSEEvent | null {
    try {
      const data = JSON.parse(dataStr);

      if (this.provider.sseFormat === 'openai') {
        return this.translateOpenAIEvent(data);
      }

      // Anthropic format — pass through with event type
      return {
        type: eventType || data.type || 'unknown',
        index: data.index,
        delta: data.delta,
        content_block: data.content_block,
        message: data.type === 'message_start' ? data.message : undefined,
        usage: data.usage ?? data.message?.usage,
      };
    } catch {
      // Malformed JSON — skip this event
      return null;
    }
  }

  /**
   * Translate OpenAI-format SSE events into Anthropic-format SSEEvents.
   * This lets the agent loop remain provider-agnostic.
   */
  private translateOpenAIEvent(data: Record<string, unknown>): SSEEvent | null {
    const choices = data.choices as Array<Record<string, unknown>> | undefined;
    if (!choices || choices.length === 0) {
      // Could be a usage-only event
      if (data.usage) {
        const usage = data.usage as Record<string, number>;
        return {
          type: 'message_delta',
          usage: {
            input_tokens: usage.prompt_tokens ?? 0,
            output_tokens: usage.completion_tokens ?? 0,
          },
        };
      }
      return null;
    }

    const choice = choices[0];
    const delta = choice.delta as Record<string, unknown> | undefined;
    const finishReason = choice.finish_reason as string | null;

    if (!delta) return null;

    // Text content
    if (typeof delta.content === 'string' && delta.content) {
      return {
        type: 'content_block_delta',
        index: 0,
        delta: { type: 'text_delta', text: delta.content },
      };
    }

    // Tool calls
    const toolCalls = delta.tool_calls as Array<Record<string, unknown>> | undefined;
    if (toolCalls && toolCalls.length > 0) {
      const tc = toolCalls[0];
      const fn = tc.function as Record<string, unknown> | undefined;
      const index = (tc.index as number) ?? 0;

      // Tool call start (has id + function name)
      if (tc.id && fn?.name) {
        return {
          type: 'content_block_start',
          index,
          content_block: {
            type: 'tool_use',
            id: tc.id,
            name: fn.name,
          },
        };
      }

      // Tool call argument delta
      if (fn?.arguments && typeof fn.arguments === 'string') {
        return {
          type: 'content_block_delta',
          index,
          delta: { type: 'input_json_delta', partial_json: fn.arguments },
        };
      }
    }

    // Finish reason
    if (finishReason) {
      const stopReason = finishReason === 'stop' ? 'end_turn'
        : finishReason === 'tool_calls' ? 'tool_use'
        : finishReason === 'length' ? 'max_tokens'
        : 'end_turn';

      return {
        type: 'message_delta',
        delta: { stop_reason: stopReason },
        usage: data.usage ? {
          input_tokens: (data.usage as Record<string, number>).prompt_tokens ?? 0,
          output_tokens: (data.usage as Record<string, number>).completion_tokens ?? 0,
        } : undefined,
      };
    }

    return null;
  }

  private buildRequest(request: StreamRequest): {
    url: string;
    headers: Record<string, string>;
    body: string;
  } {
    if (this.provider.sseFormat === 'anthropic') {
      return this.buildAnthropicRequest(request);
    }
    return this.buildOpenAIRequest(request);
  }

  private buildAnthropicRequest(request: StreamRequest): {
    url: string;
    headers: Record<string, string>;
    body: string;
  } {
    const url = `${this.provider.baseUrl}/v1/messages`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'x-api-key': this.provider.apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-beta': 'prompt-caching-2024-07-31',
    };

    // OpenRouter uses Authorization header instead of x-api-key
    if (this.provider.type === 'openrouter') {
      delete headers['x-api-key'];
      headers['Authorization'] = `Bearer ${this.provider.apiKey}`;
    }

    // Strip internal fields from tool definitions for the API
    const tools = request.tools.map(t => ({
      name: t.name,
      description: t.description,
      input_schema: t.input_schema,
      ...(t.cache_control ? { cache_control: t.cache_control } : {}),
    }));

    const body = JSON.stringify({
      model: this.provider.model,
      max_tokens: request.maxTokens,
      stream: true,
      system: request.system,
      messages: request.messages,
      ...(tools.length > 0 ? { tools } : {}),
      ...(request.temperature !== undefined ? { temperature: request.temperature } : {}),
    });

    return { url, headers, body };
  }

  private buildOpenAIRequest(request: StreamRequest): {
    url: string;
    headers: Record<string, string>;
    body: string;
  } {
    const base = this.provider.baseUrl.replace(/\/+$/, '');
    const url = `${base}/chat/completions`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.provider.apiKey}`,
    };

    // Convert Anthropic system blocks → OpenAI system message
    const systemText = request.system.map(b => b.text).join('\n\n');

    // Convert Anthropic messages → OpenAI messages
    const messages = this.convertMessagesToOpenAI(systemText, request.messages);

    // Convert tool definitions → OpenAI format
    const tools = request.tools.map(t => ({
      type: 'function' as const,
      function: {
        name: t.name,
        description: t.description,
        parameters: t.input_schema,
      },
    }));

    const body = JSON.stringify({
      model: this.provider.model,
      max_tokens: request.maxTokens,
      stream: true,
      messages,
      ...(tools.length > 0 ? { tools } : {}),
      ...(request.temperature !== undefined ? { temperature: request.temperature } : {}),
    });

    return { url, headers, body };
  }

  private convertMessagesToOpenAI(
    systemText: string,
    messages: Message[],
  ): Record<string, unknown>[] {
    const result: Record<string, unknown>[] = [];

    if (systemText) {
      result.push({ role: 'system', content: systemText });
    }

    for (const msg of messages) {
      if (typeof msg.content === 'string') {
        result.push({ role: msg.role, content: msg.content });
        continue;
      }

      // Complex content blocks
      if (msg.role === 'assistant') {
        // Extract text and tool_use blocks
        const textParts: string[] = [];
        const toolCalls: Record<string, unknown>[] = [];

        for (const block of msg.content) {
          if (block.type === 'text') {
            textParts.push(block.text);
          } else if (block.type === 'tool_use') {
            toolCalls.push({
              id: block.id,
              type: 'function',
              function: {
                name: block.name,
                arguments: JSON.stringify(block.input),
              },
            });
          }
        }

        const entry: Record<string, unknown> = {
          role: 'assistant',
          content: textParts.join('\n') || null,
        };
        if (toolCalls.length > 0) entry.tool_calls = toolCalls;
        result.push(entry);
      } else {
        // User message with tool_result blocks
        for (const block of msg.content) {
          if (block.type === 'tool_result') {
            result.push({
              role: 'tool',
              tool_call_id: block.tool_use_id,
              content: block.content,
            });
          } else if (block.type === 'text') {
            result.push({ role: 'user', content: block.text });
          }
        }
      }
    }

    return result;
  }
}
