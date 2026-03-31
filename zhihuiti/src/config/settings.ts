import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { DEFAULT_CONFIG } from './defaults.js';
import type { AnvilConfig, ProviderConfig } from '../core/types.js';

function loadEnv(dir: string): Record<string, string> {
  const envPath = resolve(dir, '.env');
  if (!existsSync(envPath)) return {};

  const vars: Record<string, string> = {};
  const content = readFileSync(envPath, 'utf-8');
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    let value = trimmed.slice(eqIdx + 1).trim();
    // Strip surrounding quotes
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    vars[key] = value;
  }
  return vars;
}

function loadProjectConfig(dir: string): Partial<AnvilConfig> {
  const configPath = resolve(dir, '.anvil', 'config.json');
  if (!existsSync(configPath)) return {};

  try {
    const raw = readFileSync(configPath, 'utf-8');
    return JSON.parse(raw) as Partial<AnvilConfig>;
  } catch {
    return {};
  }
}

function resolveProvider(env: Record<string, string>, overrides?: Partial<ProviderConfig>): ProviderConfig {
  // If explicit overrides specify a type, use that
  if (overrides?.type) {
    const base = { ...DEFAULT_CONFIG.provider, ...overrides };
    if (!base.apiKey) {
      if (base.type === 'anthropic') {
        base.apiKey = env['ANTHROPIC_API_KEY'] || process.env['ANTHROPIC_API_KEY'] || '';
      } else if (base.type === 'openrouter') {
        base.apiKey = env['OPENROUTER_API_KEY'] || process.env['OPENROUTER_API_KEY'] || '';
        base.baseUrl = base.baseUrl || 'https://openrouter.ai/api/v1';
        base.sseFormat = 'openai';
      } else {
        base.apiKey = env['LLM_API_KEY'] || process.env['LLM_API_KEY'] || '';
        base.sseFormat = 'openai';
      }
    }
    return base;
  }

  // Auto-detect provider from available keys (priority: OpenRouter > Anthropic > OpenAI-compat)
  const openrouterKey = env['OPENROUTER_API_KEY'] || process.env['OPENROUTER_API_KEY'];
  if (openrouterKey) {
    return {
      ...DEFAULT_CONFIG.provider,
      ...overrides,
      type: 'openrouter',
      apiKey: openrouterKey,
      baseUrl: overrides?.baseUrl || 'https://openrouter.ai/api/v1',
      model: overrides?.model || env['OPENROUTER_MODEL'] || 'anthropic/claude-sonnet-4-20250514',
      sseFormat: 'anthropic',
    };
  }

  const anthropicKey = env['ANTHROPIC_API_KEY'] || process.env['ANTHROPIC_API_KEY'];
  if (anthropicKey) {
    return {
      ...DEFAULT_CONFIG.provider,
      ...overrides,
      type: 'anthropic',
      apiKey: anthropicKey,
      baseUrl: overrides?.baseUrl || 'https://api.anthropic.com',
      model: overrides?.model || env['ANTHROPIC_MODEL'] || DEFAULT_CONFIG.provider.model,
      sseFormat: 'anthropic',
    };
  }

  const llmKey = env['LLM_API_KEY'] || process.env['LLM_API_KEY'];
  const llmBase = env['LLM_BASE_URL'] || process.env['LLM_BASE_URL'];
  if (llmKey && llmBase) {
    return {
      ...DEFAULT_CONFIG.provider,
      ...overrides,
      type: 'openai-compat',
      apiKey: llmKey,
      baseUrl: overrides?.baseUrl || llmBase,
      model: overrides?.model || env['LLM_MODEL'] || 'default',
      sseFormat: 'openai',
    };
  }

  // No keys found — return defaults (will fail with "no API key" error)
  return { ...DEFAULT_CONFIG.provider, ...overrides };
}

export function loadConfig(projectDir: string = process.cwd()): AnvilConfig {
  const env = loadEnv(projectDir);
  const projectConfig = loadProjectConfig(projectDir);

  const provider = resolveProvider(env, projectConfig.provider);

  return {
    ...DEFAULT_CONFIG,
    ...projectConfig,
    provider,
  };
}
