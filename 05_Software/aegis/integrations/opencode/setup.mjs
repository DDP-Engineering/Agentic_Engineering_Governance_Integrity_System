#!/usr/bin/env node
// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { parse } from '../shared/vendor/jsonc.mjs';
import { defaultConfigDir, discoverRuntime } from '../shared/runtime.mjs';
import { manageFiles, collectFiles, exists } from '../shared/install.mjs';
import { agentNames, commands } from './lib/config.mjs';

export async function openCodeSetup(action, { configDir = defaultConfigDir(), runtime = {} } = {}) {
  const source = path.dirname(fileURLToPath(import.meta.url));
  if (!await exists(path.join(source, 'package.json'))) throw new Error('Use the assembled OpenCode package; build it with 02_Tools/build_agent_plugins.mjs first.');
  configDir = path.resolve(configDir);
  if (action === 'doctor') {
    const stored = path.join(configDir, 'aegis-plugin/runtime.json');
    const settings = await discoverRuntime({ ...await exists(stored) ? JSON.parse(await fs.readFile(stored, 'utf8')) : {}, ...runtime });
    const hooks = await (await import(pathToFileURL(path.join(source, 'index.mjs')).href)).default({ directory: process.cwd() });
    const config = {}; await hooks.config(config);
    return { runtime: settings, agents: Object.keys(config.agent), commands: Object.keys(config.command), tools: Object.keys(hooks.tool), models_invoked: false };
  }
  if (action !== 'uninstall') {
    for (const name of ['opencode.json', 'opencode.jsonc']) {
      const file = path.join(configDir, name);
      if (!await exists(file)) continue;
      const errors = []; const config = parse(await fs.readFile(file, 'utf8'), errors, { allowTrailingComma: true });
      if (errors.length || !config || typeof config !== 'object') throw new Error(`Invalid ${name}; no files changed.`);
      for (const [kind, names] of [['agent', agentNames], ['command', Object.keys(commands)]])
        for (const key of names) if (config[kind]?.[key]) throw new Error(`Existing ${kind}.${key}; remove the earlier AEGIS integration first.`);
      for (const entry of config.plugin || []) if (JSON.stringify(entry).includes('@aegis/opencode-plugin')) throw new Error('AEGIS is already configured as an npm plugin; choose one installation method.');
    }
    for (const file of ['plugins/aegis.js', 'plugins/aegis.ts', ...agentNames.flatMap(n => [`agents/${n}.md`, `agent/${n}.md`]), ...Object.keys(commands).flatMap(n => [`commands/${n}.md`, `command/${n}.md`])])
      if (await exists(path.join(configDir, file))) throw new Error(`Existing ${file}; preserve/remove the earlier AEGIS integration first.`);
  }
  let settings, files = {};
  if (action !== 'uninstall') {
    const stored = path.join(configDir, 'aegis-plugin/runtime.json');
    settings = await discoverRuntime({ ...await exists(stored) ? JSON.parse(await fs.readFile(stored, 'utf8')) : {}, ...runtime });
    const packageFiles = await collectFiles(source);
    files = Object.fromEntries(Object.entries(packageFiles).map(([k,v]) => [`aegis-plugin/${k}`, v]));
    files['aegis-plugin/runtime.json'] = JSON.stringify(settings, null, 2) + '\n';
    files['plugins/aegis-package.js'] = 'export { default } from "../aegis-plugin/index.mjs";\n';
  }
  return manageFiles(action, { root: configDir, owner: 'opencode', prefixes: ['aegis-plugin/', 'plugins/aegis-package.js'], files, cache: settings?.cache });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const [action = 'doctor', ...args] = process.argv.slice(2); const options = { runtime: {} };
    for (let i = 0; i < args.length; i += 2) {
      if (!args[i + 1]) throw new Error(`Missing value for ${args[i]}`);
      if (args[i] === '--config-dir') options.configDir = args[i + 1];
      else if (['--node', '--python', '--cache'].includes(args[i])) options.runtime[args[i].slice(2)] = args[i + 1];
      else throw new Error(`Unknown option ${args[i]}`);
    }
    console.log(JSON.stringify(await openCodeSetup(action, options), null, 2));
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
