# Integração BCP ↔ PULSE

> Documento canônico em PT-BR ([ADR 0001](../ADR/0001-localization-strategy.md)).
> Chaves de frontmatter/schema são EN (interoperabilidade).

## Princípio: acoplamento frouxo mediado por contrato de dados

BCP e PULSE são dois módulos BMAD irmãos que **não se importam mutuamente**.
Nenhum dos dois faz `import` do outro, nenhum lê o código do outro, nenhum
falha se o outro estiver ausente. Os pontos de contato são dois contratos de
dados complementares: o **frontmatter da story** (spec) e a seção
**`bcp_metrics` do sprint-status** (operacional).

- **BCP** estima: pontua a complexidade e deriva `estimated_hours`.
- **PULSE** mede: compara horas estimadas com horas reais de IA e calcula
  alavancagem.

PULSE lê `estimated_hours` de forma **agnóstica ao escritor**. Tanto faz se
quem escreveu foi a Amelia (agente padrão do BMAD) ou o BCP — PULSE consome o
número e segue. Por isso **nenhum ajuste no PULSE é necessário** para a
integração funcionar.

## Quem escreve o quê

### Frontmatter da story (dados de especificação)

| Chave | BCP | PULSE |
| --- | --- | --- |
| `estimated_hours` | **escreve** (sobrescreve, consentimento via install) | lê (plano → previsibilidade) |
| `estimated_hours_pre_bcp` | **escreve uma única vez** (auditoria) | — |
| `estimated_hours_basis` | **escreve** (`bcp`) | lê (opcional) |
| `estimated_hours_reference` | **escreve** (âncora frozen, issue #32) | lê (âncora → alavancagem estável) |
| `bcp.total`, `bcp.breakdown`, `bcp.scored_by` | **escreve** | lê (opcional) |
| `pulse_metrics` | **nunca toca** | escreve |

### sprint-status.yaml (dados operacionais)

| Chave | BCP | PULSE |
| --- | --- | --- |
| `bcp_metrics[story_key].history` | **escreve** (histórico de rescores, FIFO cap 50) | — |
| `pulse_metrics[story_key].*` | **nunca toca** | escreve |

Regra dura: **BCP nunca escreve `pulse_metrics`; PULSE nunca escreve `bcp.*` nem `bcp_metrics`.**
As trilhas de dados são disjuntas e cada módulo é dono exclusivo da sua.

## Separação spec vs operacional (issue #19)

O frontmatter da story contém **dados de especificação** — complexidade e
estimativa no momento de criação, imutáveis após o score inicial. O
sprint-status contém **dados operacionais** — o que mudou ao longo da vida da
story (rescores, histórico de revisões).

| Dado | Natureza | Onde vive |
| --- | --- | --- |
| `bcp.total`, `bcp.breakdown` | Especificação — complexidade estrutural | story frontmatter |
| `estimated_hours` | Planejamento — derivado do BCP | story frontmatter |
| `bcp_metrics[key].history` | Operacional — histórico de rescores | sprint-status.yaml |

## Contrato de frontmatter

Schema formal (JSON Schema Draft 2020-12):
[`skills/bmad-bcp-score/assets/bcp-frontmatter.schema.yaml`](../../skills/bmad-bcp-score/assets/bcp-frontmatter.schema.yaml).
`$id`: `bcp-frontmatter-1.0`.

Exemplo do que o BCP grava numa story:

```yaml
estimated_hours: 33
estimated_hours_pre_bcp: 10
estimated_hours_basis: bcp
estimated_hours_reference: 40        # âncora frozen = total × reference rate (issue #32)
bcp:
  schema_version: "1.0"
  rule_version: "ciandt-2014"
  total: 8
  scored_at: "2026-05-17T12:00:00Z"
  scored_by: bruno
  breakdown:
    business_rules:
      - { size: M, points: 3, note: "validação de elegibilidade" }
    interface_elements:
      - { size: S, points: 2 }
      - { size: M, points: 3 }
```

`history` não aparece mais no frontmatter. Histórico de rescores vai para
`bcp_metrics[story_key].history` no sprint-status (ver seção abaixo).

`estimated_hours = total × h_per_bcp(categoria)`, onde `h_per_bcp` vem do
`bcp-baseline.yaml` (seed 4.13 no cold start). `estimated_hours_pre_bcp`
guarda o valor original **só na primeira vez** que o BCP sobrescreve — é
trilha de auditoria, não é reescrito em rescores.

### Dois denominadores: plano vs âncora (issue #32)

O BCP grava **dois** números de horas, com papéis ortogonais:

| Campo | Fórmula | Denominador | PULSE usa para |
| --- | --- | --- | --- |
| `estimated_hours` | `total × h_per_bcp` (recalibrado/vivo) | segue a realidade do time | **previsibilidade** (drift `actual` vs plano) |
| `estimated_hours_reference` | `total × reference_h_per_bcp` (frozen) | benchmark fixo, governado | **alavancagem estável** (`reference / actual`, não colapsa) |

PULSE só **lê** os dois — não importa o BCP, não lê o baseline, não converte
BCP→horas. **Degradação graciosa:** sem `estimated_hours_reference` (BCP antigo
ou ausente), o PULSE cai na alavancagem-vs-plano de hoje. A reference rate muda
só por governança (ledger forward-only); a recalibração nunca a toca — ver
[README → Governança da reference rate](../../README.md).

## Contrato no sprint-status

Quando `apply_score.py` é invocado com `--project-root` (ou `--sprint-status`
explícito), o histórico de rescores vai para o sprint-status:

```yaml
bcp_metrics:
  "5-7-minha-story":
    history:
      - rule_version: "1.0"
        total: 8
        scored_at: "2026-03-01T10:00:00Z"
        scored_by: manual
        estimated_hours: 33.0
      - rule_version: "1.0"
        total: 11
        scored_at: "2026-03-15T14:00:00Z"
        scored_by: bruno
        estimated_hours: 45.4
```

`story_key` = stem do arquivo de story (ex: `5-7-minha-story` de
`5-7-minha-story.md`). FIFO, cap 50 entradas por story.

## Auto-detecção do sprint-status (issue #25)

O caller não precisa conhecer o path do sprint-status. Passando apenas
`--project-root`, o script resolve a cadeia de tokens do BMAD config:

```
_bmad/config.yaml → output_folder → pulse.pulse_data_folder
  → + pulse_sprint_status_filename
```

Se o arquivo existir → modo sprint-status automático. Se não existir → modo
legado (history na story, backward compat). `--sprint-status` explícito
funciona como override para paths não-padrão.

## Degradação graciosa

| Cenário | Comportamento |
| --- | --- |
| BCP presente, PULSE ausente | BCP estima normalmente; `bcp_metrics` no sprint-status (se existir) fica sem `actual_hours` correspondente. |
| PULSE presente, BCP ausente | PULSE usa o `estimated_hours` da Amelia. Zero erro. |
| Ambos presentes | BCP estima → PULSE mede → auto-recalibrate no code review. Caminho feliz. |
| BCP presente, consentimento negado | BCP só anexa `bcp.*`; `estimated_hours` fica como a Amelia deixou. PULSE mede contra a Amelia. |
| `--project-root` sem sprint-status | Modo legado: history no frontmatter da story, advisory de deprecação. |

Nenhuma combinação quebra. A ausência de um módulo nunca é erro para o outro.

## Versionamento do contrato

`bcp.schema_version` rastreia o formato do bloco `bcp.*`. Mudança
incompatível ⇒ bump de `schema_version` + nota de migração. Leitores
(incluindo PULSE) devem tolerar campos extras desconhecidos — o schema é
`additionalProperties: false` só dentro de `bcp`, nunca no documento todo.

## Por que essa fronteira

PULSE já existia e mede eficiência sem saber de onde vem a estimativa. Acoplar
por código criaria dependência circular entre dois módulos opcionais. Mediar
por contratos de dados (frontmatter + sprint-status) mantém cada um
instalável, testável e versionável de forma independente — e o usuário escolhe
rodar um, o outro, ou os dois.
