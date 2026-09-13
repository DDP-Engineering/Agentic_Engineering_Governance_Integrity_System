// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import { tool } from './vendor/opencode-tool.mjs';
import { discoverRuntime, readSettings } from './runtime.mjs';
import { createAdapter } from './adapter.mjs';

const s = tool.schema;
export const taskSchema = s.string().regex(/^TASK-[a-f0-9]{4,32}$/).describe('Complete TASK-<hex> identifier from this checkout.');
const optionalTask = taskSchema.optional();
const define = (operation, description, args, readOnly = true) => {
  const schema = s.strictObject(args);
  return { name: 'aegis_' + operation, operation, description, schema,
    inputSchema: s.toJSONSchema(schema, { target: 'draft-7', io: 'input' }),
    annotations: { readOnlyHint: readOnly, openWorldHint: false } };
};

export const operations = [
  define('status', 'Read installed AEGIS task state and active verification. Without a task, list tasks; do not infer a selection.', { task: optionalTask, all: s.boolean().optional() }),
  define('resume', 'Read the task brief, verify branch alignment and remember a session-local pointer. Does not advance stages or grant approval.', { task: taskSchema }),
  define('read', 'Read authoritative installed AEGIS instructions, configuration, current step or journal. Read root AGENTS.md with the host read tool too.', { document: s.enum(['contract', 'cli', 'config', 'step', 'journal']), task: optionalTask }),
  define('summary', 'Read the recorded stage report; this is not fresh verification.', { task: taskSchema }),
  define('check', 'Run static AEGIS checks without tests. Advisory exit zero does not imply passing verification.', { task: optionalTask, strict: s.boolean().optional() }),
  define('scaffold', 'Coordinator only: create a task or requirement scaffold. Inspect existing records first and fill the generated record afterwards.', { kind: s.enum(['task', 'requirement']), task: optionalTask, title: s.string().min(1).max(500), type: s.enum(['feature', 'fix', 'change', 'adopt']).optional(), category: s.enum(['functional', 'ux', 'nfr', 'security', 'data', 'platform', 'reliability', 'test']).optional(), parent: optionalTask }, false),
  define('evidence', 'Coordinator only: record an anchor after a real red test, refresh evolution after edits or append a delivery report. Never fabricate observations.', { action: s.enum(['anchor', 'evolution', 'report']), task: optionalTask, compact: s.boolean().optional().describe('Evolution only: omit hashes from the response, preserving saved evidence.') }, false),
  define('candidate', 'Fingerprint Git-visible files for independent reviews and final proof. Task journals are excluded and must be read separately; this is not tamper-proof.', {}),
  define('diff', 'Read Git status, tracked diff against a named base (default HEAD) and untracked paths. Read relevant untracked contents separately.', { base: s.string().optional(), path: s.string().optional() }),
  define('run', 'Coordinator only: start tracked validation or a named configured test command. Returns a job ID immediately. Poll job; do not duplicate an active suite.', { kind: s.enum(['validate', 'test']), task: optionalTask, command: s.string().optional().describe('Configured command name, never shell text.'), impacted: s.boolean().optional(), no_fallback: s.boolean().optional().describe('With impacted testing, refuse a full-suite fallback.'), base: s.string().optional() }, false),
  define('job', 'Read tracked verification progress and results. Cancellation requires an exact ID and coordinator authority. Restarting the host does not stop a run.', { action: s.enum(['status', 'cancel']).default('status'), id: s.string().uuid().optional() }, false),
];

export function createDispatcher() {
  let pending;
  return async (operation, input, context) => {
    const definition = operations.find(item => item.operation === operation);
    if (!definition) throw new Error('Unknown AEGIS operation');
    const args = definition.schema.parse(input);
    pending ||= readSettings().then(discoverRuntime).then(createAdapter).catch(error => { pending = undefined; throw error; });
    return (await pending)[operation](args, context);
  };
}
