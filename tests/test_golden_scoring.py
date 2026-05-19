"""Golden set: deterministic scoring regression.

The LLM picks sizes (judgment, not tested here). Everything downstream of
the breakdown is deterministic and is the module's estimation contract:
`total = Σ Fibonacci(size)` and `estimated_hours = total × h_per_bcp`.

The golden set is the full 10-element × 5-size matrix (50 single-element
cases) plus realistic composites. Generating it from the frozen rule slugs
gives complete rule-mapping coverage for free and makes any drift in the
points table or the hours derivation fail loudly.
"""
from __future__ import annotations

import json

import pytest
import yaml

from .conftest import APPLY_SCORE, run_script
from .test_rule_immutability import FIB, FROZEN_SLUGS

SEED = 4.13
RULE_ARG = ("--rule", "skills/bmad-bcp-rule-card/assets/bcp-rule.yaml")

# 50-case golden matrix: every element at every size.
MATRIX = [
    (slug, size, pts)
    for slug in sorted(FROZEN_SLUGS)
    for size, pts in FIB.items()
]


@pytest.mark.parametrize("slug,size,pts", MATRIX,
                         ids=[f"{s}-{z}" for s, z, _ in MATRIX])
def test_single_element_golden(slug, size, pts, seeded_baseline,
                               story_file, breakdown_file):
    story = story_file({"story_id": "g", "category": "backend",
                        "estimated_hours": 1})
    bd = breakdown_file({slug: [{"size": size, "points": pts}]})
    proc = run_script(
        APPLY_SCORE, "--story", str(story), "--breakdown", str(bd),
        "--baseline", str(seeded_baseline), *RULE_ARG,
        "--scored-by", "manual", "--now", "2026-05-17T12:00:00Z",
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["total"] == pts
    assert out["estimated_hours"] == round(pts * SEED, 2)
    assert out["hours_per_bcp_source"] == "seed"


# Realistic composite stories — hand-curated golden expectations.
COMPOSITES = [
    pytest.param(
        {"business_rules": [{"size": "M", "points": 3}],
         "interface_elements": [{"size": "S", "points": 2},
                                {"size": "M", "points": 3}],
         "audits": [{"size": "XS", "points": 1}]},
        9, id="crud-with-audit"),
    pytest.param(
        {"business_rules": [{"size": "XL", "points": 8}],
         "background_processes": [{"size": "L", "points": 5}],
         "notifications": [{"size": "XS", "points": 1}],
         "roles_permissions": [{"size": "M", "points": 3}]},
        17, id="complex-workflow"),
    pytest.param(
        {"domain_entities": [{"size": "XS", "points": 1}]},
        1, id="trivial-single"),
]


@pytest.mark.parametrize("breakdown,expected_total", COMPOSITES)
def test_composite_golden(breakdown, expected_total, seeded_baseline,
                          story_file, breakdown_file):
    story = story_file({"story_id": "c", "category": "backend",
                        "estimated_hours": 20})
    bd = breakdown_file(breakdown)
    proc = run_script(
        APPLY_SCORE, "--story", str(story), "--breakdown", str(bd),
        "--baseline", str(seeded_baseline), *RULE_ARG,
        "--scored-by", "manual", "--now", "2026-05-17T12:00:00Z",
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["total"] == expected_total
    assert out["estimated_hours"] == round(expected_total * SEED, 2)


def test_calibrated_category_uses_rolling_mean_not_seed(
    tmp_path, story_file, breakdown_file
):
    """Once a category has left the seed, hours derive from its rolling
    mean, not 4.13. Golden-pins the seed→calibrated switchover."""
    baseline = tmp_path / "bcp-baseline.yaml"
    baseline.write_text(yaml.dump({
        "schema_version": "1.0",
        "config_snapshot": {"seed": 4.13, "min_samples": 5,
                            "rolling_window": 10},
        "categories": {
            "backend": {"h_per_bcp": 6.0, "n_samples": 7, "is_seed": False},
        },
    }))
    story = story_file({"story_id": "k", "category": "backend",
                        "estimated_hours": 5})
    bd = breakdown_file({"business_rules": [{"size": "L", "points": 5}]})
    proc = run_script(
        APPLY_SCORE, "--story", str(story), "--breakdown", str(bd),
        "--baseline", str(baseline), *RULE_ARG,
        "--scored-by", "manual", "--now", "2026-05-17T12:00:00Z",
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["total"] == 5
    assert out["estimated_hours"] == 30.0  # 5 × 6.0, not 5 × 4.13
    assert out["hours_per_bcp_source"] == "baseline:backend"
