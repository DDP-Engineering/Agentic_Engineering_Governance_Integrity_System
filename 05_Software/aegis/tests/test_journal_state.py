#!/usr/bin/env python3
"""
The CLI journal writers: `advance`, `pause`, `log`, `ruling`, `verdict`.

The writers record what the agent decided and never refuse a
transition because work looks unfinished; they keep legacy journals
readable and replace the old Handoff and Stage report on first write.
"""


from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_check import make_repo, run_check, write, write_task
from test_run_report import config, run, summary_fields


def new_task(tmp_path: Path, monkeypatch, capsys, *argv: str):
    """An initialised repo with one fresh journal; returns (agentic, aegis, path)."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "git_branch", lambda: "feature/state")
    monkeypatch.setattr(aegis, "git_head", lambda: "")
    code, out = run(aegis, capsys, "task", *(argv or ("Export playlist",)))
    assert code == 0
    return agentic, aegis, tmp_path / out.strip()


def journal(aegis, path: Path) -> tuple[str, dict, dict]:
    """The journal text, its parsed form and its State fields."""
    text = path.read_text(encoding="utf-8")
    return text, aegis.parse_journal(text), aegis.parse_state(text)


def section(aegis, text: str, name: str) -> str:
    """One section's body, stripped."""
    start, end = aegis.section_bounds(text, name)
    return "\n".join(text.split("\n")[start:end]).strip()


def enable_review(agentic: Path, cycles: int = 2) -> None:
    """Turn explicit review on with the given fix-cycle bound."""
    config(agentic, 'test = "unused"',
           extra=f"[review]\nenabled = true\nmax_fix_cycles = {cycles}")


LEGACY = """
## Handoff

current: build
status: ready
next: run the focused test
must_read: .agentic/steps/4_build.md
blockers:

## Stage report

stage: build
result: in_progress
current: build
changed: src/app.py
evidence: focused test red
issues: none
next: implement
needs_user: no
spec_compliance:
implementation_quality:
review_round:
"""


def test_advance_follows_the_full_path_and_prints_the_next_card(tmp_path, monkeypatch, capsys):
    """Without --to the next stage comes from the journal's path."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    code, out = run(aegis, capsys, "advance", path.stem, "--changed", "Frame card written")
    assert code == 0
    text, data, state = journal(aegis, path)
    assert data["header"]["stage"] == "specify"
    assert state["status"] == "ready" and state["reported"] == "frame - completed"
    assert state["next"] == "start specify: read .agentic/steps/2_specify.md"
    assert state["must_read"] == f".agentic/tasks/{path.stem}.md, .agentic/steps/2_specify.md"
    assert state["changed"] == "Frame card written"
    assert section(aegis, text, "done checklist") == aegis.done_when("specify")
    unticked = aegis.done_when("frame").count("- [ ]")
    assert data["log"][-1].endswith(
        f"frame: completed; next specify ({unticked} Done checklist item(s) left unticked)")
    assert summary_fields(out.split("Note:")[0])["Stage"] == "frame - completed"
    assert out.rstrip().endswith("Next: read .agentic/steps/2_specify.md and continue specify")


def test_new_journals_carry_no_path_and_advance_has_no_path_option(tmp_path, monkeypatch,
                                                                    capsys):
    """Every task walks one stage order; the retired quick path left no option behind."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    _text, data, _state = journal(aegis, path)
    assert "path" not in data["header"]
    with pytest.raises(SystemExit) as exc:
        aegis.main(["advance", path.stem, "--path", "quick"])
    assert exc.value.code == 2
    assert journal(aegis, path)[1]["header"]["stage"] == "frame"


