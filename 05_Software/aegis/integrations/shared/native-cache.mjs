// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { collectFiles, exists } from './install.mjs';

const canonical = value => process.platform === 'win32' ? path.resolve(value).toLowerCase() : path.resolve(value);

/** Inspect only the native AEGIS cache subtree, including additional versions/files. */
export async function snapshotNativeCache(codexHome, installedPath) {
  codexHome = await fs.realpath(codexHome);
  let root = codexHome;
  for (const part of ['plugins', 'cache', 'personal', 'aegis']) {
    root = path.join(root, part);
    if (await exists(root) && (await fs.lstat(root)).isSymbolicLink()) throw new Error('Linked native Codex cache; preserve it before changing this installation.');
  }
  if (installedPath) {
    const relative = path.relative(root, path.resolve(installedPath));
    if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) throw new Error('Codex returned an unexpected AEGIS installedPath.');
  }
  const content = await exists(root) ? await collectFiles(root) : {};
  return { root, installedPath, files: Object.fromEntries(Object.entries(content).map(([name, bytes]) =>
    [name, createHash('sha256').update(bytes).digest('hex')])) };
}

/** Refuse replacement/removal when native installation bytes have changed. */
export async function verifyNativeCache(codexHome, previous) {
  const current = await snapshotNativeCache(codexHome, previous?.installedPath);
  if (previous && canonical(previous.root) !== canonical(current.root)) throw new Error('Native Codex cache ownership path changed.');
  if (!previous && Object.keys(current.files).length) throw new Error('Unowned native Codex AEGIS cache exists; preserve it before installation.');
  for (const name of new Set([...Object.keys(previous?.files || {}), ...Object.keys(current.files)])) {
    if (previous?.files?.[name] !== current.files[name]) throw new Error(`Installed native Codex file changed: ${name}; preserve edits before replacement/removal.`);
  }
  return current;
}
