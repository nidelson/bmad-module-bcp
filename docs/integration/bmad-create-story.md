# Integração BCP ↔ bmad-create-story

> Documento canônico em PT-BR ([ADR 0001](../ADR/0001-localization-strategy.md)).
> Identificadores de skill/campo são EN.

## O que é este hook

`bmad-create-story` é o workflow padrão do BMAD que cria o arquivo de uma
story. O BCP **não modifica esse workflow** — ele se anexa via o sistema de
customização do BMAD (`customize.toml` / `persistent_facts`), de forma que o
scoring rode automaticamente logo após a story ser criada.

Resultado: você roda o fluxo normal de criação de story e o `estimated_hours`
já sai pontuado pelo BCP, sem passo manual.

## Como o `setup` registra o hook

`/bmad-bcp-setup` chama `inject_customize.py --skill bmad-create-story`, que
materializa o template
[`assets/customize-templates/bmad-create-story.toml`](../../skills/bmad-bcp-setup/assets/customize-templates/bmad-create-story.toml)
no `customize.toml` do consumidor. A única skill suportada por esse hook é
`bmad-create-story` (`SUPPORTED_SKILLS = {"bmad-create-story"}`).

O conteúdo entra em `[workflow].persistent_facts` com **semântica de append**
— não sobrescreve fatos de outros módulos (ex.: PULSE). É aditivo e
idempotente.

## O que o hook instrui o agente a fazer

Em resumo, o `persistent_fact` injetado diz ao agente BMAD: depois que
`bmad-create-story` gravar o arquivo da story (frontmatter com `story_id`,
`category` e `estimated_hours`), invoque `/bmad-bcp-score <caminho-da-story>`
**antes de encerrar**.

Comportamento do scoring disparado:

- **Não-interativo por padrão** acima do `bcp_confidence_threshold` (default
  `0.75`). Auto-score direto, sem interromper o fluxo.
- **Dry-run review** só quando: divergência relevante com a estimativa da
  Amelia, confiança baixa, ou rescore.
- **Idempotente** — preserva a trilha de auditoria (`estimated_hours_pre_bcp`
  gravado uma única vez, `estimated_hours_basis`).
- **Pula** stories exploratórias/spike sem implementação real.

## Editar ou regenerar

O arquivo gerado é editável, mas re-rodar `/bmad-bcp-setup` **aborta** se o
`customize.toml` já existe (proteção anti-clobber). Para regenerar
sobrescrevendo suas edições, passe `--force`.

## Convivência com o PULSE

PULSE também usa `persistent_facts` para o seu próprio hook. Por a semântica
ser de append, os dois coexistem no mesmo `customize.toml` sem conflito: o
agente recebe ambos os fatos e executa os dois (BCP pontua, PULSE registra).
Ordem não importa — BCP age na criação da story, PULSE no track-done.
