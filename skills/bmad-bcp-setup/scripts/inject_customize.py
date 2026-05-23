#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Emit a `_bmad/custom/<skill>.toml` override from a packaged template.

BCP uses this to hook BCP scoring into consumer workflows without editing
BMAD core (the override lives in `_bmad/custom/`, which BMAD never overwrites).

Two injection modes:

  copy (default)  — plain file copy from template. Aborts (exit 3) if the
                    destination already exists, unless --force is passed.
                    Idempotent under --force: rerunning produces a byte-
                    identical file (sha256 stable) as long as the template
                    has not changed.

  merge           -- appends the template's `on_complete` value to the
                    destination's existing `on_complete` (separated by a
                    single space). Used when another module (e.g. PULSE) has
                    already registered an on_complete in the same file.
                    If the destination does not exist, behaves like copy.
                    Idempotent: re-running detects that the BCP sentence is
                    already present and skips without modifying the file.

Exit codes: 0=success, 1=already-present (merge idempotent skip),
            2=bad args, 3=conflict (copy mode only)
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

TEMPLATES_DIR = Path(__file__).parent.parent / "assets/customize-templates"
SUPPORTED_SKILLS = {"bmad-create-story", "bmad-code-review"}
MERGE_SKILLS = {"bmad-code-review"}

EXIT_OK = 0
EXIT_ALREADY_PRESENT = 1
EXIT_BAD_ARGS = 2
EXIT_CONFLICT = 3

_ON_COMPLETE_RE = re.compile(
    r'^on_complete\s*=\s*"((?:[^"\\]|\\.)*)"',
    re.MULTILINE,
)


def _read_on_complete(text: str) -> str | None:
    """Extract on_complete value from TOML text (simple single-line string only)."""
    m = _ON_COMPLETE_RE.search(text)
    return m.group(1) if m else None


def _replace_on_complete(text: str, new_value: str) -> str:
    """Replace the on_complete value in TOML text."""
    escaped = new_value.replace("\\", "\\\\").replace('"', '\\"')
    replacement = f'on_complete = "{escaped}"'
    return _ON_COMPLETE_RE.sub(replacement, text)


def emit_copy(project_root: Path, skill: str, force: bool) -> int:
    template = TEMPLATES_DIR / f"{skill}.toml"
    if not template.exists():
        sys.stderr.write(f"error: template missing for skill '{skill}': {template}\n")
        return EXIT_BAD_ARGS
    dest_dir = project_root / "_bmad/custom"
    dest = dest_dir / f"{skill}.toml"
    if dest.exists() and not force:
        sys.stderr.write(
            f"error: {dest} already exists. "
            f"Re-run with --force to overwrite, or remove the file manually.\n"
        )
        return EXIT_CONFLICT
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, dest)
    sys.stdout.write(f"wrote {dest}\n")
    return EXIT_OK


def emit_merge(project_root: Path, skill: str) -> int:
    """Append template's on_complete to existing file's on_complete.

    If destination does not exist, falls back to copy.
    If BCP sentence already present in destination, skips (idempotent).
    """
    template = TEMPLATES_DIR / f"{skill}.toml"
    if not template.exists():
        sys.stderr.write(f"error: template missing for skill '{skill}': {template}\n")
        return EXIT_BAD_ARGS

    dest_dir = project_root / "_bmad/custom"
    dest = dest_dir / f"{skill}.toml"

    if not dest.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template, dest)
        sys.stdout.write(f"wrote {dest} (new file)\n")
        return EXIT_OK

    template_text = template.read_text(encoding="utf-8")
    bcp_sentence = _read_on_complete(template_text)
    if not bcp_sentence:
        sys.stderr.write(f"error: template {template} has no on_complete value\n")
        return EXIT_BAD_ARGS

    dest_text = dest.read_text(encoding="utf-8")

    # Idempotency: skip if BCP sentence already in destination
    if bcp_sentence in dest_text:
        sys.stdout.write(f"skipped {dest} — BCP on_complete already present\n")
        return EXIT_ALREADY_PRESENT

    existing_oc = _read_on_complete(dest_text)
    if existing_oc is not None:
        merged = existing_oc.rstrip() + " " + bcp_sentence
        new_text = _replace_on_complete(dest_text, merged)
    else:
        # No on_complete in dest yet — append the BCP block
        new_text = dest_text.rstrip("\n") + "\n" + template_text

    dest.write_text(new_text, encoding="utf-8")
    sys.stdout.write(f"merged {dest}\n")
    return EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--skill", choices=sorted(SUPPORTED_SKILLS), required=True)
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing file (copy mode only)")
    parser.add_argument("--merge", action="store_true",
                        help="append on_complete to existing file instead of replacing")
    args = parser.parse_args()

    use_merge = args.merge or args.skill in MERGE_SKILLS
    if use_merge:
        return emit_merge(args.project_root, args.skill)
    return emit_copy(args.project_root, args.skill, args.force)


if __name__ == "__main__":
    sys.exit(main())
