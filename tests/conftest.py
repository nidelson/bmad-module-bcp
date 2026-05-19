"""Shared fixtures for the repo-level NFR suite.

These tests live above the per-script co-located unit tests
(`skills/*/scripts/tests/`). They assert cross-file invariants, the
BCP↔PULSE frontmatter contract, deterministic scoring against a golden
set, and end-to-end fault tolerance — the non-functional requirements of
v0.1.0.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
SKILLS = REPO_ROOT / "skills"
RULE_PATH = SKILLS / "bmad-bcp-rule-card/assets/bcp-rule.yaml"
SCHEMA_PATH = SKILLS / "bmad-bcp-score/assets/bcp-frontmatter.schema.yaml"
APPLY_SCORE = SKILLS / "bmad-bcp-score/scripts/apply_score.py"
SEED_BASELINE = SKILLS / "bmad-bcp-setup/scripts/seed_baseline.py"
RECALIBRATE = SKILLS / "bmad-bcp-recalibrate/scripts/recalibrate.py"

# The eight skills shipped in v0.1.0. Single source of truth for the
# cross-file consistency tests.
EXPECTED_SKILLS = (
    "bmad-bcp-setup",
    "bmad-bcp-rule-card",
    "bmad-bcp-score",
    "bmad-bcp-score-batch",
    "bmad-bcp-rescore",
    "bmad-bcp-recalibrate",
    "bmad-bcp-backfill-baseline",
    "bmad-bcp-agent-bruno",
)

FIB = {"XS": 1, "S": 2, "M": 3, "L": 5, "XL": 8}


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a module script the same way the SKILL.md chain would."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def rule() -> dict:
    return yaml.safe_load(RULE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def schema() -> dict:
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def seeded_baseline(tmp_path: Path) -> Path:
    """A fresh cold-start baseline (seed 4.13, all categories on seed)."""
    path = tmp_path / "bcp-baseline.yaml"
    proc = run_script(
        SEED_BASELINE,
        "--baseline-path", str(path),
        "--seed", "4.13",
        "--min-samples", "5",
        "--rolling-window", "10",
    )
    assert proc.returncode == 0, proc.stderr
    return path


@pytest.fixture
def story_file(tmp_path: Path):
    """Factory: write a story with given frontmatter, return its path."""
    def _make(frontmatter: dict, body: str = "Conteúdo da story.\n") -> Path:
        p = tmp_path / "story.md"
        fm = yaml.dump(frontmatter, default_flow_style=False,
                       allow_unicode=True, sort_keys=False)
        p.write_text(f"---\n{fm}---\n{body}", encoding="utf-8")
        return p
    return _make


@pytest.fixture
def breakdown_file(tmp_path: Path):
    """Factory: write a breakdown JSON payload, return its path."""
    def _make(breakdown: dict) -> Path:
        p = tmp_path / "breakdown.json"
        p.write_text(json.dumps({"breakdown": breakdown}), encoding="utf-8")
        return p
    return _make
