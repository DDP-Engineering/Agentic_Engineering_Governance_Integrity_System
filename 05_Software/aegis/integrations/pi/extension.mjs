import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { operations, createDispatcher } from '../shared/operations.mjs';

const root = path.dirname(fileURLToPath(import.meta.url));
export default function register(pi) {
  const dispatch = createDispatcher();
  const context = (ctx, abort) => ({ directory: ctx.cwd, worktree: ctx.cwd,
    sessionID: ctx.sessionManager?.getSessionId() || 'pi-command', agent: 'aegis', abort });
  const show = result => pi.sendMessage({ customType: 'aegis', content: JSON.stringify(result, null, 2), display: true }, { triggerTurn: false });
  pi.on('resources_discover', async () => ({ skillPaths: [path.join(root, 'skills')] }));
  for (const definition of operations) pi.registerTool({
    name: definition.name, label: definition.name, description: definition.description,
    parameters: definition.inputSchema,
    async execute(_id, args, signal, _update, ctx) {
      const result = await dispatch(definition.operation, args, context(ctx, signal));
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }], details: result };
    },
  });
  pi.registerCommand('aegis-start', { description: 'Start or resume governed software work using installed AEGIS.',
    async handler(args) {
      const instructions = await fs.readFile(path.join(root, 'skills/aegis/SKILL.md'), 'utf8');
      pi.sendUserMessage('Skill source: ' + path.join(root, 'skills/aegis/SKILL.md') + '\n\n' + instructions + '\n\nUser request:\n' + args);
    } });
  for (const [name, operation, extra] of [
    ['resume', 'resume', {}], ['status', 'status', {}], ['check', 'check', {}], ['validate', 'run', { kind: 'validate' }],
  ]) pi.registerCommand('aegis-' + name, {
    description: `${name} AEGIS workflow state${name === 'validate' ? ' (starts tracked verification)' : ''}; ${['resume', 'validate'].includes(name) ? 'requires' : 'optionally accepts'} a complete TASK ID.`,
    async handler(args, ctx) {
      try {
        const task = args.trim();
        if (['resume', 'validate'].includes(name) && !task) throw new Error('Supply a complete TASK-<hex> identifier.');
        show(await dispatch(operation, { ...extra, ...(task ? { task } : {}) }, context(ctx)));
      } catch (error) { show({ error: error.message }); }
    },
  });
}
