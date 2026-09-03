// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { execFileSync, spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { fileURLToPath, pathToFileURL } from 'node:url';
import registerPi from '../pi/extension.mjs';
import { reviewArguments } from '../pi/review.mjs';
import { createProtocol } from '../qwen/server.mjs';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
let built;
async function packages() {
  if (!built) built = (async () => {
    if (process.env.AEGIS_TEST_PACKAGES) return process.env.AEGIS_TEST_PACKAGES;
    const root = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-additional-'));
    execFileSync(process.execPath, [path.join(repo, '02_Tools/build_agent_plugins.mjs'), '--output', root]);
    return root;
  })();
  return built;
}

function fakePi() {
  const tools = new Map(), commands = new Map(), events = new Map(), messages = [];
  return { tools, commands, events, messages,
    registerTool: tool => tools.set(tool.name, tool),
    registerCommand: (name, command) => commands.set(name, command),
    on: (name, callback) => events.set(name, callback),
    sendMessage: message => messages.push(message),
    sendUserMessage: message => messages.push(message),
  };
}

async function fixture() {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-native-fixture-'));
  const python = process.env.AEGIS_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
  await fs.cp(process.env.AEGIS_TEST_PAYLOAD || path.join(repo, '05_Software/aegis/template/.agentic'), path.join(root, '.agentic'), { recursive: true });
  const git = (...args) => execFileSync('git', args, { cwd: root, windowsHide: true });
  const cli = (...args) => execFileSync(python, ['.agentic/aegis.py', ...args], { cwd: root, windowsHide: true, encoding: 'utf8' });
  git('init', '-q'); cli('init'); git('add', '.');
  git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'Fixture');
  const task = cli('task', 'Native tool fixture').match(/TASK-[a-f0-9]+/)[0];
  return { root, task, git };
}

test('pi: register bounded tools and dispatch a workflow request without shell interpolation', async () => {
  const pi = fakePi(); await registerPi(pi);
  assert.equal(pi.tools.size, 11);
  assert.equal(pi.commands.size, 5);
  assert.equal(pi.tools.get('aegis_job').parameters.required?.includes('action') || false, false);
  assert.ok(pi.events.has('resources_discover'));
  await pi.commands.get('aegis-start').handler('Inspect text with $(literal) & punctuation', { cwd: repo });
  assert.ok(pi.messages.some(message => typeof message === 'string' && message.includes('$(literal) & punctuation')));
  await assert.rejects(pi.tools.get('aegis_summary').execute('id', { task: '../bad' }, new AbortController().signal, undefined, { cwd: repo }), /TASK|pattern|format/);
});

test('pi_review: fresh reviewer process has only read tools and no discovered add-ons', () => {
  const args = reviewArguments({ role: 'spec', task: 'TASK-abcd', promptFile: path.join(repo, 'review prompt.md') });
  assert.equal(args[args.indexOf('--tools') + 1], 'read,grep,find,ls');
  for (const flag of ['--no-session', '--no-extensions', '--no-skills', '--no-prompt-templates', '--no-context-files']) assert.ok(args.includes(flag), flag);
  assert.equal(args.includes('--continue'), false);
  assert.ok(args.at(-1).includes('TASK-abcd'));
  assert.throws(() => reviewArguments({ role: 'build', task: 'TASK-abcd', promptFile: 'x' }), /role/);
});

test('pi: execute resume, journal read and static check against the actual installed workflow', async () => {
  const { root, task, git } = await fixture();
  const before = git('status', '--porcelain').toString();
  const pi = fakePi(); registerPi(pi);
  const ctx = { cwd: root, sessionManager: { getSessionId: () => 'native-fixture' } };
  const execute = (operation, args) => pi.tools.get('aegis_' + operation).execute('fixture', args, new AbortController().signal, undefined, ctx);
  assert.equal((await execute('resume', { task })).details.exit_code, 0);
  assert.match((await execute('read', { document: 'journal' })).details.content, new RegExp(task));
  assert.equal((await execute('check', { task })).details.verification, 'not_run');
  assert.equal(git('status', '--porcelain').toString(), before);
});

