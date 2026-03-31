/**
 * ANSI color theme. No dependencies — raw escape codes.
 * Node.js 22 supports these in all modern terminals.
 */

const ESC = '\x1b[';
const RESET = `${ESC}0m`;

// Check if color output is supported
const NO_COLOR = 'NO_COLOR' in process.env;
const FORCE_COLOR = 'FORCE_COLOR' in process.env;
const isTTY = process.stdout.isTTY ?? false;
const colorEnabled = FORCE_COLOR || (isTTY && !NO_COLOR);

function wrap(code: string, text: string): string {
  if (!colorEnabled) return text;
  return `${ESC}${code}m${text}${RESET}`;
}

// ── Foreground colors ──
export const dim = (t: string) => wrap('2', t);
export const bold = (t: string) => wrap('1', t);
export const italic = (t: string) => wrap('3', t);
export const underline = (t: string) => wrap('4', t);

export const red = (t: string) => wrap('31', t);
export const green = (t: string) => wrap('32', t);
export const yellow = (t: string) => wrap('33', t);
export const blue = (t: string) => wrap('34', t);
export const magenta = (t: string) => wrap('35', t);
export const cyan = (t: string) => wrap('36', t);
export const white = (t: string) => wrap('37', t);
export const gray = (t: string) => wrap('90', t);

// ── Semantic aliases ──
export const error = (t: string) => bold(red(t));
export const warn = (t: string) => yellow(t);
export const success = (t: string) => green(t);
export const info = (t: string) => cyan(t);
export const muted = (t: string) => dim(t);
export const label = (t: string) => bold(white(t));
export const toolName = (t: string) => bold(magenta(t));
export const filePath = (t: string) => underline(cyan(t));
