import fs from 'node:fs/promises';
import { openSync, closeSync } from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { terminateTree } from './process-tree.mjs';
import { fingerprint, jsonWrite } from './adapter.mjs';

const file = process.argv[2];
const job = JSON.parse(await fs.readFile(file, 'utf8'));
const cancelFile = path.join(path.dirname(file), `${job.id}.cancel`);
let out, err, timer, child, cancelling = false;
const persist = () => jsonWrite(file, job);
try {
  job.pid = process.pid;
  job.state = 'running';
  await persist();
  job.candidate_before = await fingerprint(job.root);
  out = openSync(job.stdout, 'a'); err = openSync(job.stderr, 'a');
  child = spawn(job.python, [path.join(job.root, '.agentic/aegis.py'), ...job.argv], {
    cwd: job.root, shell: false, windowsHide: true, detached: process.platform !== 'win32',
    stdio: ['ignore', out, err], env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
  });
  const completion = new Promise((resolve, reject) => { child.once('error', reject); child.once('close', (code, signal) => resolve({ code, signal })); });
  job.child_pid = child.pid;
  await persist();
  timer = setInterval(async () => {
    if (cancelling) return;
    try { await fs.access(cancelFile); } catch { return; }
    cancelling = true;
    try {
      await terminateTree(child);
    } catch (e) { job.cancel_detail = e.message; }
  }, 100);
  const ended = await completion;
  clearInterval(timer);
  job.state = cancelling ? 'cancelled' : 'completed';
  job.exit_code = cancelling ? null : ended.code;
  job.signal = ended.signal;
  job.candidate_after = await fingerprint(job.root);
  job.candidate_unchanged = job.candidate_before.digest === job.candidate_after.digest;
} catch (e) {
  job.state = 'failed'; job.exit_code = null; job.error = e.message;
} finally {
  clearInterval(timer);
  if (out !== undefined) closeSync(out);
  if (err !== undefined) closeSync(err);
  job.finished_at = new Date().toISOString();
  await persist();
  // Keep an uncertain lock if a worker failure may have left a child running.
  if (job.state !== 'failed' || !job.child_pid) {
    const lock = JSON.parse(await fs.readFile(job.lock, 'utf8').catch(() => '{}'));
    if (lock.id === job.id) await fs.unlink(job.lock);
  }
  await fs.unlink(cancelFile).catch(() => {});
}
