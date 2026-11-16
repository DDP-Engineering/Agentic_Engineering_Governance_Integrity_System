#!/usr/bin/env node

import { runBridge } from '../lib/bridge.mjs';
try { console.log(JSON.stringify(await runBridge(process.argv.slice(2)), null, 2)); }
catch (error) { console.error(error.message); process.exitCode = 1; }
