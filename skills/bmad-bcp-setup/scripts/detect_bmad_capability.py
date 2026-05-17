#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Detect whether the consumer project has BMAD >=6.6.0 installed.

BCP requires BMAD >=6.6.0: the customize.toml hook framework
(activation_steps_*, persistent_facts, on_complete) is the integration
surface BCP uses to wire scoring into `bmad-create-story`. Unlike the
filesystem-marker proxy used by older modules, this reads the precise
installed version from `_bmad/_config/manifest.yaml`.

Returns:
  exit 0 - BMAD >=6.6.0 (manifest version satisfies the gate)
  exit 1 - BMAD installed but <6.6.0 (manifest version too old)
  exit 2 - BMAD not installed (manifest absent or unparseable)

Outputs JSON to stdout describing the result.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml is required (PEP 723 dependency)", file=sys.stderr)
    sys.exit(2)

MIN_VERSION = (6, 6, 0)
MANIFEST_REL = "_bmad/_config/manifest.yaml"

CAPABILITY_OK = "bmad-6.6.0+"
CAPABILITY_OLD = "bmad-too-old"
CAPABILITY_NONE = "bmad-not-installed"

CAPABILITY_TO_EXIT = {
    CAPABILITY_OK: 0,
    CAPABILITY_OLD: 1,
    CAPABILITY_NONE: 2,
}


def parse_version(raw: str) -> tuple[int, int, int] | None:
    """Parse a 'X.Y.Z' (optionally 'vX.Y.Z') string into a comparable tuple.

    Returns None when the string is not a dotted numeric version (e.g.
    'main', 'v1.7.0' is accepted, 'main' is not).
    """
    if not raw:
        return None
    s = str(raw).strip().lstrip("vV")
    parts = s.split(".")
    if len(parts) < 2:
        return None
    nums = []
    for p in parts[:3]:
        if not p.isdigit():
            return None
        nums.append(int(p))
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])  # type: ignore[return-value]


def detect(project_root: Path) -> dict:
    manifest = project_root / MANIFEST_REL
    if not manifest.exists():
        return {"capability": CAPABILITY_NONE, "manifest_path": str(manifest)}
    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return {
            "capability": CAPABILITY_NONE,
            "manifest_path": str(manifest),
            "error": f"unparseable manifest: {e}",
        }

    # Top-level version, with a fallback to the `core` module entry.
    raw_version = data.get("version")
    if raw_version is None:
        for mod in data.get("modules", []) or []:
            if isinstance(mod, dict) and mod.get("name") == "core":
                raw_version = mod.get("version")
                break

    parsed = parse_version(raw_version)
    if parsed is None:
        return {
            "capability": CAPABILITY_NONE,
            "manifest_path": str(manifest),
            "error": f"no usable version in manifest (got {raw_version!r})",
        }

    capability = CAPABILITY_OK if parsed >= MIN_VERSION else CAPABILITY_OLD
    return {
        "capability": capability,
        "manifest_path": str(manifest),
        "detected_version": ".".join(str(n) for n in parsed),
        "min_version": ".".join(str(n) for n in MIN_VERSION),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    payload = detect(args.project_root)
    sys.stdout.write(json.dumps(payload) + "\n")
    return CAPABILITY_TO_EXIT[payload["capability"]]


if __name__ == "__main__":
    sys.exit(main())
