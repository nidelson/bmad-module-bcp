# BCP — Business Complexity Points Scorer

[![BMAD Module](https://img.shields.io/badge/BMAD-Module-blue)](https://docs.bmad-method.org/)
[![BMAD Version](https://img.shields.io/badge/BMAD-%3E%3D6.6.0-blue)](https://docs.bmad-method.org/)
[![GitHub release](https://img.shields.io/github/v/release/nidelson/bmad-module-bcp)](https://github.com/nidelson/bmad-module-bcp/releases)
[![Module: MIT](https://img.shields.io/badge/Module-MIT-yellow.svg)](LICENSE)
[![Rule: CC BY-NC-ND 4.0](https://img.shields.io/badge/BCP%20Rule-CC%20BY--NC--ND%204.0-lightgrey.svg)](ATTRIBUTION.md)

> **Estimate by complexity, not by gut.**

Score every BMAD story with CI&T's Business Complexity Points framework and let
`estimated_hours` fall out of the score. Sibling to the
[PULSE](https://github.com/nidelson/bmad-module-pulse) efficiency module —
loosely coupled, schema-mediated, graceful degradation.

## 🇧🇷 Full documentation is in Portuguese

This module's canonical manual is the default **[README.md](README.md)**
(Portuguese) — install guide, skills, baseline/recalibration, configuration,
and the BCP↔PULSE contract all live there. This English file is a minimal
shell by design; see [ADR 0001](docs/ADR/0001-localization-strategy.md) for
the localization policy.

## Quick start

```bash
npx bmad-method install --custom-source github:nidelson/bmad-module-bcp
```

Requires BMAD ≥ 6.6.0 and Python 3.11+. Then run `/bmad-bcp-setup` inside the
project. Eight skills ship (`setup`, `rule-card`, `score`, `score-batch`,
`rescore`, `recalibrate`, `backfill-baseline`, `agent-bruno`) — full table in
the [PT-BR manual](README.md#skills-inclusas).

## License

Intentional, load-bearing split: module code is **MIT** ([LICENSE](LICENSE));
the embedded CI&T BCP rule
(`skills/bmad-bcp-rule-card/assets/bcp-rule.yaml`) is a separate work licensed
**CC BY-NC-ND 4.0** — attribution is a prerequisite of use, not a footnote.
See **[ATTRIBUTION.md](ATTRIBUTION.md)**.
