import type {
  Message,
  TextBlock,
  ToolUseBlock,
  ToolResultBlock,
  ContentBlock,
  StopReason,
  AgentLoopResult,
  AnvilConfig,
  TokenUsage,
} from './types.js';
import { SSEClient } from './sse-client.js';
import { SystemPromptBuilder } from './system-prompt.js';
import { ContextManager } from './context-manager.js';
import { compactMessages } from './compact.js';
import { ToolRegistry } from '../tools/registry.js';
import { checkPermission, type PermissionResult } from '../tools/permissions.js';

/** Callback for streaming text to the terminal. */
export type OnText = (text: string) => void;

/** Callback for displaying tool calls before execution. */
export type OnToolCall = (name: string, input: Record<string, unknown>) => void;

/** Callback for prompting user permission. Returns true if allowed. */
export type OnPermissionRequest = (
  toolName: string,
  input: Record<string, unknown>,
) => Promise<boolean>;

export interface AgentLoopOptions {
  config: AnvilConfig;
  onText?: OnText;
  onToolCall?: OnToolCall;
  onPermissionRequest?: OnPermissionRequest;
}

export class AgentLoop {
  private sseClient: SSEClient;
  private systemPrompt: SystemPromptBuilder;
  private toolRegistry: ToolRegistry;
  private contextManager: ContextManager;
  private config: AnvilConfig;
  private onText: OnText;
  private onToolCall: OnToolCall;
  private onPermissionRequest: OnPermissionRequest;

  constructor(options: AgentLoopOptions) {
    this.config = options.config;
    this.sseClient = new SSEClient(options.config.provider);
    this.systemPrompt = new SystemPromptBuilder();
    this.toolRegistry = new ToolRegistry();
    this.contextManager = new ContextManager(
      options.config.contextWindow,
      options.config.compactThreshold,
    );
    this.onText = options.onText ?? (() => {});
    this.onToolCall = options.onToolCall ?? (() => {});
    this.onPermissionRequest = options.onPermissionRequest ?? (async () => true);
  }

  async run(userMessage: string): Promise<AgentLoopResult> {
    const messages: Message[] = [{ role: 'user', content: userMessage }];
    return this.loop(messages);
  }

  /** Continue a conversation with an additional user message. */
  async continueWith(messages: Message[], userMessage: string): Promise<AgentLoopResult> {
    messages.push({ role: 'user', content: userMessage });
    return this.loop(messages);
  }

