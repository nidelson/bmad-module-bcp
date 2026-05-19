"""Cross-file consistency invariants for the installable distribution.

v0.1.0 ships the same skill set described in four places that release-please
and the BMAD installer read independently:

  - skills/bmad-bcp-setup/assets/module.yaml  (canonical, installer copies it)
  - module.yaml                               (repo root, discoverability)
  - .claude-plugin/marketplace.json           (plugin marketplace)
  - skills/bmad-bcp-setup/assets/module-help.csv

If any drifts the module installs inconsistently. These tests pin them
together so a single-file edit can never ship silently.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from .conftest import EXPECTED_SKILLS, REPO_ROOT, SKILLS

SETUP_MODULE_YAML = SKILLS / "bmad-bcp-setup/assets/module.yaml"
ROOT_MODULE_YAML = REPO_ROOT / "module.yaml"
MARKETPLACE = REPO_ROOT / ".claude-plugin/marketplace.json"
MODULE_HELP = SKILLS / "bmad-bcp-setup/assets/module-help.csv"
RELEASE_CONFIG = REPO_ROOT / "release-please-config.json"
RELEASE_MANIFEST = REPO_ROOT / ".release-please-manifest.json"


def test_root_module_yaml_is_byte_identical_to_setup_asset():
    """The root module.yaml is an intentional copy (not a symlink — the
    installer copies the setup asset into the consumer, the root file is
    only for scrapers/readers). release-please bumps the version in both
    via extra-files; every other byte must stay identical so the two
    never describe different modules."""
    assert ROOT_MODULE_YAML.read_bytes() == SETUP_MODULE_YAML.read_bytes(), (
        "module.yaml (root) diverged from skills/bmad-bcp-setup/assets/"
        "module.yaml — edit the setup asset and copy it to the root, or "
        "the module installs differently than it advertises."
    )


def test_module_code_is_bcp():
    data = yaml.safe_load(SETUP_MODULE_YAML.read_text(encoding="utf-8"))
    assert data["code"] == "bcp"


def test_module_version_aligned_across_shipped_artifacts():
    """The three files that *describe the shipped module* must agree —
    release-please bumps all of them via extra-files, so a drift here
    means the module advertises inconsistent versions."""
    setup_v = yaml.safe_load(SETUP_MODULE_YAML.read_text())["module_version"]
    root_v = yaml.safe_load(ROOT_MODULE_YAML.read_text())["module_version"]
    market = json.loads(MARKETPLACE.read_text())["plugins"][0]["version"]
    assert setup_v == root_v == market, (
        f"version drift: setup={setup_v} root={root_v} marketplace={market}"
    )


def _semver(v: str) -> tuple[int, int, int]:
    parts = v.split("-")[0].split(".")
    return tuple(int(p) for p in (parts + ["0", "0", "0"])[:3])


def test_release_manifest_is_a_valid_cursor_not_ahead_of_module():
    """`.release-please-manifest.json` is release-please's *last released*
    cursor, not the module version. It is intentionally behind the
    module's version until the first release PR merges (bootstrap: manifest
    0.0.0 → first release cuts v0.1.0). It must be valid semver and never
    ahead of what the module advertises."""
    manifest = json.loads(RELEASE_MANIFEST.read_text())["."]
    module_v = yaml.safe_load(SETUP_MODULE_YAML.read_text())["module_version"]
    assert _semver(manifest) <= _semver(module_v), (
        f"manifest cursor {manifest} is ahead of module version "
        f"{module_v} — release-please would never cut the gap release"
    )


def test_release_please_extra_files_exist():
    """Every path release-please bumps must exist or the release job
    fails mid-run with a half-applied version bump."""
    cfg = json.loads(RELEASE_CONFIG.read_text())
    extra = cfg["packages"]["."]["extra-files"]
    for entry in extra:
        target = REPO_ROOT / entry["path"]
        assert target.exists(), f"release-please extra-file missing: {entry['path']}"


def test_marketplace_lists_exactly_the_expected_skills():
    plugins = json.loads(MARKETPLACE.read_text())["plugins"]
    assert len(plugins) == 1
    listed = {Path(s).name for s in plugins[0]["skills"]}
    assert listed == set(EXPECTED_SKILLS), (
        f"marketplace skills {sorted(listed)} != expected "
        f"{sorted(EXPECTED_SKILLS)}"
    )


def test_skills_directory_matches_expected_set():
    on_disk = {p.name for p in SKILLS.iterdir()
               if p.is_dir() and p.name.startswith("bmad-bcp-")}
    assert on_disk == set(EXPECTED_SKILLS), (
        f"skills/ on disk {sorted(on_disk)} != expected "
        f"{sorted(EXPECTED_SKILLS)}"
    )


def test_module_help_csv_rows_match_skills():
    with MODULE_HELP.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    csv_skills = {r["skill"] for r in rows}
    assert csv_skills == set(EXPECTED_SKILLS), (
        f"module-help.csv skills {sorted(csv_skills)} != expected "
        f"{sorted(EXPECTED_SKILLS)}"
    )
    # menu-code must be unique — the agent menu indexes by it.
    codes = [r["menu-code"] for r in rows]
    assert len(codes) == len(set(codes)), f"duplicate menu-code in {codes}"


def test_path_results_do_not_double_prefix_project_root():
    """`{output_folder}` already resolves under `{project-root}`; a
    `result` template must not prefix `{project-root}/` on top of it or
    the installer writes `{project-root}/{project-root}/...`."""
    data = yaml.safe_load(SETUP_MODULE_YAML.read_text())
    for key in ("bcp_data_folder", "bcp_baseline_path"):
        entry = data.get(key)
        assert entry is not None, f"missing {key} in module.yaml"
        if str(entry.get("default", "")).startswith("{output_folder}"):
            assert "{project-root}" not in str(entry.get("result", "")), (
                f"{key}: result double-prefixes {{project-root}}"
            )
