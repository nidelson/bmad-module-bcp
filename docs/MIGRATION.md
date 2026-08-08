# BCP Migration Guide

Per-release upgrade notes. Newest first. Each section is self-contained;
skip to the version you are migrating from.

---

## Module deprecated — scoring moves to PULSE (nidelson/bmad-module-pulse#84)

BCP scoring now ships inside
[PULSE](https://github.com/nidelson/bmad-module-pulse). This module keeps only
`/bmad-bcp-setup`, rewritten as the migration path, and the repository is
archived — archived rather than deleted, because its issues and pull requests
are the record of how the ruler was frozen and the baseline calibrated.

### Nothing about your data changes

The BCP ruler, `bcp-baseline.yaml`, and the `bcp.*` frontmatter block are
byte-for-byte what they were. The skills moved; the schema did not. There is no
conversion step, nothing to re-score, and no version bump to the frontmatter
contract.

### What to do

1. Install PULSE and run `/bmad-pulse-setup`, answering `bcp` when it asks for
   the estimation method. That is the switch — scoring is opt-in and stays that
   way.
2. Run `/bmad-bcp-setup` here one last time. It moves the `bcp_*` keys and
   verifies the baseline survived.
3. Uninstall this module and drop `[modules.bcp]` from `_bmad/config.toml`.

### The step that is easy to miss

The `bcp_*` settings live under `[modules.bcp]`, a table **this** module's
`module.yaml` produces. Uninstalling deletes it.

PULSE reads `[modules.pulse]` first and falls back to `[modules.bcp]`, so
nothing breaks the moment PULSE arrives — but that fallback lasts exactly as
long as this module does. Resolution does not fail when the table disappears;
it returns built-in defaults and reports success. A project that calibrated
`bcp_baseline_seed` or `bcp_reference_h_per_bcp` and then lost them gets
plausible numbers that describe nobody.

Check with the `sources` map before uninstalling:

```bash
python3 .claude/skills/bmad-bcp-score/scripts/bcp_config.py --project-root .
```

Every key should read `modules.pulse`, or `default` for keys you never
configured. Anything still reading `modules.bcp` is a key you are about to lose.

### Do not re-seed the baseline

`/bmad-pulse-setup` creates `bcp-baseline.yaml` only when none exists and
reports `skipped_exists` otherwise. Do not pass `--force` to `seed_baseline.py`
on a migration: it replaces measured per-category rates with the cold-start seed
and reports success.

### Why the skills were removed instead of pointing at PULSE

Skill names are one global namespace. `_bmad/_config/skill-manifest.csv` holds
one row per skill name with one owning module, and installed skills land in
`.claude/skills/<name>/` — one directory per name, last writer wins.

Both modules ship `bmad-bcp-score`, `bmad-bcp-rule-card` and the rest. Had this
module kept those directories as notices saying "moved to PULSE", installing or
reinstalling it after PULSE would have overwritten PULSE's working skills with
the notices. Archived repositories stay cloneable, so this module stays
installable — the redirect would have caused the outage it was meant to prevent,
indefinitely. Removing the directories is what makes both modules safe to have
installed at the same time.

---

## toml-first config — `config.toml` with per-key `config.yaml` fallback (issue #36)

**Who this affects:** installs on post-#2285 BMAD, where the canonical config is
`_bmad/config.toml` (resolved by `_bmad/scripts/resolve_config.py` across four
layers — `config.toml` + `config.user.toml` + `custom/config.toml` +
`custom/config.user.toml`) and `_bmad/config.yaml` is a legacy bridge. Before
this change BCP read/wrote **only** the yaml, so it never saw `config.toml` nor
the `custom/config.toml` overrides — a split-brain where the values diverged and
BCP stayed on the legacy file.

**What changed:**

- **The engine resolves toml-first.** `apply_score.py` and the config-reading
  workflows/agent (`bmad-bcp-score`, `bmad-bcp-rescore`, `bmad-bcp-agent-bruno`)
  now resolve `bcp_*` through a small helper, `bcp_config.py`. It runs the core
  `resolve_config.py --key modules.bcp` (so `custom/config.toml` overrides win),
  **falls back per key** to the legacy `bcp:` section of `config.yaml`, and uses
  the `module.yaml` default only when neither has the key. The sprint-status
  token chain (`output_folder` + the sister PULSE module keys) is resolved the
  same toml-first way.
- **Setup writes toml.** `merge-config.py` writes the module section to
  `_bmad/custom/config.toml` under `[modules.bcp]` (the layer that wins over the
  installer defaults), preserving that file's comments and other sections via
  `tomlkit`. It no longer writes the `bcp:` section into `config.yaml` and
  **strips** a stale one on run.

**⚠ Caveat crítico (leitura + escrita andam juntas).** The `[modules.bcp]` in
`config.toml` on a post-#2285 install carries the *install defaults*. A team
that had pinned custom values (custom taxonomy, a governance-set
`bcp_reference_h_per_bcp`, non-default thresholds) only in the legacy
`config.yaml` `bcp:` section keeps working during the transition — the per-key
yaml fallback still reads those. But to make the values durable and visible to
the core resolver, re-run setup so they land in `custom/config.toml`.

**How to migrate (re-run setup):** re-running `/bmad-bcp-setup` is the
migration. It reads the current effective values (resolved toml, then the legacy
`bcp:` in `config.yaml`) and offers them as the prompt defaults; accepting the
defaults pins the team's answers into `custom/config.toml [modules.bcp]` and
strips the legacy yaml section. Verify `bcp_reference_h_per_bcp` and your
thresholds in `custom/config.toml` after migrating.

**Backward compatibility.** No re-run is *required* for correctness: with no
`config.toml` present (pure legacy install) or on a Python that predates 3.11,
the toml layer resolves to empty and the yaml fallback + module defaults keep
every consumer working exactly as before. The split-brain is only resolved once
you re-run setup and the values live in the toml layer.
