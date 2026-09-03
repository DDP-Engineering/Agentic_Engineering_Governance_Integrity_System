#!/usr/bin/env node
// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { hostSetup, setupMain } from '../shared/host-setup.mjs';
const source = path.dirname(fileURLToPath(import.meta.url));
export const setup = (action, options) => hostSetup('qwen', source, action, options);
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await setupMain(setup, process.argv.slice(2));
