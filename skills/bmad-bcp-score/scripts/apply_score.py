#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Apply a BCP score to a story file (deterministic engine).

The LLM selects sizes per element (judgment) via the auto-score prompt and
hands this script a breakdown JSON. This script does only the deterministic
parts: total, hours derivation from the per-category baseline, audit-field
preservation, rescore history (FIFO cap 50, warn on truncate), delta
advisory, contract-invariant validation, and idempotent frontmatter write.

It NEVER reads or writes `pulse_metrics` — all non-BCP frontmatter keys are
preserved verbatim (PULSE owns those).

Exit codes: 0=success, 1=validation error, 2=runtime error, 3=conflict
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml is required (PEP 723 dependency)", file=sys.stderr)
    sys.exit(2)

FIB = {"XS": 1, "S": 2, "M": 3, "L": 5, "XL": 8}
HISTORY_CAP = 50
SINGLE_DELTA_THRESHOLD = 0.5   # >50% single rescore delta
CUMULATIVE_FACTOR = 2.0        # >2x (or <0.5x) cumulative drift


def split_frontmatter(text: str) -> tuple[dict, str, str]:
    """Return (frontmatter_dict, body, newline). Raises ValueError if no
    leading `---` YAML frontmatter block is present."""
    if not text.startswith("---"):
        raise ValueError("story has no leading '---' YAML frontmatter")
    nl = "\r\n" if "\r\n" in text[:200] else "\n"
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("malformed frontmatter (missing closing '---')")
    fm = yaml.safe_load(parts[1]) or {}
    if not isinstance(fm, dict):
        raise ValueError("frontmatter is not a mapping")
    body = parts[2]
    if body.startswith(nl):
        body = body[len(nl):]
    return fm, body, nl


def render(fm: dict, body: str, nl: str) -> str:
    dumped = yaml.dump(fm, default_flow_style=False, allow_unicode=True,
                        sort_keys=False).rstrip(nl)
    return f"---{nl}{dumped}{nl}---{nl}{body}"


def h_per_bcp(baseline: dict, category: str | None) -> tuple[float, str]:
    """Return (hours_per_bcp, source). Uses the category rolling mean when
    the category has left the seed; otherwise the cold-start seed."""
    snap = baseline.get("config_snapshot", {}) or {}
    seed = float(snap.get("seed", 4.13))
    cats = baseline.get("categories", {}) or {}
    if category and category in cats:
        c = cats[category]
        if not c.get("is_seed", True) and c.get("h_per_bcp") is not None:
            return float(c["h_per_bcp"]), f"baseline:{category}"
    return seed, "seed"


