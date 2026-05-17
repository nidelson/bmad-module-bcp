---
title: 'Module Plan — bmad-module-bcp'
status: 'complete'
module_name: 'BCP — Business Complexity Points Scorer'
module_code: 'bcp'
module_description: 'Pontua stories com o framework Business Complexity Points da CI&T, deriva estimated_hours do score, é dono do baseline por categoria e escreve de volta no frontmatter da story.'
architecture: 'multiplos workflows + 1 agente facilitador opcional (espelho do bmad-module-pulse)'
standalone: true
expands_module: ''
skills_planned:
  - bmad-bcp-setup
  - bmad-bcp-score
  - bmad-bcp-score-batch
  - bmad-bcp-rescore
  - bmad-bcp-recalibrate
  - bmad-bcp-backfill-baseline
  - bmad-bcp-rule-card
  - bmad-bcp-agent-bruno
config_variables:
  - bcp_estimation_basis
  - bcp_confidence_threshold
  - bcp_non_interactive_default
  - bcp_baseline_seed
  - bcp_baseline_min_samples
  - bcp_baseline_rolling_window
  - bcp_overwrite_estimated_hours
created: '2026-05-16'
updated: '2026-05-16'
---

# Module Plan — bmad-module-bcp

> Política de localização: este documento segue o ADR 0001 — corpo em PT-BR
> (trilha de decisão interna), identificadores de código sempre em EN.
> Fonte de verdade do escopo: GitHub issue #1 de `nidelson/bmad-module-bcp`.
> Decisão de faseamento confirmada pelo usuário: **MVP-first em 4 fases**.

## Vision

`bmad-module-bcp` é um módulo BMAD que traz scoring **Business Complexity Points
(BCP)** — o framework publicado e normalizado da CI&T — para dentro do fluxo
BMAD. Organizações no formato CI&T usam BCP internamente para estimativa;
Story Points são subjetivos e não comparáveis entre times, horas brutas
escondem complexidade vs produtividade. Não existe tooling BMAD-nativo para BCP.

O módulo pontua uma story (10 elementos × 5 tamanhos × Fibonacci), **deriva
`estimated_hours` a partir do score × baseline por categoria**, escreve um bloco
`bcp.*` auditável no frontmatter da story, e é dono do `bcp-baseline.yaml`
(média rolling por categoria com seed de cold start). Scoring retroativo é
capability de primeira classe: um squad com histórico instala e sai do seed no
dia um.

**Público:** squads CI&T-shaped que adotam BMAD. **Fronteira de ownership
limpa com PULSE** (Approach A — acoplamento frouxo, cross-awareness zero): BCP
é dono de scoring/regra/baseline/derivação de horas/escritas de frontmatter;
PULSE é dono de `pulse_metrics`/`actual_hours`/telemetria. Comunicação só por
convenção de arquivo (frontmatter). BCP roda **sem PULSE instalado**; PULSE roda
**sem BCP instalado**.

## Architecture

**Decisão:** múltiplos workflows + 1 agente facilitador opcional — espelho
direto da arquitetura de `bmad-module-pulse` (módulo irmão, local em
`/Users/nidelson/Projects/nidelson/bmad-module-pulse`).

**Rationale:**

- As capabilities servem jornadas distintas (instalar, pontuar uma, pontuar
  em lote, repontuar, recalibrar baseline, exibir regra) e não exigem persona
  nem memória persistente entre invocações → **workflows**, não um agente
  monolítico.
- Bruno é **camada facilitadora/coach opcional, não path crítico**. O módulo
  roda ponta-a-ponta em `--non-interactive` sem Bruno. Modelar como agente
  (`bmad-bcp-agent-bruno`) espelha `bmad-agent-pulse` (Levi) e mantém a persona
  isolada das mecânicas de scoring.
- PULSE provou o padrão setup-skill + agente + workflows; reuso reduz risco e
  garante interoperabilidade do contrato de frontmatter.

**Espelho estrutural de PULSE (root layout):**

