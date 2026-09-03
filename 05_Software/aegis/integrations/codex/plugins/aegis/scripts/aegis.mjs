#!/usr/bin/env node
// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import { runBridge } from '../lib/bridge.mjs';
try { console.log(JSON.stringify(await runBridge(process.argv.slice(2)), null, 2)); }
catch (error) { console.error(error.message); process.exitCode = 1; }
