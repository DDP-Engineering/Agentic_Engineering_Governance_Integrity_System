#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    operation_registry.py
@brief   Declare all 57 version 1 protocol operations exactly once.
@details Owns canonical inputs, bounded help, and executor bindings.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from __future__ import annotations

from aegis.application.operation_types import (
    ArgumentDefinition,
    DataFieldDefinition,
    MachineInputDefinition,
    MachineRevisionPolicy,
    OperationDefinition,
    OperationExecutor,
)
from aegis.application.product_operations import (
    show_help,
    show_version,
    unavailable_operation,
)
from aegis.application.workflow_operations import executor_for

# -----------------------------------------------------------------------------
# LOCAL HELPERS
# -----------------------------------------------------------------------------


def _option(
    name: str,
    display_name: str,
    description: str,
    *,
    required: bool = False,
    choices: tuple[str, ...] = (),
) -> ArgumentDefinition:
    """@return One declared option with a mechanically derived metavar."""
    value = display_name.removeprefix(f"--{name.replace('_', '-')} ").strip("<>")
    return ArgumentDefinition(
        name=name,
        flags=(f"--{name.replace('_', '-')}",),
        display_name=display_name,
        description=description,
        required=required,
        choices=choices,
        metavar=value or None,
    )


def _positional(
    name: str,
    display_name: str,
    description: str,
    *,
    choices: tuple[str, ...] = (),
) -> ArgumentDefinition:
    """@return One required positional input declaration."""
    return ArgumentDefinition(
        name=name,
        flags=(name,),
        display_name=display_name,
        description=description,
        required=True,
        choices=choices,
        metavar=display_name.strip("<>"),
    )


def _operation(
    operation: str,
    purpose: str,
    result: str,
    example: str,
    products: frozenset[str],
    arguments: tuple[ArgumentDefinition, ...] = (),
    executor: OperationExecutor | None = None,
) -> OperationDefinition:
    """@return One immutable registry declaration."""
    resolved_executor = executor_for(operation) if executor is None else executor
    policy = _MACHINE_REVISION_POLICIES[operation]
    if policy.requires_explicit_revision:
        executable, command = example.split(" ", 1)
        example = f"{executable} --expected-revision {_SHA256_EXAMPLE} {command}"
    return OperationDefinition(
        operation=operation,
        purpose=purpose,
        result=result,
        example=example,
        products=products,
        arguments=arguments,
        executor=resolved_executor,
        machine_revision_policy=policy,
        machine_input=_MACHINE_INPUTS.get(operation),
        implemented=resolved_executor is not unavailable_operation,
    )


def _field(
    name: str,
    type_name: str,
    description: str,
    *,
    required: bool = True,
    choices: tuple[str, ...] = (),
) -> DataFieldDefinition:
    """@return One operation-data field declaration."""
    return DataFieldDefinition(
        name=name,
        type_name=type_name,
        description=description,
        required=required,
        choices=choices,
    )


def _machine_input(
    *data_fields: DataFieldDefinition,
    constraints: tuple[str, ...] = (),
) -> MachineInputDefinition:
    """@return One structured input declaration for registry-owned help."""
    return MachineInputDefinition(data_fields, constraints)


# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

_COMMON = frozenset({"AEGIS", "WAEGIS"})
_AEGIS = frozenset({"AEGIS"})
_WAEGIS = frozenset({"WAEGIS"})
_CANONICAL_HEX = "0123456789abcdef0123456789abcdef"
_SHA256_EXAMPLE = "sha256:" + ("a" * 64)
_STAGES = (
    "intake",
    "alignment",
    "requirement",
    "design",
    "check",
    "implementation",
    "validation",
    "delivery",
)

