# BCP — Module Setup

## Overview

Instala e configura o módulo BCP (Business Complexity Points) num projeto BMAD. A identidade do módulo (nome, code, versão) vem de `assets/module.yaml`. Coleta preferências do usuário e as escreve em três arquivos:

- **`{project-root}/_bmad/custom/config.toml`** — camada durável, committed, **toml-first** (issue #36): a seção do módulo `[modules.bcp]` é gravada aqui (via `tomlkit`, preservando comentários e outras seções). É a camada que o `resolve_config.py` do core lê com prioridade sobre os defaults do installer em `config.toml`.
- **`{project-root}/_bmad/config.yaml`** — bridge YAML legado: só settings core na raiz (ex. `output_folder`, `document_output_language`). A seção `bcp` **não** é mais gravada aqui; uma seção legada preexistente é **removida** (strip) no merge — esse é o caminho de migração yaml→toml (re-rodar o setup migra). Chaves user-only (`user_name`, `communication_language`) **nunca** vão aqui.
- **`{project-root}/_bmad/config.user.yaml`** — settings pessoais, gitignorados: `user_name`, `communication_language` e qualquer variável de módulo marcada `user_setting: true`.
- **`{project-root}/_bmad/module-help.csv`** — registra as capabilities do módulo no sistema de help.

Além da config, o setup: aplica o **capability gate BMAD ≥6.6.0**, semeia o `bcp-baseline.yaml` por categoria, registra o agente Bruno no manifest, e emite um override `customize.toml` que conecta o scoring BCP ao workflow `bmad-create-story`.

Os scripts de config usam um padrão anti-zombie — a seção do módulo em `custom/config.toml` tem suas chaves gerenciadas sobrescritas (upsert, preservando chaves human-authored), e qualquer seção `bcp` legada no `config.yaml` é removida, então valores velhos nunca persistem em split-brain.

`{project-root}` é um **token literal** nos valores de config — nunca substitua por um caminho real. Sinaliza ao LLM consumidor que o valor é relativo à raiz do projeto.

## Conventions

- Bare paths resolvem da skill root (`scripts/`, `assets/`).
- `{skill-root}` resolve o diretório instalado desta skill (onde vive `customize.toml`).
- `{project-root}`-prefixed paths resolvem da raiz do projeto.

## Capability Gate (rodar PRIMEIRO)

BCP requer **BMAD ≥6.6.0** — o framework de hooks do `customize.toml` (`activation_steps_*`, `persistent_facts`) é a superfície de integração que o BCP usa. Greenfield: sem caminhos de compat para versões antigas.

```bash
python3 scripts/detect_bmad_capability.py --project-root "{project-root}"
```

O script lê a versão precisa de `{project-root}/_bmad/_config/manifest.yaml` e imprime JSON em stdout. Trate o exit code:

- **Exit 0** (`bmad-6.6.0+`) — prossiga com o setup.
- **Exit 1** (`bmad-too-old`) — aborte: "BCP v0.1.0 requer BMAD ≥6.6.0. Detectado {detected_version}. Atualize o BMAD com `npx bmad-method install` e re-rode `/bmad-bcp-setup`."
- **Exit 2** (`bmad-not-installed`) — aborte: "BMAD não está instalado neste projeto. Rode `npx bmad-method install` primeiro, depois `/bmad-bcp-setup`."

## On Activation

1. **Resolver customização do workflow:** rode `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. Guarde `activation_steps_prepend`, `activation_steps_append`, `persistent_facts` e `on_complete` para os passos posteriores. Se o script falhar, resolva o bloco `workflow` lendo `{skill-root}/customize.toml` + os overrides team/user em `{project-root}/_bmad/custom/bmad-bcp-setup.{toml,user.toml}` (escalares: override vence; arrays: append).
2. **Prepend steps:** execute cada entrada de `workflow.activation_steps_prepend` em ordem.
3. **Persistent facts:** trate cada entrada de `workflow.persistent_facts` como contexto fundacional pela sessão toda. Entradas com prefixo `file:` carregam o conteúdo do path/glob sob `{project-root}`; demais são fatos verbatim.
4. Leia `assets/module.yaml` para metadados e definições de variáveis (o campo `code` é o identificador do módulo).
5. Verifique se já há config do módulo — seção `[modules.bcp]` em `{project-root}/_bmad/custom/config.toml`, ou uma seção `bcp` legada em `{project-root}/_bmad/config.yaml`. Se houver, informe que é uma atualização (a legada será migrada para toml).
6. Verifique config legacy per-module em `{project-root}/_bmad/bcp/config.yaml` e `{project-root}/_bmad/core/config.yaml`. Se existirem:
   - Sem seção `bcp` no `config.yaml` consolidado → **install fresco**: informe que config do installer foi detectada e será consolidada.
   - Com seção `bcp` já presente → **migração legacy**: informe que valores legacy serão usados como defaults de fallback.
   - Em ambos os casos, os arquivos/diretórios per-module são limpos ao final.
7. **Append steps:** execute cada entrada de `workflow.activation_steps_append` em ordem.

Se o usuário passar argumentos (ex. `aceitar todos os defaults`, `--headless`, ou valores inline), mapeie os valores fornecidos, use defaults para o resto e pule o prompting interativo. Ainda exiba o resumo de confirmação no final.

## Collect Configuration

Peça os valores ao usuário. Mostre defaults entre colchetes. Apresente tudo junto para o usuário responder de uma vez só com o que quer mudar. Nunca diga "aperte enter" ou "deixe em branco" — num chat ele precisa digitar algo.

**Prioridade de default** (maior vence): valores existentes no config novo > valores legacy > defaults de `assets/module.yaml`.

**Core config** (só se nenhuma chave core existir): `user_name` (default: BMad), `communication_language` e `document_output_language` (default: Português do Brasil — pergunte como uma única questão de idioma), `output_folder` (default: `{project-root}/_bmad-output`). `user_name` e `communication_language` vão exclusivamente para `config.user.yaml`.

**Module config**: leia cada variável em `assets/module.yaml` com campo `prompt` e pergunte usando esse prompt e seu default (ou valor legacy se disponível).

**Destaque obrigatório — consentimento de overwrite:** a variável `bcp_overwrite_estimated_hours` é load-bearing. Deixe explícito ao usuário que instalar com `yes` autoriza o BCP a sobrescrever `estimated_hours` nas stories (a auditoria original fica preservada em `estimated_hours_pre_bcp`). Não trate como um prompt qualquer — confirme que o usuário entendeu o consentimento.

## Write Files

Escreva um JSON temporário com as respostas no formato `{"core": {...}, "module": {...}}` (omita `core` se já existir). Rode os dois scripts (paralelos — escrevem arquivos diferentes):

```bash
uv run scripts/merge-config.py --config-path "{project-root}/_bmad/config.yaml" --custom-config-path "{project-root}/_bmad/custom/config.toml" --user-config-path "{project-root}/_bmad/config.user.yaml" --module-yaml assets/module.yaml --answers {temp-file} --legacy-dir "{project-root}/_bmad"
python3 scripts/merge-help-csv.py --target "{project-root}/_bmad/module-help.csv" --source assets/module-help.csv --legacy-dir "{project-root}/_bmad" --module-code bcp
```

> **Nota (PEP 723):** só o `merge-config.py` roda via `uv run` — ele declara dependências de terceiros (`pyyaml`, `tomlkit`) no header inline `# /// script`. Com `python3` puro falha: `Error: tomlkit is required (PEP 723 dependency)`. `uv run` lê o header e provisiona num ambiente efêmero. Os demais scripts deste skill são stdlib-only e rodam com `python3`.

`merge-config.py` grava a seção do módulo `[modules.bcp]` em `custom/config.toml` (**toml-first**, via `tomlkit` — preserva comentários/outras seções), grava só as chaves core no `config.yaml`, e faz **strip** de qualquer seção `bcp` legada do `config.yaml` (migração yaml→toml). O `--custom-config-path` tem default `{dir do --config-path}/custom/config.toml`, mas passá-lo explícito deixa o destino claro. Ambos imprimem JSON em stdout (confira `custom_config_path`, `module_keys`). Se algum sair não-zero, mostre o erro e pare. Os scripts leem valores legacy como fallback e apagam os arquivos legacy após o merge — confira `legacy_configs_deleted` e `legacy_csvs_deleted`.

## Register Agent in Party Mode Roster

Registre o agente Bruno para ele entrar no roster do Party Mode e features agent-aware.

O Party Mode monta o roster a partir da tabela `[agents]` resolvida pelo `resolve_config.py` — deep-merge de `{project-root}/_bmad/config.toml` (base) e `{project-root}/_bmad/custom/config.toml` (team). Os módulos oficiais têm suas entradas `[agents.*]` escritas no `config.toml` base pelo installer do BMAD core, mas um **módulo custom** como o BCP nunca é escrito lá — então sem este passo o Bruno fica instalado como skill mas invisível ao Party Mode (`/bmad-party-mode` nunca o lista). Registre-o na camada team `custom/config.toml`, que sobrevive a re-install:

```bash
uv run scripts/register-party-agent.py --project-root "{project-root}" --fragment assets/agent-manifest-fragment.csv
```

O script faz upsert de `[agents.bmad-bcp-agent-bruno]` (anti-zombie, idempotente) a partir dos valores do `agent-manifest-fragment.csv`, preservando comentários e outras seções (tomlkit round-trip). Roda via `uv run` pela dependência PEP 723 `tomlkit`. Confira `agent_key` e `custom_config_path` no JSON.

Em caso de sucesso, informe: "Agente Bruno registrado no roster do Party Mode (`_bmad/custom/config.toml` → `[agents.bmad-bcp-agent-bruno]`) — rode `/bmad-party-mode` para vê-lo. Para destacá-lo, adicione um grupo curado (ex.: sala de planning/estimativa) em `_bmad/custom/bmad-party-mode.toml`."

### `agent-manifest.csv` legado (opcional, compat)

Layouts BMAD antigos também leem `{project-root}/_bmad/_config/agent-manifest.csv`. Se esse arquivo existir, faça merge adicional do fragment (inócuo onde não é usado). Se não existir, pule — o registro em `[agents]` acima é o que o Party Mode de fato lê.

```bash
python3 scripts/merge-help-csv.py --target "{project-root}/_bmad/_config/agent-manifest.csv" --source assets/agent-manifest-fragment.csv --module-code bcp
```

## Seed Baseline

Semeie o baseline por categoria para o cold start. Idempotente — se o arquivo já existe, não toca (exceto `--force`).

```bash
python3 scripts/seed_baseline.py --baseline-path "{project-root}/<bcp_baseline_path resolvido>" --seed <bcp_baseline_seed> --min-samples <bcp_baseline_min_samples> --rolling-window <bcp_baseline_rolling_window>
```

Use os valores coletados (`bcp_baseline_path`, `bcp_baseline_seed`, `bcp_baseline_min_samples`, `bcp_baseline_rolling_window`). Resolva o token `{project-root}`/`{output_folder}` do path para o caminho real apenas na operação de filesystem. Cheque o campo `action` no JSON (`created` | `skipped_exists`) para o resumo.

## Create Output Directories

Crie os diretórios de saída configurados. Para operações de filesystem, resolva o token `{project-root}` para o caminho real e crie cada valor path-type do `config.yaml` que ainda não existe (`output_folder` e qualquer variável de módulo cujo valor comece com `{project-root}/` ou `{output_folder}/`). Os paths no config continuam com o token literal; só os diretórios em disco usam o path resolvido. Use `mkdir -p`.

## Cleanup Legacy Directories

Após os merges, remova os diretórios de pacote do installer. As skills já estão instaladas em `{project-root}/.claude/skills/` — `{project-root}/_bmad/` só deve conter config.

```bash
python3 scripts/cleanup-legacy.py --bmad-dir "{project-root}/_bmad" --module-code bcp --skills-dir "{project-root}/.claude/skills"
```

O script verifica que toda skill nos diretórios legacy existe em `.claude/skills/` antes de remover. Idempotente — diretórios ausentes não são erro. Se sair não-zero, mostre o erro e pare. Use `directories_removed` e `files_removed_count` no JSON para o resumo.

## Generate Customize Overrides (BCP hooks)

### Hook 1 — Scoring BCP no `bmad-create-story`

Conecte o scoring BCP ao `bmad-create-story` emitindo um override `customize.toml` no projeto consumidor. Sobrevive a upgrades do BMAD core porque vive em `{project-root}/_bmad/custom/`, que o BMAD nunca sobrescreve. O capability gate ≥6.6.0 já foi validado no início.

```bash
python3 scripts/inject_customize.py --project-root "{project-root}" --skill bmad-create-story
```

Política de conflito **abort + `--force`**: se o destino já existe, o script sai com exit 3 e não toca no arquivo. Mostre a mensagem verbatim ao usuário (inclui o path e como re-rodar com `--force`). **Não** re-tente com `--force` automaticamente — a escolha é do usuário.

### Hook 2 — Auto-recalibrate no `bmad-code-review` (issue #18)

Conecte o recalibrate BCP ao `bmad-code-review` usando **modo merge** (`--merge`). Este hook acrescenta a instrução de recalibração ao `on_complete` existente — sem sobrescrever o arquivo caso outro módulo (ex.: PULSE) já o tenha registrado. Se o arquivo não existir, cria do zero.

```bash
python3 scripts/inject_customize.py --project-root "{project-root}" --skill bmad-code-review
```

O script detecta automaticamente o modo merge para `bmad-code-review`. Exit codes: `0` = sucesso (criou ou fez merge), `1` = já presente (idempotente, sem modificação). Nunca sai com exit 3 em modo merge — não há conflito destrutivo.

**Comportamento em runtime:** ao fim de cada code review, o LLM verifica se a story tem `bcp.total` no frontmatter. Se sim, lê `actual_hours` da seção `pulse_metrics` do sprint-status e invoca `bmad-bcp-recalibrate`. Se qualquer dado estiver ausente, pula silenciosamente. Idempotente — `recalibrate.py` deduplica por `id` da story.

### .gitignore Allowlist Snippet

Imprima um snippet copy-paste para o `.gitignore` do consumidor versionar `{project-root}/_bmad/custom/*.toml` (overrides de time) mantendo `*.user.toml` privado. Script read-only — nunca modifica o arquivo.

```bash
python3 scripts/print_gitignore_snippet.py --project-root "{project-root}"
```

Mostre o stdout do script ao usuário.

### Post-Injection

Informe:

- "Scoring BCP integrado via `{project-root}/_bmad/custom/bmad-create-story.toml`. Toda story criada por `/bmad-create-story` será pontuada automaticamente."
- "Auto-recalibrate integrado via `{project-root}/_bmad/custom/bmad-code-review.toml`. A cada code review concluído, o BCP verifica se a story tem dados suficientes para recalibrar o baseline."
- "Para desabilitar o scoring: delete `{project-root}/_bmad/custom/bmad-create-story.toml`."
- "Para desabilitar o auto-recalibrate: remova a instrução BCP do `on_complete` em `{project-root}/_bmad/custom/bmad-code-review.toml`."

Se algum passo acima falhar, **não** bloqueie o resto do setup. Reporte a falha e continue — o usuário pode re-rodar a peça que falhou depois.

## Confirm

Use o JSON dos scripts para exibir o que foi escrito: valores de config (core na raiz do `config.yaml`, módulo em `custom/config.toml [modules.bcp]` — `module_keys`/`custom_config_path`), user settings em `config.user.yaml` (`user_keys`), entradas de help, install fresco vs update, baseline semeado vs preexistente, migração legacy/strip da seção `bcp` do yaml (se houve). Depois exiba o `module_greeting` de `assets/module.yaml`.

## Outcome

Uma vez conhecidos `user_name` e `communication_language` (de input coletado, argumentos ou config existente), use-os consistentemente pelo resto da sessão: trate o usuário pelo nome configurado e comunique no `communication_language` configurado.

## On Completion

Após o Outcome (e depois que o install completou — config gravada, baseline semeado, agente registrado, hooks injetados, legacy limpo), siga `workflow.on_complete` resolvido na ativação:

- Valor **vazio** (default) → encerre sem ação adicional.
- Valor **não-vazio** → siga a string verbatim como instrução terminal — é o último passo antes de sair.

**Invariantes (sempre verdade — qualquer override precisa respeitar):**

- O hook roda **após** o install — todos os artefatos (config, baseline, manifest, customize hooks) já estão no disco.
- O hook **NÃO pode mutar** os artefatos do install (single-writer principle — os scripts de setup são donos desses arquivos durante a execução).
- Erro no hook é **warn**, não rollback — o install já completou.
- Em install falho (script sai não-zero antes do Outcome) o hook é **pulado**.

Customizar override (team-level, committed): edite `{project-root}/_bmad/custom/bmad-bcp-setup.toml`. User-level (gitignored): `bmad-bcp-setup.user.toml`.

> **Nota sobre persistência do override:** o `customize.toml` do `bmad-bcp-setup` (defaults da skill) é regravado a cada re-instalação. Para hooks duráveis, **sempre** use as camadas `{project-root}/_bmad/custom/*.toml` (team) ou `*.user.toml` (user) — essas o BMAD nunca sobrescreve.
