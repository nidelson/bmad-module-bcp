"""The deprecation, as executable invariants.

This module is archived, not deleted: its issues and pull requests are the
record of how the ruler was frozen and the baseline calibrated. Archived
repositories stay cloneable, which means this module stays *installable* — so
the properties that make it safe to install alongside PULSE have to be enforced
rather than assumed.
"""
from __future__ import annotations

import json

import yaml

from .conftest import (
    EXPECTED_SKILLS,
    PULSE_OWNED_SKILLS,
    PULSE_REPO,
    REPO_ROOT,
    SKILLS,
)

MARKETPLACE = REPO_ROOT / ".claude-plugin/marketplace.json"
MODULE_YAML = REPO_ROOT / "module.yaml"
SETUP_WORKFLOW = SKILLS / "bmad-bcp-setup/workflow.md"


# ── the collision guard ──────────────────────────────────────────────────────


def test_ships_no_skill_name_that_pulse_owns():
    """The reason the skills were removed rather than turned into pointers.

    Skill names are one global namespace: `skill-manifest.csv` keys one row per
    name with one owning module, and installed skills land in
    `.claude/skills/<name>/`. A directory here named `bmad-bcp-score` would
    overwrite PULSE's working copy whenever this module is installed after it —
    the redirect causing the outage it exists to prevent.
    """
    on_disk = {p.name for p in SKILLS.iterdir() if p.is_dir()}
    collisions = on_disk & set(PULSE_OWNED_SKILLS)
    assert not collisions, (
        f"these skill names belong to {PULSE_REPO} and must not ship here: "
        f"{sorted(collisions)}"
    )


def test_marketplace_declares_no_colliding_skill():
    """Same guard at the manifest layer.

    A directory can be absent while the marketplace still lists it, which
    installs as a broken entry rather than a safe one.
    """
    listed = {
        entry.rsplit("/", 1)[-1]
        for entry in json.loads(MARKETPLACE.read_text())["plugins"][0]["skills"]
    }
    assert listed == set(EXPECTED_SKILLS)
    assert not (listed & set(PULSE_OWNED_SKILLS))


# ── the announcement ─────────────────────────────────────────────────────────


def test_module_metadata_announces_the_deprecation():
    """A user meets this module through the installer's module list, not the
    README. If the description does not say it is deprecated, the picker is
    where the deprecation fails to land."""
    data = yaml.safe_load(MODULE_YAML.read_text(encoding="utf-8"))
    assert "DEPRECATED" in data["name"]
    assert "DEPRECATED" in data["description"]
    assert PULSE_REPO in data["description"]


def test_readmes_lead_with_the_deprecation():
    """Both READMEs, in the first screenful. A notice below the install command
    is read after the install.

    The marker is per file because the two are not translations of one language:
    `README.md` is the Portuguese manual and `README.en.md` the English one.
    Asserting one word across both would either fail on a correct document or
    force a document to carry a word in the wrong language to satisfy a test.
    """
    markers = {"README.md": "DESCONTINUADO", "README.en.md": "DEPRECATED"}
    for name, marker in markers.items():
        head = (REPO_ROOT / name).read_text(encoding="utf-8")[:1400]
        assert marker in head.upper(), f"{name} must open with the deprecation"
        assert PULSE_REPO in head, f"{name} must name where scoring went"


def test_migration_path_names_the_config_table_that_disappears():
    """The one step a reader cannot infer.

    Uninstalling this module deletes `[modules.bcp]`, and PULSE's fallback to it
    lasts exactly as long as this module does. A migration guide that omits
    moving those keys leaves the project resolving built-in defaults while
    reporting success.
    """
    text = SETUP_WORKFLOW.read_text(encoding="utf-8")
    assert "[modules.bcp]" in text
    assert "[modules.pulse]" in text
    assert "bcp_reference_h_per_bcp" in text


def test_migration_path_protects_the_baseline():
    """`bcp-baseline.yaml` holds every sample the team accumulated. The guide
    must say not to overwrite it, because the seeding script will if forced."""
    text = SETUP_WORKFLOW.read_text(encoding="utf-8")
    assert "bcp-baseline.yaml" in text
    assert "--force" in text