def validate_breakdown(breakdown: dict, rule_slugs: set[str]) -> int:
    """Validate the breakdown against contract invariants. Returns the
    total points. Raises ValueError on any violation."""
    if not isinstance(breakdown, dict) or not breakdown:
        raise ValueError("breakdown must be a non-empty object")
    total = 0
    for slug, items in breakdown.items():
        if rule_slugs and slug not in rule_slugs:
            raise ValueError(f"unknown element slug '{slug}' (not in rule)")
        if not isinstance(items, list) or not items:
            raise ValueError(f"breakdown['{slug}'] must be a non-empty list")
        for it in items:
            size = it.get("size")
            pts = it.get("points")
            if size not in FIB:
                raise ValueError(f"invalid size {size!r} for '{slug}'")
            if pts != FIB[size]:
                raise ValueError(
                    f"points {pts!r} != Fibonacci {FIB[size]} for size {size}"
                )
            total += pts
    return total


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--story", type=Path, required=True)
    p.add_argument("--breakdown", type=Path, required=True,
                   help="JSON file: {\"breakdown\": {...}} from auto-score")
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--rule", type=Path, required=True)
    p.add_argument("--scored-by", required=True,
                   choices=["bruno", "manual", "rescore", "retroactive"])
    p.add_argument("--category", default=None,
                   help="override; defaults to story frontmatter `category`")
    p.add_argument("--rescore", action="store_true",
                   help="archive prior bcp block into history before writing")
    p.add_argument("--now", default=None, help="ISO timestamp (testing)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    try:
        rule = yaml.safe_load(args.rule.read_text(encoding="utf-8")) or {}
        baseline = yaml.safe_load(args.baseline.read_text(encoding="utf-8")) or {}
        payload = json.loads(args.breakdown.read_text(encoding="utf-8"))
        story_text = args.story.read_text(encoding="utf-8")
        fm, body, nl = split_frontmatter(story_text)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        return 1

    breakdown = payload.get("breakdown", payload)
    rule_slugs = {e["slug"] for e in rule.get("elements", []) if "slug" in e}
    rule_version = str(rule.get("rule_version", "1.0"))

    try:
        total = validate_breakdown(breakdown, rule_slugs)
    except ValueError as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        return 1

    category = args.category or fm.get("category")
    hpb, hpb_source = h_per_bcp(baseline, category)
    estimated_hours = round(total * hpb, 2)
    scored_at = args.now or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")

    prev = fm.get("bcp")
    advisories: list[str] = []
    history = list(prev.get("history", [])) if isinstance(prev, dict) else []

    if isinstance(prev, dict) and args.rescore:
        prev_total = prev.get("total")
        snapshot = {
            "rule_version": prev.get("rule_version", rule_version),
            "total": prev_total,
            "scored_at": prev.get("scored_at"),
            "scored_by": prev.get("scored_by", "manual"),
            "estimated_hours": fm.get("estimated_hours"),
        }
        history = [h for h in history if h] + [snapshot]
        truncated = max(0, len(history) - HISTORY_CAP)
        if truncated:
            history = history[truncated:]
            advisories.append(
                f"bcp.history truncado: {truncated} entrada(s) mais antiga(s) "
                f"removida(s) (cap {HISTORY_CAP}).")
        if isinstance(prev_total, (int, float)) and prev_total:
            single = abs(total - prev_total) / prev_total
            if single > SINGLE_DELTA_THRESHOLD:
                advisories.append(
                    f"Delta de {single*100:.0f}% neste rescore (>50%). "
                    f"Considere split em sub-story.")
            oldest = next((h.get("total") for h in history
                           if isinstance(h.get("total"), (int, float))
                           and h.get("total")), prev_total)
            if oldest:
                cum = total / oldest
                if cum > CUMULATIVE_FACTOR or cum < 1 / CUMULATIVE_FACTOR:
                    advisories.append(
                        f"Drift cumulativo {cum:.1f}× vs primeiro score "
                        f"(>2× ou <0.5×). Considere split em sub-story.")

    # Audit: capture the original estimate exactly once.
    if "estimated_hours" in fm and "estimated_hours_pre_bcp" not in fm:
        fm["estimated_hours_pre_bcp"] = fm["estimated_hours"]

    fm["estimated_hours"] = estimated_hours
    fm["estimated_hours_basis"] = "bcp"
    fm["bcp"] = {
        "schema_version": "1.0",
        "rule_version": rule_version,
        "total": total,
        "scored_at": scored_at,
        "scored_by": args.scored_by,
        "breakdown": breakdown,
        "history": history,
    }
    # pulse_metrics and every other key are left untouched by construction.

    result = {
        "status": "success",
        "story": str(args.story),
        "total": total,
        "hours_per_bcp": hpb,
        "hours_per_bcp_source": hpb_source,
        "estimated_hours": estimated_hours,
        "estimated_hours_pre_bcp": fm.get("estimated_hours_pre_bcp"),
        "scored_by": args.scored_by,
        "history_len": len(history),
        "advisories": advisories,
        "dry_run": bool(args.dry_run),
    }

    if args.dry_run:
        result["preview_frontmatter"] = fm
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    try:
        args.story.write_text(render(fm, body, nl), encoding="utf-8")
    except OSError as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        return 2

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
