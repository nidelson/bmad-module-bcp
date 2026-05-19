"""The bmad-create-story customize hook is shipped verbatim.

`inject_customize.py` does a plain `shutil.copyfile` — what the setup skill
packages is exactly what lands in the consumer's `_bmad/custom/`. A golden
snapshot under `tests/fixtures/golden/` pins that surface so any edit to
the injected persistent_fact (which steers the BMAD agent) is a reviewed,
deliberate change, never an accident. CI also `diff`s these directly.
"""
from __future__ import annotations

import hashlib
import sys

import pytest

from .conftest import REPO_ROOT, SKILLS, run_script

TEMPLATE = (SKILLS / "bmad-bcp-setup/assets/customize-templates"
            / "bmad-create-story.toml")
GOLDEN = REPO_ROOT / "tests/fixtures/golden/customize-bmad-create-story.toml"
INJECT = SKILLS / "bmad-bcp-setup/scripts/inject_customize.py"


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_template_matches_golden_snapshot():
    assert _sha(TEMPLATE) == _sha(GOLDEN), (
        "customize template drifted from its golden snapshot. If the "
        "change is intentional, refresh "
        "tests/fixtures/golden/customize-bmad-create-story.toml in the "
        "same PR so the hook surface stays reviewed."
    )


def test_inject_emits_byte_identical_to_golden(tmp_path):
    proc = run_script(INJECT, "--project-root", str(tmp_path),
                      "--skill", "bmad-create-story")
    assert proc.returncode == 0, proc.stderr
    emitted = tmp_path / "_bmad/custom/bmad-create-story.toml"
    assert emitted.exists()
    assert _sha(emitted) == _sha(GOLDEN), (
        "inject_customize output != golden — the consumer would receive a "
        "different hook than the one under test"
    )


def test_inject_is_idempotent_under_force(tmp_path):
    a = run_script(INJECT, "--project-root", str(tmp_path),
                   "--skill", "bmad-create-story")
    assert a.returncode == 0, a.stderr
    emitted = tmp_path / "_bmad/custom/bmad-create-story.toml"
    first = _sha(emitted)
    b = run_script(INJECT, "--project-root", str(tmp_path),
                   "--skill", "bmad-create-story", "--force")
    assert b.returncode == 0, b.stderr
    assert _sha(emitted) == first, "re-run under --force not byte-stable"


def test_inject_aborts_on_conflict_without_force(tmp_path):
    a = run_script(INJECT, "--project-root", str(tmp_path),
                   "--skill", "bmad-create-story")
    assert a.returncode == 0, a.stderr
    b = run_script(INJECT, "--project-root", str(tmp_path),
                   "--skill", "bmad-create-story")
    assert b.returncode == 3, (
        "second run without --force must abort (exit 3), not clobber a "
        "user-edited hook"
    )