test('pi_review: launch validates the real task and forwards literal arguments to a fresh process', async () => {
  const { root, task, git } = await fixture();
  const fake = path.join(root, 'fake pi.mjs');
  const capture = path.join(root, 'captured.json');
  await fs.writeFile(fake, 'import fs from "node:fs"; fs.writeFileSync(process.env.AEGIS_CAPTURE, JSON.stringify(process.argv.slice(2)));');
  await fs.writeFile(path.join(root, 'review packet.md'), 'Candidate fixture; no model requested.');
  const script = path.join(await packages(), 'aegis-pi/review.mjs');
  const args = [script, '--root', root, '--task', task, '--role', 'quality', '--packet', 'review packet.md', '--host-cli', fake, '--model', 'provider/literal$(text)'];
  execFileSync(process.execPath, args, { env: { ...process.env, AEGIS_CAPTURE: capture }, windowsHide: true });
  const captured = JSON.parse(await fs.readFile(capture, 'utf8'));
  assert.equal(captured[captured.indexOf('--model') + 1], 'provider/literal$(text)');
  assert.match(captured.at(-1), /review packet.md/);
  await fs.unlink(capture); git('checkout', '-qb', 'wrong-review-branch');
  assert.throws(() => execFileSync(process.execPath, args, { env: { ...process.env, AEGIS_CAPTURE: capture }, stdio: 'pipe', windowsHide: true }), /branch mismatch/);
  await assert.rejects(fs.access(capture));
});

test('qwen: expose native resources and bind the tool server to the workspace', async () => {
  const root = path.join(await packages(), 'aegis-qwen');
  const manifest = JSON.parse(await fs.readFile(path.join(root, 'qwen-extension.json'), 'utf8'));
  assert.equal(manifest.name, 'aegis');
  assert.equal(manifest.mcpServers?.aegis?.cwd, '${workspacePath}');
  for (const name of ['aegis-start', 'aegis-resume', 'aegis-status', 'aegis-check', 'aegis-validate']) await fs.access(path.join(root, 'commands', name + '.md'));
  for (const role of ['spec', 'quality']) {
    const agent = await fs.readFile(path.join(root, 'agents', `aegis-${role}-review.md`), 'utf8');
    assert.match(agent, /approvalMode: plan/);
    assert.match(agent, /ReadFile/);
    assert.doesNotMatch(agent.split('---')[1], /Shell|Bash|WriteFile|Edit|model:/);
  }
});

test('protocol: negotiate tools, reject malformed requests and surface actual missing-workflow errors', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-protocol-'));
  execFileSync('git', ['init', '-q', root]);
  const protocol = createProtocol({ root, version: 'fixture' });
  const call = (id, method, params = {}) => protocol.handle({ jsonrpc: '2.0', id, method, params });
  assert.equal((await call(0, 'tools/list')).error.code, -32002);
  const initialized = await call(1, 'initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'fixture', version: '1' } });
  assert.equal(initialized.result.protocolVersion, '2025-06-18');
  await protocol.handle({ jsonrpc: '2.0', method: 'notifications/initialized' });
  const result = await call(2, 'tools/list'); assert.equal(result.result.tools.length, 11);
  assert.equal((await call(3, 'unknown')).error.code, -32601);
  assert.equal((await call(4, 'tools/call', { name: 'aegis_summary', arguments: { task: 'bad' } })).error.code, -32602);
  const status = await call(5, 'tools/call', { name: 'aegis_status', arguments: {} });
  assert.equal(status.result.isError, true);
  assert.match(status.result.content[0].text, /AEGIS is not installed/);
});

