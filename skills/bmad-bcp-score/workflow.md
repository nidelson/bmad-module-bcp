# BCP — Score

## Overview

Pontua **uma** story pelo framework Business Complexity Points e deriva `estimated_hours` a partir do score × baseline por categoria, gravando um bloco `bcp.*` auditável no frontmatter. É o coração do loop BCP.

Divisão de responsabilidade: o **LLM faz o julgamento** (escolher tamanho por elemento via régua); o **script `scripts/apply_score.py` faz o determinístico** (total, derivação de horas, preservação de auditoria, history, advisory de delta, validação de invariantes, escrita idempotente).

**Não-negociáveis:**
- **Non-interactive por padrão** acima do threshold de confiança. Dry-run review **apenas** em: divergência material com a estimativa da Amelia, baixa confiança, ou rescore.
- **Nunca** escreve `pulse_metrics` (PULSE é dono). Toda chave não-BCP do frontmatter é preservada verbatim.
- Auditoria: `estimated_hours_pre_bcp` gravado **uma única vez** (original da Amelia); `estimated_hours_basis: bcp`.

## Conventions

- Bare paths resolvem da skill root (`references/`, `scripts/`, `assets/`).
- `{skill-root}` resolve o diretório instalado desta skill (onde vive `customize.toml`).
- `{project-root}`-prefixed paths resolvem da raiz do projeto.

## On Activation

