---
name: bmad-bcp-rule-card
description: Exibe a régua Business Complexity Points (10 elementos × 5 tamanhos). Use quando o usuário pedir 'mostrar régua BCP', 'rule card', 'ver a régua de complexidade' ou 'consultar a regra BCP'.
---

# BCP — Rule Card

## Overview

Renderiza a régua canônica **Business Complexity Points (BCP)** da CI&T para consulta rápida durante scoring: 10 elementos de complexidade × 5 tamanhos (XS, S, M, L, XL) na escala Fibonacci [1, 2, 3, 5, 8], com a definição de cada elemento e o descritor verbatim de cada célula.

A régua vem de `assets/bcp-rule.yaml` — transcrição **verbatim e imutável** do ruler publicado pela CI&T, licenciado **CC BY-NC-ND 4.0**. Esta skill só **lê e exibe**; nunca modifica a regra.

## Conventions

- Bare paths resolvem da skill root (ex.: `assets/bcp-rule.yaml`).
- `{project-root}`-prefixed paths resolvem da raiz do projeto.

## On Activation

Leia `assets/bcp-rule.yaml`. Trate `descriptors.<size>: null` como **célula vazia** no ruler canônico (não invente texto — o ruler é esparso de propósito; o ND da licença proíbe derivar/preencher).

Aceite argumento opcional de filtro: um nome ou slug de elemento (ex.: `business_rules`, `Boundaries`) → exiba só aquele elemento. Sem argumento → exiba a régua completa.

## Render

Produza um card legível em `{communication_language}`:

1. **Cabeçalho** — título "Business Complexity Ruler" + a escala de tamanhos com pontos: `XS=1 · S=2 · M=3 · L=5 · XL=8` (de `sizes`).
2. **Tabela** — uma linha por elemento, colunas: Elemento · Definição · XS · S · M · L · XL. Para células `null`, mostre um traço `—`. Marque os elementos com `always_there: true` (ex.: badge "sempre presente") — o ruler os agrupa sob "ALWAYS THERE".
3. **Rodapé de atribuição (OBRIGATÓRIO, nunca omitir)** — exiba o bloco `license.attribution` verbatim + o link `license.url`. A licença CC BY-NC-ND exige atribuição em toda redistribuição/exibição; emitir o card sem a atribuição viola a licença.

Se o terminal/contexto for estreito, prefira layout por elemento (lista) em vez de tabela larga — mas as três partes acima são invariantes.

## Design Notes

- **Imutabilidade load-bearing:** `assets/bcp-rule.yaml` é CC BY-NC-ND 4.0 (ND = sem derivações). Nunca edite elementos/definições/descritores/pontos. Só os blocos `hints` editoriais (se existirem, marcados como autorais do BCP — não parte do framework CI&T) seriam mutáveis.
- Sem scripts: renderizar YAML→tabela é capability nativa do LLM; um script não agregaria valor (princípio outcome-driven).
- A definição de **New Domain Entities** no ruler canônico fala de "interactions ... sources/destinations ... durability of the information exchanged" — parece semântica de Boundaries, mas é o texto **publicado verbatim**. Não corrija: ND.
