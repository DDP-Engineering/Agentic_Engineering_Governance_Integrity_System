#!/usr/bin/env node
import { operations, createDispatcher } from './operations.mjs';

const failure = (id, code, message) => ({ jsonrpc: '2.0', id, error: { code, message } });
const success = (id, result) => ({ jsonrpc: '2.0', id, result });
const validId = id => typeof id === 'string' || (typeof id === 'number' && Number.isFinite(id));

/** Minimal MCP stdio server: tools only, no network listener or shell evaluation. */
export function createProtocol({ root = process.cwd(), version = 'unknown', host = 'qwen' } = {}) {
  const dispatch = createDispatcher();
  const active = new Map();
  let initialized = false, ready = false;
  const handle = async message => {
    if (!message || Array.isArray(message) || message.jsonrpc !== '2.0' || typeof message.method !== 'string' ||
      (Object.hasOwn(message, 'id') && !validId(message.id))) return failure(null, -32600, 'Invalid JSON-RPC request');
    const { id, method } = message;
    const params = message.params ?? {};
    if (id === undefined) {
      if (method === 'notifications/initialized' && initialized) ready = true;
      if (method === 'notifications/cancelled') active.get(params?.requestId)?.abort();
      return undefined;
    }
    if (active.has(id)) return failure(id, -32600, 'Request ID already active');
    if (!params || typeof params !== 'object' || Array.isArray(params)) return failure(id, -32602, 'Parameters must be an object');
    if (method === 'ping') return success(id, {});
    if (method === 'initialize') {
      if (initialized) return failure(id, -32600, 'Already initialized');
      if (typeof params.protocolVersion !== 'string' || !params.clientInfo || !params.capabilities) return failure(id, -32602, 'Missing initialization parameters');
      initialized = true;
      const supported = ['2025-06-18', '2025-03-26', '2024-11-05'];
      return success(id, { protocolVersion: supported.includes(params.protocolVersion) ? params.protocolVersion : supported[0],
        capabilities: { tools: {} }, serverInfo: { name: 'aegis', version },
        instructions: 'Use the installed AEGIS skill and checkout workflow. Static checks are not test proof; poll tracked jobs.' });
    }
    if (!ready) return failure(id, -32002, 'Initialize the server and send notifications/initialized first');
    if (method === 'tools/list') return success(id, { tools: operations.map(({ name, description, inputSchema, annotations }) => ({ name, description, inputSchema, annotations })) });
    if (method !== 'tools/call') return failure(id, -32601, 'Method not found');
    const definition = operations.find(item => item.name === params.name);
    if (!definition) return failure(id, -32602, 'Unknown AEGIS tool');
    const parsed = definition.schema.safeParse(params.arguments ?? {});
    if (!parsed.success) return failure(id, -32602, parsed.error.message);
    if (active.size >= 32) return failure(id, -32000, 'Too many active requests');
    const controller = new AbortController(); active.set(id, controller);
    try {
      const result = await dispatch(definition.operation, parsed.data,
        { directory: root, worktree: root, sessionID: `${host}-mcp-${process.pid}`, agent: 'aegis', abort: controller.signal });
      return success(id, { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] });
    } catch (error) {
      return success(id, { isError: true, content: [{ type: 'text', text: error.message }] });
    } finally { active.delete(id); }
  };
  return { handle };
}

export function serve(protocol, input = process.stdin, output = process.stdout) {
  const limit = 1024 * 1024;
  let buffer = '', closed = false;
  const send = message => { if (message !== undefined && !closed) output.write(JSON.stringify(message) + '\n'); };
  input.setEncoding('utf8');
  input.on('data', chunk => {
    if (closed) return;
    buffer += chunk;
    let boundary;
    while ((boundary = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 1);
      if (Buffer.byteLength(line) > limit) { send(failure(null, -32600, 'Message exceeds one MiB')); closed = true; input.destroy(); return; }
      if (!line.trim()) continue;
      let message;
      try { message = JSON.parse(line); }
      catch { send(failure(null, -32700, 'Invalid JSON')); continue; }
      Promise.resolve(protocol.handle(message)).then(send).catch(() => send(failure(message?.id ?? null, -32603, 'Internal error')));
    }
    if (Buffer.byteLength(buffer) > limit) { send(failure(null, -32600, 'Message exceeds one MiB')); closed = true; input.destroy(); }
  });
  input.on('end', () => { if (buffer.trim() && !closed) send(failure(null, -32700, 'Incomplete newline-delimited message')); });
  input.on('error', error => { console.error(`AEGIS input error: ${error.message}`); });
  output.on('error', () => { closed = true; input.destroy(); });
}