_MACHINE_REVISION_POLICIES = {
    **{
        operation: MachineRevisionPolicy.EXEMPT_READ_ONLY
        for operation in (
            "help.show",
            "version.show",
            "config.show",
            "config.validate",
            "payload.verify",
            "run.list",
            "run.show",
            "stage.show",
            "requirement.show",
            "requirement.list",
            "requirement.validate",
            "component.show",
            "component.list",
            "component.validate",
            "component.find",
            "trace.validate",
            "execution.list",
            "adoption.list",
            "adoption.show",
        )
    },
    **{
        operation: MachineRevisionPolicy.EXEMPT_CREATE
        for operation in (
            "run.create",
            "requirement.create",
            "component.create",
            "adoption.create",
        )
    },
    "run.select": MachineRevisionPolicy.EXEMPT_WORKING_CONTEXT,
    "run.set_profile": MachineRevisionPolicy.REQUIRED_RUN,
    "run.abandon": MachineRevisionPolicy.CONDITIONAL_RUN,
    "scope.revise": MachineRevisionPolicy.REQUIRED_RUN,
    **{
        operation: MachineRevisionPolicy.REQUIRED_STAGE
        for operation in (
            "stage.start",
            "stage.set_section",
            "stage.complete",
            "stage.skip",
            "stage.revisit",
            "evidence.add",
            "finding.add",
            "finding.set_disposition",
            "finding.waive",
            "decision.add",
            "attachment.add",
            "trace.impacted",
            "execution.run",
        )
    },
    **{
        operation: MachineRevisionPolicy.REQUIRED_REQUIREMENT
        for operation in (
            "requirement.update",
            "requirement.delete",
            "specification.set",
            "specification.delete",
        )
    },
    **{
        operation: MachineRevisionPolicy.REQUIRED_COMPONENT
        for operation in ("component.update", "component.delete")
    },
    **{
        operation: MachineRevisionPolicy.REQUIRED_ADOPTION
        for operation in (
            "adoption.set_section",
            "adoption.complete",
            "adoption.abandon",
        )
    },
    **{
        operation: MachineRevisionPolicy.EXEMPT_SEPARATE_PLAN_PROTOCOL
        for operation in (
            "repository_init.plan",
            "repository_init.apply",
            "install.plan",
            "install.apply",
            "upgrade.plan",
            "upgrade.apply",
            "remove.plan",
            "remove.apply",
        )
    },
}

