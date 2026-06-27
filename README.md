# BCP — Business Complexity Points Scorer

[![BMAD Module](https://img.shields.io/badge/BMAD-Module-blue)](https://docs.bmad-method.org/)
[![BMAD Version](https://img.shields.io/badge/BMAD-%3E%3D6.6.0-blue)](https://docs.bmad-method.org/)
[![GitHub release](https://img.shields.io/github/v/release/nidelson/bmad-module-bcp)](https://github.com/nidelson/bmad-module-bcp/releases)
[![Module: MIT](https://img.shields.io/badge/Module-MIT-yellow.svg)](LICENSE)
[![Rule: CC BY-NC-ND 4.0](https://img.shields.io/badge/BCP%20Rule-CC%20BY--NC--ND%204.0-lightgrey.svg)](ATTRIBUTION.md)

> **Estimativa por complexidade, não por chute.**

Pontue cada story pelo framework Business Complexity Points (BCP) da CI&T. O `estimated_hours` sai do score × baseline da categoria — recalibrado com horas reais do seu time.

🌐 [English 🇺🇸](README.en.md) · este é o manual canônico (PT-BR, default).

> ⚠️ **Documentação canônica em PT-BR.** O `README.en.md` é uma vitrine mínima que aponta para cá. Política completa: [ADR 0001](docs/ADR/0001-localization-strategy.md).

---

## O problema

Estimativa por "feeling" não escala e não audita. Dois desenvolvedores olham a mesma story e cravam 8h e 40h — sem critério compartilhado, sem rastro de como chegaram lá, sem como melhorar na próxima.

O **Business Complexity Points (BCP)** — framework publicado pela CI&T — troca o chute por uma régua: 10 elementos de complexidade, cada um dimensionado em 5 tamanhos (XS/S/M/L/XL), pontos Fibonacci. O score total vira horas via um fator `h_per_bcp` **por categoria** que o próprio módulo recalibra com horas reais.

## O que você ganha

- **Score reproduzível** — mesma story, mesma régua, mesmo total. Critério explícito no frontmatter.
- **`estimated_hours` derivado** — horas saem do score × baseline da categoria, não de opinião.
- **Baseline que aprende** — recalibração FIFO com horas reais; cada categoria sai do seed depois de N amostras.
- **Trilha de auditoria** — todo rescore entra em `bcp.history` (cap 50), com motivo do delta.
- **Acopla limpo com o PULSE** — BCP estima, PULSE mede eficiência. Zero import cruzado, degradação graciosa.

## Quick start

Instale o módulo num projeto BMAD (requer BMAD ≥ 6.6.0):

```bash
npx bmad-method install --custom-source github:nidelson/bmad-module-bcp
```

Depois, dentro do projeto:

```text
/bmad-bcp-setup            # configura, semeia o baseline, registra o customize hook
/bmad-bcp-rule-card        # consulta a régua (10 elementos × 5 tamanhos)
/bmad-bcp-score <story>    # pontua uma story e deriva estimated_hours
```

`setup` é o consentimento: ao instalar, você autoriza o BCP a ser dono do `estimated_hours` (o valor original da Amelia é preservado uma única vez em `estimated_hours_pre_bcp`). Para desligar isso, responda "Não" na pergunta `bcp_overwrite_estimated_hours` do setup.

## Skills inclusas

| Comando | Faz | Depende de |
| --- | --- | --- |
| `/bmad-bcp-setup` | Instala, configura, semeia baseline, registra o customize hook | — |
| `/bmad-bcp-rule-card` | Renderiza a régua BCP + atribuição CC BY-NC-ND | — |
| `/bmad-bcp-score` | Pontua uma story, deriva `estimated_hours` | setup |
| `/bmad-bcp-score-batch` | Pontua várias stories em lote (retroativo) | score |
| `/bmad-bcp-rescore` | Repontua story já pontuada (+ history + horas) | score |
| `/bmad-bcp-recalibrate` | Recalibra `h_per_bcp` por categoria com horas reais | score |
| `/bmad-bcp-backfill-baseline` | Mata o cold-start do baseline com o histórico do squad | recalibrate |
| `/bmad-bcp-agent-bruno` | Coach de complexidade (agente facilitador opcional) | setup |

## Bruno — seu coach de complexidade

`/bmad-bcp-agent-bruno` ativa o **Bruno**, agente facilitador opcional. Lema: *"Régua antes de régua."* Ele conduz o scoring elemento a elemento, questiona tamanhos inflados e explica a régua — útil para times entrando no BCP. Não é obrigatório: as skills `score`/`rescore` rodam sem ele.

## Como funciona

1. **Régua imutável.** `bcp-rule.yaml` é a régua da CI&T transcrita verbatim (CC BY-NC-ND — conteúdo não pode ser alterado; só hints editoriais são mutáveis).
2. **Score.** Cada elemento aplicável recebe um tamanho; o tamanho mapeia para pontos Fibonacci (XS=1, S=2, M=3, L=5, XL=8). `total` = soma do breakdown.
3. **Horas.** `estimated_hours = total × h_per_bcp(categoria)`. O fator vem do `bcp-baseline.yaml`.
4. **Aprendizado.** `recalibrate` alimenta horas reais numa janela FIFO por categoria; ao atingir `min_samples`, a categoria sai do seed (`is_seed: false`) e passa a usar a média móvel.

### Baseline e recalibração

| Parâmetro | Default | Significado |
| --- | --- | --- |
| `bcp_baseline_seed` | `4.13` | Horas por BCP no cold start (referência CI&T 2014) |
| `bcp_baseline_min_samples` | `5` | Amostras antes de uma categoria sair do seed |
| `bcp_baseline_rolling_window` | `10` | Tamanho da janela FIFO de recalibração |

O baseline vive em `{output_folder}/implementation-artifacts/bcp-baseline.yaml`. Squad com histórico? `/bmad-bcp-backfill-baseline <glob>` pontua o passado e calibra sem esperar o acúmulo natural.

### Os três números h/BCP

Existem **três** fatores `h_per_bcp` com papéis distintos — não confunda:

| Número | Ex. | Muda como | Deriva | Serve a |
| --- | --- | --- | --- | --- |
| **Seed** | `4.13` | uma vez, no setup | cold-start interno | bootstrap |
| **Recalibrado** (vivo) | `~0.5` | contínuo, automático (`recalibrate`) | `estimated_hours` — o **plano** | **previsibilidade** |
| **Referência** (frozen) | `5.0` | raro, por **governança** | `estimated_hours_reference` — a **âncora** | **alavancagem estável** |

`estimated_hours = total × recalibrado` segue a realidade do time — ótimo para planejar, mas faz a alavancagem (`estimated_hours / actual_hours`) colapsar para ~1× conforme a categoria calibra. `estimated_hours_reference = total × referência` usa um denominador **frozen** que não colapsa — é o número de ROI estável que a liderança pede. O BCP é dono de **toda** conversão BCP→horas (single-writer); o PULSE só **lê** os dois campos e divide. Sem `bcp_reference_h_per_bcp` configurado, a âncora cai no seed (computável desde o dia 1).

> **Guardrail:** mudar a referência **nunca** toca o fator recalibrado. Ninguém "compra" previsibilidade de entrega mexendo no número de marketing.

### Governança da reference rate

A reference rate é um knob deliberado (benchmark de marketing/indústria), não o seed. Mudá-la (ex.: `5h → 4h`) escala **toda** a alavancagem (×0.8) — vetor de Goodhart. Por isso é **governada e versionada**, nunca edit silencioso:

1. **Editar a config durável** — `bcp_reference_h_per_bcp` na camada `_bmad/custom/` (nunca `_bmad/config.toml`, installer-owned).
2. **Carimbar o ledger** — anexe uma entrada a `{output_folder}/implementation-artifacts/bcp-reference-ledger.yaml`:
   ```yaml
   - value: 4.0
     effective_from: "2026-07-01"
     previous: 5.0
     source: "Decisão C-Level Q3 — rebench vs mercado 2026"
   ```
3. **Forward-only (recomendado):** stories novas pontuam com o valor novo; stories velhas mantêm o `estimated_hours_reference` já frozen no frontmatter delas. Zero rewrite, auditável; o dashboard do PULSE rotula a quebra de regime.
4. **Retroativo (opcional):** `/bmad-bcp-rescore` recomputa a âncora de todas com a nova taxa — comparável ponta a ponta, mas apaga a base histórica.

`recalibrate` **não** participa: ele amadurece só o fator vivo. Seed e referência são imutáveis por ele.

## Configuração

Setup grava as respostas via o sistema de config em quatro camadas do BMAD. Principais variáveis:

| Variável | Default | Efeito |
| --- | --- | --- |
| `bcp_overwrite_estimated_hours` | `yes` | BCP é dono de `estimated_hours` (preserva `_pre_bcp`) |
| `bcp_non_interactive_default` | `yes` | Auto-score direto; dry-run só em divergência |
| `bcp_confidence_threshold` | `0.75` | Acima disso, pula o dry-run review |
| `bcp_estimation_basis` | `bcp` | Rótulo gravado em `estimated_hours_basis` |
| `bcp_reference_h_per_bcp` | _(seed)_ | Reference rate frozen da âncora de alavancagem; muda só por governança (ledger) |
| `bcp_data_folder` | `{output_folder}/implementation-artifacts` | Onde baseline e artefatos ficam |

Para mudar de forma durável: re-rodar o installer ou usar as camadas `_bmad/custom/`. **Nunca** editar `_bmad/config.toml` direto (installer-owned, regenerado a cada install).

## Estendendo as skills — hook `on_complete`

Toda skill BCP (exceto a persona Bruno) expõe um `on_complete` opt-in que roda **após** a persistência do artefato primário — `bcp-baseline.yaml`, frontmatter `bcp.*`, o que for. Default é vazio (zero comportamento); override em `_bmad/custom/<skill>.toml` (team, committed) ou `*.user.toml` (pessoal, gitignored).

**Exemplo — encadear recalibração com regen do dashboard PULSE:**

```toml
# _bmad/custom/bmad-bcp-recalibrate.toml
[workflow]
on_complete = "invoque a skill /bmad-pulse-dashboard (sem argumentos) para regenerar o dashboard cumulativo refletindo o novo h_per_bcp."
```

Quando `bmad-bcp-recalibrate` termina de gravar o baseline, o LLM lê esse texto como instrução terminal e invoca `/bmad-pulse-dashboard`. Idempotente, opt-in, e sem acoplamento — BCP não importa PULSE; o `customize.toml` do projeto consumidor é que decide chain.

**Invariantes do hook** (qualquer override precisa respeitar):

- Roda **após** persistência — o artefato já está no disco.
- **NÃO pode mutar** o artefato primário da skill (single-writer principle).
- Erro no hook é **warn**, não rollback — o trabalho já foi gravado.
- `--dry-run` (sem persistência) **pula** o hook.

Mesmas três camadas de override que o resto da config (skill defaults < team < user). Resolver: `python3 _bmad/scripts/resolve_customization.py --skill <skill-path> --key workflow.on_complete`.

## Integração com o PULSE

BCP e PULSE são frouxamente acoplados, **mediados por schema** — nenhum importa o outro. BCP escreve o bloco `bcp.*` e o `estimated_hours`; PULSE lê `estimated_hours` de forma agnóstica ao escritor e mede eficiência de IA. Nenhum ajuste no PULSE é necessário.

- BCP **escreve:** `estimated_hours`, `estimated_hours_pre_bcp`, `estimated_hours_basis`, `estimated_hours_reference`, `bcp.*`, `bcp.history`.
- BCP **nunca escreve:** `pulse_metrics`.
- PULSE **lê** `estimated_hours` (plano → previsibilidade) e `estimated_hours_reference` (âncora frozen → alavancagem estável). Sem o campo de referência, cai na alavancagem-vs-plano.
- Se o PULSE estiver ausente, o BCP funciona sozinho. Se o BCP estiver ausente, o PULSE usa a estimativa da Amelia.

Contrato completo: [docs/integration/pulse.md](docs/integration/pulse.md). Hook no fluxo de criação de story: [docs/integration/bmad-create-story.md](docs/integration/bmad-create-story.md).

## Licença

Split intencional e *load-bearing*:

- **Código do módulo** — MIT ([LICENSE](LICENSE)).
- **Régua BCP embarcada** (`skills/bmad-bcp-rule-card/assets/bcp-rule.yaml`) — obra da CI&T, **CC BY-NC-ND 4.0**. O conteúdo da régua é imutável (ND). Ver [ATTRIBUTION.md](ATTRIBUTION.md) — aceite da atribuição é pré-requisito de uso, não rodapé.

## Requisitos

- BMAD ≥ 6.6.0 (gate verificado no setup via `manifest.yaml`).
- Python 3.11+ (stdlib apenas; scripts rodam sem venv/pip).
- Opcional: módulo irmão [PULSE](https://github.com/nidelson/bmad-module-pulse) para medição de eficiência.

---

Dúvidas e sugestões: <https://github.com/nidelson/bmad-module-bcp>