def test_a_legacy_quick_journal_follows_the_one_stage_order(tmp_path, capsys):
    """An older `path: quick` line is kept and no longer changes the next stage."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    path = write(agentic / "tasks" / "TASK-ab12.md",
                 "# TASK-ab12 - legacy\n\nstage: frame\ntype: fix\npath: quick\n"
                 "requirements:\nbranch: feature\n\n"
                 "## Done checklist (current stage)\n\n- [x] done\n\n## Log\n\n- 2026-08-02 frame: opened\n"
                 "\n## Stage report\n\nstage: frame\nresult: in_progress\ncurrent: frame\n")
    code, out = run(aegis, capsys, "advance", "ab12")
    assert code == 0 and "add them" not in out  # no quick-path reminder remains
    header = aegis.parse_journal(path.read_text(encoding="utf-8"))["header"]
    assert (header["stage"], header["path"]) == ("specify", "quick")
    write(path, path.read_text(encoding="utf-8").replace("stage: specify", "stage: build", 1))
    assert run(aegis, capsys, "advance", "ab12")[0] == 0
    assert aegis.parse_journal(path.read_text(encoding="utf-8"))["header"]["stage"] == "validate"


def test_header_writer_adds_a_missing_line_inside_the_header_block(tmp_path):
    """An older journal without a header key gains it at the end of the header block."""
    _agentic, aegis = make_repo(tmp_path)
    text = ("# TASK-ab12 - legacy\n\nstage: frame\ntype: fix\nbranch: feature\n\n"
            "## Log\n\n- 2026-08-02 frame: opened\n")
    updated = aegis.header_with(text, "interaction", "autopilot")
    assert updated.startswith("# TASK-ab12 - legacy\n\nstage: frame\ntype: fix\n"
                              "branch: feature\ninteraction: autopilot\n\n## Log\n")


def test_header_writer_never_touches_a_same_named_field_outside_the_header(tmp_path):
    """A `stage:` line in another section is content, not the header."""
    _agentic, aegis = make_repo(tmp_path)
    text = "# TASK-ab12 - x\n\ntype: fix\n\n## Notes\n\nstage: frame\n"
    updated = aegis.header_with(text, "stage", "build")
    assert updated == "# TASK-ab12 - x\n\ntype: fix\nstage: build\n\n## Notes\n\nstage: frame\n"
    assert aegis.header_with("# TASK-ab12 - x\n\n## Log\n", "stage", "frame") == (
        "# TASK-ab12 - x\n\nstage: frame\n\n## Log\n")


@pytest.mark.parametrize("lines,value", [
    (("requirements: REQ-FUNC-1111", "requirements:"), "REQ-FUNC-1111"),
    (("requirements:", "requirements: REQ-FUNC-1111"), "REQ-FUNC-1111"),
    (("requirements: REQ-FUNC-1111", "requirements: REQ-FUNC-2222"), "REQ-FUNC-1111"),
])
def test_a_repeated_header_key_keeps_its_written_value(tmp_path, lines, value):
    """An empty template line never hides a written one; the first written one wins,
    as `header_with` rewrites the first line."""
    _agentic, aegis = make_repo(tmp_path)
    data = aegis.parse_journal("# TASK-ab12 - x\n\nstage: frame\n" + "\n".join(lines) + "\n")
    assert data["header"]["requirements"] == value
    assert data["repeated"] == ["requirements"]
    assert aegis.parse_journal("# TASK-ab12 - x\n\nstage: frame\n")["repeated"] == []


def test_pause_points_out_rulings_that_ruling_did_not_write(tmp_path, monkeypatch, capsys):
    """A hand-written note under Rulings is named at the next writer, never refused."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    assert run(aegis, capsys, "ruling", path.stem, "--decision", "keep 30 days",
               "--reason", "user answer", "--source", "user")[0] == 0
    code, out = run(aegis, capsys, "pause", path.stem, "--next", "Accept the scope?")
    assert code == 0 and "Rulings holds" not in out
    text = path.read_text(encoding="utf-8")
    write(path, text.replace("## Rulings\n", "## Rulings\n\n- 2026-10-25 frame: two questions deferred\n", 1))
    code, out = run(aegis, capsys, "pause", path.stem, "--next", "Accept the scope?")
    assert code == 0 and journal(aegis, path)[2]["status"] == "waiting"
    assert "Note: Rulings holds lines `ruling` did not write (invalid ruling record at line" in out
    assert ("); record a settled decision with `ruling`, and keep other notes in the Frame "
            "or the Log") in out


