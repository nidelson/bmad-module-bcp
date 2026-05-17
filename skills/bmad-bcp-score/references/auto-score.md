# Auto-Score Prompt Template

EN scaffolding (prompt-engineering robustness); few-shot examples in PT-BR
(audience fit) — per ADR 0001.

## Task

Score one story against the canonical BCP ruler. For **each** of the 10
complexity elements, decide:

1. Is the element **present** in this story's scope?
2. If present, which **size** (XS, S, M, L, XL) best matches, using the
   element's verbatim `descriptors` from `bcp-rule.yaml` as the rubric.
   Treat `null` descriptor cells as "this size does not exist for this
   element" — never select a `null` cell.
3. A short **note** (PT-BR) justifying the size, grounded in story text.

An element may contribute **more than one item** (e.g. two distinct sets of
interface elements). Omit absent elements entirely.

## Inputs

- The story file (frontmatter + body).
- `bcp-rule.yaml` (resolved rule): elements, definitions, per-size
  descriptors, Fibonacci `sizes` map.
- Optional: the story's `category` and prior `bcp.*` block (when rescoring).

## Output (strict)

Emit a single JSON object — nothing else:

```json
{
  "breakdown": {
    "<element_slug>": [
      { "size": "M", "points": 3, "note": "<PT-BR justificativa curta>" }
    ]
  },
  "confidence": 0.0,
  "divergence_with_agent_estimate": false,
  "rationale_summary": "<PT-BR, 1-2 frases>"
}
```

- `points` MUST equal the Fibonacci value of `size` from the rule's `sizes`
  map (XS=1, S=2, M=3, L=5, XL=8). Do not invent values.
- `element_slug` MUST match a `slug` in `bcp-rule.yaml`.
- `confidence` ∈ [0,1]: your calibrated certainty in the overall scoring.
- `divergence_with_agent_estimate`: true if the BCP-derived hours would
  differ materially (>30%) from any pre-existing `estimated_hours`.
- Do not write files. Do not compute hours. The deterministic script
  derives total/hours and mutates frontmatter.

## Few-shot (PT-BR)

**Story:** "Adicionar endpoint REST que valida CPF e grava log de auditoria
por entidade alterada. Sem UI."

**Raciocínio:** Business Rules = validação simples de fórmula → XS. Audits =
trilha por 1 entidade → XS. Sem UI (Interface Elements ausente). Boundaries
self-contained → XS. Demais elementos ausentes.

```json
{
  "breakdown": {
    "business_rules": [{ "size": "XS", "points": 1, "note": "Validação de CPF, fórmula simples sem decisão." }],
    "audits": [{ "size": "XS", "points": 1, "note": "Trilha de auditoria para 1 entidade." }],
    "boundaries": [{ "size": "XS", "points": 1, "note": "Self-contained, não cruza boundaries." }]
  },
  "confidence": 0.82,
  "divergence_with_agent_estimate": false,
  "rationale_summary": "Story pequena: validação + auditoria de 1 entidade, sem UI nem integrações."
}
```

**Story:** "Refatorar fluxo de checkout multi-tenant: processo iterativo com
muitas decisões, 6 entidades de domínio tocadas, notificação push no fim."

```json
{
  "breakdown": {
    "business_rules": [{ "size": "XL", "points": 8, "note": "Fluxo iterativo com muitas decisões." }],
    "domain_entities": [{ "size": "L", "points": 5, "note": "6 entidades incorporadas/modificadas." }],
    "solution_variabilities": [{ "size": "XL", "points": 8, "note": "Comportamento multi-tenant varia significativamente por parâmetro." }],
    "notifications": [{ "size": "XS", "points": 1, "note": "Notificação push como saída de evento." }]
  },
  "confidence": 0.7,
  "divergence_with_agent_estimate": true,
  "rationale_summary": "Story grande: lógica iterativa pesada, variabilidade multi-tenant, 6 entidades."
}
```
