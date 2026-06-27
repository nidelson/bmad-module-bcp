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

Rescore history operational store (sprint-status.yaml):

  --project-root <path>   Auto-detects sprint-status from BMAD config:
                          _bmad/config.yaml → output_folder →
                          pulse.pulse_data_folder + pulse_sprint_status_filename.
                          If the resolved file exists → sprint-status mode.
                          If not → legacy mode (history in story frontmatter).

  --sprint-status <path>  Explicit override. Takes precedence over --project-root.

  Neither flag            Legacy mode: history written to bcp.history in story
                          frontmatter with deprecation advisory on --rescore.

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


def resolve_sprint_status(project_root: Path) -> Path | None:
    """Derive sprint-status path from BMAD config token chain.

    Chain: project_root → _bmad/config.yaml
             → output_folder (resolve {project-root})
               → pulse.pulse_data_folder (resolve {output_folder})
                 → + pulse_sprint_status_filename

    Returns the resolved Path if the file exists, else None.
    """
    config_path = project_root / "_bmad/config.yaml"
    if not config_path.exists():
        return None
    try:
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None

    raw_output = str(cfg.get("output_folder", "{project-root}/_bmad-output"))
    output_folder = raw_output.replace("{project-root}", str(project_root))

    pulse = cfg.get("pulse", {}) or {}
    raw_data = str(pulse.get("pulse_data_folder",
                             "{output_folder}/implementation-artifacts"))
    data_folder = raw_data.replace("{output_folder}", output_folder) \
                          .replace("{project-root}", str(project_root))

    filename = str(pulse.get("pulse_sprint_status_filename", "sprint-status.yaml"))
    candidate = Path(data_folder) / filename
    return candidate if candidate.exists() else None


def write_history_to_sprint_status(
    sprint_status_path: Path,
    story_key: str,
    history: list[dict],
) -> None:
    """Upsert bcp_metrics[story_key].history in sprint-status.yaml.

    Creates the bcp_metrics section if absent. FIFO-caps at HISTORY_CAP.
    Preserves all other sprint-status content verbatim.
    """
    text = sprint_status_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError("sprint-status.yaml root is not a mapping")

    bcp_metrics = data.setdefault("bcp_metrics", {})
    entry = bcp_metrics.setdefault(story_key, {})
    entry["history"] = history[-HISTORY_CAP:]

    sprint_status_path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True,
                  sort_keys=False),
        encoding="utf-8",
    )


def read_history_from_sprint_status(
    sprint_status_path: Path,
    story_key: str,
) -> list[dict]:
    """Read bcp_metrics[story_key].history from sprint-status.yaml."""
    if not sprint_status_path.exists():
        return []
    data = yaml.safe_load(sprint_status_path.read_text(encoding="utf-8")) or {}
    return list(data.get("bcp_metrics", {}).get(story_key, {}).get("history", []))


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
    p.add_argument("--reference-h-per-bcp", type=float, default=None,
                   help="frozen reference rate (governance anchor) used to derive "
                        "estimated_hours_reference. Defaults to the baseline seed "
                        "when omitted. NEVER the live recalibrated factor.")
    p.add_argument("--rescore", action="store_true",
                   help="archive prior bcp block into history before writing")
    p.add_argument("--project-root", type=Path, default=None,
                   help="BMAD project root; sprint-status path is auto-derived "
                        "from _bmad/config.yaml token chain "
                        "(output_folder → pulse_data_folder → filename). "
                        "Ignored when --sprint-status is explicit.")
    p.add_argument("--sprint-status", type=Path, default=None,
                   help="explicit path to sprint-status.yaml (overrides "
                        "--project-root auto-detection)")
    p.add_argument("--now", default=None, help="ISO timestamp (testing)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    # Resolve sprint-status: explicit flag wins; fallback to auto-detect.
    sprint_status_path: Path | None = args.sprint_status
    if sprint_status_path is None and args.project_root is not None:
        sprint_status_path = resolve_sprint_status(args.project_root)

    use_sprint_status = sprint_status_path is not None
    story_key = args.story.stem

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

    # Frozen reference anchor (issue #32): a stable denominator for leverage that
    # does NOT collapse as the category calibrates. Defaults to the cold-start
    # seed so the anchor is computable from day one; a governance-set reference
    # rate (via --reference-h-per-bcp) overrides it. NEVER the recalibrated factor.
    snap = baseline.get("config_snapshot", {}) or {}
    seed = float(snap.get("seed", 4.13))
    if args.reference_h_per_bcp is not None:
        reference_rate, reference_source = float(args.reference_h_per_bcp), "config"
    else:
        reference_rate, reference_source = seed, "seed"
    estimated_hours_reference = round(total * reference_rate, 2)

    scored_at = args.now or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")

    prev = fm.get("bcp")
    advisories: list[str] = []

    # Load history from the appropriate store.
    if use_sprint_status:
        history = read_history_from_sprint_status(sprint_status_path, story_key)
    else:
        history = list(prev.get("history", [])) if isinstance(prev, dict) else []
        if args.rescore:
            advisories.append(
                "bcp.history gravado no frontmatter da story (modo legado). "
                "Passe --sprint-status para mover para sprint-status.yaml "
                "(separação spec/operacional — issue #19).")

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
    fm["estimated_hours_reference"] = estimated_hours_reference

    bcp_block: dict = {
        "schema_version": "1.0",
        "rule_version": rule_version,
        "total": total,
        "scored_at": scored_at,
        "scored_by": args.scored_by,
        "breakdown": breakdown,
    }
    if not use_sprint_status:
        # Legacy: keep history in story frontmatter when no sprint-status provided.
        bcp_block["history"] = history
    else:
        # Modern: history lives in sprint-status; omit from story frontmatter.
        # Migrate any legacy history block that may already be in frontmatter.
        if isinstance(prev, dict) and prev.get("history"):
            advisories.append(
                "bcp.history migrado do frontmatter para sprint-status.yaml.")

    fm["bcp"] = bcp_block
    # pulse_metrics and every other key are left untouched by construction.

    result = {
        "status": "success",
        "story": str(args.story),
        "total": total,
        "hours_per_bcp": hpb,
        "hours_per_bcp_source": hpb_source,
        "estimated_hours": estimated_hours,
        "estimated_hours_pre_bcp": fm.get("estimated_hours_pre_bcp"),
        "reference_h_per_bcp": reference_rate,
        "reference_source": reference_source,
        "estimated_hours_reference": estimated_hours_reference,
        "scored_by": args.scored_by,
        "history_len": len(history),
        "history_store": "sprint-status" if use_sprint_status else "story-frontmatter",
        "advisories": advisories,
        "dry_run": bool(args.dry_run),
    }

    if args.dry_run:
        result["preview_frontmatter"] = fm
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    try:
        args.story.write_text(render(fm, body, nl), encoding="utf-8")
        if use_sprint_status and sprint_status_path.exists():
            write_history_to_sprint_status(sprint_status_path, story_key, history)
    except (OSError, ValueError, yaml.YAMLError) as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        return 2

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
