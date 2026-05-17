# ADR 0001 — Localization Strategy: PT-BR Primary for Narrative, EN for Code Surface

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-05-08 |
| Autor | Nidelson Gimenez |
| Revisores | Paige (agente BMAD Tech Writer), Mary (agente BMAD Analyst) — rodada party-mode |
| Substitui | — |

## Contexto

O `bmad-module-bcp` v0.1.0 mira primariamente organizações no formato CI&T que adotam BMAD. Estimativa interna: ~90% dos prováveis usuários da v0.1.0 são internos da CI&T, onde pt-BR é a língua de trabalho para gestão de entrega, teses, sprint reviews e a maior parte da documentação interna. O módulo irmão `bmad-module-pulse` foi publicado EN-primário com companheiro `README.pt-BR.md`.

O brief e as rodadas de party-mode trouxeram à tona duas pressões concorrentes:

1. **Redução de fricção.** A audiência ~90%-CI&T lê, escreve issues, defende teses e cria artefatos internos em pt-BR. Forçar EN-primeiro cria imposto de tradução tanto para o mantenedor quanto para os usuários.
2. **Normas open-source e preservação de opcionalidade.** "PT-BR-only" fecha a porta para escritórios CI&T não-brasileiros (EUA, Reino Unido, Portugal, Singapura, Austrália, Japão), para a hipótese-de-comprador não validada (Head of Delivery / COO de consultoria de médio porte fora do Brasil) e para a audiência terciária (consultorias e agências que faturam por hora).

Mary sinalizou o número "~90% pt-BR" como hipótese, não evidência, e pediu três medições baratas (headcount CI&T por escritório, língua de trabalho de squads fora do Brasil, sinal geográfico adjacente a BMAD) antes de apostar a estratégia nisso. Paige propôs um camadeamento limpo entre código e narrativa: identificadores técnicos sempre em EN, docs narrativos PT-BR-canônicos com uma casca de entrada em EN.

## Decisão

Adotar uma estratégia **PT-BR-primária para narrativa, EN para superfície de código** na v0.1.0, com governança explícita para o fluxo bilíngue que os usuários CI&T trarão (issues em PT-BR, discussões em PT-BR).

### Política por tipo de artefato

| Artefato | Língua | Notas |
|---|---|---|
| Identificadores de código (nomes de skill, slugs de agente, paths, comandos `/bmad-bcp-*`) | **EN** | Inegociável. Renomear depois quebra usuários instalados. |
| Chaves YAML, campos de frontmatter, JSON Schema, estrutura de arquivo baseline | **EN** | Interoperabilidade com o contrato PULSE; amigável a parsers. |
| Mensagens de Conventional Commits | **EN** | `release-please` e tooling de changelog esperam estrutura EN. |
| Nomes de branch | **EN** | Convenção GitHub, scriptável. |
| Títulos de issue | **PT-BR ou EN, escolha do autor** | Labels (`bug`, `enhancement`, `docs`, `licensing`, `pulse-integration`) permanecem EN para grep-abilidade. |
| Corpo de issue, threads de discussão, prosa de PR review | **Língua do autor — PT-BR plenamente bem-vindo e esperado de usuários CI&T** | Mantenedor responde na mesma língua do autor. |
| Descrições de PR | **PT-BR aceito; se o PR entrega feature relevante para changelog, anexar resumo de uma linha em EN para o `release-please`** | Híbrido permanece compatível com o tooling de release. |
| `README.md` (raiz) | **Casca EN mínima** (vitrine, comando de instalação, link para o README PT-BR) | Preserva findability no GitHub + descoberta por não-brasileiros. |
| `README.pt-BR.md` | **PT-BR canônico — manual completo** | O documento de onboarding real. |
| `docs/integration/*.md` (guias de integração PULSE, bmad-create-story) | **PT-BR canônico** + stub de quickstart em EN | Prosa longa segue a audiência. |
| `ATTRIBUTION.md` | **PT-BR canônico**; frase de crédito canônica da CI&T reproduzida verbatim em EN (crédito legal exato exigido pela CC BY-NC-ND, não narrativa) | Revisado 2026-05-17: doc em PT-BR (audiência ~90% CI&T-BR); o BY exige preservar o crédito como publicado — mantido verbatim EN dentro do doc PT-BR. |
| `CHANGELOG.md` | **EN** (gerenciado por release-please) | Tooling espera EN; espelho PT-BR opcional em `CHANGELOG.pt-BR.md`. |
| ADRs (`docs/ADR/*.md`) | **Títulos-EN + corpo-PT-BR aceitável** | Híbrido: títulos grepáveis em EN, corpo na língua do autor. Este ADR segue esse padrão. |
| Docs de tech-refinement (`docs/tech-refinement/`) | **PT-BR canônico** | Trilha de decisão interna. |
| Diálogo do agente Bruno, prosa de review dry-run, mensagens de erro, prompts ao usuário | **PT-BR primário** | Onde a fricção mora; otimização de UX para a audiência real. |
| Campos de texto livre `bcp.history.note` / `delta_reason` / log de scoring | **Língua do squad (padrão PT-BR)** | Trilha de auditoria na língua de quem escreve. Estrutura/chaves permanecem EN. |
| Template de prompt de auto-score do Bruno (`assets/prompts/auto-score.md`) | **Estrutura EN com exemplos PT-BR** | Engenharia de prompt se beneficia de scaffolding EN; exemplos few-shot em PT-BR para encaixe com a audiência. |

