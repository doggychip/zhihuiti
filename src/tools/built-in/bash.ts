import { spawn } from 'node:child_process';
import type { ToolDefinition, ToolExecutor } from '../../core/types.js';

const DEFAULT_TIMEOUT_MS = 120_000; // 2 minutes
const MAX_OUTPUT_BYTES = 100_000;   // ~100KB output cap

export const bashToolDefinition: ToolDefinition = {
  name: 'Bash',
  description:
    'Executes a shell command and returns its output (stdout + stderr combined). ' +
    'Default timeout is 120 seconds. Use for system commands and operations ' +
    'that require shell execution.',
  input_schema: {
    type: 'object',
    properties: {
      command: {
        type: 'string',
        description: 'The shell command to execute',
      },
      timeout: {
        type: 'number',
        description: 'Timeout in milliseconds (max 600000). Default: 120000.',
      },
    },
    required: ['command'],
  },
  category: 'dangerous',
};

export const bashToolExecutor: ToolExecutor = async (input) => {
  const command = input.command as string;
  const timeout = Math.min(
    (input.timeout as number | undefined) ?? DEFAULT_TIMEOUT_MS,
    600_000,
  );

  if (!command) return 'Error: command is required';

  return new Promise<string>((resolve) => {
    const shell = process.env['SHELL'] || '/bin/sh';
    const child = spawn(shell, ['-c', command], {
      cwd: process.cwd(),
      env: process.env,
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout,
    });

    const chunks: Buffer[] = [];
    let totalBytes = 0;
    let truncated = false;

    const collect = (data: Buffer) => {
      if (truncated) return;
      totalBytes += data.length;
      if (totalBytes > MAX_OUTPUT_BYTES) {
        truncated = true;
        const remaining = MAX_OUTPUT_BYTES - (totalBytes - data.length);
        if (remaining > 0) chunks.push(data.subarray(0, remaining));
      } else {
        chunks.push(data);
      }
    };

    child.stdout.on('data', collect);
    child.stderr.on('data', collect);

    // Close stdin immediately — we don't support interactive commands
    child.stdin.end();

    child.on('error', (err) => {
      if (err.message.includes('ETIMEDOUT') || err.message.includes('killed')) {
        resolve(`Error: command timed out after ${timeout}ms`);
      } else {
        resolve(`Error: ${err.message}`);
      }
    });

    child.on('close', (code) => {
      let output = Buffer.concat(chunks).toString('utf-8');
      if (truncated) {
        output += `\n\n... (output truncated at ${MAX_OUTPUT_BYTES} bytes)`;
      }

      if (code !== 0 && code !== null) {
        if (!output.trim()) {
          resolve(`Exit code ${code}`);
        } else {
          resolve(`Exit code ${code}\n${output}`);
        }
      } else {
        resolve(output || '(no output)');
      }
    });
  });
};
