// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { createAdapter, resolveRepository, commandArgs } from '../shared/adapter.mjs';

const source = process.env.AEGIS_TEST_PAYLOAD;
const python = process.env.AEGIS_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const tmp = await fs.mkdtemp(path.join(os.tmpdir(), 'opencode-aegis-test-'));
const cache = path.join(tmp, 'cache');
const settings = { python, node: process.execPath, cache };
const git = (root, ...args) => execFileSync('git', args, { cwd: root, windowsHide: true, encoding: 'utf8' }).trim();
async function fixture(name) {
  const root = path.join(tmp, name);
  await fs.mkdir(root);
  await fs.cp(source, path.join(root, '.agentic'), { recursive: true });
  git(root, 'init', '-q');
  execFileSync(python, [path.join(root, '.agentic/aegis.py'), 'init'], { cwd: root, windowsHide: true });
  await fs.writeFile(path.join(root, 'hello.py'), 'print("hello")\n');
  git(root, 'add', '.');
  git(root, '-c', 'user.name=Adapter Test', '-c', 'user.email=adapter@example.invalid', 'commit', '-qm', 'Fixture');
  const output = execFileSync(python, [path.join(root, '.agentic/aegis.py'), 'task', 'Fixture task'], { cwd: root, windowsHide: true, encoding: 'utf8' });
  const task = output.match(/TASK-[a-f0-9]+/)[0];
  return { root, task };
}
const context = root => ({ directory: root, worktree: root, sessionID: 'test-session', agent: 'aegis', abort: new AbortController().signal });

test('argument arrays preserve metacharacters and reject malformed IDs and unsupported operations', () => {
  assert.deepEqual(commandArgs('scaffold', { kind: 'task', title: 'Fix "x"; $(echo pwned)', type: 'fix' }), ['task', 'Fix "x"; $(echo pwned)', '--type', 'fix']);
  assert.throws(() => commandArgs('resume', { task: '../../outside' }), /task/i);
  assert.throws(() => commandArgs('run', { kind: 'validate', task: 'TASK-aabb', command: 'evil' }), /command/i);
  assert.throws(() => commandArgs('evidence', { action: 'init', task: 'TASK-aabb' }), /action/i);
});

test('resolves the actual checkout from a subdirectory; rejects uninstalled nested Git repos', async () => {
  const { root } = await fixture('root with spaces');
  const sub = path.join(root, 'src');
  await fs.mkdir(sub);
  assert.equal(await resolveRepository(sub), await fs.realpath(root));
  const nested = path.join(sub, 'nested');
  await fs.mkdir(nested);
  git(nested, 'init', '-q');
  await assert.rejects(resolveRepository(nested), /installed|AEGIS/);
});

test('status/check are read-only; advisory findings are not reported as passing verification', async () => {
  const { root, task } = await fixture('read-only');
  const adapter = createAdapter(settings);
  const before = git(root, 'status', '--porcelain');
  const journal = await fs.readFile(path.join(root, '.agentic/tasks', `${task}.md`), 'utf8');
  const result = await adapter.status({ task }, context(root));
  assert.equal(result.result.schema, 1);
  const check = await adapter.check({ task }, context(root));
  assert.equal(check.verification, 'not_run');
  assert.equal(check.exit_code, 0);
  assert.ok(check.result.findings.length > 0);
  assert.equal(git(root, 'status', '--porcelain'), before);
  assert.equal(await fs.readFile(path.join(root, '.agentic/tasks', `${task}.md`), 'utf8'), journal);
});

test('resume binds session to task and branch; mutation refuses mismatches and reviewers', async () => {
  const { root, task } = await fixture('resume');
  const adapter = createAdapter(settings);
  await adapter.resume({ task }, context(root));
  assert.match(await adapter.compact('test-session', root), new RegExp(task));
  git(root, 'checkout', '-qb', 'different');
  assert.match(await adapter.compact('test-session', root), /invalidated/i);
  await assert.rejects(adapter.evidence({ action: 'anchor', task }, context(root)), /branch/i);
  await assert.rejects(adapter.scaffold({ kind: 'task', title: 'No' }, { ...context(root), agent: 'aegis-spec-review' }), /coordinator/i);
});

test('candidate detects source/untracked changes while journal report edits do not invalidate reviews', async () => {
  const { root, task } = await fixture('candidate');
  const adapter = createAdapter(settings);
  const first = await adapter.candidate({}, context(root));
  await fs.appendFile(path.join(root, '.agentic/tasks', `${task}.md`), '\nEvidence recorded.\n');
  assert.equal((await adapter.candidate({}, context(root))).digest, first.digest);
  await fs.writeFile(path.join(root, 'new.py'), 'print("new")\n');
  assert.notEqual((await adapter.candidate({}, context(root))).digest, first.digest);
});

