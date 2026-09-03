// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const source = path.join(repo, '05_Software/aegis/integrations/claude');
const plugin = path.join(source, 'plugins/aegis');
const present = async file => fs.access(file).then(() => true, () => false);

test('resources: native workflow resources expose bounded independent review roles', async () => {
  assert.ok(await present(path.join(plugin, '.claude-plugin/plugin.json')), 'native Claude plugin is missing');
  const manifest = JSON.parse(await fs.readFile(path.join(plugin, '.claude-plugin/plugin.json'), 'utf8'));
  assert.equal(manifest.name, 'aegis');
  assert.deepEqual((await fs.readdir(path.join(plugin, 'commands'))).sort(), ['check.md','resume.md','start.md','status.md','validate.md']);
  for (const name of ['spec-review', 'quality-review']) {
    const text = await fs.readFile(path.join(plugin, 'agents', name + '.md'), 'utf8');
    assert.match(text, /^tools: Read, Grep, Glob$/m);
    assert.doesNotMatch(text, /^(model|permissionMode|mcpServers):/m);
  }
  assert.ok(await present(path.join(plugin, 'skills/workflow/SKILL.md')));
});

test('protocol: Claude exposes real checkout operations with validated inputs', async () => {
  const entry = path.join(plugin, 'server.mjs');
  assert.ok(await present(entry), 'Claude transport is missing');
  const { createProtocol } = await import(pathToFileURL(entry));
  const protocol = createProtocol({ root: repo, version: 'test' });
  const call = (id, method, params) => protocol.handle({ jsonrpc: '2.0', id, method, params });
  await call(1, 'initialize', { protocolVersion: '2025-06-18', clientInfo: { name: 'test', version: '1' }, capabilities: {} });
  await protocol.handle({ jsonrpc: '2.0', method: 'notifications/initialized' });
  const list = await call(2, 'tools/list', {});
  assert.equal(list.result.tools.length, 11);
  const status = await call(3, 'tools/call', { name: 'aegis_status', arguments: {} });
  assert.equal(JSON.parse(status.result.content[0].text).exit_code, 0);
  const bad = await call(4, 'tools/call', { name: 'aegis_summary', arguments: { task: '../bad' } });
  assert.equal(bad.error.code, -32602);
});

test('hooks: context is bounded, read-only and scoped to governed work', async () => {
  const entry = path.join(plugin, 'hooks.mjs');
  assert.ok(await present(entry), 'AEGIS context hook is missing');
  const { hookResponse } = await import(pathToFileURL(entry));
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-hook-'));
  assert.deepEqual(await hookResponse({ cwd: root, hook_event_name: 'SessionStart' }), {});
  await fs.mkdir(path.join(root, '.agentic/tasks'), { recursive: true });
  await fs.writeFile(path.join(root, '.agentic/aegis.py'), '# fixture');
  const journal = path.join(root, '.agentic/tasks/TASK-abcd.md');
  const original = '# TASK-abcd - untrusted title\nstage: build\n' + 'Untrusted body '.repeat(10000);
  await fs.writeFile(journal, original);
  const result = await hookResponse({ cwd: root, hook_event_name: 'SessionStart' });
  assert.match(result.hookSpecificOutput.additionalContext, /AEGIS/);
  assert.ok(JSON.stringify(result).length < 6000);
  assert.equal(await fs.readFile(journal, 'utf8'), original);
  assert.deepEqual(await hookResponse({ cwd: root, hook_event_name: 'PreToolUse', tool_name: 'Write' }), {});
  const beforeRun = await hookResponse({ cwd: root, hook_event_name: 'PreToolUse', tool_name: 'mcp__plugin_aegis_aegis__aegis_run' });
  assert.equal(beforeRun.hookSpecificOutput.hookEventName, 'PreToolUse');
  assert.equal(beforeRun.hookSpecificOutput.permissionDecision, undefined);
  assert.deepEqual(await hookResponse({ cwd: null, hook_event_name: 'SessionStart' }), {});
});

test('install: portable Claude setup is available before native registration', async () => {
  const entry = path.join(source, 'setup.mjs');
  assert.ok(await present(entry), 'Claude lifecycle is missing');
  const { claudeSetup } = await import(pathToFileURL(entry));
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-claude-install-'));
  const settings = '{"theme":"dark","enabledPlugins":{"other@example":true}}\n';
  await fs.writeFile(path.join(root, 'settings.json'), settings);
  await assert.rejects(claudeSetup('invalid', { configDir: root }), /install|update|uninstall|doctor/);
  await assert.rejects(claudeSetup('install', { configDir: root }), /Build the portable package/);
  assert.equal(await fs.readFile(path.join(root, 'settings.json'), 'utf8'), settings);
});

