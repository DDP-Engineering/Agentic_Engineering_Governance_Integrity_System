// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const exec = promisify(execFile);
export const defaultConfigDir = () => process.env.OPENCODE_CONFIG_DIR || path.join(process.env.XDG_CONFIG_HOME || path.join(os.homedir(), '.config'), 'opencode');
export const defaultCache = () => path.join(process.env.XDG_CACHE_HOME || path.join(os.homedir(), '.cache'), 'aegis', 'integrations');
export async function readSettings() {
  let stored = {};
  try { stored = JSON.parse(await fs.readFile(new URL('../runtime.json', import.meta.url), 'utf8')); }
  catch (e) { if (e.code !== 'ENOENT') throw new Error(`Invalid AEGIS runtime settings: ${e.message}`); }
  const canonical = value => process.platform === 'win32' ? path.resolve(value).toLowerCase() : path.resolve(value);
  if (stored.cache && process.env.AEGIS_CACHE && canonical(stored.cache) !== canonical(process.env.AEGIS_CACHE)) {
    throw new Error('Installed AEGIS uses its recorded job cache; change it with the installer --cache option after verification finishes.');
  }
  return { ...stored, ...(process.env.AEGIS_PYTHON ? { python: process.env.AEGIS_PYTHON } : {}),
    ...(process.env.AEGIS_NODE ? { node: process.env.AEGIS_NODE } : {}),
    ...(process.env.AEGIS_CACHE ? { cache: process.env.AEGIS_CACHE } : {}) };
}

async function probe(command, args) {
  return (await exec(command, args, { windowsHide: true, shell: false, timeout: 10000, encoding: 'utf8' })).stdout.trim();
}
export async function discoverRuntime(settings = {}) {
  let node, python;
  const errors = [];
  const nodes = settings.node ? [settings.node] : [!process.versions.bun ? process.execPath : 'node', 'node'];
  for (const candidate of [...new Set(nodes)]) {
    try {
      const found = JSON.parse(await probe(candidate, ['-p', 'JSON.stringify({path:process.execPath,version:process.versions.node,bun:!!process.versions.bun})']));
      if (found.bun || Number(found.version.split('.')[0]) < 22) throw new Error('Node.js 22 or later is required');
      node = found.path; break;
    } catch (e) { errors.push(`Node ${candidate}: ${e.message}`); }
  }
  const candidates = settings.python ? [[settings.python, []]] : process.platform === 'win32'
    ? [['python', []], ['py', ['-3']], ['python3', []]] : [['python3', []], ['python', []]];
  for (const [candidate, prefix] of candidates) {
    try {
      const found = JSON.parse(await probe(candidate, [...prefix, '-c', 'import sys,json; print(json.dumps({"path":sys.executable,"version":list(sys.version_info[:2])}))']));
      if (found.version[0] !== 3 || found.version[1] < 11) throw new Error('Python 3.11 or later is required');
      python = found.path; break;
    } catch (e) { errors.push(`Python ${candidate}: ${e.message}`); }
  }
  if (!node || !python) throw new Error(`AEGIS needs Node.js >=22 and Python >=3.11. Run the installer from a terminal that can find both, or set AEGIS_NODE/AEGIS_PYTHON to executable paths.\n${errors.join('\n')}`);
  try { await probe('git', ['--version']); }
  catch { throw new Error('AEGIS needs Git available to the OpenCode backend.'); }
  return { node, python, cache: path.resolve(settings.cache || defaultCache()) };
}
