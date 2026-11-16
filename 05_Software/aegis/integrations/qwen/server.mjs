#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createProtocol as protocol, serve } from '../shared/mcp.mjs';
export { serve };
export const createProtocol = options => protocol({ host: 'qwen', ...options });
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const manifest = JSON.parse(await fs.readFile(new URL('./qwen-extension.json', import.meta.url), 'utf8'));
  serve(createProtocol({ version: manifest.version }));
}
