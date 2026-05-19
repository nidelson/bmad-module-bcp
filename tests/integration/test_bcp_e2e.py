"""End-to-end orchestration + fault injection.

These tests don't run the LLM. They run the same script chain a SKILL.md
would (seed → score → rescore → recalibrate) and assert filesystem deltas,
then deliberately inject the failure modes the module promises to survive:
corrupted/missing baseline, invalid breakdown, absent PULSE, history
overflow, duplicate recalibration samples. v0.1.0's non-functional promise
is graceful degradation — this file is where that promise is enforced.
"""
from __future__ import annotations

import json

import pytest
import yaml

from tests.conftest import (APPLY_SCORE, RECALIBRATE, run_script)

RULE_ARG = ("--rule", "skills/bmad-bcp-rule-card/assets/bcp-rule.yaml")
pytestmark = pytest.mark.integration


def _score(story, bd, baseline, scored_by="manual", rescore=False, now=None):
    args = [APPLY_SCORE, "--story", str(story), "--breakdown", str(bd),
            "--baseline", str(baseline), *RULE_ARG,
            "--scored-by", scored_by, "--now", now or "2026-05-18T00:00:00Z"]
    if rescore:
        args.append("--rescore")
    return run_script(*args)


def test_happy_chain_seed_score_recalibrate_leaves_seed(
    seeded_baseline, story_file, breakdown_file
):
    """Full lifecycle: a category sits on the seed until min_samples
    actuals arrive via recalibrate, then flips to its rolling mean."""
    story = story_file({"story_id": "1.1", "category": "backend",
                        "estimated_hours": 10})
    bd = breakdown_file({"business_rules": [{"size": "L", "points": 5}]})
    s = _score(story, bd, seeded_baseline)
    assert s.returncode == 0, s.stderr
    assert json.loads(s.stdout)["hours_per_bcp_source"] == "seed"

    # Feed min_samples (5) actuals for backend.
    samples = [{"category": "backend", "bcp_total": 5, "actual_hours": 30,
                "id": f"s{i}"} for i in range(5)]
    samples_path = story.parent / "samples.json"
    samples_path.write_text(json.dumps(samples))
    r = run_script(RECALIBRATE, "--baseline", str(seeded_baseline),
                   "--samples", str(samples_path),
                   "--now", "2026-05-18T01:00:00Z")
    assert r.returncode == 0, r.stderr
    base = yaml.safe_load(seeded_baseline.read_text())
    cat = base["categories"]["backend"]
    assert cat["is_seed"] is False
    assert cat["n_samples"] == 5
    assert cat["h_per_bcp"] == pytest.approx(6.0)  # mean(30/5 per sample)

    # Next score for backend now uses the calibrated mean, not the seed.
    s2 = _score(story, bd, seeded_baseline, now="2026-05-18T02:00:00Z")
    assert json.loads(s2.stdout)["hours_per_bcp_source"] == "baseline:backend"


def test_corrupted_baseline_fails_loud_not_silent(
    tmp_path, story_file, breakdown_file
):
    bad = tmp_path / "bcp-baseline.yaml"
    bad.write_text("categories: [unclosed\n  :::not yaml")
    story = story_file({"story_id": "x", "category": "backend",
                        "estimated_hours": 5})
    bd = breakdown_file({"business_rules": [{"size": "M", "points": 3}]})
    proc = _score(story, bd, bad)
    assert proc.returncode == 1
    assert json.loads(proc.stdout)["status"] == "error"
    # The story must be left untouched on failure.
    assert "bcp:" not in story.read_text()


def test_missing_baseline_fails_without_writing_story(
    tmp_path, story_file, breakdown_file
):
    story = story_file({"story_id": "x", "category": "backend",
                        "estimated_hours": 5})
    bd = breakdown_file({"business_rules": [{"size": "M", "points": 3}]})
    proc = _score(story, bd, tmp_path / "does-not-exist.yaml")
    assert proc.returncode == 1
    assert "bcp:" not in story.read_text()