```
bmad-module-bcp/
├── _metrics/
├── .claude-plugin/marketplace.json     # versão bumpada por release-please
├── .github/                            # workflows CI espelhando PULSE
├── .gitignore                          # espelho PULSE (+ config.user.*, .venv)
├── .release-please-manifest.json
├── docs/{tech-refinement,ADR,integration,rfcs}/
├── examples/
├── scripts/                            # detect_bmad_capability.py, merge-config.py,
│                                       #   inject_customize.py, cleanup-legacy.py
├── skills/                             # 8 skills (ver abaixo)
├── tests/
├── ATTRIBUTION.md                      # CC BY-NC-ND 4.0 (regra CI&T) EN-primary + mirror PT-BR
├── LICENSE                             # MIT (código do módulo)
├── module.yaml                         # espelho de pulse/module.yaml (code: bcp)
├── pyproject.toml / requirements-dev.txt
├── release-please-config.json          # espelho PULSE: release-type simple,
│                                       #   extra-files bump module.yaml + marketplace.json
├── CHANGELOG.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md / SECURITY.md
└── README.md (PT-BR canônico, default) / README.en.md (shell EN)
```

`release-please-config.json` espelha PULSE: `release-type: simple`,
`bump-minor-pre-major`, `extra-files` apontando para
`skills/bmad-bcp-setup/assets/module.yaml` (`$.module_version`) e
`.claude-plugin/marketplace.json` (`$.plugins[0].version`).

### Memory Architecture

**Pattern: personal memory only (mínima).** O módulo não exige memória
compartilhada entre agentes — só existe um agente (Bruno) e ele é opcional.
Bruno tem memória pessoal leve em `{project-root}/_bmad/memory/bmad-bcp-agent-bruno/`
para preferências de coaching (verbosidade, tom). **A fonte de verdade de
estado não é memória de agente** — é o frontmatter da story (`bcp.*`,
`bcp.history`) e o `bcp-baseline.yaml`. Decisão consciente: durabilidade e
auditabilidade ficam em arquivos versionáveis no repo do squad, não em memória
de agente.

### Memory Contract

Não se aplica (sem memória compartilhada). Estado durável documentado em
**Integration** (contrato de frontmatter + baseline).

### Cross-Agent Patterns

Não se aplica (agente único, opcional). O "roteador" é o usuário/CLI invocando
workflows; Bruno é invocado sob demanda como camada de coaching e nunca
intermedeia outros skills.

## Skills

8 skills. Convenção `bmad-bcp-{skill}` (workflows) e `bmad-bcp-agent-{name}`
(agente) — espelha PULSE (`bmad-pulse-*`, `bmad-agent-pulse`).

### bmad-bcp-setup

**Type:** workflow (setup skill, espelho de `bmad-pulse-setup`)

**Core Outcome:** módulo instalável e configurado num projeto BMAD com um
comando; baseline semeado; Bruno registrado; `customize.toml` emitido para
`bmad-create-story`.

**The Non-Negotiable:** consentimento de overwrite de `estimated_hours`
coletado no install (install = consentimento documentado). Anti-zombie ao
reescrever config.

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|---|---|---|---|
| Coletar config | Prompts (ou `--headless`/defaults) e gravar config | respostas do usuário / args | `_bmad/config.yaml` (seção `bcp`), `_bmad/config.user.yaml` |
| Pre-flight diagnostic | Verificar BMAD ≥6.6.0 (capability gate via `_bmad/_config/manifest.yaml`), detectar `bmad-create-story`, detectar PULSE | projeto | relatório de diagnóstico |
| Semear baseline | Criar `bcp-baseline.yaml` com seed 4.13 (referência CI&T 2014), min_samples, rolling_window | config | `_bmad-output/implementation-artifacts/bcp-baseline.yaml` |
| Registrar Bruno | Adicionar Bruno ao agent manifest + `module-help.csv` | module.yaml | manifest/CSV atualizados |
| Emitir customize.toml | Gerar override de `bmad-create-story` para encadear scoring BCP | — | `customize.toml` |
| Dry-run | Pré-visualizar todas as escritas sem aplicar | `--dry-run` | preview |

**Activation Modes:** interactive + headless (`--headless`, accept-defaults).

