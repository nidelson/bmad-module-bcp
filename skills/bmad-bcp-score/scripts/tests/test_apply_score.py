#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml", "pytest"]
# ///
"""Unit tests for apply_score.py — the deterministic BCP scoring engine.

Run: uv run --with pytest --with pyyaml pytest skills/bmad-bcp-score/scripts/tests/
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parent.parent / "apply_score.py"


def _rule(tmp: Path) -> Path:
    p = tmp / "bcp-rule.yaml"
    p.write_text(yaml.dump({
        "rule_version": "1.0",
        "sizes": {"XS": 1, "S": 2, "M": 3, "L": 5, "XL": 8},
        "elements": [
            {"slug": "business_rules"}, {"slug": "audits"},
            {"slug": "domain_entities"},
        ],
    }))
    return p


def _baseline(tmp: Path, categories=None) -> Path:
    p = tmp / "bcp-baseline.yaml"
    p.write_text(yaml.dump({
        "schema_version": "1.0",
        "config_snapshot": {"seed": 4.13, "min_samples": 5, "rolling_window": 10},
        "categories": categories or {},
    }))
    return p


def _story(tmp: Path, fm: dict, body="# Story\n\nCorpo.\n") -> Path:
    p = tmp / "story.md"
    p.write_text(f"---\n{yaml.dump(fm, sort_keys=False)}---\n{body}")
    return p


def _bd(tmp: Path, breakdown: dict) -> Path:
    p = tmp / "bd.json"
    p.write_text(json.dumps({"breakdown": breakdown}))
    return p


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True)


def test_score_and_derive_seed(tmp_path: Path):
    story = _story(tmp_path, {"story_id": "1.1", "category": "backend",
                              "estimated_hours": 80})
    bd = _bd(tmp_path, {"business_rules": [{"size": "XL", "points": 8}],
                        "audits": [{"size": "XS", "points": 1}]})
    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual", "--now", "2026-05-17T00:00:00Z")
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["total"] == 9
    assert out["hours_per_bcp"] == 4.13
    assert out["hours_per_bcp_source"] == "seed"
    assert out["estimated_hours"] == round(9 * 4.13, 2)
    fm, _, _ = _split(story.read_text())
    assert fm["estimated_hours_pre_bcp"] == 80          # original captured
    assert fm["estimated_hours_basis"] == "bcp"
    assert fm["bcp"]["total"] == 9
    assert fm["bcp"]["scored_at"] == "2026-05-17T00:00:00Z"


def test_baseline_category_overrides_seed(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})
    base = _baseline(tmp_path, {"backend": {"h_per_bcp": 6.0, "is_seed": False}})
    r = run("--story", str(story), "--breakdown", str(bd), "--baseline",
            str(base), "--rule", str(_rule(tmp_path)), "--scored-by", "manual")
    out = json.loads(r.stdout)
    assert out["hours_per_bcp"] == 6.0
    assert out["hours_per_bcp_source"] == "baseline:backend"
    assert out["estimated_hours"] == 18.0


def test_pre_bcp_set_once_idempotent(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 80})
    bd = _bd(tmp_path, {"audits": [{"size": "S", "points": 2}]})
    common = ("--baseline", str(_baseline(tmp_path)), "--rule",
              str(_rule(tmp_path)), "--scored-by", "manual")
    run("--story", str(story), "--breakdown", str(bd), *common)
    fm1, _, _ = _split(story.read_text())
    assert fm1["estimated_hours_pre_bcp"] == 80
    # re-run: pre_bcp must NOT become the BCP-derived value
    run("--story", str(story), "--breakdown", str(bd), *common)
    fm2, _, _ = _split(story.read_text())
    assert fm2["estimated_hours_pre_bcp"] == 80


def test_pulse_metrics_untouched(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 40,
                              "pulse_metrics": {"actual_hours": 33, "x": [1, 2]}})
    bd = _bd(tmp_path, {"business_rules": [{"size": "L", "points": 5}]})
    run("--story", str(story), "--breakdown", str(bd), "--baseline",
        str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
        "--scored-by", "manual")
    fm, body, _ = _split(story.read_text())
    assert fm["pulse_metrics"] == {"actual_hours": 33, "x": [1, 2]}
    assert "Corpo." in body


def test_rescore_history_and_delta_advisory(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 8})
    rule, base = _rule(tmp_path), _baseline(tmp_path)
    run("--story", str(story), "--breakdown",
        str(_bd(tmp_path, {"business_rules": [{"size": "S", "points": 2}]})),
        "--baseline", str(base), "--rule", str(rule), "--scored-by", "manual")
    # rescore much bigger -> >50% delta advisory + history grows
    bd2 = tmp_path / "bd2.json"
    bd2.write_text(json.dumps({"breakdown":
        {"business_rules": [{"size": "XL", "points": 8}]}}))
    r = run("--story", str(story), "--breakdown", str(bd2), "--baseline",
            str(base), "--rule", str(rule), "--scored-by", "rescore",
            "--rescore")
    out = json.loads(r.stdout)
    assert out["history_len"] == 1
    assert any("split" in a for a in out["advisories"])
    fm, _, _ = _split(story.read_text())
    assert fm["bcp"]["history"][0]["total"] == 2
    assert fm["bcp"]["total"] == 8


def test_dry_run_does_not_write(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 50})
    before = story.read_text()
    bd = _bd(tmp_path, {"audits": [{"size": "XS", "points": 1}]})
    r = run("--story", str(story), "--breakdown", str(bd), "--baseline",
            str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual", "--dry-run")
    out = json.loads(r.stdout)
    assert out["dry_run"] is True
    assert "preview_frontmatter" in out
    assert story.read_text() == before          # untouched


def test_invalid_points_rejected(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 1})
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"breakdown":
        {"business_rules": [{"size": "M", "points": 99}]}}))
    r = run("--story", str(story), "--breakdown", str(bad), "--baseline",
            str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual")
    assert r.returncode == 1
    assert "Fibonacci" in json.loads(r.stdout)["error"]


def test_unknown_slug_rejected(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 1})
    bad = _bd(tmp_path, {"not_an_element": [{"size": "M", "points": 3}]})
    r = run("--story", str(story), "--breakdown", str(bad), "--baseline",
            str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual")
    assert r.returncode == 1
    assert "unknown element slug" in json.loads(r.stdout)["error"]


# minimal frontmatter splitter mirroring the script (test helper)
def _split(text: str):
    parts = text.split("---", 2)
    return yaml.safe_load(parts[1]), parts[2], "\n"


if __name__ == "__main__":
    sys.exit(subprocess.call(
        ["uv", "run", "--with", "pytest", "--with", "pyyaml",
         "pytest", "-q", str(Path(__file__).parent)]))


# ── Sprint-status history store (issue #19) ──────────────────────────────────

def test_sprint_status_flag_writes_history_there(tmp_path: Path):
    """With --sprint-status: history goes to sprint-status, not story frontmatter."""
    sprint = tmp_path / "sprint-status.yaml"
    sprint.write_text("development_status: {}\n", encoding="utf-8")

    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10,
                               "bcp": {"schema_version": "1.0", "rule_version": "1.0",
                                       "total": 2, "scored_at": "2026-01-01T00:00:00Z",
                                       "scored_by": "manual", "breakdown": {},
                                       "history": []}})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})
    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "rescore", "--rescore",
            "--sprint-status", str(sprint))
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["history_store"] == "sprint-status"

    fm = yaml.safe_load(story.read_text().split("---", 2)[1])
    assert "history" not in fm.get("bcp", {}), "history should not be in story frontmatter"

    ss = yaml.safe_load(sprint.read_text())
    story_key = story.stem
    hist = ss["bcp_metrics"][story_key]["history"]
    assert len(hist) == 1
    assert hist[0]["total"] == 2


def test_sprint_status_history_store_field(tmp_path: Path):
    """Without --sprint-status: history_store is 'story-frontmatter'."""
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})
    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual")
    assert r.returncode == 0
    assert json.loads(r.stdout)["history_store"] == "story-frontmatter"


def test_sprint_status_idempotent_history(tmp_path: Path):
    """Rescoring twice via sprint-status accumulates history without duplication."""
    sprint = tmp_path / "sprint-status.yaml"
    sprint.write_text("development_status: {}\n", encoding="utf-8")

    bcp_block = {"schema_version": "1.0", "rule_version": "1.0",
                 "total": 2, "scored_at": "2026-01-01T00:00:00Z",
                 "scored_by": "manual", "breakdown": {}}
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10,
                               "bcp": bcp_block})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})

    base_args = ["--story", str(story), "--breakdown", str(bd),
                 "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
                 "--scored-by", "rescore", "--rescore",
                 "--sprint-status", str(sprint)]

    r1 = run(*base_args)
    assert r1.returncode == 0

    # Update story's bcp.total to simulate a new current score before second rescore
    fm = yaml.safe_load(story.read_text().split("---", 2)[1])
    fm["bcp"]["total"] = 3
    fm["bcp"]["scored_at"] = "2026-02-01T00:00:00Z"
    story.write_text(f"---\n{yaml.dump(fm)}---\n# body\n", encoding="utf-8")

    r2 = run(*base_args)
    assert r2.returncode == 0

    ss = yaml.safe_load(sprint.read_text())
    hist = ss["bcp_metrics"][story.stem]["history"]
    assert len(hist) == 2
    assert hist[0]["total"] == 2
    assert hist[1]["total"] == 3
