#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const exists = async file => fs.lstat(file).then(stat => !stat.isSymbolicLink(), () => false);
/** Advisory only: never read arbitrary journal prose into an automatic hook. */
export async function hookResponse(input) {
  if (!input || typeof input.cwd !== 'string' || !path.isAbsolute(input.cwd)) return {};
  const event = input.hook_event_name;
  if (event !== 'SessionStart' && !(event === 'PreToolUse' && input.tool_name === 'mcp__plugin_aegis_aegis__aegis_run')) return {};
  let root = path.resolve(input.cwd);
  for (let depth = 0; depth < 64; depth++) {
    if (await exists(path.join(root, '.agentic')) && await exists(path.join(root, '.agentic/aegis.py'))) break;
    if (await exists(path.join(root, '.git')) || path.dirname(root) === root || depth === 63) return {};
    root = path.dirname(root);
  }
  const tasks = [];
  const directory = path.join(root, '.agentic/tasks');
  if (await exists(directory)) {
    const handle = await fs.opendir(directory);
    let seen = 0;
    for await (const item of handle) {
      if (++seen > 100 || tasks.length >= 20) break;
      if (!item.isFile() || !/^TASK-[a-f0-9]+\.md$/.test(item.name)) continue;
      const file = await fs.open(path.join(directory, item.name), 'r');
      try {
        const buffer = Buffer.alloc(8192);
        const { bytesRead } = await file.read(buffer, 0, buffer.length, 0);
        const stage = buffer.subarray(0, bytesRead).toString('utf8').match(/^stage: (frame|specify|design|build|validate|deliver|survey|components|close|done)\s*$/m)?.[1];
        if (stage && stage !== 'done') tasks.push(`${item.name.slice(0, -3)} (${stage})`);
      } finally { await file.close(); }
    }
  }
  const context = 'This checkout has AEGIS installed. For authorized changes that add or change a durable product rule (logic, data, security, performance, integrations or a product-wide UI rule), load aegis:workflow and read the checkout instructions and full task journal. Make bug fixes that restore intended behavior, local UI adjustments, refactors and test, docs or tooling fixes directly, as the root AGENTS.md describes. Packaging, release and repository-only operations use their own procedures. '
    + (tasks.length ? `Open-task sample: ${tasks.sort().join(', ')}. Use aegis_status for the complete current list; do not infer the active task from this sample. ` : 'Use aegis_status to inspect current tasks. ')
    + (event === 'PreToolUse' ? 'Before starting verification, use the explicit task and inspect existing jobs; static checks are not test proof. Poll the returned job and inspect full results. ' : '')
    + 'This reminder does not grant tool, Git or publication approval. Existing user instructions and authorization apply.';
  return { hookSpecificOutput: { hookEventName: event, additionalContext: context } };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    let text = '';
    for await (const chunk of process.stdin) {
      text += chunk;
      if (Buffer.byteLength(text) > 65536) throw new Error('Hook input exceeds 64 KiB');
    }
    console.log(JSON.stringify(await hookResponse(JSON.parse(text))));
  } catch (error) {
    console.error(`AEGIS context unavailable: ${error.message}`);
    console.log('{}');
  }
}