**Tool Dependencies:** `scripts/detect_bmad_capability.py`, `merge-config.py`,
`inject_customize.py`, `cleanup-legacy.py` (espelho dos scripts/padrões PULSE).

**Design Notes:** espelhar o padrão anti-zombie e a migração legacy
per-module → consolidado de `bmad-pulse-setup`. `{project-root}` é token
literal em valores de config.

### bmad-bcp-score

**Type:** workflow

**Core Outcome:** uma story pontuada com BCP; `estimated_hours` derivado e
sobrescrito (auditoria preservada); bloco `bcp.*` escrito no frontmatter.

**The Non-Negotiable:** non-interactive por default acima do confidence
threshold; dry-run review **apenas** em divergência com a Amelia, low-confidence
ou rescore. Nunca escrever em `pulse_metrics`.

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|---|---|---|---|
| Auto-score | Pontuar 10 elementos × 5 tamanhos via prompt template | story file, `bcp-rule.yaml` | breakdown `bcp.*` |
| Derivar horas | `estimated_hours = total × h_per_bcp(category)` do baseline | score, baseline | `estimated_hours` |
| Escrita auditável | Preservar `estimated_hours_pre_bcp`, `estimated_hours_basis` | frontmatter atual | frontmatter atualizado |
| Dry-run review | Revisão interativa só em divergência/low-confidence/rescore | flags/contexto | confirmação |

**Activation Modes:** non-interactive (default) + interactive (review).

**Tool Dependencies:** `assets/prompts/auto-score.md` (estrutura EN, exemplos
few-shot PT-BR), `assets/bcp-rule.yaml`, `assets/bcp-frontmatter.schema.yaml`.

**Design Notes:** advisory "considere split em sub-story" se delta >50% em
rescore único ou >2× cumulativo.

### bmad-bcp-score-batch

**Type:** workflow

**Core Outcome:** múltiplas stories existentes pontuadas com
`bcp.scored_by: retroactive`.

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|---|---|---|---|
| Score em lote | Pontuar glob de stories | `<glob>` | N frontmatters atualizados |
| Dry-run cost | Prever gasto de tokens antes de rodar | `--dry-run-cost` | estimativa de custo |

**Design Notes:** `scored_by: retroactive` distinto de `bruno/manual/rescore`.
Base do scoring retroativo de primeira classe.

### bmad-bcp-rescore

**Type:** workflow

**Core Outcome:** total + `history` + `estimated_hours` atualizados; trilha de
auditoria preservada.

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|---|---|---|---|
| Repontuar | Recalcular total, append em `bcp.history` (cap 50, warn no truncate) | story file | frontmatter + history |
| Advisory de split | Disparar aviso em delta >50% único / >2× cumulativo | deltas | advisory |

### bmad-bcp-recalibrate

**Type:** workflow

**Core Outcome:** `bcp-baseline.yaml` atualizado em ordem cronológica a partir
de horas reais.

**The Non-Negotiable:** funciona **sem PULSE** — lê
`pulse_metrics.actual_hours` se disponível, senão flag `--actual-hours`
(só por convenção de arquivo, zero cross-awareness).

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|---|---|---|---|
| Recalibrar | Atualizar `h_per_bcp` por categoria (janela FIFO + snapshot history) | actual_hours, baseline | baseline atualizado |
| Fonte agnóstica | `pulse_metrics` OU `--actual-hours` manual | frontmatter / flag | — |

### bmad-bcp-backfill-baseline

**Type:** workflow

**Core Outcome:** cold start eliminado a partir do histórico do squad.

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|---|---|---|---|
| Encadear | score-batch + recalibrate em sequência | glob histórico | baseline saído do seed |
| Idempotente | Re-rodar não corrompe baseline | estado atual | baseline estável |

### bmad-bcp-rule-card

**Type:** workflow

**Core Outcome:** regra BCP 10×5 exibida ao usuário.

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|---|---|---|---|
| Exibir regra | Renderizar 10 elementos × 5 tamanhos × Fibonacci | `bcp-rule.yaml` | card legível |

