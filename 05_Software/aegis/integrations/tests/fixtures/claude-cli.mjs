// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
// Test-only native CLI seam; no authentication or model access.
import fs from 'node:fs/promises';
import path from 'node:path';
const root = process.env.CLAUDE_CONFIG_DIR;
const stateFile = path.join(root, 'fixture-state.json');
let state;
try { state = JSON.parse(await fs.readFile(stateFile, 'utf8')); }
catch { state = { catalogs: [], plugins: [] }; }
const args = process.argv.slice(2);
const output = value => console.log(JSON.stringify(value));
if (args[0] === '--version') console.log('2.1.259 (Claude Code fixture)');
else if (args[1] === 'marketplace') {
  if (args[2] === 'list') output(state.catalogs);
  else if (args[2] === 'add') state.catalogs = [{ name: 'aegis-claude', source: 'directory', path: args[3] }];
  else if (args[2] === 'remove') state.catalogs = [];
} else if (args[1] === 'list') output(state.plugins);
else if (args[1] === 'install') {
  if (state.failInstall) { console.error('Fixture registration failure'); process.exitCode = 1; }
  else {
    const source = path.join(state.catalogs[0].path, 'plugins/aegis');
    const { version } = JSON.parse(await fs.readFile(path.join(source, '.claude-plugin/plugin.json'), 'utf8'));
    const installPath = path.join(root, 'plugins/cache/aegis-claude/aegis', version);
    await fs.cp(source, installPath, { recursive: true });
    state.plugins = [{ id: 'aegis@aegis-claude', scope: 'user', enabled: true, installPath }];
  }
} else if (args[1] === 'uninstall') {
  for (const item of state.plugins) await fs.writeFile(path.join(item.installPath, '.orphaned_at'), String(Date.now()));
  state.plugins = [];
} else if (args[1] === 'disable') state.plugins[0].enabled = false;
else throw new Error('Unexpected fixture command: ' + args.join(' '));
await fs.writeFile(stateFile, JSON.stringify(state));
