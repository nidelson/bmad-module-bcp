# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é este repositório

Projeto **meta**: usa a metodologia BMAD para **construir um novo módulo BMAD** chamado `bmad-module-bcp`. O produto final é um módulo de scoring de complexidade (Business Complexity Points / BCP, framework publicado pela CI&T) que roda ao lado do módulo irmão PULSE.

Estado atual: **greenfield, fase de planejamento**. Existe Product Brief completo; o PRD foi iniciado (`_bmad-output/planning-artifacts/prd.md` — só o cabeçalho, corpo não escrito). **O código do módulo ainda não foi scaffoldado** — não há diretório `skills/` (saída do BMad Builder) ainda. Ler o Product Brief antes de qualquer trabalho de planejamento: `_bmad-output/planning-artifacts/product-brief.md`.

Repositório irmão (acesso de leitura concedido em `settings.local.json`): `/Users/nidelson/Projects/nidelson/bmad-module-pulse`. O contrato BCP↔PULSE é o ativo central — consultar o PULSE ao desenhar a integração.

## Arquitetura do produto a ser construído

Dois módulos BMAD frouxamente acoplados, **integração schema-mediated**: nenhum importa o outro, ambos degradam graciosamente quando o outro está ausente. O contrato é um bloco de frontmatter documentado no arquivo da story:

- **BCP escreve:** `estimated_hours` (sobrescreve, preservando `estimated_hours_pre_bcp`), `estimated_hours_basis`, bloco `bcp.*`, `bcp.history` (trilha de auditoria, cap 50).
- **PULSE lê:** `estimated_hours` de forma agnóstica ao escritor; renderiza seção condicional quando `pulse_estimation_method=bcp`.

Entregáveis v0.1.0: 8 skills (`bmad-bcp-setup`, `-score`, `-score-batch`, `-rescore`, `-recalibrate`, `-backfill-baseline`, `-rule-card`, `-agent-bruno`), persona Bruno, `bcp-rule.yaml` imutável, baseline por categoria `bcp-baseline.yaml` (seed 4.13, `min_samples=5`, `rolling_window=10`).

**Split de licença é load-bearing:** código do módulo = MIT; regra BCP embarcada da CI&T = CC BY-NC-ND 4.0, imutável (só hints editoriais mutáveis). `ATTRIBUTION.md` é pré-requisito de aceite, não rodapé.

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

## Localização — ADR 0001 (vinculante)

`docs/ADR/0001-localization-strategy.md` define a política. Resumo operacional:

- **EN inegociável:** identificadores de código (nomes de skill, slugs de agente, comandos `/bmad-bcp-*`), chaves YAML/frontmatter/JSON Schema, mensagens de Conventional Commits, nomes de branch, `CHANGELOG.md`, títulos de ADR, `ATTRIBUTION.md` (EN-primário).
- **PT-BR canônico:** `README.pt-BR.md` (manual real), guias de integração, docs de tech-refinement, corpo de ADR, diálogo do agente Bruno, mensagens de erro/prompts, notas de auditoria `bcp.history`.
- `README.md` (raiz) = casca EN mínima (vitrine + link para o PT-BR).
- Comunicação com o usuário em **Português do Brasil**; `document_output_language` da config = English (afeta artefatos estruturados, não a narrativa).

Commits seguem **Conventional Commits**: o **type em EN conforme a spec** (`feat`, `fix`, `docs`, `chore`, `refactor`, `perf`, `test`, `build`, `ci`, `style`, `revert`) — `release-please`/changelog parseiam o type e a estrutura. O **texto da mensagem (subject + body) pode ser PT-BR**. O changelog gerado refletirá o texto em PT-BR (aceito). Não é necessário anexar resumo EN em PRs.

## Fluxo Git — Trunk Based Development (vinculante)

**Nunca commitar direto na `main`.** Todo trabalho segue: criar branch → commit → abrir PR.

- Branches de vida curta a partir de `main`, nomes em EN (Conventional Commits / scriptável).
- Commit em Conventional Commits EN.
- Abrir PR via `gh pr create`; merge na `main` só via PR.
- Se já estiver na `main` ao iniciar trabalho: criar branch antes de qualquer commit.
- Trabalho isolado pode usar worktree (ver abaixo).

## Worktrees

Trabalho isolado em `.claude/worktrees/` (ex.: `module-plan` no branch `worktree-module-plan`). Verificar com `git worktree list` antes de criar novos.