test('runner prevents duplicates across instances, preserves output and strict failures, and recovers by ID', async () => {
  const { root, task } = await fixture('jobs');
  // TOML literal avoids shell/JSON escaping in the fixture itself.
  await fs.writeFile(path.join(root, '.agentic/aegis.toml'), `[commands]\ntest = '"${python.replaceAll('\\', '/')}" -c "import time,sys; print(123); time.sleep(2); sys.exit(7)"'\n`);
  const first = createAdapter(settings);
  const started = await first.run({ kind: 'validate', task }, context(root));
  const second = createAdapter(settings);
  const duplicate = await second.run({ kind: 'validate', task }, { ...context(root), sessionID: 'another' });
  assert.equal(duplicate.duplicate, true);
  assert.equal(duplicate.job.id, started.job.id);
  let result;
  for (let i = 0; i < 100; i++) {
    result = await second.job({ action: 'status', id: started.job.id }, context(root));
    if (!['starting', 'running'].includes(result.job.state)) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.equal(result.job.state, 'completed');
  assert.equal(result.job.exit_code, 1); // The configured test failed; preserve strict failure.
  assert.equal(result.result.schema, 1);
  assert.ok(result.result.run.length > 0);
  assert.ok((await fs.readFile(result.job.stderr, 'utf8')).includes('123'));
});

test('cancels a running verification tree and reports cancellation, never a pass', async () => {
  const { root, task } = await fixture('cancel');
  const pidFile = path.join(root, 'cancel-pids.json');
  await fs.writeFile(path.join(root, 'slow.py'), 'import os,sys,subprocess,json,time\nchild=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"])\nopen("cancel-pids.json","w").write(json.dumps([os.getpid(),child.pid]))\ntime.sleep(30)\n');
  await fs.writeFile(path.join(root, '.agentic/aegis.toml'), `[commands]\ntest = '"${python.replaceAll('\\', '/')}" slow.py'\n`);
  const adapter = createAdapter(settings);
  const started = await adapter.run({ kind: 'test', task }, context(root));
  let pids;
  for (let i = 0; i < 100; i++) {
    try { pids = JSON.parse(await fs.readFile(pidFile, 'utf8')); break; } catch { await new Promise(resolve => setTimeout(resolve, 100)); }
  }
  assert.ok(pids, 'configured test and its child started');
  const cancelled = await adapter.job({ action: 'cancel', id: started.job.id }, context(root));
  assert.equal(cancelled.job.state, 'cancelled');
  assert.notEqual(cancelled.job.exit_code, 0);
  const living = async pid => {
    try {
      if (process.platform === 'linux') return !/\) Z /.test(await fs.readFile(`/proc/${pid}/stat`, 'utf8'));
      process.kill(pid, 0); return true;
    } catch { return false; }
  };
  for (let i = 0; i < 30 && (await Promise.all(pids.map(living))).some(Boolean); i++) await new Promise(resolve => setTimeout(resolve, 100));
  const survivors = [];
  for (const pid of pids) if (await living(pid)) { survivors.push(pid); try { process.kill(pid, 'SIGKILL'); } catch {} }
  assert.deepEqual(survivors, [], 'cancellation must stop configured tests even when AEGIS launches a separate process session');
});

test('scaffolds records in the selected checkout and round-trips installed steps/evidence/diff', async () => {
  const { root } = await fixture('records');
  const adapter = createAdapter(settings);
  const opened = await adapter.scaffold({ kind: 'task', title: 'Handle "quoted" arguments; literally', type: 'fix' }, context(root));
  assert.equal(opened.exit_code, 0);
  const task = opened.stdout.match(/TASK-[a-f0-9]+/)[0];
  const step = await adapter.read({ document: 'step', task }, context(root));
  assert.match(step.path, /1_frame\.md$/);
  const req = await adapter.scaffold({ kind: 'requirement', category: 'functional', title: 'Literal argument handling' }, context(root));
  assert.equal(req.exit_code, 0);
  assert.match(req.stdout, /REQ-FUNC-/);
  assert.equal((await adapter.evidence({ action: 'anchor', task }, context(root))).exit_code, 0);
  await fs.writeFile(path.join(root, 'hello.py'), 'print("modified")\n');
  assert.equal((await adapter.evidence({ action: 'evolution', task }, context(root))).exit_code, 0);
  assert.match((await adapter.diff({}, context(root))).diff, /modified/);
  assert.equal((await adapter.summary({ task }, context(root))).exit_code, 0);
});

test('successful command remains exit zero but changed candidate is explicitly marked', async () => {
  const { root, task } = await fixture('candidate-during-run');
  await fs.writeFile(path.join(root, '.agentic/aegis.toml'), `[commands]\ntest = '"${python.replaceAll('\\', '/')}" -c "import time; print(456); time.sleep(2)"'\n`);
  const adapter = createAdapter(settings);
  const started = await adapter.run({ kind: 'test', task }, context(root));
  let result;
  for (let i = 0; i < 100; i++) {
    result = await adapter.job({ id: started.job.id }, context(root));
    if (result.job.child_pid) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.ok(result.job.child_pid);
  await fs.writeFile(path.join(root, 'hello.py'), 'print("changed during verification")\n');
  for (let i = 0; i < 100; i++) {
    result = await adapter.job({ id: started.job.id }, context(root));
    if (!['starting', 'running'].includes(result.job.state)) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.equal(result.job.state, 'completed');
  assert.equal(result.job.exit_code, 0);
  assert.equal(result.job.candidate_unchanged, false);
});
