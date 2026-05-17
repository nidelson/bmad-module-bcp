---
title: "Product Brief: bmad-module-bcp"
status: "complete"
created: "2026-05-07"
updated: "2026-05-08"
inputs:
  - "/Users/nidelson/Projects/nidelson/sip/docs/superpowers/specs/2026-05-07-bcp-pulse-integration-design.md"
  - "https://github.com/nidelson/bmad-module-pulse/issues/30"
  - "https://github.com/nidelson/bmad-module-bcp/issues/1"
  - "https://ciandt.com/us/en-us/complexitypoints"
  - "/Users/nidelson/Projects/nidelson/bmad-module-pulse/README.md"
mode: autonomous
language: pt-BR
translation_of: original-en-2026-05-07
---

# Product Brief: bmad-module-bcp

## Sumário Executivo

Se você é um squad CI&T-shaped reportando produtividade de IA para a liderança, hoje você não consegue defender o número. Suas estimativas vivem em **Business Complexity Points (BCP)** — o framework publicado pela CI&T de pontuação por 10 elementos × 5 tamanhos, nascido do "Re-Thinking Story Points" para entregar uma unidade de complexidade normalizada, objetiva e comparável entre times (segundo a CI&T, os cinco pilares do BCP são Communication, Normalized System, Comparisons, Best Practices e Quality). Já o módulo de telemetria do BMAD (PULSE) fala em horas, story points ou T-shirts. Ou você re-estima cada story duas vezes, ou maquia o número, ou abandona a telemetria.

`bmad-module-bcp` fecha essa lacuna. É um módulo de scoring BMAD-nativo, instalável em minutos, com um agente dedicado (Bruno) que faz auto-score via Claude Sonnet 4.6, apresenta um dry-run review e então **deriva `estimated_hours` a partir de `BCP × baseline h/BCP por categoria`**, gravando o resultado de volta no arquivo da story. PULSE consome esse número de forma agnóstica e renderiza um dashboard condicional ciente de BCP. Dois módulos, um contrato schema-mediated, sem fork.

Estrategicamente, esta é a primeira instância de um padrão maior: uma implementação de referência para embarcar qualquer framework de estimativa publicado e licenciado dentro de um loop de desenvolvimento assistido por IA, sem violar atribuição e sem forkar o consumidor (PULSE). BCP é a cunha; o contrato é o ativo.

**Por que agora:** times CI&T-shaped estão adotando BMAD e pedindo telemetria de leverage do PULSE hoje, e a CI&T publicou o BCP sob CC BY-NC-ND 4.0 justamente para difundir o framework. Uma implementação fiel, com atribuição correta e BMAD-nativa cabe nessa janela antes que alguém forke o PULSE ou reconstrua tudo em planilha.

## O Problema

Três dores convergem em todo time CI&T-shaped que tenta medir leverage de IA dentro do BMAD hoje:

1. **Descasamento de metodologia de estimativa.** PULSE aceita `hours`, `story_points` ou `tshirt`. Nenhum mapeia para BCP, que é a linguagem de estimativa contratualmente exigida nas orgs CI&T-shaped. O time é forçado a re-estimar duas vezes ou abandonar um dos sistemas.

2. **Sem baseline de escopo defensável.** Agentes de PM como a Amelia escrevem `estimated_hours` por heurística. O número derrapa entre stories, devs e projetos. PULSE então calcula leverage ratios em cima dessa derrapagem — preciso, não acurado. A liderança vê "6.9x leverage" e não distingue ganho real de produtividade de estimativa otimista.

3. **Não existe tooling BCP nativo.** BCP é um framework publicado (a introdução "Comparing Apples to Apples" e a série em três partes "Measure productivity in Agile before it's too late" da CI&T articulam a metodologia), mas vive em PDFs, planilhas e conhecimento tribal. Não há agente que pontue um arquivo de story, nem baseline que aprenda com o tempo, nem trilha de auditoria quando o escopo cresce no meio do sprint, nem rule card pra consultar inline. Soluções adjacentes (plugins de complexity no Jira, contadores de Function Points, sugeridores de story points com IA) falham em pelo menos um critério: AI-loop-native, embarque correto da licença, maturação de baseline por categoria, ou integração com BMAD. Cada time reconstrói o mesmo tooling sombra em privado.

