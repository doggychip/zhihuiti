import type { AnvilConfig, ProviderConfig } from '../core/types.js';

export const DEFAULT_PROVIDER: ProviderConfig = {
  type: 'anthropic',
  apiKey: '',
  baseUrl: 'https://api.anthropic.com',
  model: 'claude-sonnet-4-20250514',
  sseFormat: 'anthropic',
};

export const DEFAULT_CONFIG: AnvilConfig = {
  provider: DEFAULT_PROVIDER,
  permissionMode: 'default',
  maxIterations: 25,
  maxTokens: 8192,
  compactThreshold: 0.85,
  contextWindow: 200_000,
};