def test_writers_point_out_a_stage_section_left_empty(tmp_path, monkeypatch, capsys):
    """A stage that pauses or completes with its own section empty is told so, never refused."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    code, out = run(aegis, capsys, "pause", path.stem, "--next", "Accept the scope?")
    assert code == 0 and ("Note: the Frame section is still empty; frame writes it in the "
                          "journal as an ordinary edit\n") in out
    write(path, path.read_text(encoding="utf-8").replace("Problem:", "Problem: names keep spaces", 1))
    code, out = run(aegis, capsys, "advance", path.stem)
    assert code == 0 and "section is still empty" not in out
    code, out = run(aegis, capsys, "pause", path.stem, "--next", "Accept the requirements?")
    assert "Note: the Requirement coverage section is still empty; specify writes it" in out
    write(path, path.read_text(encoding="utf-8").replace(
        "## Requirement coverage\n", "## Requirement coverage\n\n| a | b | REQ-FUNC-1111 | c | |\n", 1))
    assert "section is still empty" not in run(aegis, capsys, "advance", path.stem)[1]
    code, out = run(aegis, capsys, "pause", path.stem, "--next", "Accept the design?")
    assert ("Note: the Design section is still empty; design writes it in the journal as an "
            "ordinary edit, or records why design is skipped") in out
    code, out = run(aegis, capsys, "advance", path.stem, "--skipped", "--reason", "one function")
    assert code == 0 and "section is still empty" not in out  # a skip has its reason
    assert "section is still empty" not in run(aegis, capsys, "pause", path.stem, "--next", "x")[1]


def test_pause_names_a_repeated_header_line(tmp_path, monkeypatch, capsys):
    """An inserted second `requirements:` line still counts and is pointed out."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    write(path, path.read_text(encoding="utf-8").replace(
        "type: feature", "type: feature\nrequirements: REQ-FUNC-1111", 1))
    code, out = run(aegis, capsys, "pause", path.stem, "--next", "Accept the scope?")
    assert code == 0 and summary_fields(out)["Requirements"] == "REQ-FUNC-1111"
    assert "Note: the header has more than one requirements: line; keep the one with " \
           "its value and delete the other" in out
    assert "add them" not in out


def test_task_with_an_id_for_a_title_points_to_brief(tmp_path, monkeypatch, capsys):
    """Resuming through `task TASK-<id>` would open a second journal; it is refused."""
    agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    capsys.readouterr()
    assert aegis.main(["task", path.stem]) == 1
    assert f"brief {path.stem.upper()}" in capsys.readouterr().err
    assert len(list((agentic / "tasks").glob("TASK-*.md"))) == 1
    assert aegis.main(["task", f"{path.stem} follow-up"]) == 0  # a real title may mention one


def test_log_keeps_one_stage_prefix(tmp_path, monkeypatch, capsys):
    """Text that already names the current stage is not prefixed twice."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    assert run(aegis, capsys, "log", path.stem, "frame: scope decision recorded")[0] == 0
    assert journal(aegis, path)[1]["log"][-1] == f"{aegis.today()} frame: scope decision recorded"


def test_log_text_may_start_with_a_dash_after_the_separator(tmp_path, monkeypatch, capsys):
    """Adapters pass `--` before free text; argparse then keeps a leading dash."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    assert run(aegis, capsys, "log", path.stem, "--", "-red: exit 1")[0] == 0
    assert journal(aegis, path)[1]["log"][-1].endswith("frame: -red: exit 1")


