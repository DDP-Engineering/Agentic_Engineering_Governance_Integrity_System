/*
 * Copyright (c) 2026 DDP Engineering
 * This software is licensed under the PolyForm Noncommercial License 1.0.0.
 * Commercial use requires a separate commercial license.
 * See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  AgenticGuard,
  parseHookDecision,
} from "../plugins/agentic-guard.mjs";

test("parseHookDecision returns deny reason from hook stdout", () => {
  const stdout = JSON.stringify({
    hookSpecificOutput: {
      permissionDecision: "deny",
      permissionDecisionReason: "blocked",
    },
  });

  assert.equal(parseHookDecision(stdout), "blocked");
});

test("read tools use the shared configured Python hook", async () => {
  const calls = [];
  const hooks = await AgenticGuard(
    { directory: "/repo" },
    {
      cwd: "/repo",
      runPythonHook: async (hook, payload) => {
        calls.push({ hook, payload });
        return null;
      },
    },
  );

  await hooks["tool.execute.before"](
    { tool: "read" },
    { args: { filePath: "private/data.json" } },
  );

  assert.equal(calls.length, 1);
  assert.equal(calls[0].hook, "guard_read_path.py");
  assert.equal(calls[0].payload.tool_name, "Read");
  assert.equal(calls[0].payload.tool_input.file_path, "private/data.json");
});

test("write tools run write-zone and secret hooks", async () => {
  const calls = [];
  const hooks = await AgenticGuard(
    { directory: "/repo" },
    {
      cwd: "/repo",
      runPythonHook: async (hook, payload) => {
        calls.push({ hook, payload });
        return null;
      },
    },
  );

  await hooks["tool.execute.before"](
    { tool: "write" },
    { args: { filePath: "src/app.py", content: "print('ok')" } },
  );

  assert.deepEqual(
    calls.map((call) => call.hook),
    ["guard_write_zone.py", "secret_scan.py"],
  );
  assert.equal(calls[0].payload.tool_name, "Write");
  assert.equal(calls[0].payload.tool_input.file_path, "src/app.py");
});

test("bash tools run secret and delivery hooks", async () => {
  const calls = [];
  const hooks = await AgenticGuard(
    { directory: "/repo" },
    {
      cwd: "/repo",
      runPythonHook: async (hook, payload) => {
        calls.push({ hook, payload });
        return null;
      },
    },
  );

  await hooks["tool.execute.before"](
    { tool: "bash" },
    { args: { command: "git push origin main" } },
  );

  assert.deepEqual(
    calls.map((call) => call.hook),
    ["secret_scan.py", "delivery_preflight.py"],
  );
  assert.equal(calls[0].payload.tool_name, "Bash");
  assert.equal(calls[0].payload.tool_input.command, "git push origin main");
});

test("hook deny reasons block the tool call", async () => {
  const hooks = await AgenticGuard(
    { directory: "/repo" },
    {
      cwd: "/repo",
      runPythonHook: async () => "blocked by hook",
    },
  );

  await assert.rejects(
    hooks["tool.execute.before"]({ tool: "edit" }, { args: { filePath: "src/app.py" } }),
    /blocked by hook/,
  );
});

test("after tools record evidence", async () => {
  const calls = [];
  const hooks = await AgenticGuard(
    { directory: "/repo" },
    {
      cwd: "/repo",
      runPythonHook: async (hook, payload) => {
        calls.push({ hook, payload });
        return null;
      },
    },
  );

  await hooks["tool.execute.after"](
    { tool: "bash", toolCallId: "call-1" },
    { output: "ok" },
  );

  assert.equal(calls.length, 1);
  assert.equal(calls[0].hook, "post_tool_evidence.py");
  assert.equal(calls[0].payload.hook_event_name, "PostToolUse");
  assert.equal(calls[0].payload.tool_use_id, "call-1");
});
