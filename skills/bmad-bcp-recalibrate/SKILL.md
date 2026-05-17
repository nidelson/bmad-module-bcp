---
name: bmad-bcp-recalibrate
description: Recalibra o baseline BCP por categoria com horas reais. Use quando o usuário pedir 'recalibrar baseline', 'recalibrate', 'atualizar h por BCP' ou após stories concluídas com horas reais.
---

# BCP — Recalibrate

## Overview

Atualiza o `bcp-baseline.yaml` por categoria a partir de **horas reais**: cada amostra `(categoria, bcp_total, actual_hours)` produz um `h_per_bcp` observado (`actual_hours / bcp_total`); o baseline guarda uma janela FIFO por categoria e o `h_per_bcp` vira a média da janela. Uma categoria **sai do seed** (`is_seed: false`) ao acumular `min_samples` amostras — só então o `bmad-bcp-score` passa a derivar horas pelo fator do time em vez do seed 4.13.

**Não-negociável — funciona sem PULSE:** a fonte de `actual_hours` é agnóstica. Lê `pulse_metrics.actual_hours` da story **se existir** (convenção de arquivo, zero cross-awareness) **ou** aceita `--actual-hours` manual. O script nunca importa, exige ou checa PULSE — `actual_hours` é só um número.

O determinístico vive em `scripts/recalibrate.py` (média de janela, dedup por id, ordem cronológica, flip de `is_seed`, snapshot em `history`). Idempotente: amostra com `id` já aplicado é pulada.

## Conventions

- Bare paths resolvem da skill root (`scripts/`).
- `{project-root}`-prefixed paths resolvem da raiz do projeto.

## On Activation

1. **Baseline:** `bcp.bcp_baseline_path` da config, ou `{project-root}/_bmad-output/implementation-artifacts/bcp-baseline.yaml`. Ausente → pare e oriente `/bmad-bcp-setup` (semeia o baseline).
2. **Fonte das horas reais** (em ordem de preferência):
   - Usuário passou `--actual-hours N` + uma story → amostra única manual.
   - Story tem `pulse_metrics.actual_hours` (PULSE instalado e rodou) → leitura por convenção.
   - Lote: monte um JSON de amostras `[{category, bcp_total, actual_hours, id?, at?}]` a partir de várias stories concluídas (cada story precisa ter `bcp.total`).
   - Nenhuma fonte → peça as horas reais ao usuário; **não invente**.

## Recalibrate

Prefira **preview** primeiro:

```bash
python3 scripts/recalibrate.py --baseline "{baseline-path}" \
  --story "{story-abs-path}" [--actual-hours N] [--category X] --dry-run
```

ou em lote:

```bash
python3 scripts/recalibrate.py --baseline "{baseline-path}" \
  --samples {tmp-samples.json} --dry-run
```

Apresente em PT-BR, por categoria: `h_per_bcp` antigo → novo, `n_samples`, flip de `is_seed` (cego → calibrado), amostras puladas por dedup. Em ordem cronológica (campo `at`; default = `bcp.scored_at`).

Após confirmação (ou direto se o usuário pediu não-interativo), rode **sem** `--dry-run` para persistir. Exit não-zero: mostre o erro verbatim e pare.

## Confirm

Resuma: categorias afetadas com `h_per_bcp` antigo→novo, quais saíram do seed (`is_seed: true→false`), total de amostras aplicadas vs puladas. Lembre que `recalibrate` **não** muda o `bcp.total` de stories já pontuadas — só o fator; re-derivar horas de stories antigas exige `bmad-bcp-rescore`.

## Design Notes

- **Sem PULSE acoplado:** `actual_hours` é lido como chave de frontmatter por convenção; ausência sem PULSE é esperada e tratada (cai no `--actual-hours`). BCP nunca escreve `pulse_metrics`.
- **Cold-start protegido:** enquanto `n_samples < min_samples` a categoria fica `is_seed: true` e o `bmad-bcp-score` ignora o `h_per_bcp` calculado (usa o seed) — evita confiar em média de poucas amostras.
- **Idempotência:** dedup por `id` (story_id/scored_at) em `samples` e `history.last_id`. `bmad-bcp-backfill-baseline` (Fase 2) encadeia `score-batch` + esta skill contando com isso.
- `history` por categoria mantém snapshot por execução (cap 50, FIFO) — trilha de auditoria da evolução do fator.
- Janela FIFO = `config_snapshot.rolling_window`; `min_samples` e `seed` também do snapshot (gravados pelo `bmad-bcp-setup`).
