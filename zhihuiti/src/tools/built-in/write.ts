import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import type { ToolDefinition, ToolExecutor } from '../../core/types.js';

export const writeToolDefinition: ToolDefinition = {
  name: 'Write',
  description:
    'Writes content to a file. Creates parent directories if needed. ' +
    'Overwrites the file if it already exists. Use Edit for partial modifications.',
  input_schema: {
    type: 'object',
    properties: {
      file_path: {
        type: 'string',
        description: 'Absolute path to the file to write',
      },
      content: {
        type: 'string',
        description: 'The full content to write to the file',
      },
    },
    required: ['file_path', 'content'],
  },
  category: 'write',
};

export const writeToolExecutor: ToolExecutor = async (input) => {
  const filePath = input.file_path as string;
  const content = input.content as string;

  if (!filePath) return 'Error: file_path is required';
  if (content === undefined || content === null) return 'Error: content is required';

  try {
    // Ensure parent directories exist
    mkdirSync(dirname(filePath), { recursive: true });
    writeFileSync(filePath, content, 'utf-8');
    return `File written successfully: ${filePath}`;
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return `Error writing file: ${msg}`;
  }
};
