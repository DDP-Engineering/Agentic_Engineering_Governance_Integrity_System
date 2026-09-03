#!/usr/bin/env node
// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { randomUUID } from 'node:crypto';
import { discoverRuntime } from '../shared/runtime.mjs';
import { manageFiles, collectFiles, exists } from '../shared/install.mjs';
import { snapshotNativeCache, verifyNativeCache } from '../shared/native-cache.mjs';

const exec = promisify(execFile);
async function resolveCodex(node, explicit) {
  if (explicit) return explicit.endsWith('.js') ? [node, [path.resolve(explicit)]] : [explicit, []];
  if (process.platform !== 'win32') return ['codex', []];
  for (const folder of (process.env.PATH || '').split(path.delimiter)) {
    if (await exists(path.join(folder, 'codex.exe'))) return [path.join(folder, 'codex.exe'), []];
    const shim = path.join(folder, 'node_modules/@openai/codex/bin/codex.js');
    if (await exists(shim)) return [node, [shim]];
  }
  throw new Error('Codex CLI was not found. Install it or pass --codex with its executable or codex.js path.');
}

async function setup(action, { codexHome, codex, runtime = {} }) {
  const source = path.dirname(fileURLToPath(import.meta.url));
  codexHome = path.resolve(codexHome);
  await fs.mkdir(codexHome, { recursive: true });
  const stored = path.join(codexHome, 'aegis-marketplace/plugins/aegis/runtime.json');
  const settings = await discoverRuntime({ ...await exists(stored) ? JSON.parse(await fs.readFile(stored, 'utf8')) : {}, ...runtime });
  const [command, prefix] = await resolveCodex(settings.node, codex);
  const invoke = async args => {
    const result = await exec(command, [...prefix, ...args], { env: { ...process.env, CODEX_HOME: codexHome }, windowsHide: true, shell: false, timeout: 60000, maxBuffer: 8 * 1024 * 1024 });
    return result.stdout.trim();
  };
  const version = await invoke(['--version']);
  const catalog = JSON.parse(await fs.readFile(path.join(source, '.agents/plugins/marketplace.json'), 'utf8'));
  const marketRoot = path.join(codexHome, 'aegis-marketplace');
  if (action === 'doctor') return { runtime: settings, codex: version, plugin: 'aegis', skill: 'aegis', roles: ['aegis-spec-review', 'aegis-quality-review'], models_invoked: false };
  const registered = JSON.parse(await invoke(['plugin', 'marketplace', 'list', '--json']));
  const existing = registered.marketplaces?.find(m => m.name === catalog.name);
  const canonical = value => process.platform === 'win32' ? path.resolve(value).toLowerCase() : path.resolve(value);
  if (existing && canonical(existing.root) !== canonical(marketRoot)) throw new Error(`Marketplace ${catalog.name} is already owned by another source; no files changed. Install this package through a separately named catalog.`);
  let files = {};
  if (action !== 'uninstall') {
    const content = await collectFiles(source);
    files = Object.fromEntries(Object.entries(content).map(([k,v]) => [`aegis-marketplace/${k}`, v]));
    files['aegis-marketplace/plugins/aegis/runtime.json'] = JSON.stringify(settings, null, 2) + '\n';
    for (const name of ['aegis-spec-review', 'aegis-quality-review']) files[`agents/${name}.toml`] = await fs.readFile(path.join(source, 'plugins/aegis/agents', `${name}.toml`));
  }
  const options = { root: codexHome, owner: 'codex', prefixes: ['aegis-marketplace/', 'agents/aegis-spec-review.toml', 'agents/aegis-quality-review.toml'], files, cache: settings.cache };
  await manageFiles(action, { ...options, dryRun: true });
  const manifestFile = path.join(codexHome, '.aegis-codex-installation.json');
  const previous = await exists(manifestFile) ? JSON.parse(await fs.readFile(manifestFile, 'utf8')) : {};
  await verifyNativeCache(codexHome, previous.nativeCache);
  if (action === 'uninstall') {
    if (existing) {
      await invoke(['plugin', 'remove', `aegis@${catalog.name}`]);
      await invoke(['plugin', 'marketplace', 'remove', catalog.name]);
    }
    return manageFiles(action, options);
  }
  const result = await manageFiles(action, options);
  try {
    await invoke(['plugin', 'marketplace', 'add', marketRoot, '--json']);
    const registration = JSON.parse(await invoke(['plugin', 'add', `aegis@${catalog.name}`, '--json']));
    const nativeCache = await snapshotNativeCache(codexHome, registration.installedPath);
    if (!registration.installedPath || !Object.keys(nativeCache.files).length) throw new Error('Codex registration did not produce a verifiable native plugin cache.');
    const manifest = JSON.parse(await fs.readFile(manifestFile, 'utf8'));
    const temporary = `${manifestFile}.${randomUUID()}.tmp`;
    try {
      await fs.writeFile(temporary, JSON.stringify({ ...manifest, nativeCache }, null, 2) + '\n', { flag: 'wx' });
      await fs.rename(temporary, manifestFile);
    } finally { await fs.unlink(temporary).catch(() => {}); }
    return { ...result, registration, note: 'Start a new Codex task to discover the AEGIS skill and review roles.' };
  } catch (error) {
    throw new Error(`Package files were saved, but Codex registration failed: ${error.stderr || error.message}. Resolve the CLI error, then rerun update. No successful installation is claimed.`);
  }
}

/** Serialize native registration together with its owned-file transaction. */
export async function codexSetup(action, options = {}) {
  let codexHome = path.resolve(options.codexHome || process.env.CODEX_HOME || path.join(os.homedir(), '.codex'));
  await fs.mkdir(codexHome, { recursive: true });
  codexHome = await fs.realpath(codexHome);
  if (action === 'doctor') return setup(action, { ...options, codexHome });
  const lockFile = path.join(codexHome, '.aegis-codex-registration.lock');
  const lock = await fs.open(lockFile, 'wx').catch(e => { if (e.code === 'EEXIST') throw new Error('Another Codex registration holds the lock; inspect it before retrying.'); throw e; });
  try { return await setup(action, { ...options, codexHome }); }
  finally { await lock.close(); await fs.unlink(lockFile); }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const [action = 'doctor', ...args] = process.argv.slice(2); const options = { runtime: {} };
    for (let i = 0; i < args.length; i += 2) {
      if (!args[i + 1]) throw new Error(`Missing value for ${args[i]}`);
      if (args[i] === '--codex-home') options.codexHome = args[i + 1];
      else if (args[i] === '--codex') options.codex = args[i + 1];
      else if (['--node', '--python', '--cache'].includes(args[i])) options.runtime[args[i].slice(2)] = args[i + 1];
      else throw new Error(`Unknown option ${args[i]}`);
    }
    console.log(JSON.stringify(await codexSetup(action, options), null, 2));
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
