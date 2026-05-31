# BCP — Backfill Baseline

## Overview

Encadeia **`score-batch` → coleta de samples → `recalibrate`** para matar o cold-start: um squad que instala o BCP com stories já entregues sai do seed (4.13) no dia um, com `h_per_bcp` por categoria fiel ao histórico real.

Skill de **orquestração**. Não duplica lógica: delega o scoring retroativo ao `bmad-bcp-score-batch` instalado e a recalibração ao `bmad-bcp-recalibrate` instalado; o único determinístico próprio é `scripts/collect_samples.py` (ponte: stories pontuadas → samples JSON, com `id` estável que garante idempotência).

## Conventions

- Bare paths resolvem da skill root (`scripts/`).
- `{skill-root}` resolve o diretório instalado desta skill (onde vive `customize.toml`).
- `{project-root}`-prefixed paths resolvem da raiz do projeto.

## On Activation

1. **Resolver customização do workflow:** rode `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. Guarde `activation_steps_prepend`, `activation_steps_append`, `persistent_facts` e `on_complete` para os passos posteriores. Se o script falhar, resolva o bloco `workflow` lendo `{skill-root}/customize.toml` + os overrides team/user em `{project-root}/_bmad/custom/bmad-bcp-backfill-baseline.{toml,user.toml}` (escalares: override vence; arrays: append).
2. **Prepend steps:** execute cada entrada de `workflow.activation_steps_prepend` em ordem.
3. **Persistent facts:** trate cada entrada de `workflow.persistent_facts` como contexto fundacional pela sessão toda. Entradas com prefixo `file:` carregam o conteúdo do path/glob sob `{project-root}`; demais são fatos verbatim.
4. **Glob do histórico:** stories já entregues (ex.: `docs/stories/**/*.md`). Sem argumento → peça.
5. **Dependências (Fase 1+2 instaladas):**
   - `{project-root}/.claude/skills/bmad-bcp-score-batch/scripts/batch_plan.py`
   - `{project-root}/.claude/skills/bmad-bcp-score/scripts/apply_score.py` + `references/auto-score.md`
   - `{project-root}/.claude/skills/bmad-bcp-rule-card/assets/bcp-rule.yaml`
   - `{project-root}/.claude/skills/bmad-bcp-recalibrate/scripts/recalibrate.py`
   - Baseline: `bcp.bcp_baseline_path` ou `{project-root}/_bmad-output/implementation-artifacts/bcp-baseline.yaml`
   - Ausente → pare e oriente `/bmad-bcp-setup` (e instalar as skills da Fase 1/2).
6. **Fonte de horas reais:** `pulse_metrics.actual_hours` nas stories (PULSE rodou) **ou** um JSON `{story_id: horas}` fornecido pelo usuário (`--actual-hours-map`) — backfill **sem PULSE**. Sem nenhuma → peça ao usuário; não invente horas.
7. **Append steps:** execute cada entrada de `workflow.activation_steps_append` em ordem.

## Step 1 — Score Batch (retroativo)

Siga o fluxo do `bmad-bcp-score-batch` sobre o glob (scoring `retroactive`). Idempotente: stories já com `bcp.*` são puladas. Ao fim, as stories do histórico têm `bcp.total`.

## Step 2 — Collect Samples

```bash
python3 scripts/collect_samples.py --project-root "{project-root}" \
  --glob "{glob}" [--actual-hours-map {tmp-hours.json}] \
  --out {tmp-samples.json}
```

Reporte `collected` vs `skipped` (com motivos: sem `bcp.total`, sem `actual_hours`, sem `category`). Stories puladas não entram no baseline — informe o usuário quais e por quê (ele pode completar o mapa de horas e re-rodar).

## Step 3 — Recalibrate

Preview primeiro:

```bash
python3 "{project-root}/.claude/skills/bmad-bcp-recalibrate/scripts/recalibrate.py" \
  --baseline "{baseline-path}" --samples {tmp-samples.json} --dry-run
```

Apresente por categoria: `h_per_bcp` antigo → novo, `n_samples`, flip `is_seed` (cego → calibrado). Após confirmação (ou direto se não-interativo), repita **sem** `--dry-run`.

## Idempotência

Re-rodar o backfill **não corrompe** o baseline:
- `score-batch` pula stories já pontuadas (sem `--rescore`).
- `collect_samples.py` emite `id` estável (`story_id`/stem).
- `recalibrate.py` deduplica por `id` (em `samples` e `history.last_id`) → samples já aplicados são pulados.

Logo, backfill é seguro para re-execução parcial (ex.: completar horas faltantes e rodar de novo só processa o delta).

## Confirm

Resuma: stories pontuadas no batch, samples coletadas vs puladas (motivos), categorias que saíram do seed (`is_seed: true→false`) com `h_per_bcp` resultante. Lembre que stories pontuadas no batch ficaram com `estimated_hours` derivado do **seed** (cego no momento do score); para re-derivar com o novo fator calibrado use `bmad-bcp-rescore` nas que importam.

## On Completion

Após o Confirm (e depois que `bcp-baseline.yaml` foi persistido na execução sem `--dry-run` do Step 3), siga `workflow.on_complete` resolvido na ativação:

- Valor **vazio** (default) → encerre sem ação adicional.
- Valor **não-vazio** → siga a string verbatim como instrução terminal — é o último passo antes de sair.

**Invariantes (sempre verdade — qualquer override precisa respeitar):**

- O hook roda **após** persistência — stories pontuadas estão no disco E `bcp-baseline.yaml` reflete a calibração.
- O hook **NÃO pode mutar** o frontmatter de stories nem `bcp-baseline.yaml` (single-writer principle).
- Erro no hook é **warn**, não rollback — backfill já gravou.
- Em `--dry-run` (sem persistência do baseline) o hook é **pulado**.

Customizar override (team-level, committed): edite `{project-root}/_bmad/custom/bmad-bcp-backfill-baseline.toml`. User-level (gitignored): `bmad-bcp-backfill-baseline.user.toml`.

## Design Notes

- **Zero duplicação:** orquestra skills instaladas (`score-batch`, `recalibrate`) + régua só no `rule-card` (respeita ND). Próprio só a ponte `collect_samples.py`.
- **Sem PULSE:** `--actual-hours-map` cobre o caso PULSE-ausente; `pulse_metrics.actual_hours` é lido por convenção quando presente.
- **Resiliente/parcial:** stories sem horas são puladas e reportadas, não bloqueiam o resto; completar e re-rodar processa só o delta (idempotência).
- Ordem cronológica da recalibração é garantida pelo `recalibrate.py` (campo `at` = `bcp.scored_at`).
- **Customization surface:** `customize.toml` segue o padrão BMad — três camadas (skill defaults < team `<project>/_bmad/custom/*.toml` < user `*.user.toml`) resolvidas por `_bmad/scripts/resolve_customization.py`. `on_complete` é o extension point para encadear ações pós-backfill sem fork da skill.
