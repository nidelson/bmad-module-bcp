#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml", "pytest"]
# ///
"""Unit tests for BCP setup scripts with non-trivial logic:
seed_baseline.py (idempotency, content) and detect_bmad_capability.py
(manifest version gate). The other scripts are ported verbatim/structural
from the PULSE module's already-tested generic equivalents.

Run: uv run --with pytest pytest skills/bmad-bcp-setup/scripts/tests/
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parent.parent
SEED = SCRIPTS / "seed_baseline.py"
DETECT = SCRIPTS / "detect_bmad_capability.py"


def run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True,
    )


# ---- seed_baseline.py ----

def test_seed_creates_baseline(tmp_path: Path):
    dest = tmp_path / "bcp-baseline.yaml"
    r = run(SEED, "--baseline-path", str(dest))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["action"] == "created"
    data = yaml.safe_load(dest.read_text())
    assert data["schema_version"] == "1.0"
    assert data["config_snapshot"] == {
        "seed": 4.13, "min_samples": 5, "rolling_window": 10,
    }
    assert data["categories"] == {}


def test_seed_is_idempotent(tmp_path: Path):
    dest = tmp_path / "bcp-baseline.yaml"
    run(SEED, "--baseline-path", str(dest))
    before = dest.read_text()
    r = run(SEED, "--baseline-path", str(dest), "--seed", "9.99")
    assert r.returncode == 0
    assert json.loads(r.stdout)["action"] == "skipped_exists"
    assert dest.read_text() == before  # untouched


def test_seed_force_overwrites(tmp_path: Path):
    dest = tmp_path / "bcp-baseline.yaml"
    run(SEED, "--baseline-path", str(dest))
    r = run(SEED, "--baseline-path", str(dest), "--seed", "5.0", "--force")
    assert r.returncode == 0
    data = yaml.safe_load(dest.read_text())
    assert data["config_snapshot"]["seed"] == 5.0


def test_seed_custom_params(tmp_path: Path):
    dest = tmp_path / "nested" / "bcp-baseline.yaml"
    r = run(SEED, "--baseline-path", str(dest),
            "--seed", "3.5", "--min-samples", "8", "--rolling-window", "20")
    assert r.returncode == 0
    data = yaml.safe_load(dest.read_text())
    assert data["config_snapshot"] == {
        "seed": 3.5, "min_samples": 8, "rolling_window": 20,
    }


# ---- detect_bmad_capability.py ----

def _write_manifest(root: Path, version: str | None):
    cfg = root / "_bmad" / "_config"
    cfg.mkdir(parents=True, exist_ok=True)
    payload = {} if version is None else {"version": version}
    (cfg / "manifest.yaml").write_text(yaml.dump(payload))


def test_detect_ok_on_660(tmp_path: Path):
    _write_manifest(tmp_path, "6.6.0")
    r = run(DETECT, "--project-root", str(tmp_path))
    assert r.returncode == 0
    assert json.loads(r.stdout)["capability"] == "bmad-6.6.0+"


def test_detect_ok_on_newer(tmp_path: Path):
    _write_manifest(tmp_path, "6.7.2")
    r = run(DETECT, "--project-root", str(tmp_path))
    assert r.returncode == 0


def test_detect_too_old(tmp_path: Path):
    _write_manifest(tmp_path, "6.4.0")
    r = run(DETECT, "--project-root", str(tmp_path))
    assert r.returncode == 1
    assert json.loads(r.stdout)["capability"] == "bmad-too-old"


def test_detect_not_installed(tmp_path: Path):
    r = run(DETECT, "--project-root", str(tmp_path))
    assert r.returncode == 2
    assert json.loads(r.stdout)["capability"] == "bmad-not-installed"


def test_detect_falls_back_to_core_module_version(tmp_path: Path):
    cfg = tmp_path / "_bmad" / "_config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "manifest.yaml").write_text(
        yaml.dump({"modules": [{"name": "core", "version": "6.6.0"}]})
    )
    r = run(DETECT, "--project-root", str(tmp_path))
    assert r.returncode == 0


if __name__ == "__main__":
    sys.exit(subprocess.call(
        ["uv", "run", "--with", "pytest", "pytest", "-q", str(Path(__file__).parent)]
    ))
