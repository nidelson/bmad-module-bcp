"""Workflow `on_complete` extension point — coverage across all workflow skills.

Pins the post-persistence hook surface introduced by issue #28:

  - every workflow skill has a `customize.toml` with a `[workflow]` block
    exposing `activation_steps_prepend`, `activation_steps_append`,
    `persistent_facts`, and `on_complete`;
  - the default `on_complete` is the empty string (opt-in only — zero
    behavior unless explicitly overridden);
  - team-level `_bmad/custom/<skill>.toml` overrides the default;
  - user-level `_bmad/custom/<skill>.user.toml` overrides the team value;
  - every `SKILL.md` is slim and points to `workflow.md`;
  - every `workflow.md` documents the `## On Completion` contract.

The persona agent (`bmad-bcp-agent-bruno`) is intentionally excluded — it
exposes an `[agent]` customization block, not `[workflow]`, and the
conversational persona has no "completion" semantics.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from .conftest import EXPECTED_SKILLS, REPO_ROOT, SKILLS

RESOLVER = REPO_ROOT / "_bmad/scripts/resolve_customization.py"

# Skills that participate in the `workflow.on_complete` extension point.
# `bmad-bcp-agent-bruno` is a persona (no workflow completion) — excluded.
WORKFLOW_SKILLS = tuple(s for s in EXPECTED_SKILLS if s != "bmad-bcp-agent-bruno")


def _resolve(skill_dir: Path, *keys: str) -> dict:
    args = [sys.executable, str(RESOLVER), "--skill", str(skill_dir)]
    for key in keys:
        args.extend(["--key", key])
    proc = subprocess.run(args, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _stage_skill(tmp_path: Path, name: str) -> Path:
    """Copy a real skill into a fake project tree so override files can land
    next to it without polluting the repo. find_project_root walks up from
    the skill dir until it sees `_bmad/` — so the fake `_bmad/custom/` we
    create under tmp_path/fake-project is what the resolver will read.
    """
    project = tmp_path / "fake-project"
    dst = project / "skills" / name
    dst.parent.mkdir(parents=True)
    shutil.copytree(SKILLS / name, dst)
    (project / "_bmad" / "custom").mkdir(parents=True)
    return dst


@pytest.mark.parametrize("name", WORKFLOW_SKILLS)
def test_skill_ships_customize_toml(name: str) -> None:
    assert (SKILLS / name / "customize.toml").exists(), (
        f"{name} is a workflow skill but ships no customize.toml — the "
        f"workflow customization surface (activation hooks + on_complete) "
        f"requires this file."
    )


@pytest.mark.parametrize("name", WORKFLOW_SKILLS)
def test_default_workflow_block_has_all_four_knobs(name: str) -> None:
    """All four customization knobs are present at the [workflow] table —
    arrays default to empty, on_complete defaults to the empty string.
    Locks the schema so a future edit can't silently drop a knob."""
    out = _resolve(SKILLS / name, "workflow")
    workflow = out["workflow"]
    assert workflow["activation_steps_prepend"] == []
    assert workflow["activation_steps_append"] == []
    assert workflow["persistent_facts"] == []
    assert workflow["on_complete"] == ""


@pytest.mark.parametrize("name", WORKFLOW_SKILLS)
def test_default_on_complete_is_empty_no_op(name: str) -> None:
    """Default `on_complete = ""` is the opt-in contract — installing the
    module never silently triggers downstream actions. The user must
    explicitly override in `_bmad/custom/<skill>.toml` to enable a hook."""
    out = _resolve(SKILLS / name, "workflow.on_complete")
    assert out == {"workflow.on_complete": ""}