def test_advance_walks_a_task_to_done_without_a_deliver_stage(tmp_path, monkeypatch, capsys):
    """validate closes to done; commit and push stay with the developer."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    assert run(aegis, capsys, "advance", path.stem)[0] == 0
    for _ in range(2):  # existing requirements cover it: specify and design skipped
        assert run(aegis, capsys, "advance", path.stem, "--skipped",
                   "--reason", "REQ-FUNC-1111 covers it")[0] == 0
    for _ in range(2):
        assert run(aegis, capsys, "advance", path.stem)[0] == 0
    code, out = run(aegis, capsys, "advance", path.stem)
    assert code == 1  # nothing follows done
    _text, data, state = journal(aegis, path)
    assert data["header"]["stage"] == "done"
    assert (state["status"], state["reported"]) == ("done", "validate - completed")
    assert "commit, push and integration belong to the developer" in state["next"]
    assert [line.split(" ", 1)[1].split(";")[0] for line in data["log"][1:]] == [
        "frame: completed", "specify: skipped", "design: skipped",
        "build: completed", "validate: completed"]


def test_advance_to_an_earlier_stage_is_a_return_that_waits(tmp_path, monkeypatch, capsys):
    """A return clears enabled verdicts, keeps the consumed round and waits for the user."""
    agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    enable_review(agentic)
    for target in ("build", "validate"):
        assert run(aegis, capsys, "advance", path.stem, "--to", target)[0] == 0
    assert run(aegis, capsys, "verdict", path.stem, "--spec", "approved",
               "--quality", "changes_required", "--round", "1")[0] == 0
    code, _out = run(aegis, capsys, "advance", path.stem, "--to", "build",
                     "--reason", "quality review found a missing guard")
    assert code == 0
    _text, data, state = journal(aegis, path)
    assert data["header"]["stage"] == "build"
    assert (state["status"], state["reported"]) == ("waiting", "build - paused")
    assert state["next"] == "continue build: quality review found a missing guard"
    assert (state["spec_compliance"], state["implementation_quality"]) == ("", "")
    assert state["review_round"] == "1"
    assert data["log"][-1].endswith(
        "validate: returned to build - quality review found a missing guard")
    # the return is current resume state, never a stale record
    code, out = run(aegis, capsys, "summary", path.stem)
    assert code == 0 and summary_fields(out)["Stage"] == "build - paused"
    assert summary_fields(out)["Needs user"] == "yes"


def test_going_back_from_a_legacy_deliver_journal_is_a_return(tmp_path, capsys):
    """deliver sits after validate, so --to validate waits for the user."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    write_task(agentic, "TASK-ab12", stage="deliver")
    assert run(aegis, capsys, "advance", "ab12", "--to", "validate",
               "--reason", "candidate changed after proof")[0] == 0
    _text, data, state = journal(aegis, agentic / "tasks" / "TASK-ab12.md")
    assert data["header"]["stage"] == "validate"
    assert (state["status"], state["reported"]) == ("waiting", "validate - paused")
    assert data["log"][-1].endswith("deliver: returned to validate - candidate changed after proof")


def test_advance_skipped_marks_the_stage_skipped(tmp_path, monkeypatch, capsys):
    """A skipped design is a recorded skip, not a completion."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    for target in ("specify", "design"):
        assert run(aegis, capsys, "advance", path.stem, "--to", target)[0] == 0
    assert run(aegis, capsys, "advance", path.stem, "--skipped",
               "--reason", "one obvious approach")[0] == 0
    _text, data, state = journal(aegis, path)
    assert data["header"]["stage"] == "build"
    assert state["reported"] == "design - skipped"
    assert data["log"][-1].endswith("design: skipped; next build - one obvious approach")


def test_advance_notes_unapproved_review_at_done_without_refusing(tmp_path, monkeypatch, capsys):
    """Guidance, not a gate: the transition happens and the Log keeps the gap."""
    agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    enable_review(agentic)
    assert run(aegis, capsys, "advance", path.stem, "--to", "validate")[0] == 0
    code, out = run(aegis, capsys, "advance", path.stem)
    assert code == 0
    _text, data, _state = journal(aegis, path)
    assert data["header"]["stage"] == "done"
    assert "review verdicts not both approved" in data["log"][-1]
    assert "Note: review verdicts not both approved; recorded in the Log" in out


def test_advance_walks_adoption_phases(tmp_path, monkeypatch, capsys):
    """Adoption journals use survey, components and close."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys,
                                     "Adopt the service", "--type", "adopt")
    _text, data, state = journal(aegis, path)
    assert data["header"]["stage"] == "survey" and data["log"][0].endswith("survey: journal opened")
    assert state["must_read"].endswith(".agentic/steps/adopt.md")
    for expected in ("components", "close", "done"):
        assert run(aegis, capsys, "advance", path.stem)[0] == 0
        assert journal(aegis, path)[1]["header"]["stage"] == expected


