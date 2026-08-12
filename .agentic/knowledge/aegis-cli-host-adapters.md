# AEGIS CLI and host adapters

## Purpose

This component exposes one application protocol through the flat command-line
interface, human and JSON presenters, and five thin agent-host descriptors. It
owns transport and presentation only; workflow decisions and result semantics
remain in the application layer.

## Public interface

- `python -m aegis` and the `aegis` entry point expose registry-derived flat
  commands with human or JSON output.
- Input helpers read standard input, files, and scalar arguments into validated
  application inputs.
- Human and JSON presenters render the same `OperationResult`.
- The composition root constructs the concrete service graph.
- Claude Code, Codex, Qwen Code, OpenCode, and Pi descriptors bind host tools to
  the common dotted-operation contract.

## Key behaviors

- `REQ-PLAT-67c5d05e`, `REQ-PLAT-4ce82986` - machine output for every command
  with stdout reserved for one JSON response.
- `REQ-FUNC-7a19b623`, `REQ-FUNC-41d09b16` - equal human/machine semantics from
  one application result.
- `REQ-PLAT-f183e3cc` - one flat argparse subparser per command.
- `REQ-PLAT-7cd54b8e`, `REQ-PLAT-bc526721` - multiple hosts and the initial five
  supported descriptors.
- `REQ-FUNC-e5c2b57d`, `REQ-PLAT-7663bb1d`, `REQ-PLAT-5afdbb8a` - identical
  workflow meaning through policy-free common-protocol transports.
- `REQ-NFR-4b767a8b` - concrete construction only at composition.
- `REQ-PLAT-0e917260` - single product-version declarations.

## Files

- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/__init__.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/__main__.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/composition.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/interface/__init__.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/interface/cli.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/interface/input.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/interface/human_presenter.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/interface/json_presenter.py`
- `05_Software/aegis/template/.agentic/aegis/adapters/contract.json`
- `05_Software/aegis/template/.agentic/aegis/adapters/claude-code/adapter.json`
- `05_Software/aegis/template/.agentic/aegis/adapters/codex/adapter.json`
- `05_Software/aegis/template/.agentic/aegis/adapters/qwen-code/adapter.json`
- `05_Software/aegis/template/.agentic/aegis/adapters/opencode/adapter.json`
- `05_Software/aegis/template/.agentic/aegis/adapters/pi/adapter.json`
- `05_Software/aegis/tests/test_cli_protocol.py`
- `05_Software/aegis/tests/test_host_adapters.py`
- `05_Software/aegis/tests/test_architecture.py`

## Adoption notes

Adopted from 12 authoritative planning statements and 30 passing focused tests
on 2026-08-12. No suspected defect or untested load-bearing behavior was found.
