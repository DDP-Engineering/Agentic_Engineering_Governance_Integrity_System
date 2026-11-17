import { tool } from '../shared/vendor/opencode-tool.mjs';
import { configure } from './lib/config.mjs';
import { discoverRuntime, readSettings } from '../shared/runtime.mjs';
import { createAdapter } from '../shared/adapter.mjs';

export default async ({ directory }) => {
  let adapterPromise;
  const getAdapter = () => adapterPromise ||= readSettings().then(discoverRuntime).then(createAdapter).catch(error => { adapterPromise = undefined; throw error; });
  const s = tool.schema;
  const task = s.string().regex(/^TASK-[a-f0-9]{4,32}$/).describe('Complete TASK-<hex> identifier from this checkout.');
  const optionalTask = task.optional();
  const define = (name, operation, description, args) => tool({
    description,
    args,
    async execute(input, context) {
      await context.ask({ permission: name, patterns: [operation], always: ['*'], metadata: { operation } });
      const adapter = await getAdapter();
      const result = await adapter[operation](input, context);
      context.metadata({ title: name, metadata: { root: result.root || result.job?.root, jobID: result.job?.id } });
      return JSON.stringify(result, null, 2);
    },
  });
  return {
    config: configure,
    tool: {
      aegis_status: define('aegis_status', 'status', 'Read installed AEGIS task state and active verification. With no task, list open tasks; do not infer a selection.', { task: optionalTask, all: s.boolean().optional() }),
      aegis_resume: define('aegis_resume', 'resume', 'Read the task brief and status, verify branch alignment, and remember a session-local resume pointer. Does not advance stages or grant approval.', { task }),
      aegis_read: define('aegis_read', 'read', 'Read authoritative installed AEGIS instructions, configuration, current step, or complete journal. Read root AGENTS.md with the normal read tool too.', { document: s.enum(['contract', 'cli', 'config', 'step', 'journal']), task: optionalTask }),
      aegis_summary: define('aegis_summary', 'summary', 'Read the recorded State summary. This is agent-authored state, not fresh verification.', { task }),
      aegis_check: define('aegis_check', 'check', 'Run advisory or strict static AEGIS checks, without tests. Exit zero in advisory mode does not imply passing verification.', { task: optionalTask, strict: s.boolean().optional() }),
      aegis_scaffold: define('aegis_scaffold', 'scaffold', 'Coordinator only: create a task or requirement scaffold using the installed CLI. Inspect existing tasks/requirements first. Requirements need a named or resumed task. Fill in the generated record afterwards.', { kind: s.enum(['task', 'requirement']), task: optionalTask, title: s.string().min(1).max(500), type: s.enum(['feature', 'fix', 'change', 'adopt']).optional(), category: s.enum(['functional', 'ux', 'nfr', 'security', 'data', 'platform', 'reliability', 'test']).optional(), parent: optionalTask }),
      aegis_evidence: define('aegis_evidence', 'evidence', 'Coordinator only: record anchor after red test, refresh evolution after edits, or append the closing report at the end of validate. Does not fabricate observations or Git authority.', { action: s.enum(['anchor', 'evolution', 'report']), task: optionalTask, compact: s.boolean().optional().describe('Evolution only: omit hashes from the response, preserving saved evidence.') }),
      aegis_journal: define('aegis_journal', 'journal', 'Coordinator only: write task-journal state through the installed CLI. advance finishes a stage (to, skipped, reason, next); pause stops for the user (next, blocked); log appends one durable event (text); ruling appends a decision (decision, reason, source, supersedes); verdict records explicit review results (spec, quality, round). advance and pause also take read, changed, evidence and issues. Records your decision; never judges whether a stage is done.', {
        action: s.enum(['advance', 'pause', 'log', 'ruling', 'verdict']), task: optionalTask,
        to: s.enum(['frame', 'specify', 'design', 'build', 'validate', 'done', 'survey', 'components', 'close', 'deliver']).optional(),
        skipped: s.boolean().optional(), reason: s.string().max(1000).optional(),
        next: s.string().max(1000).optional(), blocked: s.boolean().optional(), read: s.array(s.string().max(500)).max(20).optional(),
        changed: s.string().max(1000).optional(), evidence: s.string().max(1000).optional(), issues: s.string().max(1000).optional(),
        text: s.string().max(1000).optional(), decision: s.string().max(1000).optional(),
        source: s.enum(['user', 'repository', 'requirement', 'technical']).optional(), supersedes: s.string().regex(/^RULING-\d{3}$/i).optional(),
        spec: s.enum(['approved', 'changes_required']).optional(), quality: s.enum(['approved', 'changes_required']).optional(),
        round: s.number().int().min(1).max(256).optional() }),
      aegis_candidate: define('aegis_candidate', 'candidate', 'Fingerprint the Git-visible candidate for both reviewers and final proof. Excludes task journals/evidence; read them separately. This fingerprint is not tamper-proof.', {}),
      aegis_diff: define('aegis_diff', 'diff', 'Read Git status, tracked diff against a named base (default HEAD), and untracked paths. Use the task journal base for a complete task review. Read relevant untracked contents separately.', { base: s.string().optional(), path: s.string().optional() }),
      aegis_run: define('aegis_run', 'run', 'Coordinator only: start tracked validation (check --strict --run --json) or a configured test command. Returns a job ID immediately. One active adapter run per checkout; poll aegis_job. No adapter timeout; installed AEGIS timeouts still apply.', { kind: s.enum(['validate', 'test']), task: optionalTask, command: s.string().optional().describe('For test only: name in [commands], never shell text.'), impacted: s.boolean().optional(), no_fallback: s.boolean().optional().describe('With impacted testing, refuse a full-suite fallback.'), base: s.string().optional() }),
      aegis_job: define('aegis_job', 'job', 'Read progress/log tails and complete results of tracked verification. No ID returns the active checkout job. Cancel requires an exact ID and the coordinator. Restarting OpenCode does not stop a run.', { action: s.enum(['status', 'cancel']).default('status'), id: s.string().uuid().optional() }),
    },
    'experimental.session.compacting': async ({ sessionID }, output) => {
      if (!adapterPromise) return;
      const adapter = await adapterPromise;
      const pointer = await adapter.compact(sessionID, directory);
      if (pointer) output.context.push(pointer);
    },
  };
};