**Design Notes:** `assets/bcp-rule.yaml` com header de atribuição
CC BY-NC-ND 4.0 — **imutável**, modificar viola licença.

### bmad-bcp-agent-bruno

**Type:** agent (espelho de `bmad-agent-pulse`/Levi)

**Persona:** Bruno — coach de complexidade. Bordão: **"Régua antes de régua"**.
Tom PT-BR, didático, provocador na medida. Persona desenhada para entrega
pt-BR (ADR 0001: tradução EN exige reautoria fiel, não literal).

**Core Outcome:** facilitar scoring com explicação pedagógica do porquê de cada
elemento/tamanho; nunca bloquear o loop core.

**The Non-Negotiable:** camada **opcional**. Módulo roda ponta-a-ponta sem ele.

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|---|---|---|---|
| Coaching de scoring | Explicar/desafiar score elemento-a-elemento | story, score draft | score refinado + rationale |
| Leitura de baseline | Contextualizar h_per_bcp da categoria | baseline | narrativa |

**Memory:** pessoal leve em `{project-root}/_bmad/memory/bmad-bcp-agent-bruno/`
(verbosidade, tom). Estado de scoring **não** vive aqui — vive no frontmatter.

**Activation Modes:** interactive (coaching). Resolve agent block via
`resolve_customization.py` + `customize.toml` (espelho de Levi).

## Configuration

Módulo **exige** config além do core BMad. Espelha o padrão de prompts de
`pulse/module.yaml`.

| Variable | Prompt | Default | Result | User Setting |
|---|---|---|---|---|
| `bcp_overwrite_estimated_hours` | BCP pode sobrescrever `estimated_hours` da Amelia? (install = consentimento) | `yes` | `{value}` | no |
| `bcp_confidence_threshold` | Threshold de confiança p/ pular dry-run review | `0.75` | `{value}` | no |
| `bcp_non_interactive_default` | Rodar score em non-interactive por default? | `yes` | `{value}` | no |
| `bcp_baseline_seed` | Seed h/BCP cold start (referência CI&T 2014) | `4.13` | `{value}` | no |
| `bcp_baseline_min_samples` | Amostras mínimas antes de sair do seed | `5` | `{value}` | no |
| `bcp_baseline_rolling_window` | Janela FIFO de recalibração | `10` | `{value}` | no |
| `bcp_estimation_basis` | Rótulo de `estimated_hours_basis` | `bcp` | `{value}` | no |

## External Dependencies

Nenhuma CLI/MCP externa. Scripts Python internos (espelho PULSE):
`detect_bmad_capability.py`, `merge-config.py`, `inject_customize.py`,
`cleanup-legacy.py`. Capability gate: **BMAD ≥6.6.0** (revisado vs ≥6.4.0 do plano original). Rationale: greenfield sem compat debt; o framework de hooks `customize.toml` (`activation_steps_*`, `persistent_facts`) é a superfície de integração 6.6.0; gate por versão precisa lida de `_bmad/_config/manifest.yaml` (semver real), não por proxy-filesystem como o PULSE.
Integração opcional com `bmad-create-story` via `customize.toml`.

## UI and Visualization

Sem dashboard próprio (PULSE é dono de dashboards). `bmad-bcp-rule-card`
renderiza a regra como card textual. NFR de eval suite pode emitir relatório
HTML do golden set (Fase 4).

## Setup Extensions

`bmad-bcp-setup` além de config: semeia `bcp-baseline.yaml`, registra Bruno
no manifest, emite `customize.toml` para `bmad-create-story`, roda pre-flight
diagnostic, suporta `--dry-run`, migra config legacy per-module → consolidado.

## Integration

**Standalone:** valor independente — pontua e deriva horas sem PULSE
(recalibrate aceita `--actual-hours`).

**Contrato de frontmatter (BCP escreve, leitores agnósticos consomem):**

- BCP é dono de: `estimated_hours` (sobrescreve com consentimento),
  `estimated_hours_pre_bcp`, `estimated_hours_basis`, `bcp.*`,
  `bcp-baseline.yaml`.