1. **Resolver customização do workflow:** rode `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. Guarde `activation_steps_prepend`, `activation_steps_append`, `persistent_facts` e `on_complete` para os passos posteriores. Se o script falhar, resolva o bloco `workflow` lendo `{skill-root}/customize.toml` + os overrides team/user em `{project-root}/_bmad/custom/bmad-bcp-score.{toml,user.toml}` (escalares: override vence; arrays: append).
2. **Prepend steps:** execute cada entrada de `workflow.activation_steps_prepend` em ordem.
3. **Persistent facts:** trate cada entrada de `workflow.persistent_facts` como contexto fundacional pela sessão toda. Entradas com prefixo `file:` carregam o conteúdo do path/glob sob `{project-root}`; demais são fatos verbatim.
4. **Story alvo:** caminho passado como argumento, ou a story in-progress do contexto.
5. **Régua:** `{project-root}/.claude/skills/bmad-bcp-rule-card/assets/bcp-rule.yaml` (fonte única imutável; não duplicar — ND). Se ausente: pare e informe que o módulo BCP não está instalado (`/bmad-bcp-setup`).
6. **Baseline:** `{project-root}/_bmad-output/implementation-artifacts/bcp-baseline.yaml` (ou `bcp.bcp_baseline_path` da config). Se ausente: pare e oriente rodar `/bmad-bcp-setup` (semeia o baseline).
7. **Config:** leia a seção `bcp` de `{project-root}/_bmad/config.yaml`: `bcp_confidence_threshold` (default 0.75), `bcp_non_interactive_default` (default yes), `bcp_overwrite_estimated_hours` (consentimento — se `no`, não sobrescreva `estimated_hours`: apenas anexe o bloco `bcp.*` e informe), `bcp_reference_h_per_bcp` (reference rate frozen para a âncora de alavancagem — se ausente, o script usa o seed; **nunca** o fator recalibrado). Sem config → defaults + siga (módulo pode não ter rodado setup).
8. **Append steps:** execute cada entrada de `workflow.activation_steps_append` em ordem.

## Auto-Score

Carregue `references/auto-score.md` e siga o template: leia a story + a régua resolvida, decida presença/tamanho por elemento, e produza o JSON estrito (`breakdown`, `confidence`, `divergence_with_agent_estimate`, `rationale_summary`). Grave esse JSON num arquivo temporário.

`scored_by`: `retroactive` se a story já foi entregue/é histórica; `rescore` se já existe bloco `bcp.*` e o usuário pede repontuar; `bruno` se invocado via agente Bruno; senão `manual`.

## Decide Review Mode

**Dry-run review** (interativo) se **qualquer**: `confidence` < `bcp_confidence_threshold`; `divergence_with_agent_estimate` true; é rescore (bloco `bcp.*` já existe); ou `bcp_non_interactive_default` = `no`.

Caso contrário: **non-interactive** — aplique direto.

## Apply

Sempre rode primeiro em modo preview para validar invariantes:

```bash
python3 scripts/apply_score.py --story "{story-path}" --breakdown {tmp-breakdown.json} --baseline "{baseline-path}" --rule "{rule-path}" --scored-by {scored_by} [--reference-h-per-bcp {bcp_reference_h_per_bcp}] [--rescore] --dry-run
```

Passe `--reference-h-per-bcp` **apenas** quando `bcp_reference_h_per_bcp` estiver configurado (passo 7); omita-o quando ausente — o script cai no seed automaticamente. Nunca derive esse valor do baseline recalibrado.

- **Non-interactive:** se o dry-run sai 0, rode de novo **sem** `--dry-run` para gravar.
- **Dry-run review:** apresente ao usuário o preview (total, `estimated_hours`, fonte do `h_per_bcp`, `estimated_hours_pre_bcp`, breakdown, advisories). Só grave (rerun sem `--dry-run`) após confirmação explícita. Em rescore, passe `--rescore` (arquiva o bloco anterior em `bcp.history`, FIFO cap 50).

Exit não-zero: mostre o erro verbatim e pare (1=validação, 2=runtime, 3=conflito).

## Surface Advisories

Se `result.advisories` não vazio (delta >50% num rescore, drift cumulativo >2×, ou truncate de history), repasse ao usuário em PT-BR — inclui a sugestão "considere split em sub-story". Advisory **não bloqueia**; é orientação.

## Confirm

Resuma: total BCP, `estimated_hours` derivado (e `estimated_hours_pre_bcp` preservado), fonte do `h_per_bcp` (`seed` vs `baseline:<categoria>`), `estimated_hours_reference` derivado + `reference_source` (`seed` vs `config`), `scored_by`, tamanho de `bcp.history`. Confirme que `pulse_metrics` e demais chaves ficaram intactas.

## On Completion

Após o Confirm (e depois que o bloco `bcp.*` foi persistido na execução sem `--dry-run`), siga `workflow.on_complete` resolvido na ativação:

- Valor **vazio** (default) → encerre sem ação adicional.
- Valor **não-vazio** → siga a string verbatim como instrução terminal — é o último passo antes de sair.

**Invariantes (sempre verdade — qualquer override precisa respeitar):**

- O hook roda **após** persistência — o frontmatter da story já reflete o novo bloco `bcp.*`.
- O hook **NÃO pode mutar** o frontmatter da story (single-writer principle — só `apply_score.py` escreve `bcp.*`).
- Erro no hook é **warn**, não rollback — o score já foi gravado.
- Em execução `--dry-run` (sem persistência) o hook é **pulado**.

Customizar override (team-level, committed): edite `{project-root}/_bmad/custom/bmad-bcp-score.toml`. User-level (gitignored): `bmad-bcp-score.user.toml`.

## Design Notes

- A régua é lida da skill `bmad-bcp-rule-card` instalada — fonte única, evita drift e respeita o ND da licença (sem cópia).
- O script preserva o corpo da story verbatim; só re-serializa o mapa de frontmatter (chaves não-BCP mantidas, ordem preservada).
- Idempotência: re-rodar o mesmo breakdown sem `--rescore` não re-sobrescreve `estimated_hours_pre_bcp` nem polui `history`.
- `bcp-frontmatter.schema.yaml` (em `assets/`) documenta o contrato; o script valida os invariantes em código (sem dependência extra de jsonschema).
- **Três números h/BCP (issue #32):** *seed* (cold-start) e *recalibrado* (fator vivo por categoria) derivam o **plano** (`estimated_hours`) → previsibilidade. A *reference rate* frozen (`bcp_reference_h_per_bcp`) deriva a **âncora** (`estimated_hours_reference`) → alavancagem estável que não colapsa. O script é dono de toda conversão BCP→horas (single-writer); o PULSE só **lê** os campos. A reference rate muda só por **governança** (config durável + ledger, forward-only) — `recalibrate` nunca a toca. Procedimento completo no README.
- **Customization surface:** `customize.toml` segue o padrão BMad — três camadas (skill defaults < team `<project>/_bmad/custom/*.toml` < user `*.user.toml`) resolvidas por `_bmad/scripts/resolve_customization.py`. `on_complete` é o extension point para encadear ações pós-persistência sem fork da skill.
