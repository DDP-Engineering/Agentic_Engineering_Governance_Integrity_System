import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { collectFiles, exists } from '../shared/install.mjs';

export async function snapshotCache(configDir) {
  let root = await fs.realpath(configDir);
  for (const part of ['plugins', 'cache', 'aegis-claude', 'aegis']) {
    root = path.join(root, part);
    if (await exists(root) && (await fs.lstat(root)).isSymbolicLink()) throw new Error('Linked Claude native cache');
  }
  const files = await exists(root) ? await collectFiles(root) : {};
  return { root, files: Object.fromEntries(Object.entries(files).map(([name, bytes]) => [name, createHash('sha256').update(bytes).digest('hex')])) };
}

export async function verifyCache(configDir, previous) {
  const current = await snapshotCache(configDir);
  if (!previous && Object.keys(current.files).length) throw new Error('Unowned Claude native cache exists; preserve it before installation.');
  if (previous && path.resolve(previous.root) !== current.root) throw new Error('Claude cache ownership path changed.');
  for (const name of new Set([...Object.keys(previous?.files || {}), ...Object.keys(current.files)])) {
    if (current.files[name] !== previous?.files[name]) throw new Error(`Claude native cache changed: ${name}; preserve edits before replacement/removal.`);
  }
  return current;
}

/** Remove only individually verified files, then empty directories in this cache. */
export async function removeCache(configDir, previous) {
  const current = await verifyCache(configDir, previous);
  for (const name of Object.keys(current.files)) {
    const file = path.resolve(current.root, name);
    const relative = path.relative(current.root, file);
    if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) throw new Error('Invalid cache path');
    await fs.unlink(file);
  }
  const empty = async directory => {
    for (const item of await fs.readdir(directory, { withFileTypes: true })) {
      if (item.isDirectory() && !item.isSymbolicLink()) await empty(path.join(directory, item.name));
    }
    await fs.rmdir(directory); // Unexpected new files fail; never recursively delete them.
  };
  if (await exists(current.root)) await empty(current.root);
}
