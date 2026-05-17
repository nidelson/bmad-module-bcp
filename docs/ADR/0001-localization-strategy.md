# ADR 0001 — Localization Strategy: PT-BR Primary for Narrative, EN for Code Surface

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-08 |
| Author | Nidelson Gimenez |
| Reviewers | Paige (BMAD Tech Writer agent), Mary (BMAD Analyst agent) — party-mode round |
| Supersedes | — |

## Context

`bmad-module-bcp` v0.1.0 targets primarily CI&T-shaped organizations adopting BMAD. Internal estimate: ~90% of likely v0.1.0 users are CI&T-internal, where pt-BR is the working language for delivery management, theses, sprint reviews, and most internal documentation. Sibling module `bmad-module-pulse` shipped EN-primary with `README.pt-BR.md` companion.

Brief and party-mode rounds surfaced two competing pressures:

1. **Friction reduction.** ~90%-CI&T audience reads, writes issues, defends theses, and creates internal artifacts in pt-BR. Forcing EN-first creates translation tax for both maintainer and users.
2. **Open-source norms and optionality preservation.** "PT-BR-only" closes the door for non-Brazilian CI&T offices (US, UK, Portugal, Singapore, Australia, Japan), for the unvalidated buyer-hypothesis (Head of Delivery / COO of mid-size consultancy outside Brazil), and for tertiary audience (hour-billing consultancies and agencies).

Mary flagged the "~90% pt-BR" figure as hypothesis, not evidence, and called for three cheap measurements (CI&T headcount by office, working language of squads outside Brazil, BMAD-adjacent geo signal) before betting the strategy on it. Paige proposed a clean code/narrative layering: technical identifiers always in EN, narrative docs PT-BR-canonical with an EN entry shell.

## Decision

Adopt a **PT-BR-primary for narrative, EN for code surface** strategy for v0.1.0, with explicit governance for the bilingual workflow CI&T users will bring (issues in PT-BR, discussions in PT-BR).

### Policy by artifact type

| Artifact | Language | Notes |
|---|---|---|
| Code identifiers (skill names, agent slugs, paths, commands `/bmad-bcp-*`) | **EN** | Non-negotiable. Renaming later breaks installed users. |
| YAML keys, frontmatter fields, JSON Schema, baseline file structure | **EN** | Interoperability with PULSE contract; parser-friendly. |
| Conventional Commits messages | **EN** | `release-please` and changelog tooling expect EN structure. |
| Branch names | **EN** | GitHub-conventional, scriptable. |
| Issue titles | **PT-BR or EN, submitter's choice** | Labels (`bug`, `enhancement`, `docs`, `licensing`, `pulse-integration`) stay EN for grep-ability. |
| Issue body, discussion threads, PR review prose | **Submitter's language — PT-BR fully welcomed and expected from CI&T users** | Maintainer answers in the same language as the submitter. |
| PR descriptions | **PT-BR accepted; if PR ships changelog-relevant feature, append a one-line EN summary for `release-please`** | Hybrid stays compatible with release tooling. |
| `README.md` (root) | **EN-shell mínima** (vitrine, install command, link to PT-BR README) | Preserves GitHub findability + non-Brazilian discoverability. |
| `README.pt-BR.md` | **PT-BR canônico — full manual** | The real onboarding document. |
| `docs/integration/*.md` (PULSE, bmad-create-story integration guides) | **PT-BR canônico** + EN quickstart stub | Long-form prose follows audience. |
| `ATTRIBUTION.md` | **EN-primary** + PT-BR mirror | License attribution must be unambiguously parseable in EN per CC BY-NC-ND 4.0 norms. |
| `CHANGELOG.md` | **EN** (release-please-managed) | Tooling expects EN; optional PT-BR mirror at `CHANGELOG.pt-BR.md`. |
| ADRs (`docs/ADR/*.md`) | **EN-titles + PT-BR-body acceptable** | Hybrid: titles greppable in EN, body in author's language. This ADR follows that pattern. |
| Tech-refinement docs (`docs/tech-refinement/`) | **PT-BR canônico** | Internal decision trail. |
| Bruno agent dialogue, dry-run review prose, error messages, user-facing prompts | **PT-BR primary** | Where friction lives; UX optimization for the actual audience. |
| `bcp.history.note` / `delta_reason` / scoring log free-text fields | **Squad's language (default PT-BR)** | Audit trail in language of the people who write it. Structure/keys stay EN. |
| Bruno auto-score prompt template (`assets/prompts/auto-score.md`) | **EN structure with PT-BR examples** | Prompt engineering benefits from EN scaffolding; few-shot examples in PT-BR for audience fit. |

## Consequences

### Positive

- ~90% audience friction drop on onboarding and daily use.
- Zero-cost preservation of open-source surface for non-CI&T discoverability (EN README shell, EN identifiers, EN commits) — module remains forkable, scannable, citable.
- CI&T users contribute issues and PRs in their native language — lower barrier to contribution feedback.
- Maintainer (single, pt-BR-native) writes once in audience language, no translation tax for v0.1.0.
- Compatible with `release-please` and standard GitHub tooling.

### Negative / risks

- Non-CI&T discoverability for narrative content is reduced; new EN-speaking user lands on EN README shell and may bounce if PT-BR content is the real value.
- Mary's three evidence gaps remain unvalidated: this ADR bets on the ~90% hypothesis without numerical backing.
- Potential design partner outside Brazil (CI&T US, UK, etc.) may find the docs surface insufficient. Mitigation: ATTRIBUTION + EN README quickstart cover bare-minimum self-onboarding; full EN translation can be commissioned reactively.
- Adding full EN parity later is linear effort (~1-2 days per epic per Paige's estimate), but accumulates if v0.1.0 ships many epics before reassessment.

### Reversal cost

- **Low** for narrative artifacts (translate once when needed).
- **Zero** for code surface (already in EN).
- **Low** for issues/PRs (existing threads can be translated on-demand if a non-pt-BR reviewer joins; or simply left as historical record).

### Reassessment trigger

This ADR will be revisited at one of the following events, whichever comes first:

1. v0.2.0 planning (~6 months post-v0.1.0).
2. Design partner identification — if partner office is outside Brazil, schedule reassessment immediately and prioritize EN README + integration guides translation as a v0.1.x patch.
3. First externally-submitted issue in EN that reveals friction caused by PT-BR-canonical docs.

Mary's three evidence-gap measurements (CI&T headcount by office, working language of non-Brazil squads, BMAD-adjacent geo signal) should be collected before reassessment.

### Evidence collected so far (partial)

- **CI&T headcount — Brasil: ~7.000 colaboradores** (informed by Nidelson, 2026-05-08). Strengthens the pt-BR concentration hypothesis substantially. Still owed: non-Brazil headcount breakdown (US, UK, Portugal, Singapore, Australia, Japan, China offices) to confirm proportional concentration. Working-language of non-Brazil squads and BMAD-adjacent geo signal remain unmeasured.

## Notes for downstream agents

- Bruno's persona description, catchphrase ("Régua antes de régua"), and coaching dialogue are explicitly designed for pt-BR delivery; EN translation will require persona-faithful re-authoring, not literal translation.
- Code Connect-style references between PT-BR docs and EN code identifiers should use explicit `lang` frontmatter fields and `translation_of:` pointers when EN counterparts exist.
- This ADR itself is structured per the bilingual policy: EN headings/identifiers + PT-BR-friendly prose tone for narrative, mirroring the recommended pattern for future ADRs.