**Custo do status quo:** times CI&T-shaped não conseguem adotar PULSE sem rodar um processo de scoring manual paralelo. A adoção do PULSE empaca exatamente na audiência mais propensa a financiar e validar o produto. O ecossistema permanece ancorado em estimativa subjetiva.

## A Solução

Um módulo BMAD frouxamente acoplado que vive ao lado do PULSE, não dentro dele. Os dois módulos se comunicam por um **contrato documentado de frontmatter**: BCP escreve, PULSE lê, nenhum dos dois importa o outro, e cada um degrada graciosamente quando o outro está ausente.

**Experiência do desenvolvedor, ponta-a-ponta:**

- `/bmad-create-story 5.7` — Amelia cria o draft normalmente.
- Um hook `on_complete` injetado dispara `/bmad-bcp-score 5.7` automaticamente.
- Bruno faz auto-score nos 10 elementos × 5 tamanhos, apresenta um breakdown compacto para dry-run review e pergunta antes de finalizar quando a confiança fica abaixo do threshold. O modo `--non-interactive` auto-confirma acima do threshold para pipelines de CI ou marca `bcp.needs_review: true` para passagem humana assíncrona.
- Na confirmação: BCP **sobrescreve** `estimated_hours` (consentimento dado no install, com diff por story impresso a cada score), preserva o original como `estimated_hours_pre_bcp` e escreve o bloco `bcp.*` completo.
- `track-start` e `track-done` do PULSE consomem `estimated_hours` de forma agnóstica ao escritor e expõem uma seção condicional "📊 BCP Productivity" no dashboard.
- Após done, `/bmad-bcp-recalibrate 5.7` atualiza o baseline rolling de `h/BCP` por categoria (janela FIFO de 10, semente em 4.13 da referência CI&T até 5+ amostras). O `track-done` do PULSE imprime um lembrete de uma linha para que o recalibrate manual permaneça visível até o auto-hook entrar em v0.2.0.

**Para o tech lead:** todo leverage ratio do PULSE passa a ser rastreável até um número de escopo normalizado, uma flag explícita de maturidade do baseline e uma trilha completa de ΔBCP em `bcp.history` sempre que o escopo cresce no meio da story.

**Para o IC que só quer entregar:** Bruno custa ~20 segundos por story; em troca, o score viaja com o arquivo, scope creep é capturado automaticamente e o time para de re-estimar no Jira só pra alimentar o reporting do PM.

## O Que Torna Isto Diferente

- **Primeiro tooling BCP BMAD-nativo.** Soluções adjacentes existem (plugins de complexity no Jira, contadores de Function Points, sugeridores story-points-com-IA); nenhuma entrega como módulo BMAD-instalável com embarque correto da licença, scoring AI-loop-native e maturação de baseline por categoria. Uma tabela curta de comparação vai no README.
- **Integração schema-mediated, não acoplamento zero.** BCP e PULSE compartilham um contrato documentado de frontmatter (`estimated_hours`, `estimated_hours_basis`, `bcp.*`, `pulse_estimation_method=bcp`). Nenhum importa o outro. Cada um funciona standalone. O contrato é versionado e testado.
- **Embarque fiel à licença.** A regra 10×5 da CI&T é embarcada imutável sob atribuição CC BY-NC-ND 4.0; apenas hints editoriais são mutáveis. O código do módulo é MIT. ATTRIBUTION.md traz tabela de permissões em linguagem clara; postura jurídica é pré-requisito de aceite v0.1.0, não rodapé.
- **Auto-score híbrido, não estimativa LLM cega.** Bruno propõe; o humano confirma. Dry-run review é o contrato. Resiliência a Goodhart: rescore opcional por segundo agente para spot-check + detecção de anomalia de baseline (off por default, opt-in para orgs com múltiplos squads).
- **Baseline próprio, não média global.** `h/BCP` rolling por categoria (backend / web / mobile / fullstack), com tratamento explícito de cold start. Até maturar, leverage ratios são suprimidos dos números de manchete e claramente rotulados como não-calibrados — evitando a crise de credibilidade do tipo "leverage parecia alto no modo seed e depois caiu".
- **Trilha de auditoria por padrão.** `bcp.history` captura todo rescore com delta e razão, com cap de 50 entradas. Scope creep vira artefato visível, não atualização silenciosa de estimativa.
- **Scoring retroativo como capability de primeira classe.** Squad X que adota no sprint 12 não começa do seed — `/bmad-bcp-score-batch` e `/bmad-bcp-backfill-baseline` pontuam stories históricas e bootstrappam um `h/BCP` calibrado a partir de evidência real no dia um. Entradas retroativas ficam marcadas em `bcp.history` (auditoria explícita) e sinalizadas com flag de confiança quando o contexto está raso.

