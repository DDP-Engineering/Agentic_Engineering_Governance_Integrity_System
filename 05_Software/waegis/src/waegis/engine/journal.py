#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file journal.py
@brief Checkpoint journal for wizard runs (plan §4: resume + doctor input).
@details Records one JSON file per run under the WAEGIS home
         (``WAEGIS_HOME`` env override, else ``%APPDATA%\\waegis`` on Windows,
         else ``~/.config/waegis`` on POSIX). The journal captures per-step
         timestamps, detect/act/verify outcomes, the non-secret answers and
         artifacts each step recorded, and the overall run status; it is
         rewritten after every step so an aborted run is recoverable. Secret
         values never enter a ``StepResult.answers`` map, so they cannot appear
         here. The current schema includes command/catalog/target/answers/
         payload fingerprints. Only an incomplete compatible journal may contribute
         replay answers, and its previously green steps are re-detected.
"""

# IMPORTS

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .step import GREEN_STATUSES, Remediation, StepResult, StepStatus

# CONSTANTS

# @brief Single current schema. WAEGIS is unreleased; no legacy schema is read.
JOURNAL_VERSION = 1

# @brief Run status recorded while steps are still executing.
STATUS_IN_PROGRESS = "in_progress"

# @brief Run status recorded when every planned step reached a green outcome.
STATUS_COMPLETED = "completed"

# @brief Run status recorded when a step failed and stopped the run.
STATUS_FAILED = "failed"

# @brief Run status recorded when an assisted step was declined and stopped the run.
STATUS_DECLINED = "declined"

# @brief Run status recorded when the run stopped for another reason (e.g. plan rejected).
STATUS_STOPPED = "stopped"

# @brief Subdirectory of the WAEGIS home that holds per-run journals.
_JOURNAL_DIRNAME = "journals"


# HELPER FUNCTIONS


def utc_now_iso() -> str:
    """
    @brief      Current UTC time as an ISO-8601 string with a trailing ``Z``.
    @return     Timestamp such as ``"2026-07-12T13:05:01Z"`` (second precision).
    @exception  None
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def waegis_home() -> Path:
    """
    @brief      Resolve the WAEGIS home directory for local state.
    @details    Resolution order: the ``WAEGIS_HOME`` environment override, else
                ``%APPDATA%\\waegis`` on Windows (falling back to
                ``~/AppData/Roaming/waegis`` if ``APPDATA`` is unset), else
                ``~/.config/waegis`` on POSIX. The directory is not created here.
    @return     Path to the WAEGIS home (may not yet exist).
    @exception  None
    """
    override = os.environ.get("WAEGIS_HOME")
    if override:
        return Path(override)
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "waegis"
    return Path.home() / ".config" / "waegis"


