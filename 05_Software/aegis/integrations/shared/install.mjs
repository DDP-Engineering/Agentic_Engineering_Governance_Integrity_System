// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';

const hash = bytes => createHash('sha256').update(bytes).digest('hex');
export const exists = async file => {
  try { await fs.lstat(file); return true; } catch (e) { if (e.code === 'ENOENT') return false; throw e; }
};
export async function collectFiles(root, prefix = '') {
  const files = {};
  for (const item of await fs.readdir(path.join(root, prefix), { withFileTypes: true })) {
    const relative = path.posix.join(prefix, item.name);
    if (item.isSymbolicLink()) throw new Error(`Package contains a symbolic link: ${relative}`);
    if (item.isDirectory()) Object.assign(files, await collectFiles(root, relative));
    else files[relative] = await fs.readFile(path.join(root, relative));
  }
  return files;
}

/** Install/update/remove a declared set of files. Never replace host config. */
export async function manageFiles(action, { root, owner, prefixes, files = {}, cache, dryRun = false }) {
  if (!['install', 'update', 'uninstall'].includes(action)) throw new Error('Unknown lifecycle action');
  if (!/^[a-z-]+$/.test(owner)) throw new Error('Invalid installation owner');
  root = path.resolve(root);
  await fs.mkdir(root, { recursive: true });
  root = await fs.realpath(root);
  const target = async relative => {
    if (relative.includes('\\') || !prefixes.some(p => p.endsWith('/') ? relative.startsWith(p) : relative === p)) throw new Error(`Out-of-scope installation path: ${relative}`);
    const resolved = path.resolve(root, relative);
    const rel = path.relative(root, resolved);
    if (!rel || rel.startsWith('..') || path.isAbsolute(rel)) throw new Error('Invalid manifest path');
    let current = root;
    for (const part of rel.split(path.sep)) {
      current = path.join(current, part);
      if (await exists(current) && (await fs.lstat(current)).isSymbolicLink()) throw new Error(`Linked installation path: ${relative}`);
    }
    return resolved;
  };
  for (const relative of Object.keys(files)) await target(relative);
  const manifestFile = path.join(root, `.aegis-${owner}-installation.json`);
  const lockFile = path.join(root, `.aegis-${owner}-installation.lock`);
  const lock = await fs.open(lockFile, 'wx').catch(e => { if (e.code === 'EEXIST') throw new Error('Another installation holds the lock; inspect it before retrying.'); throw e; });
  try {
    const present = await exists(manifestFile);
    if (present && action === 'install') throw new Error('Installation already exists; use update.');
    if (!present && action !== 'install') throw new Error('No owned installation found.');
    if (present && (await fs.lstat(manifestFile)).isSymbolicLink()) throw new Error('Linked installation manifest');
    const old = present ? JSON.parse(await fs.readFile(manifestFile, 'utf8')) : { files: {} };
    if (present && old.owner !== owner) throw new Error('Installation owner mismatch');
    for (const jobCache of new Set([old.cache, cache].filter(Boolean))) {
      if (action !== 'install' && await exists(jobCache) && (await fs.readdir(jobCache)).some(n => n.endsWith('.lock'))) throw new Error('Active or uncertain verification exists; inspect jobs first.');
    }
    const previous = {};
    for (const [relative, digest] of Object.entries(old.files)) {
      const file = await target(relative);
      const bytes = await fs.readFile(file);
      if (hash(bytes) !== digest) throw new Error(`Installed file changed: ${relative}; preserve edits before replacement/removal.`);
      previous[relative] = bytes;
    }
    for (const relative of Object.keys(files)) {
      if (!Object.hasOwn(old.files, relative) && await exists(await target(relative))) throw new Error(`Unowned destination already exists: ${relative}`);
    }
    if (dryRun) return { action, root, verified: true };
    // All conflicts are checked before mutation. Roll back only our writes on failure.
    const next = action === 'uninstall' ? {} : files;
    const touched = new Set();
    const write = async (relative, bytes) => {
      const file = await target(relative);
      await fs.mkdir(path.dirname(file), { recursive: true });
      const temporary = `${file}.${randomUUID()}.tmp`;
      try { await fs.writeFile(temporary, bytes); await fs.rename(temporary, file); }
      finally { await fs.unlink(temporary).catch(() => {}); }
    };
    let backup;
    if (present) {
      backup = path.join(root, 'aegis-install-backups', owner, randomUUID());
      for (const [relative, bytes] of Object.entries(previous)) {
        const file = path.join(backup, relative); await fs.mkdir(path.dirname(file), { recursive: true }); await fs.writeFile(file, bytes);
      }
      await fs.copyFile(manifestFile, path.join(backup, 'installation.json'));
    }
    try {
      for (const [relative, bytes] of Object.entries(next)) { touched.add(relative); await write(relative, bytes); }
      for (const relative of Object.keys(previous)) if (!Object.hasOwn(next, relative)) { touched.add(relative); await fs.unlink(await target(relative)); }
      if (action === 'uninstall') await fs.unlink(manifestFile);
      else {
        const manifest = { ...old, owner, installedAt: new Date().toISOString(), cache: cache || old.cache,
          files: Object.fromEntries(Object.entries(next).map(([k,v]) => [k, hash(v)])) };
        const temporary = `${manifestFile}.${randomUUID()}.tmp`;
        await fs.writeFile(temporary, JSON.stringify(manifest, null, 2) + '\n');
        await fs.rename(temporary, manifestFile);
      }
    } catch (error) {
      for (const relative of touched) {
        if (Object.hasOwn(previous, relative)) await write(relative, previous[relative]);
        else await fs.unlink(await target(relative)).catch(() => {});
      }
      throw error;
    }
    return { action, root, ...(backup ? { backup } : {}), files: Object.keys(next).length };
  } finally { await lock.close(); await fs.unlink(lockFile); }
}
