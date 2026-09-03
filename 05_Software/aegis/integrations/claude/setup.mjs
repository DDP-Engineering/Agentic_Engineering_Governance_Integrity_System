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
import { collectFiles, exists, manageFiles } from '../shared/install.mjs';
import { discoverRuntime } from '../shared/runtime.mjs';
import { setupMain } from '../shared/host-setup.mjs';
import { snapshotCache, verifyCache, removeCache } from './cache.mjs';
const exec = promisify(execFile);
const source = path.dirname(fileURLToPath(import.meta.url));
const identity = 'aegis@aegis-claude';
const samePath = (a, b) => process.platform === 'win32' ? path.resolve(a).toLowerCase() === path.resolve(b).toLowerCase() : path.resolve(a) === path.resolve(b);

async function resolveClaude(node, explicit) {
  if (explicit) {
    const file = path.resolve(explicit);
    if (/\.[cm]?js$/i.test(file)) return { command: node, args: [file] };
    if (/\.(cmd|bat|ps1)$/i.test(file)) throw new Error('Supply a native Claude executable or JavaScript entry, not a shell shim.');
    return { command: file, args: [] };
  }
  for (const directory of [path.join(os.homedir(), '.local/bin'), ...(process.env.PATH || '').split(path.delimiter).filter(Boolean)]) {
    const file = path.join(directory, process.platform === 'win32' ? 'claude.exe' : 'claude');
    if (await exists(file)) return { command: file, args: [] };
    const script = path.join(directory, 'node_modules/@anthropic-ai/claude-code/cli-wrapper.cjs');
    if (await exists(script)) return { command: node, args: [script] };
  }
  throw new Error('Claude Code CLI not found; use --host-cli with its native executable.');
}

