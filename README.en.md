# BCP — Business Complexity Points Scorer

[![BMAD Module](https://img.shields.io/badge/BMAD-Module-blue)](https://docs.bmad-method.org/)
[![BMAD Version](https://img.shields.io/badge/BMAD-%3E%3D6.6.0-blue)](https://docs.bmad-method.org/)
[![GitHub release](https://img.shields.io/github/v/release/nidelson/bmad-module-bcp)](https://github.com/nidelson/bmad-module-bcp/releases)
[![Module: MIT](https://img.shields.io/badge/Module-MIT-yellow.svg)](LICENSE)
[![Rule: MIT](https://img.shields.io/badge/BCP%20Rule-MIT-yellow.svg)](ATTRIBUTION.md)

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
**MIT** since May 2026 ([flow-ciandt/bcp-agent](https://github.com/flow-ciandt/bcp-agent)); it previously circulated under CC BY-NC-ND 4.0. Module code and embedded rule now share the same license.
See **[ATTRIBUTION.md](ATTRIBUTION.md)**.
