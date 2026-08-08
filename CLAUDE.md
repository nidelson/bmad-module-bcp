# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é este repositório

> ⚠️ **Módulo descontinuado e arquivado.** Não implemente features aqui.

O scoring BCP foi portado para o [PULSE](https://github.com/nidelson/bmad-module-pulse) (issue `nidelson/bmad-module-pulse#84`), que passou a ser dono do ciclo inteiro: pontua a story, deriva `estimated_hours`, cronometra a implementação e recalibra o baseline com as horas reais. **Trabalho novo de scoring vai para lá.**

O que restou aqui: `skills/bmad-bcp-setup`, reescrita como caminho de migração, e o histórico. O repositório é arquivado — não deletado — porque suas issues e PRs são o registro de como a régua foi congelada e o baseline calibrado.

**As demais skills `bmad-bcp-*` foram removidas, não viradas ponteiro.** Nome de skill é namespace global: `skill-manifest.csv` tem uma linha por nome com um módulo dono, e skill instalada vai para `.claude/skills/<nome>/` — um diretório por nome, último a escrever ganha. Um ponteiro deixado aqui sobrescreveria a skill funcional do PULSE sempre que este módulo fosse instalado depois. Repositório arquivado continua clonável, logo continua instalável: o redirect causaria a quebra que deveria evitar, indefinidamente.

Se você está aqui para migrar um projeto, o guia é [`docs/MIGRATION.md`](docs/MIGRATION.md).

Repositório irmão (acesso de leitura concedido em `settings.local.json`): `/Users/nidelson/Projects/nidelson/bmad-module-pulse`.

## Arquitetura do produto a ser construído

Dois módulos BMAD frouxamente acoplados, **integração schema-mediated**: nenhum importa o outro, ambos degradam graciosamente quando o outro está ausente. O contrato é um bloco de frontmatter documentado no arquivo da story:

- **BCP escreve:** `estimated_hours` (sobrescreve, preservando `estimated_hours_pre_bcp`), `estimated_hours_basis`, `hours_per_bcp` + `hours_per_bcp_source` (o fator e sua procedência — `seed` | `baseline:<cat>` | `baseline:<cat>:provisional`), bloco `bcp.*`, `bcp.history` (trilha de auditoria, cap 50).
- **PULSE lê:** `estimated_hours` de forma agnóstica ao escritor; renderiza seção condicional quando `pulse_estimation_method=bcp`.

Entregáveis v0.1.0: 8 skills (`bmad-bcp-setup`, `-score`, `-score-batch`, `-rescore`, `-recalibrate`, `-backfill-baseline`, `-rule-card`, `-agent-bruno`), persona Bruno, `bcp-rule.yaml` imutável por decisão de projeto, baseline por categoria `bcp-baseline.yaml` (seed 4.13, `min_samples=5`, `rolling_window=10`).

**Licença unificada (desde maio/2026):** código do módulo e regra BCP embarcada da CI&T são ambos MIT — o framework foi republicado como open source em `flow-ciandt/bcp-agent`. O split CC BY-NC-ND que era load-bearing no design original deixou de existir. A régua segue imutável por **decisão de projeto** (comparabilidade entre times), não por imposição legal. `ATTRIBUTION.md` registra a mudança.

## Sistema de configuração BMAD

Merge TOML de quatro camadas (prioridade crescente):

1. `_bmad/config.toml` — **installer-owned, tratar como read-only.** Regenerado a cada install; edições diretas são perdidas.
2. `_bmad/config.user.toml` — installer-owned, usuário.
3. `_bmad/custom/config.toml` — team, **committed**, autorável (overrides duráveis, agentes custom).
4. `_bmad/custom/config.user.toml` — pessoal, **gitignored**.

Para mudar uma resposta de install de forma durável: re-rodar o installer ou usar as camadas `custom/`. Nunca editar `config.toml` diretamente esperando persistência.

`_bmad/config.yaml` é um **espelho-bridge YAML** de `config.toml`, exigido pelas skills PULSE (não suportam TOML nativo). **Mantê-lo sincronizado manualmente** ao alterar config relevante a PULSE.

Resolver config mergeada (Python 3.11+ stdlib `tomllib`, sem venv/pip):

```bash
python3 _bmad/scripts/resolve_config.py --project-root /Users/nidelson/Projects/nidelson/bmad-module-bcp
python3 _bmad/scripts/resolve_config.py --project-root <path> --key agents
python3 _bmad/scripts/resolve_customization.py --project-root <path>
```

## Skills e fluxo BMAD

Skills BMAD vivem em `.claude/skills/` (instaladas via installer 6.6.0; módulos: core, bmm, bmb, cis, tea, pulse). Invocar via Skill tool com o nome (ex.: `bmad-module-builder`, `bmad-create-prd`). Catálogo completo com fases e dependências: `_bmad/_config/bmad-help.csv`.

Fluxo para construir o módulo: BMad Builder (`bmad-module-builder`: ideate → create → validate; `bmad-agent-builder`; `bmad-workflow-builder`). Saída do builder vai para `skills/` (config `[modules.bmb]`).

Saídas BMAD:

- Artefatos de planejamento → `_bmad-output/planning-artifacts/`
- Artefatos de implementação → `_bmad-output/implementation-artifacts/`
- Artefatos de teste → `_bmad-output/test-artifacts/`
- Docs de projeto / ADRs → `docs/`

## Localization — ADR 0002 (binding)

`docs/ADR/0002-english-canonical.md` defines the policy. ADR 0001 is superseded —
read it only to understand PT-BR prose written before 2026-08-07.

**English is canonical.** Every artifact is authored in English: code
identifiers, YAML keys and frontmatter, Conventional Commit messages (type *and*
text), branch names, issue and PR titles and bodies, ADRs, `CHANGELOG.md`,
`ATTRIBUTION.md`, integration guides, and the Bruno agent's dialogue, error
messages and prompts.

Portuguese exists only as a **translation** of reader-facing documents, tracking
the English source. Edit the English first, then reflect it.

Answering an issue in the language its author used is courtesy in a
conversation, not a canonical artifact — it does not make Portuguese a source.

Commits follow **Conventional Commits**, type per spec (`feat`, `fix`, `docs`,
`chore`, `refactor`, `perf`, `test`, `build`, `ci`, `style`, `revert`) with the
subject and body in English.

Open items carried by ADR 0002: the `README.md` / `README.en.md` inversion,
the Portuguese `changelog-sections` labels in `release-please-config.json`, and
the remaining PT-BR prose in this file and across `docs/`.

## Fluxo Git — Trunk Based Development (vinculante)

**Nunca commitar direto na `main`.** Todo trabalho segue: criar branch → commit → abrir PR.

- Branches de vida curta a partir de `main`, nomes em EN (Conventional Commits / scriptável).
- Commit em Conventional Commits EN.
- Abrir PR via `gh pr create`; merge na `main` só via PR.
- Se já estiver na `main` ao iniciar trabalho: criar branch antes de qualquer commit.
- Trabalho isolado pode usar worktree (ver abaixo).

## Worktrees

Trabalho isolado em `.claude/worktrees/` (ex.: `module-plan` no branch `worktree-module-plan`). Verificar com `git worktree list` antes de criar novos.