test('ownership: native cache edits and unknown files prevent removal', async () => {
  const entry = path.join(source, 'cache.mjs');
  assert.ok(await present(entry), 'Claude native cache ownership is missing');
  const { snapshotCache, verifyCache, removeCache } = await import(pathToFileURL(entry));
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-claude-cache-'));
  const location = path.join(root, 'plugins/cache/aegis-claude/aegis/0.10.0');
  await fs.mkdir(location, { recursive: true });
  const file = path.join(location, 'runtime.json');
  await fs.writeFile(file, '{}');
  await assert.rejects(verifyCache(root), /Unowned/);
  const snapshot = await snapshotCache(root);
  await verifyCache(root, snapshot);
  await fs.writeFile(file, '{"custom":true}');
  await assert.rejects(removeCache(root, snapshot), /changed/);
  await fs.writeFile(file, '{}');
  const extra = path.join(location, 'keep.txt');
  await fs.writeFile(extra, 'personal');
  await assert.rejects(removeCache(root, snapshot), /changed/);
  await fs.unlink(extra);
  await removeCache(root, snapshot);
  assert.equal(await present(file), false);
});

test('build: fifth host includes its complete native runtime and portable launchers', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-five-hosts-'));
  const result = JSON.parse(execFileSync(process.execPath, [path.join(repo, '02_Tools/build_agent_plugins.mjs'), '--output', root], { encoding: 'utf8' }));
  assert.ok(result.hosts.includes('claude'), 'builder omits Claude');
  const location = path.join(root, 'aegis-claude');
  const native = path.join(location, 'plugins/aegis');
  for (const file of ['lib/bridge.mjs','lib/operations.mjs','lib/mcp.mjs','lib/runtime.mjs','server.mjs','hooks.mjs']) assert.ok(await present(path.join(native, file)), file);
  const { createProtocol } = await import(pathToFileURL(path.join(native, 'server.mjs')));
  assert.ok(createProtocol().handle);
  assert.ok(await present(path.join(location, 'Install-AEGIS.cmd')));
  assert.ok(await present(path.join(location, 'install.sh')));
});

test('install: native lifecycle preserves user state, refreshes same version and recovers a registration failure', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-claude-native-'));
  const output = path.join(root, 'packages');
  execFileSync(process.execPath, [path.join(repo, '02_Tools/build_agent_plugins.mjs'), '--output', output]);
  const { claudeSetup } = await import(pathToFileURL(path.join(output, 'aegis-claude/setup.mjs')));
  const configDir = path.join(root, 'config');
  await fs.mkdir(configDir);
  const settings = '{"theme":"unchanged"}\n';
  await fs.writeFile(path.join(configDir, 'settings.json'), settings);
  const options = { configDir, hostCli: path.join(repo, '05_Software/aegis/integrations/tests/fixtures/claude-cli.mjs'),
    runtime: { python: process.env.AEGIS_PYTHON || (process.platform === 'win32' ? 'python' : 'python3'), cache: path.join(root, 'jobs') } };
  const installed = await claudeSetup('install', options);
  assert.ok(await present(path.join(installed.installedPath, 'lib/bridge.mjs')));
  const stateFile = path.join(configDir, 'fixture-state.json');
  const state = () => fs.readFile(stateFile, 'utf8').then(JSON.parse);
  let saved = await state(); saved.plugins[0].enabled = false;
  await fs.writeFile(stateFile, JSON.stringify(saved));
  const entry = path.join(output, 'aegis-claude/plugins/aegis/hooks.mjs');
  await fs.appendFile(entry, '\n// updated fixture\n');
  await claudeSetup('update', options);
  assert.match(await fs.readFile(path.join(installed.installedPath, 'hooks.mjs'), 'utf8'), /updated fixture/);
  assert.equal((await state()).plugins[0].enabled, false);
  // A failed native reinstall must not be reported as success or lose the owned recovery path.
  saved = await state(); saved.failInstall = true;
  await fs.writeFile(stateFile, JSON.stringify(saved));
  await assert.rejects(claudeSetup('update', options), /lifecycle incomplete/);
  saved = await state(); saved.failInstall = false;
  await fs.writeFile(stateFile, JSON.stringify(saved));
  await claudeSetup('update', options);
  assert.equal((await state()).plugins[0].enabled, false);
  await fs.mkdir(options.runtime.cache, { recursive: true });
  await fs.writeFile(path.join(options.runtime.cache, 'uncertain.lock'), '{}');
  await assert.rejects(claudeSetup('uninstall', options), /uncertain/);
  await fs.unlink(path.join(options.runtime.cache, 'uncertain.lock'));
  saved = await state(); saved.catalogs[0].path = path.join(root, 'someone-else');
  await fs.writeFile(stateFile, JSON.stringify(saved));
  await assert.rejects(claudeSetup('update', options), /another source/);
  saved.catalogs[0].path = path.join(configDir, 'aegis-marketplace');
  await fs.writeFile(stateFile, JSON.stringify(saved));
  await claudeSetup('uninstall', options);
  assert.equal((await state()).plugins.length, 0);
  assert.equal(await fs.readFile(path.join(configDir, 'settings.json'), 'utf8'), settings);
});
