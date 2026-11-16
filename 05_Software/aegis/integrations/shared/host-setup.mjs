import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { discoverRuntime } from './runtime.mjs';
import { collectFiles, exists, manageFiles } from './install.mjs';

const exec = promisify(execFile);
export const hostConfig = host => host === 'pi'
  ? process.env.PI_CODING_AGENT_DIR || path.join(os.homedir(), '.pi/agent')
  : process.env.QWEN_HOME || path.join(os.homedir(), '.qwen');

export async function resolveHost(host, node, explicit) {
  if (!['pi', 'qwen'].includes(host)) throw new Error('Unknown host');
  if (explicit) {
    const file = path.resolve(explicit);
    if (/\.(?:m?js)$/i.test(file)) return { command: node, args: [file] };
    if (/\.(?:cmd|bat|ps1)$/i.test(file)) throw new Error('Supply the native executable or JavaScript CLI entry, not a shell shim.');
    return { command: file, args: [] };
  }
  const entries = host === 'pi'
    ? ['@earendil-works/pi-coding-agent/dist/bundle/cli.js', '@mariozechner/pi-coding-agent/dist/cli.js']
    : ['@qwen-code/qwen-code/cli-entry.js'];
  for (const directory of (process.env.PATH || '').split(path.delimiter).filter(Boolean)) {
    const executable = path.resolve(directory, host + (process.platform === 'win32' ? '.exe' : ''));
    if (await exists(executable)) return { command: executable, args: [] };
    for (const entry of entries) {
      const candidate = path.resolve(directory, 'node_modules', entry);
      if (await exists(candidate)) return { command: node, args: [candidate] };
    }
  }
  throw new Error(`${host} CLI not found; supply --host-cli with its executable or JavaScript entry path.`);
}

/** Install native auto-discovered extension files without rewriting user settings. */
export async function hostSetup(host, source, action, options = {}) {
  if (!['install', 'update', 'uninstall', 'doctor'].includes(action)) throw new Error('Use install, update, uninstall or doctor.');
  const root = path.resolve(options.configDir || hostConfig(host));
  const prefix = 'extensions/aegis/';
  const owner = host;
  // Removal relies on the owned manifest, not on Python or the host remaining installed.
  if (action === 'uninstall') return manageFiles(action, { root, owner, prefixes: [prefix] });
  if (!await exists(path.join(source, 'lib/runtime.mjs'))) throw new Error('Build the portable package first; setup cannot install the source tree.');
  if (action !== 'doctor') await manageFiles(action, { root, owner, prefixes: [prefix], cache: options.runtime?.cache, dryRun: true });
  const storedFile = path.join(root, prefix, 'runtime.json');
  const stored = await exists(storedFile) ? JSON.parse(await fs.readFile(storedFile, 'utf8')) : {};
  const settings = await discoverRuntime({ ...stored, ...options.runtime });
  const cli = await resolveHost(host, settings.node, options.hostCli || stored.hostCliPath);
  const env = { ...process.env, [host === 'pi' ? 'PI_CODING_AGENT_DIR' : 'QWEN_HOME']: root,
    PI_OFFLINE: '1', PI_TELEMETRY: 'off' };
  const result = await exec(cli.command, [...cli.args, '--version', ...(host === 'pi' ? ['--no-extensions', '--offline'] : [])],
    { env, windowsHide: true, shell: false, timeout: 30000, maxBuffer: 1024 * 1024 });
  const version = result.stdout.trim();
  const runtime = { ...settings, host, hostCli: cli, hostCliPath: options.hostCli ? path.resolve(options.hostCli) : stored.hostCliPath };
  if (action === 'doctor') return { host, version, configDir: root, runtime, commands: 5, tools: 12,
    reviews: host === 'pi' ? 'separate read-tool processes' : 'two native review agents', models_invoked: false };
  const content = await collectFiles(source);
  const files = Object.fromEntries(Object.entries(content).map(([name, bytes]) => [prefix + name, bytes]));
  files[prefix + 'runtime.json'] = JSON.stringify(runtime, null, 2) + '\n';
  if (host === 'qwen') {
    const manifest = JSON.parse(content['qwen-extension.json'].toString());
    manifest.mcpServers.aegis.command = settings.node;
    files[prefix + 'qwen-extension.json'] = JSON.stringify(manifest, null, 2) + '\n';
  }
  return { ...await manageFiles(action, { root, owner, prefixes: [prefix], files, cache: settings.cache }),
    host, version, models_invoked: false, note: 'Restart the host to discover the AEGIS extension.' };
}

export async function setupMain(setup, argv) {
  try {
    const [action = 'doctor', ...args] = argv; const options = { runtime: {} };
    for (let i = 0; i < args.length; i += 2) {
      if (!args[i + 1]) throw new Error(`Missing value for ${args[i]}`);
      if (args[i] === '--config-dir') options.configDir = args[i + 1];
      else if (args[i] === '--host-cli') options.hostCli = args[i + 1];
      else if (['--node', '--python', '--cache'].includes(args[i])) options.runtime[args[i].slice(2)] = args[i + 1];
      else throw new Error(`Unknown option ${args[i]}`);
    }
    console.log(JSON.stringify(await setup(action, options), null, 2));
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
