# BCP — Score Batch (retroativo)

## Overview

Pontua **múltiplas** stories existentes pelo framework BCP com `bcp.scored_by: retroactive`. É a base do scoring retroativo de primeira classe: um squad com histórico instala o módulo e sai do cold start no dia um (alimenta o `backfill-baseline` na Fase 2).

Orquestração: o **LLM faz o julgamento por story** (auto-score, mesmo template do `bmad-bcp-score`); os **scripts fazem o determinístico** — `scripts/batch_plan.py` resolve/classifica/estima custo, e o `apply_score.py` do `bmad-bcp-score` instalado aplica cada score (não duplicado — fonte única).

## Conventions

- Bare paths resolvem da skill root (`scripts/`).
- `{skill-root}` resolve o diretório instalado desta skill (onde vive `customize.toml`).
- `{project-root}`-prefixed paths resolvem da raiz do projeto.

## On Activation

1. **Resolver customização do workflow:** rode `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. Guarde `activation_steps_prepend`, `activation_steps_append`, `persistent_facts` e `on_complete` para os passos posteriores. Se o script falhar, resolva o bloco `workflow` lendo `{skill-root}/customize.toml` + os overrides team/user em `{project-root}/_bmad/custom/bmad-bcp-score-batch.{toml,user.toml}` (escalares: override vence; arrays: append).
2. **Prepend steps:** execute cada entrada de `workflow.activation_steps_prepend` em ordem.
3. **Persistent facts:** trate cada entrada de `workflow.persistent_facts` como contexto fundacional pela sessão toda. Entradas com prefixo `file:` carregam o conteúdo do path/glob sob `{project-root}`; demais são fatos verbatim.
4. **Glob alvo:** argumento do usuário (ex.: `docs/stories/*.md`). Sem argumento → peça.
5. **Dependências (Fase 1 instalada):**
   - Régua: `{project-root}/.claude/skills/bmad-bcp-rule-card/assets/bcp-rule.yaml`
   - Engine: `{project-root}/.claude/skills/bmad-bcp-score/scripts/apply_score.py`
   - Template: `{project-root}/.claude/skills/bmad-bcp-score/references/auto-score.md`
   - Baseline: `{project-root}/_bmad-output/implementation-artifacts/bcp-baseline.yaml`
   - Qualquer ausente → pare e oriente rodar `/bmad-bcp-setup` (e que `bmad-bcp-score`/`bmad-bcp-rule-card` estejam instalados).
6. **Append steps:** execute cada entrada de `workflow.activation_steps_append` em ordem.

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

## On Completion

Após o Aggregate Report (e depois que o lote terminou — sucessos persistidos, falhas reportadas), siga `workflow.on_complete` resolvido na ativação:

- Valor **vazio** (default) → encerre sem ação adicional.
- Valor **não-vazio** → siga a string verbatim como instrução terminal — é o último passo antes de sair.

**Invariantes (sempre verdade — qualquer override precisa respeitar):**

- O hook roda **após** o batch terminar — todas as stories com sucesso já estão persistidas.
- O hook **NÃO pode mutar** o frontmatter de stories (single-writer principle — só `apply_score.py` escreve `bcp.*`).
- O hook **NÃO pode mutar** `bcp-baseline.yaml` (batch não toca no baseline; `recalibrate`/`backfill-baseline` é que ajustam).
- Erro no hook é **warn**, não rollback — scores já gravados.
- Em execução `--dry-run-cost` (sem persistência do lote) o hook é **pulado**.

Customizar override (team-level, committed): edite `{project-root}/_bmad/custom/bmad-bcp-score-batch.toml`. User-level (gitignored): `bmad-bcp-score-batch.user.toml`.

## Design Notes

- **Fonte única:** reusa `apply_score.py` e o template do `bmad-bcp-score` instalado — zero duplicação (consistência + respeita o ND da régua, que mora só no `bmad-bcp-rule-card`).
- **Idempotente por padrão:** sem `--rescore`, stories já pontuadas são puladas; re-rodar o lote é seguro.
- **Não bloqueante:** falha numa story não derruba o lote (scoring retroativo de histórico grande precisa ser resiliente).
- Estimativa de custo é heurística declarada (não telemetria real) — só ordem de grandeza para decisão de seguir.
- **Customization surface:** `customize.toml` segue o padrão BMad — três camadas (skill defaults < team `<project>/_bmad/custom/*.toml` < user `*.user.toml`) resolvidas por `_bmad/scripts/resolve_customization.py`. `on_complete` é o extension point para encadear ações pós-batch sem fork da skill.