_ACTOR_REASON_FIELDS = (
    _field("actor", "string", "Actor authorizing the recorded action."),
    _field("reason", "string", "Non-empty reason for the recorded action."),
)
_REQUIREMENT_FIELDS = (
    _field("title", "string", "Concise Requirement title."),
    _field("behavior", "string", "One structured behavior statement."),
    _field("confirmation", "string", "Observable confirmation of the behavior."),
    _field(
        "status",
        "string",
        "Current Requirement status.",
        choices=("draft", "active"),
    ),
    _field(
        "priority",
        "string",
        "Requirement priority.",
        choices=("Must", "Should", "Could"),
    ),
    _field(
        "verification_kind",
        "string",
        "Whether confirmation is automated or manual.",
        choices=("automated", "manual"),
    ),
    _field(
        "impacted_files",
        "array[string]",
        "Non-empty repository-relative impacted path list.",
    ),
    _field(
        "tests",
        "array[object]",
        "Test links with path, selector, purposes, and covered_files.",
        required=False,
    ),
    _field(
        "manual_method",
        "string",
        "Concrete method required for manual verification.",
        required=False,
    ),
    _field("rationale", "string", "Optional Requirement rationale.", required=False),
)
_COMPONENT_FIELDS = (
    _field("name", "string", "Component name."),
    _field(
        "status",
        "string",
        "Current Component status.",
        choices=("draft", "active"),
    ),
    _field("files", "array[string]", "Non-empty owned path list."),
    _field(
        "file_roles",
        "array[object]",
        "One path and role object for every Component file.",
    ),
    _field(
        "requirement_links",
        "array[object]",
        "Atomic links containing exactly requirement_id and non-empty behavior.",
    ),
    _field(
        "test_links",
        "array[object]",
        "Test links with path, optional selector, and description.",
    ),
    _field("purpose_boundary", "string", "Component purpose and boundary."),
    _field("interfaces", "string", "Component interfaces."),
    _field("dependencies", "array", "Recorded dependencies.", required=False),
    _field("known_gaps", "array", "Known gaps kept visible.", required=False),
    _field(
        "drift_review",
        "object",
        (
            "Current behavior, interfaces, dependencies, and files review axes; "
            "each accepts yes, no, or uncertain, with optional finding text."
        ),
        required=False,
    ),
)
_COMPONENT_CONSTRAINTS = (
    "Do not provide legacy requirement_ids or behaviors fields; use requirement_links.",
    "Unknown drift_review fields are invalid; omitted axes default to uncertain.",
)
_MACHINE_INPUTS = {
    "run.create": _machine_input(
        _field(
            "ticket_text",
            "string",
            "Inline non-empty ticket text.",
            required=False,
        ),
        _field(
            "ticket_path",
            "string",
            "Path to UTF-8 ticket text.",
            required=False,
        ),
        _field(
            "profile",
            "string",
            "Run profile; defaults to full.",
            required=False,
            choices=("full", "short"),
        ),
        _field(
            "work_type",
            "string",
            "Run work type; defaults to change.",
            required=False,
            choices=("feature", "change", "quick_fix", "bug_fix"),
        ),
        _field(
            "actor",
            "string",
            "Opening actor; defaults to operator.",
            required=False,
        ),
        _field(
            "execution_instruction",
            "string",
            "Optional durable execution instruction.",
            required=False,
        ),
        constraints=("Provide exactly one of ticket_text or ticket_path.",),
    ),
    "run.abandon": _machine_input(*_ACTOR_REASON_FIELDS),
    "scope.revise": _machine_input(
        _field("before", "string", "Scope before the approved revision."),
        _field("after", "string", "Scope after the approved revision."),
        *_ACTOR_REASON_FIELDS,
        _field(
            "affected_work",
            "array[string]",
            "Paths or work names affected by the scope revision.",
        ),
    ),
    "stage.set_section": _machine_input(
        _field("section", "string", "Allowed section name from stage.show."),
        _field("content", "string", "Non-empty replacement section content."),
        _field(
            "actor",
            "string",
            "Actor replacing the section; defaults to operator.",
            required=False,
        ),
    ),
    "stage.skip": _machine_input(*_ACTOR_REASON_FIELDS),
    "stage.revisit": _machine_input(*_ACTOR_REASON_FIELDS),
    "evidence.add": _machine_input(
        _field(
            "kind",
            "string",
            "Evidence kind selecting its field contract.",
            choices=("manual", "automated", "imported"),
        ),
        _field("actor", "string", "Actor for manual evidence.", required=False),
        _field("procedure", "string", "Manual procedure used.", required=False),
        _field("expected", "string", "Manual expected result.", required=False),
        _field("actual", "string", "Manual observed result.", required=False),
        _field(
            "command",
            "array[string]",
            "Automated command argument vector.",
            required=False,
        ),
        _field(
            "selector",
            "string",
            "Automated configured selector alternative to command.",
            required=False,
        ),
        _field(
            "working_directory",
            "string",
            "Automated execution working directory.",
            required=False,
        ),
        _field(
            "outcome",
            "string",
            "Automated execution outcome.",
            required=False,
            choices=("passed", "failed", "timed_out", "cancelled", "launch_error"),
        ),
        _field(
            "exit_status",
            "integer|null",
            "Automated exit code, or null for incomplete execution.",
            required=False,
        ),
        _field(
            "observed_result",
            "string",
            "Concise automated observed result.",
            required=False,
        ),
        _field(
            "tests",
            "array[string]",
            "Non-empty automated test or check selectors covered.",
            required=False,
        ),
        constraints=(
            "Manual evidence requires actor, procedure, expected, and actual.",
            "Automated evidence requires command or selector, working_directory, "
            "outcome, exit_status, observed_result, and tests.",
        ),
    ),
    "finding.add": _machine_input(
        _field("severity", "string", "Non-empty finding severity."),
        _field("observation", "string", "Observed condition."),
        _field("consequence", "string", "Why the finding matters."),
    ),
    "finding.set_disposition": _machine_input(
        *_ACTOR_REASON_FIELDS,
        _field(
            "disposition",
            "string",
            "New finding disposition.",
            choices=("open", "resolved", "accepted", "waived", "not_applicable"),
        ),
    ),
    "finding.waive": _machine_input(*_ACTOR_REASON_FIELDS),
    "decision.add": _machine_input(
        _field(
            "value",
            "string",
            "Recorded decision value.",
            choices=("approved", "rejected", "exception_approved"),
        ),
        _field("actor", "string", "Decision actor."),
        _field("target", "string", "Decision target."),
        _field("reason", "string", "Decision reason or conditions."),
        _field(
            "alternative_confirmation",
            "string",
            "Required confirmation for an approved exception.",
            required=False,
        ),
        constraints=("exception_approved requires alternative_confirmation.",),
    ),
    "attachment.add": _machine_input(
        _field("source", "string", "Readable source file path."),
        _field("purpose", "string", "Purpose of the imported attachment."),
        _field("content_type", "string", "Attachment media or content type."),
    ),
    "requirement.create": _machine_input(*_REQUIREMENT_FIELDS),
    "requirement.update": _machine_input(*_REQUIREMENT_FIELDS),
    "specification.set": _machine_input(
        _field("title", "string", "Specification title."),
        _field("purpose", "string", "Specification purpose."),
        _field("contract", "string", "Behavioral contract."),
        _field("inputs_outputs", "string", "Inputs and outputs."),
        _field("rules", "array", "Specification rules."),
        _field("error_behavior", "string", "Error behavior."),
        _field("examples", "string", "Examples."),
        _field("open_details", "string", "Open implementation details."),
        _field(
            "status",
            "string",
            "Current Specification status.",
            choices=("draft", "active"),
        ),
    ),
    "component.create": _machine_input(
        *_COMPONENT_FIELDS, constraints=_COMPONENT_CONSTRAINTS
    ),
    "component.update": _machine_input(
        *_COMPONENT_FIELDS, constraints=_COMPONENT_CONSTRAINTS
    ),
    "trace.impacted": _machine_input(
        _field(
            "changed_files",
            "array[string]",
            "Repository-relative changed implementation paths.",
        ),
        _field(
            "changed_tests",
            "array[string]",
            "Repository-relative tests created or changed by the Run.",
            required=False,
        ),
    ),
    "run.set_profile": _machine_input(*_ACTOR_REASON_FIELDS),
    "adoption.create": _machine_input(
        _field("scope", "string", "Bounded Adoption scope."),
        _field("actor", "string", "Actor opening the Adoption."),
        _field(
            "observed_implementation",
            "array",
            "Observed implementation facts.",
        ),
        _field("observed_tests", "array", "Observed test facts."),
        _field("unresolved_gaps", "array", "Unresolved gaps kept visible."),
        _field(
            "component_id",
            "string",
            "Optional related Component identifier.",
            required=False,
        ),
    ),
    "adoption.set_section": _machine_input(
        _field("section", "string", "Allowed Adoption section name."),
        _field("content", "any JSON value", "Replacement section value."),
        _field("actor", "string", "Actor replacing the section."),
    ),
    "adoption.abandon": _machine_input(*_ACTOR_REASON_FIELDS),
}

