// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import fs from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

/** Stop a known child and descendants, including sessions started by AEGIS. */
export async function terminateTree(child) {
  if (!child.pid || child.exitCode !== null || child.signalCode !== null) return;
  if (process.platform === 'win32') {
    await promisify(execFile)('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true });
    return;
  }
  if (process.platform !== 'linux') throw new Error('Process-tree cancellation is supported on Windows and Linux.');
  const records = new Map();
  for (const name of await fs.readdir('/proc')) {
    if (!/^\d+$/.test(name)) continue;
    try {
      const value = await fs.readFile(`/proc/${name}/stat`, 'utf8');
      const fields = value.slice(value.lastIndexOf(')') + 2).split(' ');
      records.set(Number(name), { parent: Number(fields[1]), start: fields[19] });
    } catch { /* Processes may exit while the snapshot is read. */ }
  }
  const descendants = [child.pid];
  for (let i = 0; i < descendants.length; i++)
    for (const [pid, info] of records) if (info.parent === descendants[i] && !descendants.includes(pid)) descendants.push(pid);
  // Kill descendants before the parent. Recheck start time to avoid a recycled PID.
  for (const pid of descendants.reverse()) {
    try {
      const value = await fs.readFile(`/proc/${pid}/stat`, 'utf8');
      const fields = value.slice(value.lastIndexOf(')') + 2).split(' ');
      if (records.get(pid)?.start === fields[19]) process.kill(pid, 'SIGKILL');
    } catch (e) { if (!['ENOENT', 'ESRCH'].includes(e.code)) throw e; }
  }
}
