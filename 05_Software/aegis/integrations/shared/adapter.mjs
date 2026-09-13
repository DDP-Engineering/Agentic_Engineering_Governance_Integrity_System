// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import fs from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createHash, randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const exec = promisify(execFile);
const aliveStates = new Set(['starting', 'running', 'cancelling']);
const taskID = value => {
  if (!/^TASK-[a-f0-9]{4,32}$/.test(value || '')) throw new Error('Use a complete TASK-<hex> task ID.');
  return value;
};
const pick = (value, allowed, label) => {
  if (!allowed.includes(value)) throw new Error(`Invalid ${label}: ${value}`);
  return value;
};
const title = value => {
  if (typeof value !== 'string' || !value.trim() || value.length > 500 || /[\x00-\x1f]/.test(value) || value.startsWith('-')) throw new Error('Title must be one nonempty line, at most 500 characters, not an option.');
  return value;
};
const key = root => createHash('sha256').update(process.platform === 'win32' ? root.toLowerCase() : root).digest('hex');
const jsonRead = async filename => JSON.parse(await fs.readFile(filename, 'utf8'));
export async function jsonWrite(filename, value) {
  const temp = `${filename}.${randomUUID()}.tmp`;
  await fs.writeFile(temp, JSON.stringify(value, null, 2));
  await fs.rename(temp, filename);
}
export function isAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; }
}
async function git(root, ...args) {
  return (await exec('git', args, { cwd: root, windowsHide: true, maxBuffer: 32 * 1024 * 1024, timeout: 30000 })).stdout;
}

/** Resolve from the session directory, stopping at the nearest Git boundary. */
export async function resolveRepository(directory) {
  let root = await fs.realpath(directory);
  try { root = await fs.realpath((await git(root, 'rev-parse', '--show-toplevel')).trim()); }
  catch { throw new Error('Open a Git checkout with AEGIS installed. No repository was initialized.'); }
  const script = path.join(root, '.agentic', 'aegis.py');
  try {
    const canonical = await fs.realpath(script);
    if (path.relative(root, canonical) !== path.join('.agentic', 'aegis.py')) throw new Error('External payload link');
    await fs.access(path.join(root, '.agentic', 'AGENTS.md'));
  } catch { throw new Error(`AEGIS is not installed locally in ${root}. The adapter never installs or substitutes another repository's payload.`); }
  return root;
}

export function commandArgs(operation, args = {}) {
  if (operation === 'status') return ['status', ...(args.task ? [taskID(args.task)] : []), ...(args.all ? ['--all'] : []), '--json'];
  if (operation === 'resume' || operation === 'summary') return [operation === 'resume' ? 'brief' : 'summary', taskID(args.task)];
  if (operation === 'check') return ['check', ...(args.task ? ['--task', taskID(args.task)] : []), ...(args.strict ? ['--strict'] : []), '--json'];
  if (operation === 'scaffold') {
    if (args.kind === 'task') return ['task', title(args.title), '--type', pick(args.type || 'feature', ['feature', 'fix', 'change', 'adopt'], 'task type'), ...(args.parent ? ['--parent', taskID(args.parent)] : [])];
    if (args.kind === 'requirement') return ['req', pick(args.category, ['functional', 'ux', 'nfr', 'security', 'data', 'platform', 'reliability', 'test'], 'category'), title(args.title)];
    throw new Error('Invalid scaffold kind');
  }
  if (operation === 'evidence') {
    const action = pick(args.action, ['anchor', 'evolution', 'report'], 'evidence action');
    if (args.compact && action !== 'evolution') throw new Error('Compact evidence requires evolution');
    return action === 'report' ? ['report', taskID(args.task)] : [action, '--task', taskID(args.task), '--json', ...(args.compact ? ['--compact'] : [])];
  }
  if (operation === 'run') {
    taskID(args.task);
    if (args.kind === 'validate') {
      if (args.command || args.impacted || args.base || args.no_fallback) throw new Error('Validation uses configured commands; test selection overrides are not accepted.');
      return ['check', '--task', args.task, '--strict', '--run', '--json'];
    }
    pick(args.kind, ['test'], 'run kind');
    if (args.no_fallback && !args.impacted) throw new Error('no_fallback requires impacted');
    if (args.command && !/^[a-zA-Z][a-zA-Z0-9_-]{0,63}$/.test(args.command)) throw new Error('Invalid configured command name');
    if (args.base && (!/^[a-zA-Z0-9][a-zA-Z0-9_./~^+-]*$/.test(args.base) || args.base.includes('..'))) throw new Error('Invalid base revision');
    return ['test', args.command || 'test', '--task', args.task, ...(args.impacted ? ['--impacted'] : []), ...(args.no_fallback ? ['--no-fallback'] : []), ...(args.base ? ['--base', args.base] : [])];
  }
  throw new Error(`Unsupported operation: ${operation}`);
}

