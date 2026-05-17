---
name: bmad-bcp-score-batch
description: Pontua várias stories existentes em lote (scoring retroativo). Use quando o usuário pedir 'pontuar stories em lote', 'score-batch', 'bcp retroativo' ou 'pontuar o histórico de stories'.
---

# BCP — Score Batch (retroativo)

## Overview

Pontua **múltiplas** stories existentes pelo framework BCP com `bcp.scored_by: retroactive`. É a base do scoring retroativo de primeira classe: um squad com histórico instala o módulo e sai do cold start no dia um (alimenta o `backfill-baseline` na Fase 2).

Orquestração: o **LLM faz o julgamento por story** (auto-score, mesmo template do `bmad-bcp-score`); os **scripts fazem o determinístico** — `scripts/batch_plan.py` resolve/classifica/estima custo, e o `apply_score.py` do `bmad-bcp-score` instalado aplica cada score (não duplicado — fonte única).

## Conventions

- Bare paths resolvem da skill root (`scripts/`).
- `{project-root}`-prefixed paths resolvem da raiz do projeto.

## On Activation

1. **Glob alvo:** argumento do usuário (ex.: `docs/stories/*.md`). Sem argumento → peça.
2. **Dependências (Fase 1 instalada):**
   - Régua: `{project-root}/.claude/skills/bmad-bcp-rule-card/assets/bcp-rule.yaml`
   - Engine: `{project-root}/.claude/skills/bmad-bcp-score/scripts/apply_score.py`
   - Template: `{project-root}/.claude/skills/bmad-bcp-score/references/auto-score.md`
   - Baseline: `{project-root}/_bmad-output/implementation-artifacts/bcp-baseline.yaml`
   - Qualquer ausente → pare e oriente rodar `/bmad-bcp-setup` (e que `bmad-bcp-score`/`bmad-bcp-rule-card` estejam instalados).

## Plan

```bash
python3 scripts/batch_plan.py --project-root "{project-root}" --glob "{glob}" [--rescore]
```

Sem `--rescore`, stories que já têm bloco `bcp.*` são classificadas `already_scored` e **não** entram no lote (idempotência — re-rodar não repontua). Saída lista `stories[]` + `cost_estimate`.

## Dry-Run Cost

Se o usuário pediu `--dry-run-cost` (ou o lote é grande): apresente `cost_estimate` em PT-BR, deixando claro que é **estimativa de ordem de grandeza**, não cobrança real. Peça confirmação antes de rodar o lote. Sem `--dry-run-cost` e lote pequeno: pode seguir direto.

## Execute Batch

Para cada story com `selected: true` no plano:

1. **Auto-score** — siga o template `references/auto-score.md` do `bmad-bcp-score` instalado: leia a story + a régua resolvida, produza o JSON estrito (`breakdown`, `confidence`, …). Grave num arquivo temporário.
2. **Aplique (determinístico):** resolva o caminho absoluto da story juntando `{project-root}` com o campo `path` do plano (que já é relativo à raiz). Chame:

   ```bash
   python3 "{project-root}/.claude/skills/bmad-bcp-score/scripts/apply_score.py" \
     --story "{story-abs-path}" --breakdown {tmp-breakdown.json} \
     --baseline "{baseline-path}" --rule "{rule-path}" --scored-by retroactive
   ```

   `scored_by` é **sempre `retroactive`** neste fluxo (distingue de `manual`/`bruno`/`rescore`). Não use `--rescore` aqui salvo se o usuário pediu repontuar explicitamente (aí passe `--rescore` e o plano com `--rescore`).
3. Exit não-zero numa story: registre a falha, **não aborte o lote** — continue as demais e reporte no fim.

Em lote grande, processe incrementalmente e vá reportando progresso (N/total) para sobreviver a compactação de contexto.

## Aggregate Report

Ao final, resuma em PT-BR: total de stories no lote, pontuadas com sucesso, puladas (`already_scored`), falhas (com motivo), soma de `bcp.total`, e nota de que o baseline ainda não muda — `recalibrate`/`backfill-baseline` (Fase 2) é que ajustam `h_per_bcp` com horas reais.

## Design Notes

- **Fonte única:** reusa `apply_score.py` e o template do `bmad-bcp-score` instalado — zero duplicação (consistência + respeita o ND da régua, que mora só no `bmad-bcp-rule-card`).
- **Idempotente por padrão:** sem `--rescore`, stories já pontuadas são puladas; re-rodar o lote é seguro.
- **Não bloqueante:** falha numa story não derruba o lote (scoring retroativo de histórico grande precisa ser resiliente).
- Estimativa de custo é heurística declarada (não telemetria real) — só ordem de grandeza para decisão de seguir.