_HELP_OPERATION = _option(
    "operation", "--operation <id>", "Show help for one operation or command."
)
_TICKET_INPUT = _option(
    "input",
    "--input <source>",
    "Read ticket input from a JSON file or standard input.",
    required=True,
)
_INPUT = _option(
    "input",
    "--input <source>",
    "Read operation input from a JSON file or stdin.",
    required=True,
)
_RUN_ID = _positional("run_id", "<run-id>", "Select the Run identifier.")
_RUN = _option("run", "--run <id>", "Use the selected Run identifier.")
_PROFILE = _option(
    "profile",
    "--profile <name>",
    "Select the full or short Run profile.",
    required=True,
    choices=("full", "short"),
)
_STAGE = _option(
    "stage", "--stage <name>", "Use the named canonical Stage.", choices=_STAGES
)
_STAGE_TARGET = _option(
    "stage_name",
    "--stage <name>",
    "Use the named canonical Stage.",
    choices=_STAGES,
)
_STAGE_NAME = _positional(
    "stage_name",
    "<stage-name>",
    "Select the canonical Stage name.",
    choices=_STAGES,
)
_FINDING = _option(
    "finding", "--finding <label>", "Select the finding label.", required=True
)
_REQUIREMENT = _option(
    "requirement",
    "--requirement <id>",
    "Select the Requirement identifier.",
    required=True,
)
_COMPONENT = _option(
    "component", "--component <id>", "Select the Component identifier.", required=True
)
_PATH = _option(
    "path", "--path <path>", "Select the repository-relative path.", required=True
)
_CATEGORY = _option(
    "category",
    "--category <tests|lints|audits>",
    "Select the tests, lints, or audits category.",
    required=True,
    choices=("tests", "lints", "audits"),
)
_NAME = _option(
    "name", "--name <name>", "Select the configured command name.", required=True
)
_SELECTION = _option(
    "selection", "--selection <label>", "Use the impacted-test selection label."
)
_CURSOR = _option(
    "cursor", "--cursor <token>", "Continue a bounded list at this item offset."
)
_ADOPTION = _option(
    "adoption", "--adoption <id>", "Select the Adoption identifier.", required=True
)
_TARGET = _option(
    "target", "--target <path>", "Select the target repository.", required=True
)
_OUTPUT = _option(
    "output", "--output <path>", "Write the plan to this file.", required=True
)
_PLAN = _option("plan", "--plan <path>", "Read the approved plan file.", required=True)
_CONFIRM_DIGEST = _option(
    "confirm_digest",
    "--confirm-digest <sha256>",
    "Confirm the exact approved plan digest.",
    required=True,
)

