---
name: bmad-bcp-rescore
description: Repontua uma story já pontuada, atualizando total, history e estimated_hours. Use quando o usuário pedir 'repontuar story', 'rescore', 'atualizar o BCP da story' ou após mudança de escopo.
---

# BCP — Rescore

## Overview

Repontua **uma** story que já tem bloco `bcp.*`, recalculando o total, arquivando o score anterior em `bcp.history` (FIFO, cap 50) e re-derivando `estimated_hours`, sempre preservando a trilha de auditoria. Usado após mudança de escopo da story ou quando a régua/entendimento evolui.

Skill **fina e sem scripts**: o determinístico (arquivar history, cap 50 + warn, advisory de delta >50% / drift cumulativo >2×, re-derivação de horas, preservação de auditoria, escrita idempotente) já vive no `apply_score.py` do `bmad-bcp-score` instalado, invocado com `--rescore`. Esta skill formaliza o fluxo de repontuar com **review obrigatório** (rescore nunca é silencioso).

## Conventions

- Bare paths resolvem da skill root.
- `{project-root}`-prefixed paths resolvem da raiz do projeto.

## On Activation

1. **Story alvo:** caminho passado como argumento, ou a story do contexto.
2. **Pré-condição:** a story **deve** ter bloco `bcp.*`. Se não tiver → não é rescore; oriente usar `/bmad-bcp-score` (primeiro score).
3. **Dependências (Fase 1 instalada):**
   - Régua: `{project-root}/.claude/skills/bmad-bcp-rule-card/assets/bcp-rule.yaml`
   - Engine: `{project-root}/.claude/skills/bmad-bcp-score/scripts/apply_score.py`
   - Template: `{project-root}/.claude/skills/bmad-bcp-score/references/auto-score.md`
   - Baseline: `{project-root}/_bmad-output/implementation-artifacts/bcp-baseline.yaml`
   - Ausente → pare e oriente `/bmad-bcp-setup`.

## Re-Score

1. Mostre ao usuário o score atual (`bcp.total`, breakdown, `estimated_hours`) e o motivo do rescore (peça se não informado — vira contexto da nota).
2. **Auto-score** — siga o template `references/auto-score.md` do `bmad-bcp-score` instalado, lendo a story atual + a régua + o bloco `bcp.*` anterior como contexto. Produza o JSON estrito. Grave em arquivo temporário.
3. **Preview obrigatório** (rescore é sempre review-mandatory — não-negociável herdado do `bmad-bcp-score`):

   ```bash
   python3 "{project-root}/.claude/skills/bmad-bcp-score/scripts/apply_score.py" \
     --story "{story-abs-path}" --breakdown {tmp-breakdown.json} \
     --baseline "{baseline-path}" --rule "{rule-path}" \
     --scored-by rescore --rescore --dry-run
   ```

4. Apresente o preview em PT-BR: total antigo → novo, `estimated_hours` antigo → novo, fonte do `h_per_bcp`, tamanho de `bcp.history` após arquivar, e **todas as `advisories`** (delta >50%, drift cumulativo >2×, truncate de history → "considere split em sub-story").
5. Só após **confirmação explícita**, repita **sem** `--dry-run` para gravar.
6. Exit não-zero: mostre o erro verbatim e pare.

## Surface Advisories

Advisory **não bloqueia** — é orientação. Se o delta sugere split, deixe claro ao usuário que ele pode aceitar mesmo assim; a decisão é dele. `bcp.history` mantém a trilha independentemente.

## Confirm

Resuma: total antigo → novo, `estimated_hours` antigo → novo (e `estimated_hours_pre_bcp` **inalterado** — auditoria do original é imutável após o 1º score), `scored_by: rescore`, nova `history_len`, advisories. Confirme que `pulse_metrics` e chaves não-BCP ficaram intactas.

## Design Notes

- **Sem duplicação:** reusa `apply_score.py --rescore` e o template do `bmad-bcp-score` instalado; régua só no `bmad-bcp-rule-card` (respeita ND).
- `estimated_hours_pre_bcp` **não** muda em rescore — captura só o original da Amelia, gravado uma única vez no 1º score. Rescore mexe em `estimated_hours`, `bcp.total`, `bcp.history`.
- Idempotência: o engine arquiva o snapshot anterior em `history` a cada `--rescore`; re-rodar com o mesmo breakdown ainda arquiva (é a semântica de rescore — cada invocação é um evento de auditoria). Por isso o review obrigatório evita rescores acidentais.