test('protocol: stdio handles framing, actual workflow calls and invalid tool arguments', async t => {
  const { root, task } = await fixture();
  const script = path.join(await packages(), 'aegis-qwen/server.mjs');
  const child = spawn(process.execPath, [script], { cwd: root, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  t.after(() => child.kill());
  let stderr = ''; child.stderr.on('data', chunk => { stderr += chunk; });
  const pending = new Map();
  const lines = createInterface({ input: child.stdout });
  lines.on('line', line => { const message = JSON.parse(line); pending.get(message.id)?.(message); pending.delete(message.id); });
  const wait = id => new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`Missing response ${id}; stderr=${stderr}`)), 10000);
    timer.unref(); pending.set(id, message => { clearTimeout(timer); resolve(message); });
  });
  const send = async (id, method, params = {}) => { const response = wait(id); child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n'); return response; };
  const malformed = wait(null); child.stdin.write('{broken}\n'); assert.equal((await malformed).error.code, -32700);
  const init = wait(1);
  const initialization = JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'fixture', version: '1' } } });
  child.stdin.write(initialization.slice(0, 25)); child.stdin.write(initialization.slice(25) + '\n');
  assert.equal((await init).result.serverInfo.name, 'aegis');
  child.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n');
  const resumed = await send(2, 'tools/call', { name: 'aegis_resume', arguments: { task } });
  assert.equal(JSON.parse(resumed.result.content[0].text).exit_code, 0);
  const journal = await send(3, 'tools/call', { name: 'aegis_read', arguments: { document: 'journal' } });
  assert.match(JSON.parse(journal.result.content[0].text).content, new RegExp(task));
  assert.equal((await send(4, 'tools/call', { name: 'aegis_status', arguments: { root: '../outside' } })).error.code, -32602);
  const oversized = wait(null); child.stdin.write('x'.repeat(1024 * 1024 + 1));
  assert.equal((await oversized).error.code, -32600);
  assert.equal(stderr, '');
});

test('install: preserve settings, refuse edits and active jobs, and remove only owned resources', async () => {
  for (const host of ['pi', 'qwen']) {
    const root = await fs.mkdtemp(path.join(os.tmpdir(), `aegis-${host}-install-`));
    const fake = path.join(root, 'host.mjs'); await fs.writeFile(fake, 'console.log("0.84.4")');
    const configDir = path.join(root, 'config'); await fs.mkdir(configDir);
    const settings = path.join(configDir, 'settings.json'); const original = '{"unrelated":"preserved"}\n'; await fs.writeFile(settings, original);
    const source = path.join(await packages(), 'aegis-' + host);
    const { setup } = await import(pathToFileURL(path.join(source, 'setup.mjs')).href);
    const options = { configDir, hostCli: fake, runtime: { python: process.env.AEGIS_PYTHON || (process.platform === 'win32' ? 'python' : 'python3'), cache: path.join(root, 'cache') } };
    await setup('install', options);
    const installed = path.join(configDir, 'extensions/aegis', host === 'pi' ? 'index.js' : 'qwen-extension.json');
    const bytes = await fs.readFile(installed); await fs.appendFile(installed, '\nuser edit');
    await assert.rejects(setup('update', options), /changed/);
    await assert.rejects(setup('uninstall', options), /changed/);
    await fs.writeFile(installed, bytes);
    const runtimeFile = path.join(configDir, 'extensions/aegis/runtime.json');
    const runtimeBytes = await fs.readFile(runtimeFile);
    const alteredRuntime = JSON.parse(runtimeBytes); alteredRuntime.node = path.join(root, 'missing-node');
    await fs.writeFile(runtimeFile, JSON.stringify(alteredRuntime));
    await assert.rejects(setup('update', options), /Installed file changed/);
    await fs.writeFile(runtimeFile, runtimeBytes);
    await fs.mkdir(options.runtime.cache, { recursive: true }); const lock = path.join(options.runtime.cache, 'checkout.lock'); await fs.writeFile(lock, 'uncertain');
    await assert.rejects(setup('uninstall', options), /verification/);
    await fs.unlink(lock);
    await setup('update', options);
    await setup('uninstall', options);
    assert.equal(await fs.readFile(settings, 'utf8'), original);
    await assert.rejects(fs.access(installed));
  }
});

test('build: assemble five independently loadable host packages', async () => {
  const output = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-four-hosts-'));
  const result = JSON.parse(execFileSync(process.execPath, [path.join(repo, '02_Tools/build_agent_plugins.mjs'), '--output', output], { encoding: 'utf8' }));
  assert.deepEqual(result.hosts, ['opencode', 'codex', 'pi', 'qwen', 'claude']);
  for (const host of result.hosts) {
    const root = path.join(output, 'aegis-' + host);
    const runtime = ['codex', 'claude'].includes(host) ? 'plugins/aegis/lib/runtime.mjs' : 'lib/runtime.mjs';
    await fs.access(path.join(root, runtime));
    await fs.access(path.join(root, 'setup.mjs'));
  }
});