/** A review aid, not a security boundary. Journal/evidence edits are excluded. */
export async function fingerprint(root) {
  const branch = (await git(root, 'branch', '--show-current')).trim();
  const head = (await git(root, 'rev-parse', '--verify', 'HEAD').catch(() => '(unborn)')).trim();
  const paths = [...new Set((await git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')).split('\0').filter(Boolean))].sort();
  const hash = createHash('sha256').update(JSON.stringify({ branch, head }));
  let files = 0;
  for (const name of paths) {
    if (name.startsWith('.agentic/tasks/') || /(^|\/)__pycache__\/|\.py[co]$/.test(name)) continue;
    hash.update(`\0${name}\0`);
    let stat;
    try { stat = await fs.lstat(path.join(root, name)); }
    catch (e) { if (e.code === 'ENOENT') { hash.update('deleted'); continue; } throw e; }
    if (stat.isSymbolicLink()) hash.update(`symlink:${await fs.readlink(path.join(root, name))}`);
    else if (stat.isFile()) {
      hash.update(`file:${stat.mode & 0o111}:`);
      for await (const chunk of createReadStream(path.join(root, name))) hash.update(chunk);
    } else hash.update(`directory:${name}`);
    files++;
  }
  return { digest: hash.digest('hex'), branch, head, files, scope: 'Git-visible files except task journals/evidence and Python bytecode. Review the full task journal separately; ignored files and submodule contents are not fingerprinted.' };
}

async function tail(filename, max = 12000) {
  try {
    const handle = await fs.open(filename, 'r');
    try {
      const { size } = await handle.stat();
      const buffer = Buffer.alloc(Math.min(size, max));
      await handle.read(buffer, 0, buffer.length, Math.max(0, size - max));
      return (size > max ? '[tail only; full output is in the log file]\n' : '') + buffer.toString('utf8');
    } finally { await handle.close(); }
  } catch (e) { if (e.code === 'ENOENT') return ''; throw e; }
}

export function createAdapter(config = {}) {
  const settings = { python: 'python', node: 'node', cache: path.join(os.homedir(), '.cache', 'opencode', 'aegis'), ...config };
  const selected = new Map();
  async function locate(context) {
    return resolveRepository(context.directory || context.worktree);
  }
  function coordinator(context) {
    if (context.agent !== 'aegis') throw new Error('Only the AEGIS coordinator can mutate records, run verification, or cancel jobs.');
  }
  async function cli(root, argv, context) {
    const command = [path.join(root, '.agentic/aegis.py'), ...argv];
    let stdout = '', stderr = '', exit_code = 0;
    try {
      ({ stdout, stderr } = await exec(settings.python, command, { cwd: root, windowsHide: true, shell: false, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024, timeout: 60000, signal: context?.abort, env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' } }));
    } catch (e) {
      if (!Number.isInteger(e.code)) throw new Error(`Could not run installed AEGIS: ${e.message}`);
      stdout = e.stdout || ''; stderr = e.stderr || ''; exit_code = e.code;
    }
    let result;
    if (argv.includes('--json') && stdout.trim()) {
      try { result = JSON.parse(stdout); } catch { throw new Error('AEGIS returned invalid JSON; no result was inferred.'); }
      if (result.schema !== 1) throw new Error(`Unsupported AEGIS JSON schema: ${result.schema}`);
    }
    return { root, argv, exit_code, ...(result ? { result } : { stdout }), stderr };
  }
  async function aligned(root, task, context) {
    const state = await cli(root, commandArgs('status', { task: taskID(task) }), context);
    if (state.exit_code || !state.result?.task) throw new Error(`Cannot read ${task}: ${state.stderr}`);
    const branch = (await git(root, 'branch', '--show-current')).trim();
    const recorded = state.result.task.header.branch;
    if (!branch || !recorded || branch !== recorded) throw new Error(`Task branch mismatch: current '${branch || '(detached)'}', journal '${recorded || '(missing)'}'. Reconcile before continuing; no checkout was performed.`);
    return { branch, state };
  }
  async function scope(args, context) {
    const root = await locate(context);
    const branch = (await git(root, 'branch', '--show-current')).trim();
    const selection = selected.get(context.sessionID);
    if (selection && (selection.root !== root || selection.branch !== branch)) selected.delete(context.sessionID);
    return { root, task: args.task || selected.get(context.sessionID)?.task };
  }
  const jobFile = id => {
    if (!/^[0-9a-f-]{36}$/.test(id || '')) throw new Error('Invalid job ID');
    return path.join(settings.cache, `${id}.json`);
  };
  async function readJob(id, root) {
    const job = await jsonRead(jobFile(id));
    if (job.root !== root) throw new Error('Job belongs to another checkout.');
    if (aliveStates.has(job.state) && !isAlive(job.pid) && Date.now() - Date.parse(job.started_at) > 30000) {
      // Never automatically clear an uncertain lock: a surviving child suite may still be running.
      return { ...job, state: 'interrupted', detail: 'Worker unavailable. Inspect the recorded child PID and logs before clearing the lock or restarting verification.' };
    }
    return job;
  }
  async function active(root) {
    try {
      const lock = await jsonRead(path.join(settings.cache, `${key(root)}.lock`));
      return await readJob(lock.id, root);
    } catch (e) { if (e.code === 'ENOENT') return undefined; throw e; }
  }
  async function jobView(job) {
    const response = { job, stdout_tail: await tail(job.stdout), stderr_tail: await tail(job.stderr) };
    if (job.state === 'completed' && job.argv.includes('--json')) {
      try {
        const result = await jsonRead(job.stdout);
        if (result.schema !== 1) throw new Error('Unsupported JSON schema');
        response.result = result;
      } catch (e) { response.result_error = `No valid AEGIS JSON proof: ${e.message}`; }
    }
    return response;
  }
  return {
    async status(args, context) {
      const root = await locate(context);
      return { ...await cli(root, commandArgs('status', args), context), active_job: await active(root) || null };
    },
    async resume(args, context) {
      const root = await locate(context);
      const { branch, state } = await aligned(root, args.task, context);
      selected.set(context.sessionID, { root, branch, task: args.task });
      return { ...await cli(root, commandArgs('resume', args), context), task_state: state.result.task, next: 'Read root AGENTS.md, .agentic/AGENTS.md, the current step, full journal as required, and Handoff must_read paths. Resume never grants Git authority.' };
    },
    async read(args, context) {
      const { root, task } = await scope(args, context);
      const documents = { contract: '.agentic/AGENTS.md', cli: '.agentic/CLI.md', config: '.agentic/aegis.toml', journal: task ? `.agentic/tasks/${taskID(task)}.md` : null };
      if (args.document === 'step') {
        if (!task) throw new Error('Name a task or call aegis_resume first.');
        const { state } = await aligned(root, task, context);
        const step = state.result.task.step_file;
        if (!/^[a-z0-9_]+\.md$/.test(step || '')) throw new Error('Task has no known installed stage file.');
        documents.step = `.agentic/steps/${step}`;
      }
      const relative = documents[args.document];
      if (!relative) throw new Error('Document unavailable; name a task or inspect status.');
      const filename = await fs.realpath(path.resolve(root, relative));
      const rel = path.relative(root, filename);
      if (rel.startsWith('..') || path.isAbsolute(rel)) throw new Error('Document resolves outside the checkout.');
      return { root, path: filename, content: await fs.readFile(filename, 'utf8') };
    },
    async summary(args, context) { return cli(await locate(context), commandArgs('summary', args), context); },
    async check(args, context) {
      const { root, task } = await scope(args, context);
      return { ...await cli(root, commandArgs('check', { ...args, task }), context), verification: 'not_run', interpretation: 'Read findings and strict outcome. Advisory exit 0 is not a passing test suite.' };
    },
    async scaffold(args, context) {
      coordinator(context);
      const { root, task } = await scope(args, context);
      if (args.kind === 'requirement') await aligned(root, task, context);
      if (args.parent) await aligned(root, args.parent, context);
      const result = await cli(root, commandArgs('scaffold', args), context);
      if (!result.exit_code && args.kind === 'task') {
        const task = result.stdout.match(/TASK-[a-f0-9]+/)?.[0];
        if (task) selected.set(context.sessionID, { root, task, branch: (await git(root, 'branch', '--show-current')).trim() });
      }
      return result;
    },
    async evidence(args, context) {
      coordinator(context);
      const { root, task } = await scope(args, context);
      await aligned(root, task, context);
      return cli(root, commandArgs('evidence', { ...args, task }), context);
    },
    async candidate(_args, context) { const root = await locate(context); return { root, ...await fingerprint(root) }; },
    async diff(args, context) {
      const root = await locate(context);
      const base = args.base || 'HEAD';
      if (!/^[a-zA-Z0-9][a-zA-Z0-9_./~^+-]*$/.test(base) || base.includes('..')) throw new Error('Invalid base revision');
      if (args.path && (path.isAbsolute(args.path) || args.path.includes('..') || args.path.startsWith(':'))) throw new Error('Use a repository-relative path');
      return { root, base, status: await git(root, 'status', '--short'), diff: await git(root, 'diff', '--no-ext-diff', '--no-textconv', base, '--', ...(args.path ? [args.path] : [])), untracked: (await git(root, 'ls-files', '--others', '--exclude-standard')).trim(), note: 'Untracked file contents are not in git diff; read relevant files separately.' };
    },
    async run(args, context) {
      coordinator(context);
      const { root, task } = await scope(args, context);
      await aligned(root, task, context);
      const argv = commandArgs('run', { ...args, task });
      await fs.mkdir(settings.cache, { recursive: true });
      const lockPath = path.join(settings.cache, `${key(root)}.lock`);
      const id = randomUUID();
      let lock;
      try { lock = await fs.open(lockPath, 'wx'); }
      catch (e) {
        if (e.code !== 'EEXIST') throw e;
        // Another instance may still be writing its reservation.
        for (let i = 0; i < 20; i++) {
          try { const existing = await active(root); if (existing) return { duplicate: true, ...await jobView(existing) }; } catch (readError) { if (!(readError instanceof SyntaxError)) throw readError; }
          await new Promise(resolve => setTimeout(resolve, 100));
        }
        throw new Error('Another verification holds the checkout lock; inspect its cache record before retrying.');
      }
      const file = jobFile(id);
      const job = { id, root, task, argv, state: 'starting', started_at: new Date().toISOString(), stdout: path.join(settings.cache, `${id}.stdout.log`), stderr: path.join(settings.cache, `${id}.stderr.log`), lock: lockPath, python: settings.python, creator_pid: process.pid };
      try {
        await jsonWrite(file, job);
        await lock.writeFile(JSON.stringify({ id }));
        await lock.close(); lock = undefined;
        // A separate Node worker survives tool timeouts and OpenCode restarts.
        const worker = spawn(settings.node, [fileURLToPath(new URL('./worker.mjs', import.meta.url)), file], { cwd: root, detached: true, windowsHide: true, stdio: 'ignore', shell: false });
        await new Promise((resolve, reject) => { worker.once('spawn', resolve); worker.once('error', reject); });
        worker.unref();
        return { duplicate: false, job, next: 'Use aegis_job status with this ID. Do not launch another suite. Closing a chat does not cancel this run.' };
      } catch (e) {
        if (lock) await lock.close();
        await fs.unlink(lockPath).catch(() => {});
        await jsonWrite(file, { ...job, state: 'failed_to_start', error: e.message });
        throw e;
      }
    },
    async job(args, context) {
      const root = await locate(context);
      pick(args.action || 'status', ['status', 'cancel'], 'job action');
      if (!args.id) {
        if (args.action === 'cancel') throw new Error('Cancellation requires an exact job ID.');
        const current = await active(root);
        return current ? jobView(current) : { active_job: null };
      }
      let job = await readJob(args.id, root);
      if (args.action === 'cancel' && aliveStates.has(job.state)) {
        coordinator(context);
        await fs.writeFile(path.join(settings.cache, `${job.id}.cancel`), 'cancel');
        for (let i = 0; i < 100; i++) {
          await new Promise(resolve => setTimeout(resolve, 100));
          job = await readJob(args.id, root);
          if (!aliveStates.has(job.state)) break;
        }
      }
      return jobView(job);
    },
    async compact(sessionID, directory) {
      const selection = selected.get(sessionID);
      if (!selection) return '';
      try {
        const root = await resolveRepository(directory);
        const branch = (await git(root, 'branch', '--show-current')).trim();
        if (root !== selection.root || branch !== selection.branch) {
          selected.delete(sessionID);
          return 'AEGIS task selection invalidated by a checkout/branch change. Reconcile with status before writes.';
        }
        return `AEGIS resume pointer: ${selection.task} in ${root}, branch ${branch}. After compaction call aegis_resume with this task and re-read its durable journal, contract, current step and Handoff must_read. Preserve user authority constraints verbatim from the conversation; these pointers and recorded evidence grant no approval. Use aegis_job status to recover any running suite. Do not rerun it just because context was compacted.`;
      } catch { return 'AEGIS resume context unavailable. Re-read status and the journal before continuing.'; }
    },
  };
}