ALL_OPERATIONS = (
    _operation(
        "help.show",
        "Show bounded command help.",
        "Help metadata.",
        "aegis help-show",
        _COMMON,
        (_HELP_OPERATION,),
        show_help,
    ),
    _operation(
        "version.show",
        "Show product and protocol versions.",
        "Version and capability metadata.",
        "aegis version-show",
        _COMMON,
        executor=show_version,
    ),
    _operation(
        "config.show",
        "Show resolved project configuration.",
        "Configuration summary.",
        "aegis config-show",
        _AEGIS,
    ),
    _operation(
        "config.validate",
        "Validate project configuration.",
        "Configuration findings.",
        "aegis config-validate",
        _AEGIS,
    ),
    _operation(
        "payload.verify",
        "Verify installed payload ownership and bytes.",
        "Payload findings.",
        "aegis payload-verify",
        _AEGIS,
    ),
    _operation(
        "run.create",
        "Create one Run from ticket text.",
        "Created Run summary.",
        "aegis run-create --input ticket.json",
        _AEGIS,
        (_TICKET_INPUT,),
    ),
    _operation(
        "run.select",
        "Select one active Run.",
        "Selected Run identity.",
        "aegis run-select RUN-0123456789abcdef0123456789abcdef",
        _AEGIS,
        (_RUN_ID,),
    ),
    _operation(
        "run.list",
        "List bounded Run summaries.",
        "Run summary page.",
        "aegis run-list",
        _AEGIS,
        (_CURSOR,),
    ),
    _operation(
        "run.show",
        "Show one Run summary.",
        "Run state.",
        "aegis run-show --run RUN-0123456789abcdef0123456789abcdef",
        _AEGIS,
        (_RUN,),
    ),
    _operation(
        "run.set_profile",
        "Change one active Run profile.",
        "Updated Run state.",
        "aegis run-set-profile --profile full --input profile-change.json",
        _AEGIS,
        (_PROFILE, _INPUT),
    ),
    _operation(
        "run.abandon",
        "Abandon one active Run truthfully.",
        "Terminal abandonment state.",
        "aegis run-abandon --input abandonment.json",
        _AEGIS,
        (_INPUT,),
    ),
    _operation(
        "scope.revise",
        "Record one scope revision.",
        "Updated Run scope.",
        "aegis scope-revise --input scope.json",
        _AEGIS,
        (_INPUT,),
    ),
    _operation(
        "stage.show",
        "Show one Stage instruction and state.",
        "Stage context.",
        "aegis stage-show --stage implementation",
        _AEGIS,
        (_RUN, _STAGE_TARGET),
    ),
    _operation(
        "stage.start",
        "Start one pending Stage.",
        "Updated Stage and Run state.",
        "aegis stage-start implementation",
        _AEGIS,
        (_STAGE_NAME,),
    ),
    _operation(
        "stage.set_section",
        "Replace one mutable Stage section.",
        "Updated Stage state.",
        "aegis stage-set-section --input section.json",
        _AEGIS,
        (_INPUT,),
    ),
    _operation(
        "stage.complete",
        "Complete one current Stage.",
        "Updated Stage and Run state.",
        "aegis stage-complete",
        _AEGIS,
    ),
    _operation(
        "stage.skip",
        "Skip one eligible Stage.",
        "Skipped Stage state.",
        "aegis stage-skip --input reason.json",
        _AEGIS,
        (_INPUT,),
    ),
    _operation(
        "stage.revisit",
        "Revisit one completed or skipped Stage.",
        "Active Stage state.",
        "aegis stage-revisit validation --input reason.json",
        _AEGIS,
        (_STAGE_NAME, _INPUT),
    ),
    _operation(
        "evidence.add",
        "Append one evidence entry.",
        "Updated Stage revision.",
        "aegis evidence-add --input evidence.json",
        _AEGIS,
        (_INPUT,),
    ),
    _operation(
        "finding.add",
        "Append one finding.",
        "Updated Stage revision.",
        "aegis finding-add --input finding.json",
        _AEGIS,
        (_INPUT,),
    ),
    _operation(
        "finding.set_disposition",
        "Set one finding disposition.",
        "Updated finding state.",
        "aegis finding-set-disposition --finding F1 --input disposition.json",
        _AEGIS,
        (_FINDING, _INPUT),
    ),
    _operation(
        "finding.waive",
        "Waive one finding truthfully.",
        "Updated finding state.",
        "aegis finding-waive --finding F1 --input waiver.json",
        _AEGIS,
        (_FINDING, _INPUT),
    ),
    _operation(
        "decision.add",
        "Append one workflow decision.",
        "Updated Stage revision.",
        "aegis decision-add --input decision.json",
        _AEGIS,
        (_INPUT,),
    ),
    _operation(
        "attachment.add",
        "Import one supporting attachment.",
        "Created attachment and Stage revision.",
        "aegis attachment-add --input attachment.json",
        _AEGIS,
        (_INPUT,),
    ),
    _operation(
        "requirement.create",
        "Create one Requirement.",
        "Created Requirement.",
        "aegis requirement-create --input requirement.json",
        _AEGIS,
        (_INPUT,),
    ),
    _operation(
        "requirement.update",
        "Update one Requirement.",
        "Updated Requirement.",
        f"aegis requirement-update --requirement REQ-{_CANONICAL_HEX} "
        "--input requirement.json",
        _AEGIS,
        (_REQUIREMENT, _INPUT),
    ),
    _operation(
        "requirement.delete",
        "Delete one Requirement and dependent documentation.",
        "Deleted artifact actions.",
        f"aegis requirement-delete --requirement REQ-{_CANONICAL_HEX}",
        _AEGIS,
        (_REQUIREMENT,),
    ),
    _operation(
        "requirement.show",
        "Show one Requirement.",
        "Requirement summary.",
        f"aegis requirement-show --requirement REQ-{_CANONICAL_HEX}",
        _AEGIS,
        (_REQUIREMENT,),
    ),
    _operation(
        "requirement.list",
        "List bounded Requirement summaries.",
        "Requirement summary page.",
        "aegis requirement-list",
        _AEGIS,
        (_CURSOR,),
    ),
    _operation(
        "requirement.validate",
        "Validate one Requirement.",
        "Requirement findings.",
        f"aegis requirement-validate --requirement REQ-{_CANONICAL_HEX}",
        _AEGIS,
        (_REQUIREMENT,),
    ),
    _operation(
        "specification.set",
        "Create or update one Specification.",
        "Updated Specification.",
        f"aegis specification-set --requirement REQ-{_CANONICAL_HEX} "
        "--input specification.json",
        _AEGIS,
        (_REQUIREMENT, _INPUT),
    ),
    _operation(
        "specification.delete",
        "Delete one Specification.",
        "Deleted Specification action.",
        f"aegis specification-delete --requirement REQ-{_CANONICAL_HEX}",
        _AEGIS,
        (_REQUIREMENT,),
    ),
    _operation(
        "component.create",
        "Create one Component.",
        "Created Component.",
        "aegis component-create --input component.json",
        _AEGIS,
        (_INPUT,),
    ),
    _operation(
        "component.update",
        "Update one Component and drift review.",
        "Updated Component.",
        f"aegis component-update --component COMP-{_CANONICAL_HEX} "
        "--input component.json",
        _AEGIS,
        (_COMPONENT, _INPUT),
    ),
    _operation(
        "component.delete",
        "Delete one Component document.",
        "Deleted Component action.",
        f"aegis component-delete --component COMP-{_CANONICAL_HEX}",
        _AEGIS,
        (_COMPONENT,),
    ),
    _operation(
        "component.show",
        "Show one Component context.",
        "Component summary.",
        f"aegis component-show --component COMP-{_CANONICAL_HEX}",
        _AEGIS,
        (_COMPONENT,),
    ),
    _operation(
        "component.list",
        "List bounded Component summaries.",
        "Component summary page.",
        "aegis component-list",
        _AEGIS,
        (_CURSOR,),
    ),
    _operation(
        "component.validate",
        "Validate one Component.",
        "Component findings.",
        f"aegis component-validate --component COMP-{_CANONICAL_HEX}",
        _AEGIS,
        (_COMPONENT,),
    ),
    _operation(
        "component.find",
        "Find Components related to one path.",
        "Component matches.",
        "aegis component-find --path src/aegis",
        _AEGIS,
        (_PATH,),
    ),
    _operation(
        "trace.validate",
        "Validate current trace relationships.",
        "Trace findings.",
        "aegis trace-validate",
        _AEGIS,
    ),
    _operation(
        "trace.impacted",
        "Compute one impacted-test selection.",
        "Test selection and reasons.",
        "aegis trace-impacted --input changes.json",
        _AEGIS,
        (_INPUT,),
    ),
    _operation(
        "execution.list",
        "List configured and recorded executions.",
        "Execution summary page.",
        "aegis execution-list --stage implementation",
        _AEGIS,
        (_STAGE,),
    ),
    _operation(
        "execution.run",
        "Run one named configured command.",
        "Recorded execution outcome.",
        "aegis execution-run --category tests --name project",
        _AEGIS,
        (_CATEGORY, _NAME, _SELECTION),
    ),
    _operation(
        "adoption.create",
        "Create one Adoption journal.",
        "Created Adoption.",
        "aegis adoption-create --input adoption.json",
        _AEGIS,
        (_INPUT,),
    ),
    _operation(
        "adoption.list",
        "List bounded Adoption resume summaries.",
        "Adoption summary page.",
        "aegis adoption-list",
        _AEGIS,
        (_CURSOR,),
    ),
    _operation(
        "adoption.show",
        "Show one Adoption summary.",
        "Adoption resume state.",
        f"aegis adoption-show --adoption ADOPT-{_CANONICAL_HEX}",
        _AEGIS,
        (_ADOPTION,),
    ),
    _operation(
        "adoption.set_section",
        "Replace one Adoption section.",
        "Updated Adoption.",
        f"aegis adoption-set-section --adoption ADOPT-{_CANONICAL_HEX} "
        "--input section.json",
        _AEGIS,
        (_ADOPTION, _INPUT),
    ),
    _operation(
        "adoption.complete",
        "Complete one Adoption.",
        "Completed Adoption state.",
        f"aegis adoption-complete --adoption ADOPT-{_CANONICAL_HEX}",
        _AEGIS,
        (_ADOPTION,),
    ),
    _operation(
        "adoption.abandon",
        "Abandon one Adoption.",
        "Abandoned Adoption state.",
        f"aegis adoption-abandon --adoption ADOPT-{_CANONICAL_HEX} --input reason.json",
        _AEGIS,
        (_ADOPTION, _INPUT),
    ),
    _operation(
        "repository_init.plan",
        "Plan local Git initialization.",
        "Repository initialization plan.",
        "waegis repository-init-plan --target . --output plan.json",
        _WAEGIS,
        (_TARGET, _OUTPUT),
    ),
    _operation(
        "repository_init.apply",
        "Apply approved Git initialization.",
        "Initialization result.",
        f"waegis repository-init-apply --target . --plan p.json "
        f"--confirm-digest {_SHA256_EXAMPLE}",
        _WAEGIS,
        (_TARGET, _PLAN, _CONFIRM_DIGEST),
    ),
    _operation(
        "install.plan",
        "Plan AEGIS installation.",
        "Installation plan.",
        "waegis install-plan --target . --output plan.json",
        _WAEGIS,
        (_TARGET, _OUTPUT),
    ),
    _operation(
        "install.apply",
        "Apply an approved installation plan.",
        "Installation result.",
        f"waegis install-apply --target . --plan plan.json "
        f"--confirm-digest {_SHA256_EXAMPLE}",
        _WAEGIS,
        (_TARGET, _PLAN, _CONFIRM_DIGEST),
    ),
    _operation(
        "upgrade.plan",
        "Plan payload replacement.",
        "Upgrade plan.",
        "waegis upgrade-plan --target . --output plan.json",
        _WAEGIS,
        (_TARGET, _OUTPUT),
    ),
    _operation(
        "upgrade.apply",
        "Apply an approved upgrade plan.",
        "Upgrade result.",
        f"waegis upgrade-apply --target . --plan plan.json "
        f"--confirm-digest {_SHA256_EXAMPLE}",
        _WAEGIS,
        (_TARGET, _PLAN, _CONFIRM_DIGEST),
    ),
    _operation(
        "remove.plan",
        "Plan payload removal.",
        "Removal plan.",
        "waegis remove-plan --target . --output plan.json",
        _WAEGIS,
        (_TARGET, _OUTPUT),
    ),
    _operation(
        "remove.apply",
        "Apply an approved removal plan.",
        "Removal result.",
        f"waegis remove-apply --target . --plan plan.json "
        f"--confirm-digest {_SHA256_EXAMPLE}",
        _WAEGIS,
        (_TARGET, _PLAN, _CONFIRM_DIGEST),
    ),
)

# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------


def command_for(operation: str) -> str:
    """@return The only canonical flat command spelling."""
    return operation.replace(".", "-").replace("_", "-")


def operations_for(product: str) -> tuple[OperationDefinition, ...]:
    """@param[in] product Product name. @return Its ordered operation catalog."""
    return tuple(entry for entry in ALL_OPERATIONS if product in entry.products)


def find_operation(operation: str, product: str) -> OperationDefinition | None:
    """@return The matching product operation or ``None``."""
    return next(
        (
            entry
            for entry in ALL_OPERATIONS
            if entry.operation == operation and product in entry.products
        ),
        None,
    )


def find_command(command: str, product: str) -> OperationDefinition | None:
    """@return The matching canonical command entry or ``None``."""
    return next(
        (entry for entry in operations_for(product) if entry.command == command),
        None,
    )


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
