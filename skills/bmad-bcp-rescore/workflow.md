# BCP — Rescore

## Overview

Repontua **uma** story que já tem bloco `bcp.*`, recalculando o total, arquivando o score anterior em `bcp.history` (FIFO, cap 50) e re-derivando `estimated_hours`, sempre preservando a trilha de auditoria. Usado após mudança de escopo da story ou quando a régua/entendimento evolui.

Skill **fina e sem scripts**: o determinístico (arquivar history, cap 50 + warn, advisory de delta >50% / drift cumulativo >2×, re-derivação de horas, preservação de auditoria, escrita idempotente) já vive no `apply_score.py` do `bmad-bcp-score` instalado, invocado com `--rescore`. Esta skill formaliza o fluxo de repontuar com **review obrigatório** (rescore nunca é silencioso).

## Conventions

- Bare paths resolvem da skill root.
- `{skill-root}` resolve o diretório instalado desta skill (onde vive `customize.toml`).
- `{project-root}`-prefixed paths resolvem da raiz do projeto.

## On Activation

1. **Resolver customização do workflow:** rode `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. Guarde `activation_steps_prepend`, `activation_steps_append`, `persistent_facts` e `on_complete` para os passos posteriores. Se o script falhar, resolva o bloco `workflow` lendo `{skill-root}/customize.toml` + os overrides team/user em `{project-root}/_bmad/custom/bmad-bcp-rescore.{toml,user.toml}` (escalares: override vence; arrays: append).
2. **Prepend steps:** execute cada entrada de `workflow.activation_steps_prepend` em ordem.
3. **Persistent facts:** trate cada entrada de `workflow.persistent_facts` como contexto fundacional pela sessão toda. Entradas com prefixo `file:` carregam o conteúdo do path/glob sob `{project-root}`; demais são fatos verbatim.
4. **Story alvo:** caminho passado como argumento, ou a story do contexto.
5. **Pré-condição:** a story **deve** ter bloco `bcp.*`. Se não tiver → não é rescore; oriente usar `/bmad-bcp-score` (primeiro score).
6. **Dependências (Fase 1 instalada):**
   - Régua: `{project-root}/.claude/skills/bmad-bcp-rule-card/assets/bcp-rule.yaml`
   - Engine: `{project-root}/.claude/skills/bmad-bcp-score/scripts/apply_score.py`
   - Template: `{project-root}/.claude/skills/bmad-bcp-score/references/auto-score.md`
   - Baseline: `{project-root}/_bmad-output/implementation-artifacts/bcp-baseline.yaml`
   - Ausente → pare e oriente `/bmad-bcp-setup`.
7. **Append steps:** execute cada entrada de `workflow.activation_steps_append` em ordem.

## Re-Score

1. Mostre ao usuário o score atual (`bcp.total`, breakdown, `estimated_hours`) e o motivo do rescore (peça se não informado — vira contexto da nota).
2. **Auto-score** — siga o template `references/auto-score.md` do `bmad-bcp-score` instalado, lendo a story atual + a régua + o bloco `bcp.*` anterior como contexto. Produza o JSON estrito. Grave em arquivo temporário.
3. **Preview obrigatório** (rescore é sempre review-mandatory — não-negociável herdado do `bmad-bcp-score`):

   ```bash
   python3 "{project-root}/.claude/skills/bmad-bcp-score/scripts/apply_score.py" \
     --story "{story-abs-path}" --breakdown {tmp-breakdown.json} \
     --baseline "{baseline-path}" --rule "{rule-path}" \
     --scored-by rescore --rescore [--reference-h-per-bcp {bcp_reference_h_per_bcp}] --dry-run
   ```

   Inclua `--reference-h-per-bcp` **somente** se `bcp_reference_h_per_bcp` estiver na config `bcp` (`_bmad/config.yaml`); omita quando ausente (cai no seed). Passar o mesmo valor no rescore mantém a âncora `estimated_hours_reference` consistente — **nunca** derive-o do baseline recalibrado.

4. Apresente o preview em PT-BR: total antigo → novo, `estimated_hours` antigo → novo, fonte do `h_per_bcp`, `estimated_hours_reference` antigo → novo (âncora frozen), tamanho de `bcp.history` após arquivar, e **todas as `advisories`** (delta >50%, drift cumulativo >2×, truncate de history → "considere split em sub-story").
5. Só após **confirmação explícita**, repita **sem** `--dry-run` para gravar.
6. Exit não-zero: mostre o erro verbatim e pare.

## Surface Advisories

Advisory **não bloqueia** — é orientação. Se o delta sugere split, deixe claro ao usuário que ele pode aceitar mesmo assim; a decisão é dele. `bcp.history` mantém a trilha independentemente.

## Confirm

Resuma: total antigo → novo, `estimated_hours` antigo → novo (e `estimated_hours_pre_bcp` **inalterado** — auditoria do original é imutável após o 1º score), `scored_by: rescore`, nova `history_len`, advisories. Confirme que `pulse_metrics` e chaves não-BCP ficaram intactas.

## On Completion

Após o Confirm (e depois que o novo bloco `bcp.*` foi persistido e o anterior arquivado em `bcp.history` na execução sem `--dry-run`), siga `workflow.on_complete` resolvido na ativação:

- Valor **vazio** (default) → encerre sem ação adicional.
- Valor **não-vazio** → siga a string verbatim como instrução terminal — é o último passo antes de sair.

**Invariantes (sempre verdade — qualquer override precisa respeitar):**

- O hook roda **após** persistência — o frontmatter da story já reflete o novo `bcp.*` e o anterior está em `bcp.history`.
- O hook **NÃO pode mutar** o frontmatter da story (single-writer principle — só `apply_score.py --rescore` escreve `bcp.*` e rotaciona `history`).
- Erro no hook é **warn**, não rollback — o rescore já foi gravado.
- Em execução `--dry-run` (sem persistência) o hook é **pulado**.

Customizar override (team-level, committed): edite `{project-root}/_bmad/custom/bmad-bcp-rescore.toml`. User-level (gitignored): `bmad-bcp-rescore.user.toml`.

## Design Notes

- **Sem duplicação:** reusa `apply_score.py --rescore` e o template do `bmad-bcp-score` instalado; régua só no `bmad-bcp-rule-card` (respeita ND).
- `estimated_hours_pre_bcp` **não** muda em rescore — captura só o original da Amelia, gravado uma única vez no 1º score. Rescore mexe em `estimated_hours`, `bcp.total`, `bcp.history`.
- Idempotência: o engine arquiva o snapshot anterior em `history` a cada `--rescore`; re-rodar com o mesmo breakdown ainda arquiva (é a semântica de rescore — cada invocação é um evento de auditoria). Por isso o review obrigatório evita rescores acidentais.
- **Customization surface:** `customize.toml` segue o padrão BMad — três camadas (skill defaults < team `<project>/_bmad/custom/*.toml` < user `*.user.toml`) resolvidas por `_bmad/scripts/resolve_customization.py`. `on_complete` é o extension point para encadear ações pós-rescore sem fork da skill.
