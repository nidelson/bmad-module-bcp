# Integração BCP ↔ PULSE

> Documento canônico em PT-BR ([ADR 0001](../ADR/0001-localization-strategy.md)).
> Chaves de frontmatter/schema são EN (interoperabilidade).

## Princípio: acoplamento frouxo mediado por schema

BCP e PULSE são dois módulos BMAD irmãos que **não se importam mutuamente**.
Nenhum dos dois faz `import` do outro, nenhum lê o código do outro, nenhum
falha se o outro estiver ausente. O único ponto de contato é o **frontmatter
da story** — um contrato de dados, não de código.

- **BCP** estima: pontua a complexidade e deriva `estimated_hours`.
- **PULSE** mede: compara horas estimadas com horas reais de IA e calcula
  alavancagem.

PULSE lê `estimated_hours` de forma **agnóstica ao escritor**. Tanto faz se
quem escreveu foi a Amelia (agente padrão do BMAD) ou o BCP — PULSE consome o
número e segue. Por isso **nenhum ajuste no PULSE é necessário** para a
integração funcionar.

## Quem escreve o quê

| Chave | BCP | PULSE |
| --- | --- | --- |
| `estimated_hours` | **escreve** (sobrescreve, consentimento via install) | lê |
| `estimated_hours_pre_bcp` | **escreve uma única vez** (auditoria) | — |
| `estimated_hours_basis` | **escreve** (`bcp`) | lê (opcional) |
| `bcp.*` | **escreve** | lê (opcional) |
| `bcp.history` | **escreve** (FIFO, cap 50) | — |
| `pulse_metrics` | **nunca toca** | escreve |

Regra dura: **BCP nunca escreve `pulse_metrics`; PULSE nunca escreve `bcp.*`.**
As duas trilhas de dados são disjuntas e cada módulo é dono exclusivo da sua.

## Contrato de frontmatter

Schema formal (JSON Schema Draft 2020-12):
[`skills/bmad-bcp-score/assets/bcp-frontmatter.schema.yaml`](../../skills/bmad-bcp-score/assets/bcp-frontmatter.schema.yaml).
`$id`: `bcp-frontmatter-1.0`.

Exemplo do que o BCP grava numa story:

```yaml
estimated_hours: 33
estimated_hours_pre_bcp: 10
estimated_hours_basis: bcp
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
  history: []
```

`estimated_hours = total × h_per_bcp(categoria)`, onde `h_per_bcp` vem do
`bcp-baseline.yaml` (seed 4.13 no cold start). `estimated_hours_pre_bcp`
guarda o valor original **só na primeira vez** que o BCP sobrescreve — é
trilha de auditoria, não é reescrito em rescores.

## Degradação graciosa

| Cenário | Comportamento |
| --- | --- |
| BCP presente, PULSE ausente | BCP estima normalmente; ninguém lê `estimated_hours` além do BMAD padrão. |
| PULSE presente, BCP ausente | PULSE usa o `estimated_hours` da Amelia. Zero erro. |
| Ambos presentes | BCP estima → PULSE mede contra a estimativa do BCP. Caminho feliz. |
| BCP presente, consentimento negado | BCP só anexa `bcp.*`; `estimated_hours` fica como a Amelia deixou. PULSE mede contra a Amelia. |

Nenhuma combinação quebra. A ausência de um módulo nunca é erro para o outro.

## Versionamento do contrato

`bcp.schema_version` rastreia o formato do bloco `bcp.*`. Mudança
incompatível ⇒ bump de `schema_version` + nota de migração. Leitores
(incluindo PULSE) devem tolerar campos extras desconhecidos — o schema é
`additionalProperties: false` só dentro de `bcp`, nunca no documento todo.

## Por que essa fronteira

PULSE já existia e mede eficiência sem saber de onde vem a estimativa. Acoplar
por código criaria dependência circular entre dois módulos opcionais. Mediar
por frontmatter mantém cada um instalável, testável e versionável de forma
independente — e o usuário escolhe rodar um, o outro, ou os dois.
