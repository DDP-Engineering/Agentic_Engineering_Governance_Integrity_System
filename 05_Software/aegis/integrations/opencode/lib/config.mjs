// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import fs from 'node:fs/promises';

export const agentNames = ['aegis', 'aegis-spec-review', 'aegis-quality-review'];
export const commands = JSON.parse(await fs.readFile(new URL('./commands.json', import.meta.url), 'utf8'));
const prompts = Object.fromEntries(await Promise.all(agentNames.map(async name => [name,
  await fs.readFile(new URL(`../prompts/${name}.md`, import.meta.url), 'utf8')])));
const configured = new WeakSet();

export async function configure(config) {
  if (configured.has(config)) return;
  for (const [kind, names] of [['agent', agentNames], ['command', Object.keys(commands)]]) {
    for (const name of names) if (config[kind]?.[name]) {
      throw new Error(`AEGIS configuration conflict: ${kind}.${name} already exists. Remove the previous AEGIS integration before loading this package; keep a backup of any custom prompts.`);
    }
  }
  const inherited = config.agent?.build?.permission ?? config.permission ?? {};
  const base = typeof inherited === 'string' ? { '*': inherited } : structuredClone(inherited);
  const agents = {
    aegis: {
      description: 'Coordinate installed AEGIS tasks, independent reviews and tracked validation.',
      mode: 'primary', color: '#147D64', steps: 80, prompt: prompts.aegis,
      permission: { ...base, 'aegis_*': 'allow', task: { '*': 'deny', 'aegis-spec-review': 'allow', 'aegis-quality-review': 'allow' } },
    },
  };
  for (const name of agentNames.slice(1)) agents[name] = {
    description: name === 'aegis-spec-review' ? 'Independently review AEGIS specification compliance.' : 'Independently review AEGIS implementation quality and evidence.',
    mode: 'subagent', steps: 25, prompt: prompts[name],
    permission: { '*': 'deny', read: 'allow', glob: 'allow', grep: 'allow', list: 'allow', lsp: 'allow',
      aegis_read: 'allow', aegis_status: 'allow', aegis_resume: 'allow', aegis_summary: 'allow', aegis_candidate: 'allow', aegis_diff: 'allow' },
  };
  config.agent = { ...config.agent, ...agents };
  config.command = { ...config.command, ...Object.fromEntries(Object.entries(commands).map(([name, [description, template]]) =>
    [name, { description, template, agent: 'aegis', subtask: false }])) };
  configured.add(config);
}
