# BCP — Rule Card

## Overview

Renderiza a régua canônica **Business Complexity Points (BCP)** da CI&T para consulta rápida durante scoring: 10 elementos de complexidade × 5 tamanhos (XS, S, M, L, XL) na escala Fibonacci [1, 2, 3, 5, 8], com a definição de cada elemento e o descritor verbatim de cada célula.

A régua vem de `assets/bcp-rule.yaml` — transcrição **verbatim e imutável** do ruler publicado pela CI&T, licenciado **CC BY-NC-ND 4.0**. Esta skill só **lê e exibe**; nunca modifica a regra.

## Conventions

- Bare paths resolvem da skill root (ex.: `assets/bcp-rule.yaml`).
- `{skill-root}` resolve o diretório instalado desta skill (onde vive `customize.toml`).
- `{project-root}`-prefixed paths resolvem da raiz do projeto.

## On Activation

1. **Resolver customização do workflow:** rode `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. Guarde `activation_steps_prepend`, `activation_steps_append`, `persistent_facts` e `on_complete` para os passos posteriores. Se o script falhar, resolva o bloco `workflow` lendo `{skill-root}/customize.toml` + os overrides team/user em `{project-root}/_bmad/custom/bmad-bcp-rule-card.{toml,user.toml}` (escalares: override vence; arrays: append).
2. **Prepend steps:** execute cada entrada de `workflow.activation_steps_prepend` em ordem.
3. **Persistent facts:** trate cada entrada de `workflow.persistent_facts` como contexto fundacional pela sessão toda. Entradas com prefixo `file:` carregam o conteúdo do path/glob sob `{project-root}`; demais são fatos verbatim.
4. **Régua:** leia `assets/bcp-rule.yaml`. Trate `descriptors.<size>: null` como **célula vazia** no ruler canônico (não invente texto — o ruler é esparso de propósito; o ND da licença proíbe derivar/preencher).
5. **Filtro opcional:** aceite argumento de filtro — um nome ou slug de elemento (ex.: `business_rules`, `Boundaries`) → exiba só aquele elemento. Sem argumento → exiba a régua completa.
6. **Append steps:** execute cada entrada de `workflow.activation_steps_append` em ordem.

## Render

Produza um card legível em `{communication_language}`:

1. **Cabeçalho** — título "Business Complexity Ruler" + a escala de tamanhos com pontos: `XS=1 · S=2 · M=3 · L=5 · XL=8` (de `sizes`).
2. **Tabela** — uma linha por elemento, colunas: Elemento · Definição · XS · S · M · L · XL. Para células `null`, mostre um traço `—`. Marque os elementos com `always_there: true` (ex.: badge "sempre presente") — o ruler os agrupa sob "ALWAYS THERE".
3. **Rodapé de atribuição (OBRIGATÓRIO, nunca omitir)** — exiba o bloco `license.attribution` verbatim + o link `license.url`. A licença CC BY-NC-ND exige atribuição em toda redistribuição/exibição; emitir o card sem a atribuição viola a licença.

Se o terminal/contexto for estreito, prefira layout por elemento (lista) em vez de tabela larga — mas as três partes acima são invariantes.

## On Completion

Após o card ser renderizado, siga `workflow.on_complete` resolvido na ativação:

- Valor **vazio** (default) → encerre sem ação adicional.
- Valor **não-vazio** → siga a string verbatim como instrução terminal — é o último passo antes de sair.

**Particularidades desta skill (read-only):**

- Não há artefato persistido — o hook roda **após o display**, não após persistência. Use para oferecer follow-up actions, sugerir skills relacionadas, ou logar a consulta.
- O hook **NÃO pode modificar** `assets/bcp-rule.yaml` (ND da licença CC BY-NC-ND — imutabilidade load-bearing).
- Erro no hook é **warn** — o card já foi exibido.

Customizar override (team-level, committed): edite `{project-root}/_bmad/custom/bmad-bcp-rule-card.toml`. User-level (gitignored): `bmad-bcp-rule-card.user.toml`.

## Design Notes

- **Imutabilidade load-bearing:** `assets/bcp-rule.yaml` é CC BY-NC-ND 4.0 (ND = sem derivações). Nunca edite elementos/definições/descritores/pontos. Só os blocos `hints` editoriais (se existirem, marcados como autorais do BCP — não parte do framework CI&T) seriam mutáveis.
- Sem scripts: renderizar YAML→tabela é capability nativa do LLM; um script não agregaria valor (princípio outcome-driven).
- A definição de **New Domain Entities** no ruler canônico fala de "interactions ... sources/destinations ... durability of the information exchanged" — parece semântica de Boundaries, mas é o texto **publicado verbatim**. Não corrija: ND.
- **Customization surface:** `customize.toml` segue o padrão BMad — três camadas (skill defaults < team `<project>/_bmad/custom/*.toml` < user `*.user.toml`) resolvidas por `_bmad/scripts/resolve_customization.py`. `on_complete` é o extension point para encadear ações pós-display sem fork da skill.
