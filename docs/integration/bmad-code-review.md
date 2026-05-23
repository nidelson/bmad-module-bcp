# Integração BCP ↔ bmad-code-review

> Documento canônico em PT-BR ([ADR 0001](../ADR/0001-localization-strategy.md)).
> Identificadores de skill/campo são EN.

## O que é este hook

`bmad-code-review` é o workflow do BMAD que executa o code review adversarial
de uma story. O BCP se anexa ao `on_complete` deste workflow para **disparar
o recalibrate do baseline automaticamente** ao fim de cada review — sem passo
manual.

Resultado: toda story revisada com `bcp.total` e `actual_hours` disponíveis
contribui automaticamente para a calibração do `h_per_bcp` por categoria.

## Como o `setup` registra o hook

`/bmad-bcp-setup` chama `inject_customize.py --skill bmad-code-review` em
**modo merge** — o template BCP é acrescentado ao `on_complete` existente sem
sobrescrever o arquivo. Se o PULSE já registrou o seu `on_complete`
(track-done), ambas as instruções coexistem em sequência no mesmo campo.

Template gerado:
[`assets/customize-templates/bmad-code-review.toml`](../../skills/bmad-bcp-setup/assets/customize-templates/bmad-code-review.toml).

Re-rodar `/bmad-bcp-setup` é **idempotente** neste hook: se a instrução BCP já
está presente, o script retorna exit 1 (already-present) sem modificar o
arquivo.

## O que o hook instrui o agente a fazer

A instrução no `on_complete` diz ao agente: **somente após** todas as
instruções anteriores do on_complete completarem (incluindo o PULSE
track-done e a gravação de `actual_hours`), verificar se a story tem
`bcp.total` no frontmatter. Se sim, ler `actual_hours` da seção
`pulse_metrics` do sprint-status e invocar `bmad-bcp-recalibrate`.

Condições para o recalibrate rodar:

| Condição | Comportamento |
| --- | --- |
| `bcp.total` presente + `actual_hours` gravado pelo PULSE | Recalibra — sample adicionada ao baseline |
| `bcp.total` presente + `actual_hours` ausente | Skip silencioso (PULSE não rodou ou story sem tracking) |
| `bcp.total` ausente | Skip silencioso (story não pontuada pelo BCP) |

A recalibração é **idempotente** — `recalibrate.py` deduplica amostras por
`id` da story. Re-rodar o code review na mesma story não duplica o sample.

## Sequenciamento com o PULSE

A instrução BCP é explicitamente marcada como **execute SOMENTE APÓS** todas
as instruções anteriores do on_complete. Isso garante que o PULSE track-done
(interativo — pede `review_cycles` e `actual_hours` ao usuário) complete e
grave os dados **antes** de o BCP tentar lê-los.

Sem essa garantia, o BCP poderia tentar ler `actual_hours` antes de o PULSE
gravá-lo e silenciosamente skipparia a calibração.

## Auto-detecção do sprint-status

O recalibrate recebe `--project-root` (não `--sprint-status` explícito). O
script `apply_score.py` resolve o caminho do sprint-status internamente via
cadeia de tokens do `_bmad/config.yaml`:

```
output_folder → pulse.pulse_data_folder → pulse_sprint_status_filename
```

Ver [auto-detecção no pulse.md](./pulse.md#auto-detecção-do-sprint-status-issue-25).

## Histórico de rescores no sprint-status

Quando o recalibrate roda, o histórico de rescores da story vai para
`bcp_metrics[story_key].history` no sprint-status — não para o frontmatter.
Ver [separação spec/operacional no pulse.md](./pulse.md#separação-spec-vs-operacional-issue-19).

## Editar ou desabilitar

Para desabilitar o auto-recalibrate sem afetar o track-done do PULSE, remova
apenas a instrução BCP do `on_complete` em
`_bmad/custom/bmad-code-review.toml`. O arquivo pode coexistir com apenas a
instrução do PULSE.
