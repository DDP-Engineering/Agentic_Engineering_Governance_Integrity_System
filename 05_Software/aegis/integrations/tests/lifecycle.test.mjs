// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { manageFiles } from '../shared/install.mjs';
import { snapshotNativeCache, verifyNativeCache } from '../shared/native-cache.mjs';

test('install: cache changes cannot bypass active or uncertain reservations', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-cache-move-'));
  const cacheA = path.join(root, 'cache-a');
  const cacheB = path.join(root, 'cache-b');
  const options = { root, owner: 'sample', prefixes: ['sample/'], files: { 'sample/a.txt': 'one' }, cache: cacheA };
  await manageFiles('install', options);
  await fs.mkdir(cacheB);
  await fs.writeFile(path.join(cacheB, 'checkout.lock'), 'uncertain');
  await assert.rejects(manageFiles('update', { ...options, cache: cacheB }), /verification/);
  await assert.rejects(manageFiles('uninstall', { ...options, cache: cacheB }), /verification/);
  await fs.unlink(path.join(cacheB, 'checkout.lock'));
  await fs.mkdir(cacheA);
  await fs.writeFile(path.join(cacheA, 'checkout.lock'), JSON.stringify({ state: 'running', pid: process.pid }));
  await assert.rejects(manageFiles('update', { ...options, cache: cacheB }), /verification/);
  await assert.rejects(manageFiles('uninstall', { ...options, cache: cacheB }), /verification/);
  assert.equal(await fs.readFile(path.join(root, 'sample/a.txt'), 'utf8'), 'one');
});

test('install: protect native Codex cache edits, unowned additions and missing files', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-native-cache-'));
  await verifyNativeCache(root);
  const installedPath = path.join(root, 'plugins/cache/personal/aegis/0.10.0');
  await fs.mkdir(installedPath, { recursive: true });
  const skill = path.join(installedPath, 'SKILL.md');
  await fs.writeFile(skill, 'original skill');
  await assert.rejects(verifyNativeCache(root), /Unowned/);
  const snapshot = await snapshotNativeCache(root, installedPath);
  await verifyNativeCache(root, snapshot);
  await fs.writeFile(skill, 'personal edits');
  await assert.rejects(verifyNativeCache(root, snapshot), /changed/);
  assert.equal(await fs.readFile(skill, 'utf8'), 'personal edits');
  await fs.writeFile(skill, 'original skill');
  const extra = path.join(installedPath, 'notes.md'); await fs.writeFile(extra, 'keep');
  await assert.rejects(verifyNativeCache(root, snapshot), /changed/);
  await fs.unlink(extra); await fs.unlink(skill);
  await assert.rejects(verifyNativeCache(root, snapshot), /changed/);
  await assert.rejects(snapshotNativeCache(root, path.join(root, 'unrelated')), /unexpected/);
});

test('install: installed runtime rejects untracked cache overrides before starting a job', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-cache-override-'));
  const lib = path.join(root, 'lib'); await fs.mkdir(lib);
  await fs.copyFile(new URL('../shared/runtime.mjs', import.meta.url), path.join(lib, 'runtime.mjs'));
  const cache = path.join(root, 'cache-a');
  await fs.writeFile(path.join(root, 'runtime.json'), JSON.stringify({ cache }));
  const code = `import {readSettings} from ${JSON.stringify(pathToFileURL(path.join(lib, 'runtime.mjs')).href)}; console.log(JSON.stringify(await readSettings()));`;
  const result = spawnSync(process.execPath, ['--input-type=module', '-e', code], {
    encoding: 'utf8', env: { ...process.env, AEGIS_CACHE: path.join(root, 'cache-b') },
  });
  assert.equal(result.status, 1, 'untracked cache must be rejected');
  assert.match(result.stderr, /installer.*--cache/);
  const same = spawnSync(process.execPath, ['--input-type=module', '-e', code], {
    encoding: 'utf8', env: { ...process.env, AEGIS_CACHE: cache },
  });
  assert.equal(same.status, 0, same.stderr);
  assert.equal(JSON.parse(same.stdout).cache, cache);
});

test('install: preserve unrelated config, reject edited ownership, update and remove only owned files', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-install-'));
  const config = path.join(root, 'config.toml');
  await fs.writeFile(config, '# personal configuration\nmodel="kept"\n');
  const options = { root, owner: 'sample', prefixes: ['sample/', 'loaders/sample.js'], files: { 'sample/a.txt': 'one', 'loaders/sample.js': 'loader' } };
  await manageFiles('install', options);
  await assert.rejects(manageFiles('install', options), /already/);
  await fs.writeFile(path.join(root, 'sample/a.txt'), 'personal edit');
  await assert.rejects(manageFiles('uninstall', options), /changed/);
  assert.equal(await fs.readFile(config, 'utf8'), '# personal configuration\nmodel="kept"\n');
  await fs.writeFile(path.join(root, 'sample/a.txt'), 'one');
  await manageFiles('update', { ...options, files: { 'sample/a.txt': 'two', 'loaders/sample.js': 'loader' } });
  assert.equal(await fs.readFile(path.join(root, 'sample/a.txt'), 'utf8'), 'two');
  await manageFiles('uninstall', options);
  assert.equal(await fs.readFile(config, 'utf8'), '# personal configuration\nmodel="kept"\n');
  await assert.rejects(fs.access(path.join(root, 'sample/a.txt')));
});

test('install: refuse active verification and escaping manifest paths', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-install-lock-'));
  const cache = path.join(root, 'cache');
  const options = { root, owner: 'sample', prefixes: ['sample/'], files: { 'sample/a.txt': 'one' }, cache };
  await manageFiles('install', options);
  await fs.mkdir(cache); await fs.writeFile(path.join(cache, 'checkout.lock'), 'uncertain');
  await assert.rejects(manageFiles('update', options), /verification/);
  await assert.rejects(manageFiles('install', { ...options, owner: 'bad', files: { '../escape': 'bad' } }), /path|scope/);
  assert.equal(await fs.readFile(path.join(root, 'sample/a.txt'), 'utf8'), 'one');
});
