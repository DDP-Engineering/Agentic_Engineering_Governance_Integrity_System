#!/usr/bin/env node
// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = path.join(repo, '05_Software/aegis/integrations');
const version = (await fs.readFile(path.join(repo, '05_Software/aegis/template/.agentic/aegis.py'), 'utf8')).match(/^VERSION\s*=\s*["']([^"']+)/m)[1];
const index = process.argv.indexOf('--output');
const output = path.resolve(index >= 0 ? process.argv[index + 1] : path.join(repo, '07_Delivery/agent-plugins-unreleased'));
await fs.mkdir(output, { recursive: true });
const copy = async (from, to) => { await fs.mkdir(path.dirname(to), { recursive: true }); await fs.cp(from, to, { recursive: true }); };
const write = async (name, text) => { await fs.mkdir(path.dirname(name), { recursive: true }); await fs.writeFile(name, text); };
const hosts = ['opencode', 'codex', 'pi', 'qwen', 'claude'];
for (const host of hosts) {
  const target = path.join(output, `aegis-${host}`);
  // Refuse stale output rather than silently mixing releases or deleting user files.
  try { await fs.mkdir(target); } catch (e) { if (e.code === 'EEXIST') throw new Error(`Output already exists: ${target}; choose a fresh --output directory.`); throw e; }
  await copy(path.join(source, host), target);
  const nested = ['codex', 'claude'].includes(host);
  const shared = nested ? path.join(target, 'plugins/aegis/lib') : path.join(target, 'lib');
  for (const item of await fs.readdir(path.join(source, 'shared'))) await copy(path.join(source, 'shared', item), path.join(shared, item));
  let setup = await fs.readFile(path.join(target, 'setup.mjs'), 'utf8');
  setup = setup.replaceAll('../shared/', nested ? './plugins/aegis/lib/' : './lib/');
  await write(path.join(target, 'setup.mjs'), setup);
  await copy(path.join(repo, 'LICENSE.txt'), path.join(target, 'LICENSE.txt'));
  await copy(path.join(source, 'shared/vendor/LICENSES.txt'), path.join(target, 'THIRD-PARTY-NOTICES.txt'));
  if (host === 'opencode') {
    let entry = await fs.readFile(path.join(target, 'plugin.mjs'), 'utf8');
    entry = entry.replaceAll('../shared/', './lib/');
    await write(path.join(target, 'index.mjs'), entry);
    await fs.unlink(path.join(target, 'plugin.mjs'));
    await write(path.join(target, 'package.json'), JSON.stringify({ name: '@aegis/opencode-plugin', version, private: true, type: 'module', main: './index.mjs', exports: './index.mjs', engines: { node: '>=22' }, license: 'LicenseRef-PolyForm-Noncommercial-1.0.0' }, null, 2) + '\n');
  } else if (nested) {
    const manifestFile = path.join(target, `plugins/aegis/.${host === 'codex' ? 'codex' : 'claude'}-plugin/plugin.json`);
    const manifest = JSON.parse(await fs.readFile(manifestFile, 'utf8')); manifest.version = version;
    await write(manifestFile, JSON.stringify(manifest, null, 2) + '\n');
    await copy(path.join(repo, 'LICENSE.txt'), path.join(target, 'plugins/aegis/LICENSE.txt'));
    if (host === 'claude') {
      for (const [file, before, after] of [['plugins/aegis/server.mjs', '../../../shared/', './lib/'], ['cache.mjs', '../shared/', './plugins/aegis/lib/']]) {
        const location = path.join(target, file);
        await write(location, (await fs.readFile(location, 'utf8')).replaceAll(before, after));
      }
    }
  } else {
    const manifestFile = path.join(target, host === 'pi' ? 'package.json' : 'qwen-extension.json');
    const manifest = JSON.parse(await fs.readFile(manifestFile, 'utf8')); manifest.version = version;
    await write(manifestFile, JSON.stringify(manifest, null, 2) + '\n');
    for (const file of ['extension.mjs', 'review.mjs', 'server.mjs']) {
      const location = path.join(target, file);
      try { await write(location, (await fs.readFile(location, 'utf8')).replaceAll('../shared/', './lib/')); }
      catch (error) { if (error.code !== 'ENOENT') throw error; }
    }
  }
  await write(path.join(target, 'install.sh'), '#!/bin/sh\nset -eu\nHERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec node "$HERE/setup.mjs" install "$@"\n');
  await write(path.join(target, 'Install-AEGIS.cmd'), '@echo off\r\nnode "%~dp0setup.mjs" install %*\r\nif errorlevel 1 (\r\n  pause\r\n  exit /b 1\r\n)\r\necho Restart the application and open a new session.\r\npause\r\n');
}
console.log(JSON.stringify({ output, version, hosts, models_invoked: false }));