def test_advance_closes_a_legacy_deliver_journal_and_replaces_old_sections(tmp_path, capsys):
    """Old journals migrate on their first State write."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    path = write_task(agentic, "TASK-ab12", stage="deliver")
    write(path, path.read_text(encoding="utf-8") + LEGACY.replace("current: build", "current: deliver"))
    assert run(aegis, capsys, "advance", "ab12")[0] == 0
    text, data, state = journal(aegis, path)
    assert data["header"]["stage"] == "done"
    assert "## Handoff" not in text and "## Stage report" not in text
    assert state["changed"] == "src/app.py" and state["evidence"] == "focused test red"
    assert state["issues"] == "none"  # issues and blockers merge without repeating a value


@pytest.mark.parametrize("argv,message", [
    (("--to", "release"), "unknown stage"),
    (("--to", "frame"), "already at frame"),
])
def test_advance_rejects_unknown_or_unchanged_targets(tmp_path, monkeypatch, capsys, argv, message):
    """Expected errors are one line on stderr and leave the journal untouched."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    before = path.read_bytes()
    capsys.readouterr()
    assert aegis.main(["advance", path.stem, *argv]) == 1
    assert message in capsys.readouterr().err
    assert path.read_bytes() == before


def test_pause_records_a_waiting_state_and_prints_the_summary(tmp_path, monkeypatch, capsys):
    """A checkpoint stop waits for the user on one named question."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    code, out = run(aegis, capsys, "pause", path.stem, "--next", "Accept the framed scope?",
                    "--read", "src/app.py, docs/notes.md", "--evidence", "read src/app.py")
    assert code == 0
    _text, data, state = journal(aegis, path)
    assert data["header"]["stage"] == "frame"
    assert (state["status"], state["reported"]) == ("waiting", "frame - paused")
    assert state["must_read"] == (f".agentic/tasks/{path.stem}.md, .agentic/steps/1_frame.md, "
                                  "src/app.py, docs/notes.md")
    assert (state["spec_compliance"], state["implementation_quality"]) == ("disabled", "disabled")
    fields = summary_fields(out)
    assert fields["Needs user"] == "yes" and fields["Next"] == "Accept the framed scope?"
    assert fields["Evidence"] == "read src/app.py"


def test_pause_blocked_keeps_recorded_outcomes(tmp_path, monkeypatch, capsys):
    """Omitted outcome options keep their recorded values."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    assert run(aegis, capsys, "pause", path.stem, "--next", "first",
               "--changed", "Frame", "--issues", "retention unknown")[0] == 0
    assert run(aegis, capsys, "pause", path.stem, "--blocked",
               "--next", "Which retention period applies?")[0] == 0
    _text, _data, state = journal(aegis, path)
    assert (state["status"], state["reported"]) == ("blocked", "frame - blocked")
    assert (state["changed"], state["issues"]) == ("Frame", "retention unknown")


@pytest.mark.parametrize("value", ["", "   "])
def test_pause_requires_a_next_action(tmp_path, monkeypatch, capsys, value):
    """An empty next action is not a resumable stop."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    capsys.readouterr()
    assert aegis.main(["pause", path.stem, "--next", value]) == 1
    assert "--next" in capsys.readouterr().err


def test_pause_rejects_must_read_paths_outside_the_repository(tmp_path, monkeypatch, capsys):
    """must_read names repository paths only."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    capsys.readouterr()
    assert aegis.main(["pause", path.stem, "--next", "x", "--read", "../secrets.txt"]) == 1
    assert "inside the repository" in capsys.readouterr().err


