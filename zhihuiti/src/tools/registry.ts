import type { ToolDefinition, ToolExecutor } from '../core/types.js';
import { readToolDefinition, readToolExecutor } from './built-in/read.js';
import { writeToolDefinition, writeToolExecutor } from './built-in/write.js';
import { bashToolDefinition, bashToolExecutor } from './built-in/bash.js';

interface RegisteredTool {
  definition: ToolDefinition;
  executor: ToolExecutor;
}

/**
 * Tool registry: holds all tool definitions and dispatches execution.
 *
 * Tools are registered at startup. The registry provides:
 * - getActiveDefinitions(): tool defs to send in API requests (excludes deferred)
 * - execute(): dispatch by name to the correct executor
 */
export class ToolRegistry {
  private tools = new Map<string, RegisteredTool>();

  constructor() {
    // Register built-in tools
    this.register(readToolDefinition, readToolExecutor);
    this.register(writeToolDefinition, writeToolExecutor);
    this.register(bashToolDefinition, bashToolExecutor);
  }

  register(definition: ToolDefinition, executor: ToolExecutor): void {
    this.tools.set(definition.name, { definition, executor });
  }

  /**
   * Returns tool definitions to include in API requests.
   * Deferred tools are excluded — they're loaded on-demand via ToolSearch.
   */
  getActiveDefinitions(): ToolDefinition[] {
    const defs: ToolDefinition[] = [];
    for (const { definition } of this.tools.values()) {
      if (!definition.deferred) {
        defs.push({ ...definition });
      }
    }
    return defs;
  }

  getDefinition(name: string): ToolDefinition | undefined {
    return this.tools.get(name)?.definition;
  }

  getCategory(name: string): ToolDefinition['category'] | undefined {
    return this.tools.get(name)?.definition.category;
  }

  has(name: string): boolean {
    return this.tools.has(name);
  }

  async execute(name: string, input: Record<string, unknown>): Promise<string> {
    const tool = this.tools.get(name);
    if (!tool) return `Error: unknown tool "${name}"`;

    try {
      return await tool.executor(input);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return `Error executing tool ${name}: ${msg}`;
    }
  }
}
