# BCP Migration Guide

Per-release upgrade notes. Newest first. Each section is self-contained;
skip to the version you are migrating from.

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
