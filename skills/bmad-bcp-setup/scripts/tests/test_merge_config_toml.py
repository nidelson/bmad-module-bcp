#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "tomlkit", "pytest"]
# ///
"""Unit tests for the toml-first write path of merge-config.py.

Issue #36: BCP is toml-first. The setup write-path (merge-config.py) must
write the module answers into ``_bmad/custom/config.toml`` under
``[modules.bcp]`` — the layer ``resolve_config.py`` reads with higher
priority than the installer defaults in ``config.toml`` — and must NOT write
the legacy ``bcp:`` section into ``config.yaml`` anymore (it strips a stale
one on re-run, which is the migration path). Core keys stay in ``config.yaml``.

Matrix required by the acceptance criteria: fresh toml write, yaml→toml
migration (strip), both (preserve human custom content), none (core-only).

Run: uv run --group test pytest skills/bmad-bcp-setup/scripts/tests/test_merge_config_toml.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parent.parent
SKILL = SCRIPTS.parent
SCRIPT = SCRIPTS / "merge-config.py"
MODULE_YAML = SKILL / "assets" / "module.yaml"


def run(project_root: Path, answers: dict) -> subprocess.CompletedProcess[str]:
    answers_file = project_root / "answers.json"
    answers_file.write_text(json.dumps(answers), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--config-path",
            str(project_root / "_bmad/config.yaml"),
            "--user-config-path",
            str(project_root / "_bmad/config.user.yaml"),
            "--module-yaml",
            str(MODULE_YAML),
            "--answers",
            str(answers_file),
        ],
        capture_output=True,
        text=True,
    )


def read_custom_bcp(project_root: Path) -> dict:
    path = project_root / "_bmad/custom/config.toml"
    with path.open("rb") as f:
        data = tomllib.load(f)
    return data.get("modules", {}).get("bcp", {})


def read_yaml(project_root: Path) -> dict:
    path = project_root / "_bmad/config.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# The custom values that must survive the cutover (installs with team overrides).
CUSTOM_MODULE_ANSWERS = {
    "module": {
        "bcp_confidence_threshold": "0.9",
        "bcp_reference_h_per_bcp": "5.5",
        "bcp_baseline_seed": "4.13",
        "bcp_non_interactive_default": "no",
        "bcp_baseline_path": "{output_folder}/impl/bcp-baseline.yaml",
    }
}


# --- fresh: writes toml, never a bcp: section in config.yaml ---

def test_fresh_writes_bcp_to_custom_toml(tmp_path: Path):
    result = run(tmp_path, CUSTOM_MODULE_ANSWERS)
    assert result.returncode == 0, result.stderr

    pinned = read_custom_bcp(tmp_path)
    assert pinned["bcp_confidence_threshold"] == "0.9"
    assert pinned["bcp_reference_h_per_bcp"] == "5.5"
    assert pinned["bcp_baseline_path"] == "{output_folder}/impl/bcp-baseline.yaml"


def test_fresh_never_writes_bcp_section_to_yaml(tmp_path: Path):
    assert run(tmp_path, CUSTOM_MODULE_ANSWERS).returncode == 0
    assert "bcp" not in read_yaml(tmp_path)


def test_metadata_not_pinned_only_bcp_values(tmp_path: Path):
    assert run(tmp_path, CUSTOM_MODULE_ANSWERS).returncode == 0
    pinned = read_custom_bcp(tmp_path)
    for meta in ("name", "description", "version", "default_selected"):
        assert meta not in pinned
    assert all(k.startswith("bcp_") for k in pinned)


def test_values_are_strings(tmp_path: Path):
    assert run(tmp_path, CUSTOM_MODULE_ANSWERS).returncode == 0
    pinned = read_custom_bcp(tmp_path)
    assert pinned["bcp_confidence_threshold"] == "0.9"
    assert pinned["bcp_non_interactive_default"] == "no"
    assert all(isinstance(v, str) for v in pinned.values())


# --- migration: an existing legacy bcp: in config.yaml is stripped ---

def test_migration_strips_legacy_yaml_bcp_section(tmp_path: Path):
    (tmp_path / "_bmad").mkdir(parents=True)
    (tmp_path / "_bmad/config.yaml").write_text(
        "output_folder: '{project-root}/_bmad-output'\n"
        "bcp:\n"
        "  name: BCP\n"
        "  bcp_confidence_threshold: '0.6'\n"
        "  bcp_reference_h_per_bcp: '4.13'\n",
        encoding="utf-8",
    )
    assert run(tmp_path, CUSTOM_MODULE_ANSWERS).returncode == 0

    cfg = read_yaml(tmp_path)
    assert "bcp" not in cfg  # legacy section removed
    assert cfg.get("output_folder") == "{project-root}/_bmad-output"  # core preserved
    assert read_custom_bcp(tmp_path)["bcp_confidence_threshold"] == "0.9"


# --- both: existing custom/config.toml content + comments preserved ---

def test_preserves_existing_custom_toml_content(tmp_path: Path):
    custom = tmp_path / "_bmad/custom"
    custom.mkdir(parents=True)
    (custom / "config.toml").write_text(
        "# human-owned team config\n"
        "[core]\n"
        'user_name = "Ada"\n\n'
        "[modules.bcp]\n"
        'bcp_estimation_basis = "custom-basis"\n',
        encoding="utf-8",
    )
    assert run(tmp_path, CUSTOM_MODULE_ANSWERS).returncode == 0

    text = (custom / "config.toml").read_text(encoding="utf-8")
    assert "# human-owned team config" in text  # comment preserved

    with (custom / "config.toml").open("rb") as f:
        data = tomllib.load(f)
    assert data["core"]["user_name"] == "Ada"  # other section preserved
    # human-only key under [modules.bcp] preserved, answered keys upserted
    assert data["modules"]["bcp"]["bcp_estimation_basis"] == "custom-basis"
    assert data["modules"]["bcp"]["bcp_confidence_threshold"] == "0.9"


def test_rerun_overwrites_managed_keys(tmp_path: Path):
    assert run(tmp_path, CUSTOM_MODULE_ANSWERS).returncode == 0
    changed = {"module": dict(CUSTOM_MODULE_ANSWERS["module"], bcp_confidence_threshold="0.6")}
    assert run(tmp_path, changed).returncode == 0
    assert read_custom_bcp(tmp_path)["bcp_confidence_threshold"] == "0.6"


# --- none: core-only answers still land in config.yaml, no toml module noise ---

def test_core_keys_still_written_to_yaml(tmp_path: Path):
    answers = {"core": {"output_folder": "custom-out"}, "module": CUSTOM_MODULE_ANSWERS["module"]}
    assert run(tmp_path, answers).returncode == 0
    cfg = read_yaml(tmp_path)
    assert cfg["output_folder"] == "custom-out"
    assert "bcp" not in cfg
