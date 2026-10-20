<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Design diagrams (optional)

**Purpose:** Show the human operator the proposed implementation before
build writes code. Read this file only when `.agentic/aegis.toml` sets
`[diagrams] enabled = true`. A task with no design note (quick path, or a
design recorded as skipped) draws nothing.

**Steps:**

1. Read `[diagrams] types` in `.agentic/aegis.toml`. When the key is missing,
   use `["structure"]`. A non-list value counts as missing. An empty list draws
   nothing: write no file and no link. An unknown name is ignored.
   A list with no known name counts as an empty list.
2. From the final `## Design` text and the source you already read, draw one
   Mermaid diagram for each listed type that the design covers:

   | Type | Header | Draw when the design | Show |
   |---|---|---|---|
   | `structure` | `flowchart LR` or `flowchart TD` | adds or changes components, modules, files, or how they connect | the parts the change touches and their calls or data flow |
   | `sequence` | `sequenceDiagram` | has an execution flow across three or more participants, a process boundary, or asynchronous work | the order of calls and responses on the primary path |
   | `state` | `stateDiagram-v2` | adds or changes a lifecycle, a status field, or state transitions | states and the transitions between them |

   For a listed type the design does not cover, write that type's heading
   with one line under it: `Not drawn: <reason>.`
3. Write the whole file `.agentic/tasks/diagram_TASK-<id>.md` each time design
   reaches this step:

   ````markdown
   # TASK-<id> diagrams

   Illustrates `## Design` in `TASK-<id>.md`. The Design text is authoritative.

   ## Structure

   ```mermaid
   flowchart LR
       classDef added fill:#e1f5ee,stroke:#0f6e56
       classDef changed fill:#faeeda,stroke:#854f0b
       classDef removed stroke-dasharray:4 3
       cli["cli.parse_args"]:::changed ==> report["report.render"]:::added
       report ==> store[("task journal")]
       cli -.-> legacy["report.legacy_text"]:::removed
   ```

   ## Sequence

   Not drawn: the change runs in one process with no asynchronous work.
   ````

4. Add this line to `## Design` unless it is already there:
   `Diagrams: [diagram_TASK-<id>.md](diagram_TASK-<id>.md)`.

**Drawing rules:**

- The Design text is authoritative and the diagram only illustrates it. Draw
  nothing the Design does not state.
- Name nodes and participants after searchable code names. Give each node a
  simple id of letters, digits and underscores, with its label in double
  quotes.
- In structure diagrams, mark nodes `:::added`, `:::changed` or `:::removed`
  using the three `classDef` lines above. Draw added edges as `==>`, removed
  edges as `-.->`, and unchanged edges as `-->`.
- Keep each diagram to about 15 nodes. Split a larger change into one
  structure diagram per component.
- Put one diagram in each fenced block, using only the headers in the table
  above.

**Presentation:** in checkpoint mode, show the file's diagrams after the stage
summary and before the design stage-boundary choices. Autopilot writes the
file, names its path in the Stage report `changed` field, and adds no display
and no stop.

Nothing checks this file. It is not evidence, it is no Done when item, and no
later stage or review reads it.