## Para Quem Este Produto Serve

**Usuário primário: time adotando BMAD em organização CI&T-shaped.** Tech lead ou senior dev configurando BMAD para um squad de 1–8 engenheiros que precisa reportar estimativas em BCP internamente e quer telemetria de leverage do PULSE em cima. Sucesso = instalar os dois módulos, pontuar as próximas 5 stories sem re-estimar manualmente, ver um baseline `h/BCP` crível emergir até o sprint 2 e entrar em uma review de liderança com um único número defensável.

**Usuário secundário: squad piloto da CI&T (design partner).** Time interno da CI&T validando que a regra embarcada, o comportamento do baseline e o dashboard mapeiam para a realidade deles. Design partner é **pré-requisito de Fase 0**, não item de wishlist — o kickoff trava até existir um partner nomeado com compromisso por escrito.

**Usuário terciário: consultorias e agências por hora-faturada.** Qualquer um defendendo contrato fixed-scope ou scope creep para clientes precisa de um número de complexidade normalizado e auditável. A trilha `bcp.history` é feature de defesa contratual; BCP vira linguagem de escopo, não apenas linguagem CI&T.

**Modelo operacional:** mantenedor único (Nidelson) em v0.1.0 com self-dogfooding dentro deste próprio repositório. Plano de sustentabilidade: caminho de sucessão escrito pós-design-partner, co-manutenção opt-in com a CI&T durante F12, schema versionado estável para que o embarque da regra sobreviva a transições de mantenedor.

## Critérios de Sucesso

**v0.1.0 aceito quando:**

- Self-dogfood ponta-a-ponta: pelo menos uma story de implementação do BCP pontuada por Bruno → trackeada por Levi → done → recalibrada, todas as fases rastreáveis no git.
- Qualidade do auto-score: ≥80% no-adjust rate no batch de dogfood F11 é **alvo aspiracional**, não claim estatístico — medido contra ~5–10 stories com adjudicação manual. Aceite com confiança menor é documentado e revisitado pós-design-partner.
- Design partner CI&T identificado, aceita revisão da spec v0.1.0 e roda pelo menos uma story (pré-requisito de Fase 0).
- Ambos os módulos publicados: `bmad-module-bcp` v0.1.0 e `bmad-module-pulse` v0.5.0 (aditivo, sem breaking changes).
- Pirâmide de testes verde: unit ≥90%, integration ≥80%, 3 cenários E2E (full lifecycle, standalone-no-pulse, standalone-no-bcp).
- Documentação: PT-BR canônica (`README.pt-BR.md` manual completo, integration guides, tech-refinement) + EN-shell mínima (`README.md` vitrine + quickstart) + `ATTRIBUTION.md` EN-primary com mirror PT-BR. Política de localização formalizada em `docs/ADR/0001-localization-strategy.md`.
- Matriz de compatibilidade BCP↔PULSE publicada em ambos os READMEs.

**Sinais de saúde pós-release:** taxa de maturação do baseline por categoria; visibilidade de scope creep (% de stories com `bcp.history` não-vazio); taxa de renderização da seção BCP no dashboard em projetos com ambos os módulos; recalibrate-lag (stories done sem recalibrate aplicado).

