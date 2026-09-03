#!/usr/bin/env node
// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createProtocol as protocol, serve } from '../../../shared/mcp.mjs';
export { serve };
export const createProtocol = options => protocol({ host: 'claude', ...options });
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const manifest = JSON.parse(await fs.readFile(new URL('./.claude-plugin/plugin.json', import.meta.url), 'utf8'));
  serve(createProtocol({ version: manifest.version }));
}
