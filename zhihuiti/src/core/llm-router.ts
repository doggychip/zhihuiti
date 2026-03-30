import { SSEClient } from './sse-client.js';
import type { ProviderConfig, AnvilConfig } from './types.js';

/**
 * Multi-provider LLM router.
 *
 * Creates SSEClient instances for the configured provider.
 * Supports fallback: if primary provider fails with a non-4xx error,
 * try the next configured provider.
 */

export interface LLMRouter {
  primary: SSEClient;
  fallback?: SSEClient;
  activeProvider: ProviderConfig;
}

export function createRouter(config: AnvilConfig): LLMRouter {
  const primary = new SSEClient(config.provider);

  return {
    primary,
    activeProvider: config.provider,
  };
}

/**
 * Create a router with an explicit fallback provider.
 * Useful for e.g. Anthropic primary + OpenRouter fallback.
 */
export function createRouterWithFallback(
  primary: ProviderConfig,
  fallback: ProviderConfig,
): LLMRouter {
  return {
    primary: new SSEClient(primary),
    fallback: new SSEClient(fallback),
    activeProvider: primary,
  };
}

/**
 * Build a provider config from environment variables.
 * Detects which providers are available based on API keys.
 */
export function detectProviders(env: Record<string, string | undefined>): ProviderConfig[] {
  const providers: ProviderConfig[] = [];

  const anthropicKey = env['ANTHROPIC_API_KEY'];
  if (anthropicKey) {
    providers.push({
      type: 'anthropic',
      apiKey: anthropicKey,
      baseUrl: 'https://api.anthropic.com',
      model: env['ANTHROPIC_MODEL'] || 'claude-sonnet-4-20250514',
      sseFormat: 'anthropic',
    });
  }

  const openrouterKey = env['OPENROUTER_API_KEY'];
  if (openrouterKey) {
    providers.push({
      type: 'openrouter',
      apiKey: openrouterKey,
      baseUrl: 'https://openrouter.ai/api/v1',
      model: env['OPENROUTER_MODEL'] || 'anthropic/claude-sonnet-4-20250514',
      sseFormat: 'anthropic',
    });
  }

  const compatKey = env['LLM_API_KEY'];
  const compatBase = env['LLM_BASE_URL'];
  if (compatKey && compatBase) {
    providers.push({
      type: 'openai-compat',
      apiKey: compatKey,
      baseUrl: compatBase,
      model: env['LLM_MODEL'] || 'default',
      sseFormat: 'openai',
    });
  }

  return providers;
}