## Escopo

**Dentro de v0.1.0:**

- Oito skills: `bmad-bcp-setup`, `bmad-bcp-score`, `bmad-bcp-score-batch`, `bmad-bcp-rescore`, `bmad-bcp-recalibrate`, `bmad-bcp-backfill-baseline`, `bmad-bcp-rule-card`, `bmad-bcp-agent-bruno`.
- Persona Bruno registrada em `agent-manifest.csv` (Party Mode auto-incluído). Bruno é camada facilitadora/coach — o módulo roda ponta-a-ponta sem ele em modo `--non-interactive`.
- Embedded `bcp-rule.yaml` imutável com atribuição CC BY-NC-ND 4.0.
- Baseline por categoria `bcp-baseline.yaml` (seed 4.13, `min_samples=5`, `rolling_window=10`).
- Contrato de frontmatter (validado por schema) e injeção de `customize.toml` em `bmad-create-story` com diagnóstico pre-flight e `--dry-run`.
- Extensão menor PULSE v0.5.0: `pulse_estimation_method=bcp`, snapshot `bcp_at_start`, telemetria `bcp_recorded`, dashboard condicional.
- Manual `/bmad-bcp-recalibrate` (lê `pulse_metrics.actual_hours` se PULSE presente, senão `--actual-hours <h>`).
- Modo de scoring `--non-interactive` é o **default** acima do confidence threshold; dry-run review do Bruno só abre quando há divergência com o draft da Amelia, score com baixa confiança ou rescore.
- **Scoring retroativo (primeira classe):** `/bmad-bcp-score-batch <glob>` pontua N stories existentes com auditoria `bcp.scored_by: retroactive`; `/bmad-bcp-backfill-baseline` encadeia score + recalibrate em ordem cronológica para bootstrap de baseline calibrado a partir do histórico do squad, eliminando o cold start. `--dry-run-cost` previa custo de tokens antes de chamadas LLM em massa.

**Fora de v0.1.0 (deferido para v0.2.0+):** auto-recalibrate hook em `bmad-pulse-track-done`; baselines multi-tenant; auto-score calibrado por ML; Web UI / IDE plugin; agregação cross-team de baseline; BCP virar `pulse_estimation_method` default (sempre opt-in).

## Visão

**A tese:** desenvolvimento assistido por IA torna estimativa subjetiva obsoleta. Pontue complexidade objetivamente uma vez, aprenda produtividade empiricamente por categoria, deixe a telemetria fechar o ciclo. BCP é a primeira instância viável — este módulo é a cunha.

**Frase-âncora da Visão:** *"Medir entrega de software pela velocidade real com que valor verificável chega ao usuário, não pela energia humana consumida no caminho."*

**12 meses:** toda adoção BMAD interna na CI&T sobe com BCP instalado por padrão. Baselines `h/BCP` por time viram artefatos portáveis carregados entre projetos, acelerando cold start. CI&T HQ consome dashboards agregados PULSE+BCP para reporting de produtividade de IA em nível organizacional. Stretch: time BCP da CI&T reconhece ou linka o módulo a partir dos materiais oficiais em [ciandt.com/complexitypoints](https://ciandt.com/us/en-us/complexitypoints), tornando o módulo o companheiro AI-loop canônico da própria metodologia publicada pela CI&T.

**24–36 meses:** o padrão de loose coupling generaliza para frameworks publicados adicionais (Function Points, COSMIC, T-shirt-with-history, rubricas customer-specific), provando que o contrato é o ativo. Bruno é extraído como agente standalone (CLI / GitHub Action) para times não-BMAD que querem scoring BCP sem se comprometer com o loop BMAD. Agregação anonimizada e opt-in de baselines cria um dataset `h/BCP` de referência para a indústria — moat que nenhum fork replica. A própria metodologia (palestras, estudos comparativos, conteúdo de certificação) vira o ativo durável, com este módulo como implementação de referência canônica.