  private async loop(messages: Message[]): Promise<AgentLoopResult> {
    let iterations = 0;
    const allToolCalls: AgentLoopResult['toolCalls'] = [];
    let finalText = '';

    while (iterations < this.config.maxIterations) {
      iterations++;

      // ── 1. Check context, compact if needed ──
      if (this.contextManager.shouldCompact(messages)) {
        const compacted = await compactMessages(messages, this.config.provider);
        messages.length = 0;
        messages.push(...compacted);
      }

      // ── 2. Build request ──
      const system = this.systemPrompt.buildBlocks();
      const tools = this.toolRegistry.getActiveDefinitions();

      // Cache optimization: mark last tool definition with cache_control
      if (tools.length > 0) {
        tools[tools.length - 1].cache_control = { type: 'ephemeral' };
      }

      // ── 3. Stream API call ──
      const responseBlocks: ContentBlock[] = [];
      let stopReason: StopReason = 'end_turn';
      let currentText = '';
      let currentToolId = '';
      let currentToolName = '';
      let currentToolJson = '';
      let blockIndex = -1;

      try {
        for await (const event of this.sseClient.stream({
          system,
          messages,
          tools,
          maxTokens: this.config.maxTokens,
        })) {
          switch (event.type) {
            case 'message_start': {
              // Record initial usage from message_start
              if (event.usage) {
                this.contextManager.recordUsage(event.usage);
              }
              // Also check nested message.usage
              const msg = event.message as Record<string, unknown> | undefined;
              if (msg?.usage) {
                this.contextManager.recordUsage(msg.usage as TokenUsage);
              }
              break;
            }

            case 'content_block_start': {
              const block = event.content_block as Record<string, unknown> | undefined;
              blockIndex = event.index ?? blockIndex + 1;

              if (block?.type === 'text') {
                currentText = '';
              } else if (block?.type === 'tool_use') {
                currentToolId = (block.id as string) ?? '';
                currentToolName = (block.name as string) ?? '';
                currentToolJson = '';
              }
              break;
            }

            case 'content_block_delta': {
              const delta = event.delta as Record<string, unknown> | undefined;
              if (!delta) break;

              if (delta.type === 'text_delta') {
                const text = (delta.text as string) ?? '';
                currentText += text;
                this.onText(text);
              } else if (delta.type === 'input_json_delta') {
                currentToolJson += (delta.partial_json as string) ?? '';
              }
              break;
            }

            case 'content_block_stop': {
              // Finalize the current block
              if (currentText) {
                responseBlocks.push({
                  type: 'text',
                  text: currentText,
                } as TextBlock);
                finalText = currentText; // track last text output
                currentText = '';
              }

              if (currentToolName) {
                let toolInput: Record<string, unknown> = {};
                try {
                  toolInput = currentToolJson ? JSON.parse(currentToolJson) : {};
                } catch {
                  toolInput = { _raw: currentToolJson };
                }

                responseBlocks.push({
                  type: 'tool_use',
                  id: currentToolId,
                  name: currentToolName,
                  input: toolInput,
                } as ToolUseBlock);

                currentToolId = '';
                currentToolName = '';
                currentToolJson = '';
              }
              break;
            }

            case 'message_delta': {
              const delta = event.delta as Record<string, unknown> | undefined;
              if (delta?.stop_reason) {
                stopReason = delta.stop_reason as StopReason;
              }
              if (event.usage) {
                this.contextManager.recordUsage(event.usage);
              }
              break;
            }
          }
        }

        // Flush any pending blocks after stream ends (critical for OpenAI format
        // which doesn't emit content_block_start/stop events)
        this.flushPendingBlocks(
          currentText, currentToolId, currentToolName, currentToolJson,
          responseBlocks,
        );
        if (currentText) finalText = currentText;

      } catch (err) {
        const errMsg = err instanceof Error ? err.message : String(err);
        // If API call fails entirely, break the loop with error text
        finalText = `Error: API call failed — ${errMsg}`;
        this.onText(`\n${finalText}\n`);
        break;
      }

      // ── 4. Append assistant message ──
      if (responseBlocks.length > 0) {
        messages.push({ role: 'assistant', content: responseBlocks });
      }

      // ── 5. Check stop reason ──
      if (stopReason === 'end_turn' || stopReason === 'max_tokens') {
        break;
      }

      // ── 6. Execute tools ──
      if (stopReason === 'tool_use') {
        const toolResults: ToolResultBlock[] = [];

        for (const block of responseBlocks) {
          if (block.type !== 'tool_use') continue;

          const toolUse = block as ToolUseBlock;

          // Phase 1: Display
          this.onToolCall(toolUse.name, toolUse.input);

          // Phase 2: Permission check
          const category = this.toolRegistry.getCategory(toolUse.name);
          if (!category) {
            toolResults.push({
              type: 'tool_result',
              tool_use_id: toolUse.id,
              content: `Error: unknown tool "${toolUse.name}"`,
              is_error: true,
            });
            continue;
          }

          const permission = checkPermission(
            this.config.permissionMode,
            toolUse.name,
            category,
            toolUse.input,
          );

          const allowed = await this.resolvePermission(permission, toolUse.name, toolUse.input);
          if (!allowed) {
            toolResults.push({
              type: 'tool_result',
              tool_use_id: toolUse.id,
              content: 'Permission denied by user.',
              is_error: true,
            });
            continue;
          }

          // Phase 5: Execute
          const result = await this.toolRegistry.execute(toolUse.name, toolUse.input);

          toolResults.push({
            type: 'tool_result',
            tool_use_id: toolUse.id,
            content: result,
          });

          allToolCalls.push({
            name: toolUse.name,
            input: toolUse.input,
            result,
          });
        }

        // Cache optimization: mark last tool_result with cache_control
        if (toolResults.length > 0) {
          toolResults[toolResults.length - 1].cache_control = { type: 'ephemeral' };
        }

        messages.push({ role: 'user', content: toolResults });
      }
    }

    return {
      messages,
      finalText,
      toolCalls: allToolCalls,
      usage: this.contextManager.getUsage(),
      iterations,
    };
  }

  private flushPendingBlocks(
    currentText: string,
    currentToolId: string,
    currentToolName: string,
    currentToolJson: string,
    responseBlocks: ContentBlock[],
  ): void {
    if (currentText) {
      responseBlocks.push({ type: 'text', text: currentText } as TextBlock);
    }
    if (currentToolName) {
      let toolInput: Record<string, unknown> = {};
      try {
        toolInput = currentToolJson ? JSON.parse(currentToolJson) : {};
      } catch {
        toolInput = { _raw: currentToolJson };
      }
      responseBlocks.push({
        type: 'tool_use',
        id: currentToolId || `tool_${Date.now()}`,
        name: currentToolName,
        input: toolInput,
      } as ToolUseBlock);
    }
  }

  private async resolvePermission(
    result: PermissionResult,
    toolName: string,
    input: Record<string, unknown>,
  ): Promise<boolean> {
    switch (result) {
      case 'allow':
        return true;
      case 'deny':
        return false;
      case 'ask_user':
        return this.onPermissionRequest(toolName, input);
    }
  }
}