def test_log_appends_at_the_end_of_the_log_section(tmp_path, monkeypatch, capsys):
    """New lines go after the last entry, before the next section; old lines stay."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    before = journal(aegis, path)[1]["log"]
    assert run(aegis, capsys, "log", path.stem, "red:", "tests/test_export.py", "fails")[0] == 0
    text, data, _state = journal(aegis, path)
    assert data["log"][:-1] == before
    assert data["log"][-1] == f"{aegis.today()} frame: red: tests/test_export.py fails"
    assert text.index("frame: red:") < text.index("## Rulings")


@pytest.mark.parametrize("stage,text,owner", [
    ("frame", "red: tests fail", "build"),
    ("design", "green: tests pass", "build"),
    ("build", "final: check --strict --run exit 0", "validate"),
    ("build", "build: final: check exit 0", "validate"),
    ("build", "validate: knowledge page updated", "validate"),
    ("build", "red: tests fail", None),
    ("validate", "final: check exit 0", None),
    ("validate", "green: rerun after the fix", None),
    ("design", "specify audit: coverage rows match", None),
    ("build", "frame: scope note", None),
    ("validate", "done: nothing", None),
])
def test_log_notes_a_line_recorded_before_its_own_stage(tmp_path, monkeypatch, capsys,
                                                        stage, text, owner):
    """A red, green or final line, or one naming a later stage, reminds to advance first."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    write(path, path.read_text(encoding="utf-8").replace("stage: frame", f"stage: {stage}", 1))
    code, out = run(aegis, capsys, "log", path.stem, text)
    assert code == 0 and journal(aegis, path)[1]["log"][-1].endswith(text)  # always logged
    if owner is None:
        assert "Note:" not in out
    else:
        assert (f"Note: this line records {owner} work, but the journal is still at {stage}; "
                f"once {stage} is accepted, run `python .agentic/aegis.py advance {path.stem}` "
                f"before more {owner} work") in out


def test_rulings_number_append_and_supersede(tmp_path, monkeypatch, capsys):
    """Rulings are append-only; a replacement names what it supersedes."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    assert run(aegis, capsys, "ruling", path.stem, "--decision", "keep 30 days",
               "--reason", "user answer", "--source", "user")[0] == 0
    code, out = run(aegis, capsys, "ruling", path.stem, "--decision", "keep 90 days",
                    "--reason", "audit need", "--source", "requirement",
                    "--supersedes", "ruling-001")
    assert code == 0 and "RULING-002 recorded" in out
    assert "marks RULING-001 superseded, so leave that line as written" in out
    records, errors = aegis.parse_rulings(path.read_text(encoding="utf-8"))
    assert not errors
    assert [(r["id"], r["supersedes"]) for r in records] == [
        ("RULING-001", "none"), ("RULING-002", "RULING-001")]
    assert [r["id"] for r in aegis.active_rulings(records)] == ["RULING-002"]


@pytest.mark.parametrize("argv,message", [
    (("--decision", "a | b", "--reason", "r", "--source", "user"), "without '|'"),
    (("--decision", "a", "--reason", "r", "--source", "user", "--supersedes", "RULING-009"),
     "unknown ruling"),
])
def test_ruling_rejects_ambiguous_records(tmp_path, monkeypatch, capsys, argv, message):
    """A ruling that cannot parse back, or supersedes nothing, is refused."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    capsys.readouterr()
    assert aegis.main(["ruling", path.stem, *argv]) == 1
    assert message in capsys.readouterr().err


def test_verdict_refuses_while_review_is_disabled(tmp_path, monkeypatch, capsys):
    """Disabled review keeps both verdicts disabled."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    capsys.readouterr()
    assert aegis.main(["verdict", path.stem, "--spec", "approved"]) == 1
    assert "disabled" in capsys.readouterr().err


def test_verdict_records_both_verdicts_within_the_round_bound(tmp_path, monkeypatch, capsys):
    """Verdicts bind to the stage under review and the configured round bound."""
    agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    enable_review(agentic, cycles=1)
    assert run(aegis, capsys, "advance", path.stem, "--to", "validate")[0] == 0
    capsys.readouterr()
    assert aegis.main(["verdict", path.stem, "--spec", "approved", "--round", "3"]) == 1
    assert "1 through 2" in capsys.readouterr().err
    code, out = run(aegis, capsys, "verdict", path.stem, "--spec", "approved",
                    "--quality", "approved", "--round", "2")
    assert code == 0
    _text, _data, state = journal(aegis, path)
    assert (state["status"], state["reported"]) == ("working", "validate - in_progress")
    assert (state["spec_compliance"], state["implementation_quality"],
            state["review_round"]) == ("approved", "approved", "2")
    assert summary_fields(out)["Specification compliance"] == "approved"


def test_status_and_brief_show_the_recorded_state(tmp_path, monkeypatch, capsys):
    """The State written by the CLI is what the next session reads first."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    assert run(aegis, capsys, "pause", path.stem, "--next", "Accept the framed scope?")[0] == 0
    _code, status = run(aegis, capsys, "status", path.stem)
    assert "state: waiting (reported frame - paused)\n  next: Accept the framed scope?" in status
    _code, brief = run(aegis, capsys, "brief", path.stem)
    assert "State: waiting; reported=frame - paused; next=Accept the framed scope?" in brief
    assert "needs_user=yes" in brief
    assert "Read next: .agentic/steps/1_frame.md, then the State must_read paths" in brief