def test_invalid_breakdown_rejected(
    seeded_baseline, story_file, breakdown_file
):
    story = story_file({"story_id": "x", "category": "backend",
                        "estimated_hours": 5})
    bad = breakdown_file({"business_rules": [{"size": "M", "points": 99}]})
    proc = _score(story, bad, seeded_baseline)
    assert proc.returncode == 1
    assert "Fibonacci" in json.loads(proc.stdout)["error"]


def test_unknown_element_slug_rejected(
    seeded_baseline, story_file, breakdown_file
):
    story = story_file({"story_id": "x", "category": "backend",
                        "estimated_hours": 5})
    bad = breakdown_file({"made_up_element": [{"size": "M", "points": 3}]})
    proc = _score(story, bad, seeded_baseline)
    assert proc.returncode == 1
    assert "unknown element slug" in json.loads(proc.stdout)["error"]


def test_runs_standalone_without_pulse(
    seeded_baseline, story_file, breakdown_file
):
    """No pulse_metrics, no PULSE module — BCP must work fully alone and
    never invent the PULSE-owned key."""
    story = story_file({"story_id": "1.1", "category": "backend",
                        "estimated_hours": 8})
    bd = breakdown_file({"domain_entities": [{"size": "M", "points": 3}]})
    proc = _score(story, bd, seeded_baseline)
    assert proc.returncode == 0, proc.stderr
    written = yaml.safe_load(story.read_text().split("---")[1])
    assert "pulse_metrics" not in written
    assert written["bcp"]["total"] == 3


def test_rescore_history_is_fifo_capped_at_50(
    seeded_baseline, story_file, breakdown_file
):
    """52 rescores → history holds the most recent 50, oldest-first,
    and the script advises on the truncation."""
    story = story_file({"story_id": "1.1", "category": "backend",
                        "estimated_hours": 10})
    bd = breakdown_file({"business_rules": [{"size": "M", "points": 3}]})
    _score(story, bd, seeded_baseline, now="2026-05-18T00:00:00Z")

    truncated_seen = False
    for i in range(1, 53):
        bd_i = story.parent / f"bd{i}.json"
        size, pts = ("S", 2) if i % 2 else ("L", 5)
        bd_i.write_text(json.dumps({"breakdown": {
            "business_rules": [{"size": size, "points": pts}]}}))
        proc = _score(story, bd_i, seeded_baseline, scored_by="rescore",
                      rescore=True, now=f"2026-05-18T{i:02d}:00:00Z")
        assert proc.returncode == 0, proc.stderr
        if json.loads(proc.stdout)["advisories"]:
            truncated_seen = any("truncado" in a for a in
                                 json.loads(proc.stdout)["advisories"])
    written = yaml.safe_load(story.read_text().split("---")[1])
    assert len(written["bcp"]["history"]) == 50
    assert truncated_seen, "expected a truncation advisory past cap 50"


def test_recalibrate_dedups_by_id(seeded_baseline, tmp_path):
    """Re-running recalibrate with the same sample id must not
    double-count (idempotent backfill safety)."""
    samples = [{"category": "api", "bcp_total": 4, "actual_hours": 20,
                "id": "dup-1"}]
    sp = tmp_path / "dup-samples.json"
    sp.write_text(json.dumps(samples))
    a = run_script(RECALIBRATE, "--baseline", str(seeded_baseline),
                   "--samples", str(sp),
                   "--now", "2026-05-18T01:00:00Z")
    assert a.returncode == 0, a.stderr
    b = run_script(RECALIBRATE, "--baseline", str(seeded_baseline),
                   "--samples", str(sp),
                   "--now", "2026-05-18T02:00:00Z")
    assert b.returncode == 0, b.stderr
    base = yaml.safe_load(seeded_baseline.read_text())
    assert base["categories"]["api"]["n_samples"] == 1, (
        "duplicate sample id double-counted — backfill not idempotent"
    )