## Consequências

### Positivas

- Queda de fricção para ~90% da audiência no onboarding e uso diário.
- Preservação a custo zero da superfície open-source para descoberta não-CI&T (casca EN do README, identificadores EN, commits EN) — módulo permanece forkável, escaneável, citável.
- Usuários CI&T contribuem issues e PRs na língua nativa — barreira menor para feedback de contribuição.
- Mantenedor (único, pt-BR-nativo) escreve uma vez na língua da audiência, sem imposto de tradução na v0.1.0.
- Compatível com `release-please` e tooling padrão do GitHub.

### Negativas / riscos

- A descoberta não-CI&T de conteúdo narrativo é reduzida; novo usuário falante de EN cai na casca EN do README e pode desistir se o conteúdo PT-BR for o valor real.
- As três lacunas de evidência da Mary permanecem não validadas: este ADR aposta na hipótese ~90% sem respaldo numérico.
- Potencial design partner fora do Brasil (CI&T EUA, Reino Unido etc.) pode achar a superfície de docs insuficiente. Mitigação: ATTRIBUTION + quickstart EN do README cobrem o auto-onboarding mínimo; tradução EN completa pode ser encomendada reativamente.
- Adicionar paridade EN completa depois é esforço linear (~1-2 dias por épico, conforme estimativa da Paige), mas acumula se a v0.1.0 publicar muitos épicos antes da reavaliação.

### Custo de reversão

- **Baixo** para artefatos narrativos (traduzir uma vez quando necessário).
- **Zero** para superfície de código (já em EN).
- **Baixo** para issues/PRs (threads existentes podem ser traduzidas sob demanda se um revisor não-pt-BR entrar; ou simplesmente mantidas como registro histórico).

### Gatilho de reavaliação

Este ADR será revisitado em um dos seguintes eventos, o que vier primeiro:

1. Planejamento da v0.2.0 (~6 meses após a v0.1.0).
2. Identificação de design partner — se o escritório do parceiro for fora do Brasil, agendar reavaliação imediatamente e priorizar tradução do README EN + guias de integração como patch v0.1.x.
3. Primeira issue submetida externamente em EN que revele fricção causada por docs PT-BR-canônicos.

As três medições de lacuna de evidência da Mary (headcount CI&T por escritório, língua de trabalho de squads não-Brasil, sinal geográfico adjacente a BMAD) devem ser coletadas antes da reavaliação.

### Evidência coletada até agora (parcial)

- **Headcount CI&T — Brasil: ~7.000 colaboradores** (informado por Nidelson, 2026-05-08). Reforça substancialmente a hipótese de concentração pt-BR. Ainda pendente: breakdown de headcount não-Brasil (escritórios EUA, Reino Unido, Portugal, Singapura, Austrália, Japão, China) para confirmar a concentração proporcional. Língua de trabalho de squads não-Brasil e sinal geográfico adjacente a BMAD permanecem não medidos.

## Notas para agentes downstream

- A descrição de persona do Bruno, o bordão ("Régua antes de régua") e o diálogo de coaching são explicitamente desenhados para entrega em pt-BR; tradução EN exigirá reautoria fiel à persona, não tradução literal.
- Referências estilo Code Connect entre docs PT-BR e identificadores de código EN devem usar campos de frontmatter `lang` explícitos e ponteiros `translation_of:` quando contrapartes EN existirem.
- Este próprio ADR é estruturado conforme a política bilíngue: cabeçalhos/identificadores em EN + tom de prosa amigável a PT-BR para narrativa, espelhando o padrão recomendado para ADRs futuros.