- PULSE é dono de: `pulse_metrics.*`, `actual_hours`. BCP **nunca** escreve
  em `pulse_metrics`; PULSE **nunca** escreve em `bcp.*`.
- Schema garantido por `assets/bcp-frontmatter.schema.yaml` (JSON Schema
  versionado). Contract testing BCP↔PULSE (Pact ou JSON Schema versionado)
  com matriz de compatibilidade publicada nos READMEs de ambos.
- Issue contraparte (lado PULSE): `nidelson/bmad-module-pulse#30`.

## Creative Use Cases

- **Backfill day-one:** squad com 50+ stories entregues roda
  `bmad-bcp-backfill-baseline` e já estima com baseline real, pulando o seed.
- **Auditoria de drift:** `bcp.history` + advisory de split expõem stories que
  cresceram além do estimado (sinal de scope creep).
- **Coaching onboarding:** novo dev usa Bruno para aprender a régua BCP
  pontuando stories antigas com feedback.

## Build Roadmap

Faseamento confirmado: **MVP-first em 4 fases**. Ordem espelha dependências
de dados (baseline antes de derivação; score antes de rescore/batch).

**Fase 1 — Loop core utilizável**
1. `bmad-bcp-setup` (sem ele nada instala; semeia baseline)
2. `bmad-bcp-rule-card` (entrega `bcp-rule.yaml` + atribuição CC BY-NC-ND;
   barato, valida o asset da regra cedo)
3. `bmad-bcp-score` (coração: score → derivação → frontmatter auditável)
   - Entregável: 1 story pontuada → `estimated_hours` derivado, ponta-a-ponta.

**Fase 2 — Retroativo + calibração**
4. `bmad-bcp-score-batch` (scoring retroativo de primeira classe)
5. `bmad-bcp-rescore` (history + advisory de split)
6. `bmad-bcp-recalibrate` (baseline a partir de horas reais; com e sem PULSE)
7. `bmad-bcp-backfill-baseline` (encadeia 4+6; mata cold start)

**Fase 3 — Camada coach opcional**
8. `bmad-bcp-agent-bruno` (facilitador; não bloqueia Fases 1–2)

**Fase 4 — Endurecimento NFR + docs**
- Eval suite estatística do scorer (golden set ≥50 stories, tolerância de
  variância documentada, reprodutibilidade por seed/temperature)
- Contract testing BCP↔PULSE + matriz de compatibilidade nos READMEs
- Fault-injection E2E (PULSE indisponível mid-scoring, `customize.toml`
  corrompido, baseline fora-de-contexto, rescore concorrente)
- Docs: `README.md` PT-BR canônico (default) + `README.en.md` shell EN +
  `docs/integration/{pulse,bmad-create-story}.md` + `ATTRIBUTION.md` +
  scaffold de infra (gitignore, release-please, pyproject, .github) via
  espelho PULSE
- **Create Module (CM)** para scaffold final da infra de módulo instalável

**Next steps:**

1. Construir Fase 1 skill-a-skill via **Build a Workflow (BW)** (setup,
   rule-card, score) — passar este plano como contexto
2. Validar entregável ponta-a-ponta de Fase 1 (1 story SIP pontuada)
3. Prosseguir Fases 2–4; ao final, **Create Module (CM)** para tornar
   instalável

## Ideas Captured

- Issue #1 já consolidou party-mode + product brief + ADR 0001 — vision e
  creative exploration concluídas fora desta sessão.
- "Régua antes de régua" (bordão Bruno) é design pt-BR; EN exige reautoria.
- Espelho PULSE não é literal: PULSE = 5 skills (setup+agente+3 workflows),
  BCP = 8 (setup+agente+6 workflows). Padrões reusados: anti-zombie,
  customize.toml, resolve_customization.py, release-please extra-files,
  capability gate ≥6.6.0 (revisado), layout root.
- Fora de escopo v0.1.0 (issue #1): auto-recalibrate hook, baselines
  multi-tenant, Web UI/IDE plugin, calibração ML, BCP-as-a-service, Bruno
  standalone CLI, BCP como default de `pulse_estimation_method`.
