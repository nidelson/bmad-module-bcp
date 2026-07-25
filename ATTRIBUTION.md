# Atribuição

## Framework Business Complexity Points (BCP) — MIT

O **Business Complexity Points (BCP)** é um framework de normalização de
complexidade de software criado pela **CI&T** (www.ciandt.com) em **2015**,
adotado pelo **Itaú Unibanco** em 2018 e evoluído em parceria entre os dois.

Em **maio de 2026**, CI&T e Itaú publicaram o framework como open source sob
**Licença MIT**:

- Repositório oficial: https://github.com/flow-ciandt/bcp-agent
- Licença: MIT — `Copyright (c) 2025 CI&T HyperX`
- Página institucional: https://ciandt.com/us/en-us/complexitypoints
- Ruler canônico (imagem): https://dmwnh9nwzeoaa.cloudfront.net/2020-12/bcp-ruler.png

A régua normativa — perspectivas de complexidade, definições por tamanho,
pontos Fibonacci e exemplos — está materializada no repositório oficial em
`src/bcp/prompts/step0…step6.jinja2`, sob a mesma licença MIT.

### O que a MIT exige

Preservar o aviso de copyright e o texto da licença nas cópias e nas partes
substanciais do software. Este arquivo cumpre esse papel para a régua embarcada
em `skills/bmad-bcp-rule-card/assets/bcp-rule.yaml`.

### O que mudou em relação à publicação anterior

Até maio de 2026 o BCP circulava sob **CC BY-NC-ND 4.0**, e este módulo foi
construído sobre aquela premissa. Três restrições daquela licença **não se
aplicam à publicação MIT**:

| Termo anterior         | Efeito no módulo                        | Situação sob MIT                        |
| ---------------------- | --------------------------------------- | --------------------------------------- |
| **ND** (SemDerivações) | Régua embarcada era legalmente imutável | Modificação permitida                   |
| **NC** (NãoComercial)  | Uso comercial vedado                    | Uso comercial permitido                 |
| **BY** (Atribuição)    | Aviso e link obrigatórios               | Copyright e licença seguem obrigatórios |

### A régua continua imutável — agora por decisão de projeto

A imutabilidade de `bcp-rule.yaml` **deixou de ser imposição legal** e passa a
ser **decisão de design deste módulo**, mantida pelo mesmo motivo prático de
sempre: um score de BCP só é comparável entre times se a régua for a mesma.
Editar elementos, definições ou pontos produz números que parecem BCP e não são.

Quem quiser divergir da régua canônica agora **pode**, legalmente. Mas deve
fazê-lo alterando `rule_version` e assumindo que os scores resultantes não são
comparáveis com os de outra instalação.

Os blocos editoriais `hints` seguem mutáveis por natureza — são autorais deste
módulo, não parte do framework da CI&T.

## Código do módulo — MIT

O código-fonte do `bmad-module-bcp` (skills, scripts, schemas) é licenciado sob
a Licença MIT (ver `LICENSE`).

**Com a republicação do framework, módulo e régua passam a compartilhar a mesma
licença (MIT).** O split de licenças que antes era load-bearing no design deixou
de existir.

---

_Verificação da mudança de licença feita em 2026-07-25 contra o `LICENSE` do
repositório `flow-ciandt/bcp-agent` e o anúncio público de maio/2026. É
alteração de postura jurídica — convém revisão humana antes de apoiar decisão
comercial nela._