def test_brief_names_the_advance_that_resumes_a_waiting_checkpoint(tmp_path, monkeypatch, capsys):
    """A later session that continues past a checkpoint advances before the next stage's work."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    assert run(aegis, capsys, "pause", path.stem, "--next", "Accept the framed scope?")[0] == 0
    brief = run(aegis, capsys, "brief", path.stem)[1]
    assert (f"then the State must_read paths. The State waits on the user: when they continue "
            f"to specify, run `python .agentic/aegis.py advance {path.stem}` first and read "
            ".agentic/steps/2_specify.md\n") in brief
    assert run(aegis, capsys, "advance", path.stem, "--to", "validate")[0] == 0
    assert "waits on the user" not in run(aegis, capsys, "brief", path.stem)[1]  # ready
    assert run(aegis, capsys, "pause", path.stem, "--next", "Close the task?")[0] == 0
    brief = run(aegis, capsys, "brief", path.stem)[1]
    assert (f"when they approve closing the task, run `python .agentic/aegis.py advance "
            f"{path.stem}`\n") in brief
    assert run(aegis, capsys, "pause", path.stem, "--blocked", "--next", "Which rule?")[0] == 0
    assert "waits on the user" not in run(aegis, capsys, "brief", path.stem)[1]  # a blocker


def test_brief_names_no_advance_between_adoption_components(tmp_path, monkeypatch, capsys):
    """Adoption pauses after each component inside one stage; continuing means the next
    component, so brief must not suggest moving on to close."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys,
                                     "Adopt the service", "--type", "adopt")
    assert run(aegis, capsys, "pause", path.stem, "--next", "Review the component list?")[0] == 0
    assert "when they continue to components" in run(aegis, capsys, "brief", path.stem)[1]
    assert run(aegis, capsys, "advance", path.stem)[0] == 0
    assert run(aegis, capsys, "pause", path.stem, "--next", "Continue with the cli component?")[0] == 0
    brief = run(aegis, capsys, "brief", path.stem)[1]
    assert "Stage: components" in brief and "waits on the user" not in brief


def test_check_warns_on_a_stale_state_and_on_legacy_sections_beside_it(tmp_path, monkeypatch,
                                                                       capsys):
    """check names a State that no longer matches the header, and ignored old sections."""
    _agentic, aegis, path = new_task(tmp_path, monkeypatch, capsys)
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    text = path.read_text(encoding="utf-8").replace("stage: frame", "stage: build", 1)
    write(path, text + LEGACY)
    report = json.loads(run_check(aegis, capsys, "--json"))  # messages untruncated
    messages = [finding["message"] for finding in report["findings"]
                if finding["check"] == "journal-header" and path.stem in finding["path"]]
    assert any(message.startswith("stale state: current stage changed") for message in messages)
    assert "legacy Handoff or Stage report beside State is ignored; remove it" in messages


def test_section_writers_ignore_headings_inside_fences(tmp_path):
    """A fenced example heading is content, not the end of a section."""
    _agentic, aegis = make_repo(tmp_path)
    text = ("# TASK-ab12 - x\n\nstage: build\n\n## Log\n\n- 2026-01-01 build: one\n"
            "```text\n## State\nstatus: done\n```\n\n## Rulings\n")
    logged = aegis.log_with(text, "build: two")
    assert logged.index("build: two") < logged.index("## Rulings")
    assert "```text\n## State\nstatus: done\n```" in logged
    assert aegis.parse_state(logged) == {}
