// ── Content Blocks ──

export interface TextBlock {
  type: 'text';
  text: string;
  cache_control?: { type: 'ephemeral' };
}

export interface ToolUseBlock {
  type: 'tool_use';
  id: string;
  name: string;
  input: Record<string, unknown>;
}

export interface ToolResultBlock {
  type: 'tool_result';
  tool_use_id: string;
  content: string;
  is_error?: boolean;
  cache_control?: { type: 'ephemeral' };
}

export type ContentBlock = TextBlock | ToolUseBlock | ToolResultBlock;

// ── Messages ──

export interface Message {
  role: 'user' | 'assistant';
  content: string | ContentBlock[];
}

// ── System Prompt ──

export interface SystemBlock {
  type: 'text';
  text: string;
  cache_control?: { type: 'ephemeral' };
}

// ── Tools ──

export type ToolCategory = 'safe' | 'dangerous' | 'write' | 'bypass';

export interface ToolDefinition {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  cache_control?: { type: 'ephemeral' };
  category: ToolCategory;
  deferred?: boolean;
}

export type ToolExecutor = (input: Record<string, unknown>) => Promise<string>;

export interface ToolCallRecord {
  name: string;
  input: Record<string, unknown>;
  result: string;
}

// ── SSE Events ──

export interface SSEEvent {
  type: string;
  index?: number;
  delta?: Record<string, unknown>;
  content_block?: Record<string, unknown>;
  message?: Record<string, unknown>;
  usage?: TokenUsage;
}

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  cache_creation_input_tokens?: number;
  cache_read_input_tokens?: number;
}

// ── Stop Reasons ──

export type StopReason = 'end_turn' | 'tool_use' | 'max_tokens' | 'stop_sequence';

// ── Agent Loop ──

export interface AgentLoopResult {
  messages: Message[];
  finalText: string;
  toolCalls: ToolCallRecord[];
  usage: {
    inputTokens: number;
    outputTokens: number;
    cacheHits: number;
    cacheCreation: number;
  };
  iterations: number;
}

// ── Provider Config ──

export type ProviderType = 'anthropic' | 'openrouter' | 'openai-compat';
export type SSEFormat = 'anthropic' | 'openai';

export interface ProviderConfig {
  type: ProviderType;
  apiKey: string;
  baseUrl: string;
  model: string;
  sseFormat: SSEFormat;
}

// ── Permission Modes ──

export type PermissionMode = 'default' | 'auto' | 'plan';

// ── App Config ──

export interface AnvilConfig {
  provider: ProviderConfig;
  permissionMode: PermissionMode;
  maxIterations: number;
  maxTokens: number;
  compactThreshold: number;
  contextWindow: number;
}