async function setup(action, options, configDir) {
  if (!await exists(path.join(source, 'plugins/aegis/lib/runtime.mjs'))) throw new Error('Build the portable package first; the raw source marketplace is not installable.');
  const prefix = 'aegis-marketplace/';
  const root = path.join(configDir, prefix);
  const manifestFile = path.join(configDir, '.aegis-claude-installation.json');
  const managed = { root: configDir, owner: 'claude', prefixes: [prefix], cache: options.runtime?.cache };
  if (action !== 'doctor') await manageFiles(action, { ...managed, dryRun: true });
  const previous = await exists(manifestFile) ? JSON.parse(await fs.readFile(manifestFile, 'utf8')) : {};
  await verifyCache(configDir, previous.nativeCache);
  const runtimeFile = path.join(root, 'plugins/aegis/runtime.json');
  const stored = await exists(runtimeFile) ? JSON.parse(await fs.readFile(runtimeFile, 'utf8')) : {};
  const runtime = await discoverRuntime({ ...stored, ...options.runtime });
  const cli = await resolveClaude(runtime.node, options.hostCli || stored.hostCliPath);
  const invoke = async args => (await exec(cli.command, [...cli.args, ...args], {
    env: { ...process.env, CLAUDE_CONFIG_DIR: configDir, DISABLE_AUTOUPDATER: '1', CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: '1' },
    shell: false, windowsHide: true, timeout: 60000, maxBuffer: 8 * 1024 * 1024,
  })).stdout.trim();
  const version = await invoke(['--version']);
  const match = version.match(/^(\d+)\.(\d+)\.(\d+)/);
  if (!match || Number(match[1]) < 2 || (Number(match[1]) === 2 && Number(match[2]) === 0) || (match[1] === '2' && match[2] === '1' && Number(match[3]) < 259)) throw new Error('Claude Code 2.1.259 or newer is required for the tested hook and lifecycle format.');
  const catalogs = JSON.parse(await invoke(['plugin', 'marketplace', 'list', '--json']));
  const catalog = catalogs.find(item => item.name === 'aegis-claude');
  if (catalog && (catalog.source !== 'directory' || !samePath(catalog.path, root))) throw new Error('AEGIS marketplace is owned by another source; no package files changed.');
  const installs = JSON.parse(await invoke(['plugin', 'list', '--json']));
  const found = installs.filter(item => item.id === identity);
  const enabled = found[0]?.enabled ?? previous.enabled ?? true;
  if (found.some(item => item.scope !== 'user')) throw new Error('AEGIS has a project/local installation; preserve that separate scope before user lifecycle changes.');
  if (found.length && !previous.owner) throw new Error('Unowned Claude AEGIS registration exists.');
  if (action === 'doctor') return { host: 'claude', version, configDir, installed: found.length === 1,
    commands: 5, tools: 11, reviewers: 2, hooks: 2, runtime, models_invoked: false };

  const files = {};
  if (action !== 'uninstall') {
    for (const [name, bytes] of Object.entries(await collectFiles(source))) files[prefix + name] = bytes;
    files[prefix + 'plugins/aegis/runtime.json'] = JSON.stringify({ ...runtime, hostCliPath: options.hostCli ? path.resolve(options.hostCli) : stored.hostCliPath }, null, 2) + '\n';
    const mcp = JSON.parse(files[prefix + 'plugins/aegis/.mcp.json']);
    mcp.mcpServers.aegis.command = runtime.node;
    files[prefix + 'plugins/aegis/.mcp.json'] = JSON.stringify(mcp, null, 2) + '\n';
    const hooks = JSON.parse(files[prefix + 'plugins/aegis/hooks/hooks.json']);
    for (const groups of Object.values(hooks.hooks)) for (const group of groups) for (const hook of group.hooks) hook.command = runtime.node;
    files[prefix + 'plugins/aegis/hooks/hooks.json'] = JSON.stringify(hooks, null, 2) + '\n';
  }
  const settings = { ...managed, files, cache: runtime.cache };
  await manageFiles(action, { ...settings, dryRun: true });
  // Back up only this plugin's verified native files, never user settings or credentials.
  const native = await verifyCache(configDir, previous.nativeCache);
  let approvedCache = native;
  if (Object.keys(native.files).length) {
    const backup = path.join(configDir, 'aegis-install-backups/claude-native', randomUUID());
    await fs.mkdir(path.dirname(backup), { recursive: true });
    await fs.cp(native.root, backup, { recursive: true });
  }
  const saveSnapshot = async () => {
    if (!await exists(manifestFile)) return;
    const state = JSON.parse(await fs.readFile(manifestFile, 'utf8'));
    const temporary = `${manifestFile}.${randomUUID()}.tmp`;
    await fs.writeFile(temporary, JSON.stringify({ ...state, enabled, nativeCache: approvedCache }, null, 2) + '\n');
    await fs.rename(temporary, manifestFile);
  };
  let result;
  try {
    if (found.length) await invoke(['plugin', 'uninstall', identity, '--scope', 'user', '--keep-data']);
    // CLI versions can retain cache bytes on uninstall; verify again before removing ours.
    const remaining = await snapshotCache(configDir);
    for (const [name, digest] of Object.entries(remaining.files)) {
      if (native.files[name] === digest) continue;
      // Claude 2.1.259 marks retained cache versions for later garbage collection.
      if (found.length && /^[^/]+\/\.orphaned_at$/.test(name) && !Object.hasOwn(native.files, name)) {
        const marker = await fs.readFile(path.join(remaining.root, name), 'utf8');
        if (/^\d{13}$/.test(marker) && Math.abs(Date.now() - Number(marker)) < 120000) continue;
      }
      throw new Error('Claude changed native cache unexpectedly during uninstall.');
    }
    await removeCache(configDir, remaining);
    approvedCache = await snapshotCache(configDir);
    if (action === 'uninstall') {
      if (catalog) await invoke(['plugin', 'marketplace', 'remove', 'aegis-claude']);
      return await manageFiles(action, settings);
    }
    result = await manageFiles(action, settings);
    if (!catalog) await invoke(['plugin', 'marketplace', 'add', root]);
    await invoke(['plugin', 'install', identity, '--scope', 'user']);
    if (!enabled) await invoke(['plugin', 'disable', identity, '--scope', 'user']);
    const installed = JSON.parse(await invoke(['plugin', 'list', '--json'])).find(item => item.id === identity && item.scope === 'user');
    if (!installed?.installPath) throw new Error('Claude did not report a native installation path.');
    const expected = path.join((await snapshotCache(configDir)).root, JSON.parse(files[prefix + 'plugins/aegis/.claude-plugin/plugin.json']).version);
    if (!samePath(installed.installPath, expected)) throw new Error('Unexpected native installation path.');
    const actual = await collectFiles(installed.installPath);
    const payloadPrefix = prefix + 'plugins/aegis/';
    const expectedNames = new Set(Object.keys(files).filter(name => name.startsWith(payloadPrefix)).map(name => name.slice(payloadPrefix.length)));
    if (Object.keys(actual).some(name => !expectedNames.has(name))) throw new Error('Unexpected additional native Claude files; preserve them before retrying.');
    for (const [name, bytes] of Object.entries(files)) {
      if (name.startsWith(payloadPrefix) && !Buffer.from(bytes).equals(actual[name.slice(payloadPrefix.length)] || Buffer.alloc(0))) throw new Error(`Native Claude payload missing or stale: ${name}`);
    }
    approvedCache = await snapshotCache(configDir);
    await saveSnapshot();
    return { ...result, host: 'claude', version, installedPath: installed.installPath, models_invoked: false, note: 'Restart Claude Code; invoke /aegis:start in the Code tab or CLI.' };
  } catch (error) {
    await saveSnapshot();
    throw new Error(`Claude lifecycle incomplete: ${error.stderr || error.message}. Owned backups were preserved; correct the cause and rerun update. No successful installation is claimed.`);
  }
}

export async function claudeSetup(action, options = {}) {
  if (!['install', 'update', 'uninstall', 'doctor'].includes(action)) throw new Error('Use install, update, uninstall or doctor.');
  let configDir = path.resolve(options.configDir || process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude'));
  await fs.mkdir(configDir, { recursive: true });
  configDir = await fs.realpath(configDir);
  const lockFile = path.join(configDir, '.aegis-claude-registration.lock');
  const lock = await fs.open(lockFile, 'wx').catch(error => { if (error.code === 'EEXIST') throw new Error('Another Claude registration holds the lock; inspect it before retrying.'); throw error; });
  try { return await setup(action, options, configDir); }
  finally { await lock.close(); await fs.unlink(lockFile); }
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await setupMain(claudeSetup, process.argv.slice(2));
