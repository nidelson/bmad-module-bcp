"""Shared fixtures for what is left of this module.

The scoring engine, the ruler, the baseline and every test that pinned them
moved to bmad-module-pulse (issue nidelson/bmad-module-pulse#84). What remains
here is a migration path and the invariants that keep it honest: that this
module ships exactly one skill, that the skill does not collide with a name
PULSE owns, and that the deprecation is stated where a reader will find it.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
SKILLS = REPO_ROOT / "skills"

# The single skill this module still ships.
#
# Every other `bmad-bcp-*` name now belongs to PULSE. Skill names are one global
# namespace — `skill-manifest.csv` keys one row per name with one owning module,
# and installed skills land in `.claude/skills/<name>/`. Two modules shipping a
# name means whoever installs last wins the directory, so a pointer left behind
# here would overwrite PULSE's working skill with a notice saying it moved.
EXPECTED_SKILLS = ("bmad-bcp-setup",)

# Names PULSE owns. Nothing in this repo may ship a skill directory called any
# of these, at any point, for any reason.
PULSE_OWNED_SKILLS = (
    "bmad-bcp-rule-card",
    "bmad-bcp-score",
    "bmad-bcp-score-batch",
    "bmad-bcp-rescore",
    "bmad-bcp-recalibrate",
    "bmad-bcp-backfill-baseline",
)

PULSE_REPO = "bmad-module-pulse"


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a module script the same way the SKILL.md chain would."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
    )
