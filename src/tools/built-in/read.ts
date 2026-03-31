import { readFileSync, statSync } from 'node:fs';
import type { ToolDefinition, ToolExecutor } from '../../core/types.js';

const MAX_LINES = 2000;

export const readToolDefinition: ToolDefinition = {
  name: 'Read',
  description:
    'Reads a file from the local filesystem. Returns contents with line numbers (cat -n format). ' +
    'Use offset and limit to page through large files.',
  input_schema: {
    type: 'object',
    properties: {
      file_path: {
        type: 'string',
        description: 'Absolute path to the file to read',
      },
      offset: {
        type: 'number',
        description: 'Line number to start reading from (1-based). Only needed for large files.',
      },
      limit: {
        type: 'number',
        description: 'Max number of lines to read. Defaults to 2000.',
      },
    },
    required: ['file_path'],
  },
  category: 'safe',
};

export const readToolExecutor: ToolExecutor = async (input) => {
  const filePath = input.file_path as string;
  const offset = (input.offset as number | undefined) ?? 1;
  const limit = (input.limit as number | undefined) ?? MAX_LINES;

  if (!filePath) return 'Error: file_path is required';

  try {
    const stat = statSync(filePath);
    if (stat.isDirectory()) {
      return `Error: ${filePath} is a directory, not a file. Use Bash with 'ls' to list directory contents.`;
    }

    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n');

    // offset is 1-based
    const startIdx = Math.max(0, offset - 1);
    const endIdx = Math.min(lines.length, startIdx + limit);
    const slice = lines.slice(startIdx, endIdx);

    // Format with line numbers (cat -n style)
    const numbered = slice.map((line, i) => {
      const lineNum = startIdx + i + 1;
      return `${lineNum}\t${line}`;
    });

    let result = numbered.join('\n');

    if (endIdx < lines.length) {
      result += `\n\n... (${lines.length - endIdx} more lines. Use offset=${endIdx + 1} to continue.)`;
    }

    if (!content.trim()) {
      result = '(empty file)';
    }

    return result;
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes('ENOENT')) return `Error: file not found: ${filePath}`;
    if (msg.includes('EACCES')) return `Error: permission denied: ${filePath}`;
    return `Error reading file: ${msg}`;
  }
};