def _new_run_id() -> str:
    """
    @brief      Generate a unique, sortable run id.
    @return     Id such as ``"20260712T130501Z-a1b2c3"`` (UTC compact + random).
    @exception  None
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:6]}"


# PUBLIC API


class Journal:
    """
    @brief One run's checkpoint journal (plan §4).
    @details Holds the run metadata and the ordered per-step results, and writes
             them to a single JSON file that is refreshed after every recorded
             step. Use :meth:`begin` to start a fresh journal and :meth:`load` to
             read a prior one for resume.
    """

    def __init__(
        self,
        *,
        run_id: str,
        wizard_version: str,
        mode: str,
        target: str | None,
        dry_run: bool,
        started_at: str,
        path: Path,
        status: str = STATUS_IN_PROGRESS,
        finished_at: str | None = None,
        stopped_at_step: str | None = None,
        results: list[StepResult] | None = None,
        fingerprints: dict[str, str] | None = None,
    ) -> None:
        """
        @brief      Construct a journal from its fields. Prefer :meth:`begin` /
                    :meth:`load`.
        @param[in]  run_id Unique run identifier.
        @param[in]  wizard_version WAEGIS version that produced the run.
        @param[in]  mode Wizard mode label (``new``/``adopt``/test label).
        @param[in]  target Optional target repo path recorded for context.
        @param[in]  dry_run Whether the run was a preview only.
        @param[in]  started_at ISO-8601 start timestamp.
        @param[in]  path Filesystem path the journal is written to.
        @param[in]  status Current run status literal.
        @param[in]  finished_at ISO-8601 finish timestamp, when known.
        @param[in]  stopped_at_step Step id a stop occurred at, if any.
        @param[in]  results Ordered per-step results recorded so far.
        @param[in]  fingerprints Command/catalog/target/answers/payload
                    fingerprints recorded with the run.
        @return     None
        @exception  None
        """
        self.run_id = run_id
        self.wizard_version = wizard_version
        self.mode = mode
        self.target = target
        self.dry_run = dry_run
        self.started_at = started_at
        self.path = path
        self.status = status
        self.finished_at = finished_at
        self.stopped_at_step = stopped_at_step
        self.fingerprints = dict(fingerprints or {})
        self._results: list[StepResult] = list(results) if results else []

    @classmethod
    def begin(
        cls,
        *,
        mode: str,
        wizard_version: str,
        target: str | None = None,
        dry_run: bool = False,
        home: Path | None = None,
        fingerprints: dict[str, str] | None = None,
    ) -> "Journal":
        """
        @brief      Start a new journal under the WAEGIS home and write its
                    initial (empty, in-progress) document.
        @param[in]  mode Wizard mode label.
        @param[in]  wizard_version WAEGIS version producing the run.
        @param[in]  target Optional target repo path.
        @param[in]  dry_run Whether the run is a preview only.
        @param[in]  home Override home directory; defaults to :func:`waegis_home`.
        @param[in]  fingerprints Command/catalog/target/answers/payload
                    fingerprints to record with the run.
        @return     A ready-to-record :class:`Journal`.
        @exception  OSError If the journal directory or file cannot be created.
        """
        base = home if home is not None else waegis_home()
        run_id = _new_run_id()
        path = base / _JOURNAL_DIRNAME / f"{run_id}.json"
        journal = cls(
            run_id=run_id,
            wizard_version=wizard_version,
            mode=mode,
            target=target,
            dry_run=dry_run,
            started_at=utc_now_iso(),
            path=path,
            fingerprints=fingerprints,
        )
        journal.flush()
        return journal

    @classmethod
    def load(cls, path: str | Path) -> "Journal":
        """
        @brief      Load a prior journal from disk (for resume or inspection).
        @param[in]  path Path to the journal JSON file.
        @return     The reconstructed :class:`Journal`.
        @exception  OSError If the file cannot be read.
        @exception  json.JSONDecodeError If the file is not valid JSON.
        @exception  ValueError If the journal version is unsupported or a
                    required field is missing/malformed.
        """
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        journal_version = data.get("journal_version")
        if journal_version != JOURNAL_VERSION:
            raise ValueError(f"unsupported journal_version: {journal_version!r}")
        required = {
            "run_id",
            "wizard_version",
            "mode",
            "target",
            "dry_run",
            "started_at",
            "finished_at",
            "status",
            "stopped_at_step",
            "fingerprints",
            "steps",
        }
        missing = sorted(required - set(data))
        if missing:
            raise ValueError("current journal is missing required field(s): " + ", ".join(missing))
        if not isinstance(data["fingerprints"], dict) or not isinstance(data["steps"], list):
            raise ValueError("current journal fingerprints must be an object and steps must be an array")
        results = [cls._result_from_dict(item) for item in data["steps"]]
        return cls(
            run_id=data["run_id"],
            wizard_version=data["wizard_version"],
            mode=data["mode"],
            target=data["target"],
            dry_run=data["dry_run"],
            started_at=data["started_at"],
            path=path,
            status=data["status"],
            finished_at=data["finished_at"],
            stopped_at_step=data["stopped_at_step"],
            results=results,
            fingerprints=dict(data["fingerprints"]),
        )

    @staticmethod
    def _result_from_dict(item: dict[str, Any]) -> StepResult:
        """
        @brief      Rebuild a :class:`StepResult` from its journal mapping.
        @param[in]  item One entry of the journal ``steps`` array.
        @return     The reconstructed :class:`StepResult`.
        @exception  KeyError If the entry lacks a step id.
        @exception  ValueError If the status value is not a known ``StepStatus``.
        """
        failure = item.get("failure")
        remediation = (
            Remediation(
                diagnosis=failure.get("diagnosis", ""),
                remediation=failure.get("remediation", ""),
                it_request=failure.get("it_request"),
            )
            if failure
            else None
        )
        return StepResult(
            step_id=item["id"],
            status=StepStatus(item.get("status", StepStatus.PENDING.value)),
            detected=item.get("detected"),
            acted=item.get("acted", False),
            verified=item.get("verified"),
            started_at=item.get("started_at"),
            finished_at=item.get("finished_at"),
            answers=dict(item.get("answers", {})),
            artifacts=list(item.get("artifacts", [])),
            messages=list(item.get("messages", [])),
            failure=remediation,
            error=item.get("error"),
        )

    def record(self, result: StepResult) -> None:
        """
        @brief      Record (or replace) a step result and checkpoint to disk.
        @param[in]  result The step result to persist. A prior result for the
                    same step id is overwritten in place.
        @return     None
        @exception  OSError If the journal file cannot be written.
        """
        for position, existing in enumerate(self._results):
            if existing.step_id == result.step_id:
                self._results[position] = result
                break
        else:
            self._results.append(result)
        self.flush()

    def finalize(self, *, status: str, stopped_at_step: str | None = None) -> None:
        """
        @brief      Mark the run finished with a terminal status and checkpoint.
        @param[in]  status Terminal run status literal (e.g. ``completed``).
        @param[in]  stopped_at_step Step id a stop occurred at, if any.
        @return     None
        @exception  OSError If the journal file cannot be written.
        """
        self.status = status
        self.stopped_at_step = stopped_at_step
        self.finished_at = utc_now_iso()
        self.flush()

    def green_step_ids(self) -> set[str]:
        """
        @brief      Ids of steps that reached a green outcome in this journal.
        @return     Set of step ids whose recorded status is ``DONE`` or
                    ``SKIPPED`` — the seed set for resume.
        @exception  None
        """
        return {r.step_id for r in self._results if r.status in GREEN_STATUSES}

    def results(self) -> tuple[StepResult, ...]:
        """
        @brief      The recorded per-step results in order.
        @return     Tuple of :class:`StepResult`.
        @exception  None
        """
        return tuple(self._results)

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize the whole journal to a JSON-safe mapping.
        @return     The journal document (schema v1).
        @exception  None
        """
        return {
            "journal_version": JOURNAL_VERSION,
            "run_id": self.run_id,
            "wizard_version": self.wizard_version,
            "mode": self.mode,
            "target": self.target,
            "dry_run": self.dry_run,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "stopped_at_step": self.stopped_at_step,
            "fingerprints": dict(sorted(self.fingerprints.items())),
            "steps": [r.to_dict() for r in self._results],
        }

    def flush(self) -> None:
        """
        @brief      Atomically write the journal document to :attr:`path`.
        @details    Writes to a sibling temporary file and renames it into place
                    so a crash mid-write cannot leave a truncated journal.
        @return     None
        @exception  OSError If the directory or file cannot be created/written.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, self.path)


# END OF FILE
