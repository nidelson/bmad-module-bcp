# BCP — Migration to PULSE

## Overview

This module is **deprecated**. BCP scoring now ships inside
[PULSE](https://github.com/nidelson/bmad-module-pulse), which owns the whole
estimate-to-measurement loop: it scores the story, derives `estimated_hours`,
times the implementation, and recalibrates the baseline from the real hours.

Nothing about the format changed. The BCP ruler, `bcp-baseline.yaml`, and the
`bcp.*` frontmatter block are byte-for-byte what they were — the skills moved,
the data did not. There is no conversion step and nothing to re-score.

This workflow is what remains of the installer: it walks a project off this
module and onto PULSE. Run it, then uninstall this module.

## Why the skills are gone rather than redirecting

Skill names are a single global namespace. `_bmad/_config/skill-manifest.csv`
holds one row per skill name with one owning module, and installed skills land
in `.claude/skills/<name>/` — one directory per name, whoever wrote last.

Both modules ship `bmad-bcp-score`, `bmad-bcp-rule-card`, and the rest. Had this
module kept those directories as pointers saying "moved to PULSE", installing or
reinstalling it after PULSE would overwrite PULSE's working skills with the
pointers. The redirect would cause the outage it was meant to prevent. Removing
them is what makes the two modules safe to have installed at once.

## Conventions

- Bare paths (e.g. `customize.toml`) resolve from the skill root.
- `{project-root}`-prefixed paths resolve from the project root.
- `{project-root}` is a literal token in BMAD config **values** — never
  substitute it there. Filesystem path **arguments** are real paths: resolve it.

## Step 1 — Install PULSE

```bash
npx bmad-method install --custom-source github:nidelson/bmad-module-pulse
```

Then run `/bmad-pulse-setup` and answer `bcp` when it asks for the estimation
method. That is the switch: `pulse_estimation_method = "bcp"` is what turns the
scoring skills on, and it is opt-in permanently — PULSE without it is the
baseline product, not a degraded one.

Setup will do two things that matter to a migrating project. Let it.

## Step 2 — Move the configuration

The `bcp_*` settings live under `[modules.bcp]` in the merged BMAD config,
written by **this** module. Uninstalling it deletes that table.

PULSE reads `[modules.pulse]` first and falls back to `[modules.bcp]`, so
nothing breaks the moment PULSE is installed. But the fallback only lasts as
long as this module does. `/bmad-pulse-setup` detects values still reading
`modules.bcp` and offers to copy them into `_bmad/custom/config.toml` under
`[modules.pulse]`. Accept.

Check it landed before uninstalling:

```bash
python3 {project-root}/.claude/skills/bmad-bcp-score/scripts/bcp_config.py \
    --project-root "{project-root}"
```

Every key in the `sources` map should read `modules.pulse` — or `default` for
keys the project never configured. Any key still reading `modules.bcp` is a key
that will silently revert to a built-in default when this module goes.

`bcp_baseline_seed` and `bcp_reference_h_per_bcp` are the two to check hardest.
The seed drives every cold-start estimate; the reference rate is the frozen
denominator the leverage-vs-reference figure is measured against. A project that
calibrated them and then lost them gets plausible numbers that describe nobody.

## Step 3 — Keep the baseline

`bcp-baseline.yaml` carries every sample the team accumulated and the per-category
rates recalibration derived from them. PULSE reads the same file at the same
path, in the same schema.

`/bmad-pulse-setup` seeds a baseline only when none exists — it reports
`skipped_exists` and leaves yours untouched. Do **not** pass `--force` to
`seed_baseline.py` on a migration: it would replace measured rates with the
cold-start seed and report success.

## Step 4 — Uninstall this module

Once the config reads `modules.pulse` and scoring runs under PULSE, remove this
module from the project's BMAD install and drop `[modules.bcp]` from
`_bmad/config.toml`.

## Confirm

Report to the user:

- PULSE installed, with `pulse_estimation_method = "bcp"`.
- The `bcp_*` keys now resolving from `modules.pulse` — name any that still read
  `modules.bcp` or `default`, and say what each one does.
- The baseline preserved, with its sample count and how many categories have
  left the seed.
- That this module can now be uninstalled.

## Outcome

Use the user's configured name and language for the rest of the session:

```bash
uv run "{project-root}/_bmad/scripts/resolve_config.py" \
    --project-root "{project-root}" --key core
```

Take `user_name` and `communication_language` from the `core` table. If the
script is absent or exits non-zero, address the user neutrally in English — do
not write or repair any config file.
