# ADR 0002 — Localization Strategy: English Canonical, Portuguese as Translation

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-07 |
| Author | Nidelson Gimenez |
| Supersedes | [ADR 0001](0001-localization-strategy.md) |

## Context

ADR 0001 (2026-05-08) adopted a PT-BR-primary strategy for narrative content, on
the estimate that ~90% of v0.1.0 users would be CI&T-internal and Portuguese
speaking. Mary flagged that number at the time as a hypothesis rather than
evidence, and asked for three cheap measurements before betting the strategy on
it. Those measurements were never taken.

Three things changed since:

1. **The audience of reading is wider than the audience of writing.** The module
   is public and installed by third parties. Issues get opened, history gets
   read, and code gets inspected by people who never talk to the maintainer.
2. **Two canonical sources drift.** Under ADR 0001 the PT-BR document was the
   source and the EN shell a summary. Every edit had to be mirrored by hand, and
   nothing failed when it was not — divergence was silent by construction.
3. **The sibling module already went the other way.** `bmad-module-pulse` was
   published EN-primary with a `README.pt-BR.md` companion. Keeping the two
   modules on opposite policies costs a context switch on every contribution and
   makes shared conventions harder to state.

The MIT republication of the BCP framework (May 2026) also removed the legal
constraint that ADR 0001 cited for `ATTRIBUTION.md`. Under CC BY-NC-ND the BY
term required preserving the credit as published; under MIT the requirement is
to preserve the copyright notice and license text — a fixed string, identical in
any language. Nothing in the license now argues for one prose language over
another.

## Decision

**English is canonical.** Every artifact is authored in English. Portuguese
exists only as a *translation* of reader-facing documents, tracking the English
source rather than competing with it.

| Artifact | Language | Notes |
|---|---|---|
| Code identifiers (skill names, agent slugs, paths, `/bmad-bcp-*` commands) | **EN** | Unchanged from ADR 0001. Non-negotiable — renaming breaks installed users. |
| YAML keys, frontmatter fields, JSON Schema, baseline file structure | **EN** | Unchanged. Parser-friendly, interoperable with the PULSE contract. |
| Conventional Commit messages | **EN** — type and text | Changed. ADR 0001 allowed PT-BR subject and body. |
| Branch names | **EN** | Unchanged. |
| Issue titles and bodies, PR titles and descriptions, review prose | **EN** | Changed. ADR 0001 left this to the author's language. |
| `ATTRIBUTION.md` | **EN** | Changed. `Copyright (c) 2025 CI&T HyperX`, URLs and license term names stay verbatim. |
| ADRs (`docs/ADR/*.md`) | **EN** — title and body | Changed. ADR 0001 accepted PT-BR bodies. |
| `CHANGELOG.md` | **EN** — sections and entries | Changed. Requires updating `changelog-sections` in `release-please-config.json`. |
| `README.md` (root) | **EN canonical** | Changed. See Consequences — not yet executed. |
| `README.pt-BR.md` | **PT-BR translation** | Replaces the current inverted layout (`README.md` PT-BR + `README.en.md` shell). |
| Integration guides, tech-refinement docs | **EN** | Changed. |
| Bruno agent dialogue, error messages, user prompts | **EN** | Changed. Interactive output follows the module's language, not the maintainer's. |

Maintainers may still answer an issue in the language its author used. That is
courtesy in a conversation, not a canonical artifact.

## Consequences

**Already done in the PR that introduces this ADR:** `ATTRIBUTION.md` translated;
`CLAUDE.md` localization section rewritten to point here.

**Deliberately not done, and still open:**

- `README.md` / `README.en.md` inversion. The current layout has the manual in
  PT-BR at the root and a thin EN shell beside it. Inverting means translating
  the full manual, not moving files — a change large enough to deserve its own
  PR.
- `release-please-config.json` still carries `changelog-sections` labels in
  Portuguese (`Funcionalidades`, `Correções`, `Documentação`). Until it is
  updated, generated changelogs mix Portuguese section headings with English
  entries.
- Existing PT-BR prose across `docs/` and skill workflows. Translating it is
  incremental work; nothing breaks while it waits.

**Not to be done:** rewriting git history or editing merged PR and issue bodies
to conform. Commits and threads before 2026-08-07 were written under ADR 0001
and are a correct record of their moment.

## Notes

ADR 0001 remains in the repository as the record of the previous decision, with
its Status field pointing here. It is not deleted and not edited beyond that
pointer.