@pytest.mark.parametrize("name", WORKFLOW_SKILLS)
def test_team_override_replaces_default(tmp_path: Path, name: str) -> None:
    """Team-level `_bmad/custom/<skill>.toml` override wins over the skill
    default (scalar — override-wins per BMad merge rules)."""
    skill = _stage_skill(tmp_path, name)
    project_root = skill.parent.parent
    (project_root / "_bmad" / "custom" / f"{name}.toml").write_text(
        '[workflow]\non_complete = "team-level hook fired"\n',
        encoding="utf-8",
    )
    out = _resolve(skill, "workflow.on_complete")
    assert out == {"workflow.on_complete": "team-level hook fired"}


@pytest.mark.parametrize("name", WORKFLOW_SKILLS)
def test_user_override_beats_team_override(tmp_path: Path, name: str) -> None:
    """User-level `.user.toml` is the highest priority — beats team and
    skill defaults. Lets an individual override a team-wide hook without
    editing the committed file."""
    skill = _stage_skill(tmp_path, name)
    project_root = skill.parent.parent
    custom = project_root / "_bmad" / "custom"
    (custom / f"{name}.toml").write_text(
        '[workflow]\non_complete = "team"\n', encoding="utf-8",
    )
    (custom / f"{name}.user.toml").write_text(
        '[workflow]\non_complete = "user"\n', encoding="utf-8",
    )
    out = _resolve(skill, "workflow.on_complete")
    assert out == {"workflow.on_complete": "user"}


@pytest.mark.parametrize("name", WORKFLOW_SKILLS)
def test_array_knobs_append_under_override(tmp_path: Path, name: str) -> None:
    """Arrays append under override (per BMad merge rules) — a team override
    that adds to `activation_steps_prepend` augments the default rather
    than replacing it."""
    skill = _stage_skill(tmp_path, name)
    project_root = skill.parent.parent
    (project_root / "_bmad" / "custom" / f"{name}.toml").write_text(
        '[workflow]\n'
        'activation_steps_prepend = ["check compliance flag X"]\n'
        'persistent_facts = ["squad uses sprint 2-weeks"]\n',
        encoding="utf-8",
    )
    out = _resolve(skill, "workflow")
    workflow = out["workflow"]
    assert workflow["activation_steps_prepend"] == ["check compliance flag X"]
    assert workflow["persistent_facts"] == ["squad uses sprint 2-weeks"]
    # on_complete untouched by the override → still default empty
    assert workflow["on_complete"] == ""


@pytest.mark.parametrize("name", WORKFLOW_SKILLS)
def test_skill_md_is_slim_pointer_to_workflow(name: str) -> None:
    """SKILL.md is just frontmatter + a one-line pointer to workflow.md —
    the body lives in workflow.md so customize.toml's [workflow] block
    has a well-defined backing document."""
    skill_md = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    assert "Follow the instructions in [workflow.md](workflow.md)." in skill_md, (
        f"{name}/SKILL.md does not point to workflow.md — split required."
    )
    # After the closing `---` of the frontmatter, there is exactly one
    # non-blank line (the pointer).
    body = skill_md.split("---\n", 2)[-1]
    non_blank = [line for line in body.splitlines() if line.strip()]
    assert len(non_blank) == 1, (
        f"{name}/SKILL.md should be a thin pointer; found "
        f"{len(non_blank)} non-blank lines after the frontmatter."
    )


@pytest.mark.parametrize("name", WORKFLOW_SKILLS)
def test_workflow_md_documents_on_completion_contract(name: str) -> None:
    """workflow.md must document the hook contract — section + the four
    invariants (after-persistence, no-mutation, warn-not-rollback,
    dry-run-skipped or its skill-specific equivalent)."""
    workflow_md = (SKILLS / name / "workflow.md").read_text(encoding="utf-8")
    assert "## On Completion" in workflow_md, (
        f"{name}/workflow.md missing `## On Completion` section."
    )
    assert "workflow.on_complete" in workflow_md, (
        f"{name}/workflow.md must reference `workflow.on_complete` (resolved key)."
    )
    assert "resolve_customization.py" in workflow_md or "{skill-root}" in workflow_md, (
        f"{name}/workflow.md must explain how the hook is resolved."
    )
