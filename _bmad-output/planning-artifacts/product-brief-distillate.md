---
title: "Product Brief Distillate: bmad-module-bcp"
type: llm-distillate
source: "product-brief.md"
created: "2026-05-07"
purpose: "Token-efficient context for downstream PRD creation"
---

# Distillate — bmad-module-bcp v0.1.0

## Identity

- BMAD module installable via `npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-bcp`.
- Greenfield repo: `bmad-module-bcp/` (sibling to `bmad-module-pulse/`).
- License split: module code = MIT; embedded `bcp-rule.yaml` = CC BY-NC-ND 4.0 (CI&T).
- Capability gate: BMAD ≥6.4.0.
- Single maintainer at v0.1.0 (Nidelson).

## Architectural Decisions (locked from brainstorming)

- Approach A: separate module + minimal PULSE v0.5.0 extension. Loose schema-mediated coupling — neither imports the other.
- Communication contract: story-file frontmatter (BCP writes, PULSE reads).
- Ownership map: BCP owns `estimated_hours`, `estimated_hours_pre_bcp`, `estimated_hours_basis`, `bcp.*` block, `bcp-baseline.yaml`. PULSE owns `pulse_metrics.*` and `actual_hours`.
- BCP overwrites `estimated_hours` only if `bcp_overwrite_estimated_hours: yes` (install-time consent switch). Original preserved as `estimated_hours_pre_bcp`.
- `bcp.schema_version: "1.0"` (contract version) and `bcp.rule_version: "1.0"` (CI&T rule version) ship distinct.
- Auto-score model default: Claude Sonnet 4.6 (configurable via `bcp_bruno_model`).
- Bruno's confidence threshold default: 0.7 (`bcp_bruno_question_threshold`). Below threshold → ask before scoring.
- Scoring log default: gitignored (`bcp_log_file`). Open question: redacted commit option for team reproducibility.
- `bcp.history` capped at 50 entries with warn on truncate. >50% delta single rescore or >2× cumulative triggers Bruno's "consider split into sub-story" advisory.

## Skills (v0.1.0)

| Skill | Purpose |
|---|---|
| `bmad-bcp-setup` | Install / configure / seed baseline / register Bruno / inject `customize.toml` |
| `bmad-bcp-score` | Auto-score (default non-interactive above threshold); dry-run review only on divergence/low-confidence/rescore; overwrite `estimated_hours`; write `bcp.*` |
| `bmad-bcp-score-batch` | **NEW v0.1.0.** Score N existing stories via glob/pattern; marks `bcp.scored_by: retroactive`; supports `--dry-run-cost` token preview before bulk LLM run |
| `bmad-bcp-rescore` | Re-score with ΔBCP audit trail in `bcp.history` |
| `bmad-bcp-recalibrate` | Update baseline (reads `pulse_metrics.actual_hours` if PULSE present, else `--actual-hours`) |
| `bmad-bcp-backfill-baseline` | **NEW v0.1.0.** Chains score-batch + recalibrate in chronological order; bootstraps calibrated `h/BCP` from squad history, eliminates cold-start; idempotent on already-scored stories |
| `bmad-bcp-rule-card` | Inline reference of the 10×5 rule |
| `bmad-bcp-agent-bruno` | Chat agent for ad-hoc BCP questions; **facilitator/coach layer, not core path**; module runs end-to-end without invocation |

## Bruno (BCP-Analyst Agent)

- Methodological mirror of Levi (PULSE coach).
- Persona: methodical, license-aware, rule-faithful, pedagogical, concise by default.
- Scope: scoring, rescore diff, baseline maturity analysis, scope creep detection, rule pedagogy.
- Anti-scope: telemetry calculation (Levi), code review (Murat), scope decisions (Amelia/PM), modifying the rule.
- Catchphrase: *"Régua antes de régua"* — consistency before speed.
- Registered in `_bmad/_config/agent-manifest.csv` via `bmad-bcp-setup`. Auto-included in Party Mode.

## BCP Rule (immutable per CC BY-NC-ND 4.0)

- 10 elements: `audits`, `background_process`, `boundaries`, `business_rules`, `domain_entities`, `new_domain_entities`, `notifications`, `roles_and_permissions`, `solution_variability`, `interface_elements`.
- 5 sizes: XS / S / M / L / XL.
- Fibonacci weights: [1, 2, 3, 5, 8].
- Editorial hints (label, description, per-size hint) are mutable; only `elements`, `sizes`, `points` immutable.

## Baseline (`bcp-baseline.yaml`)

- Default categories: `backend`, `web`, `mobile`, `fullstack`.
- Seed: 4.13 h/BCP (CI&T 2014 reference). **Open question:** seed credibility — 2014 non-AI baseline applied to 2026 AI-assisted work risks inflating apparent leverage during cold start. Mitigation in brief: suppress headline leverage until `is_seed: false`, label uncalibrated. Reviewer suggests possibly seeding at 1.0 h/BCP as alternative.
- `min_samples: 5`, `rolling_window: 10` (FIFO).
- Per-category rolling avg with `is_seed` boolean — replace UX with maturation progress (`2/5 samples`) per friction reviewer.
- `bcp-recalibrate` updates baseline; never written by PULSE.

## Cross-Module Trigger

- `bmad-bcp-setup` emits `_bmad/custom/bmad-create-story.toml` with `[workflow] on_complete = "BCP scoring: invoke /bmad-bcp-score <story_id> ..."`.
- Same `customize.toml` mechanism PULSE uses (`persistent_facts` / `on_complete`). Validated in BMAD ≥6.4.0; v6.6.0 keeps the contract.
- Auto-recalibrate hook on `bmad-pulse-track-done` deferred to v0.2.0 (opt-in via `bmad-bcp-setup --auto-recalibrate`).

## Frontmatter Contract (story file)

```yaml
estimated_hours: 86.7              # BCP wrote (consent switch)
estimated_hours_pre_bcp: 80        # BCP audit
estimated_hours_basis: bcp         # bcp | agent
bcp:
  schema_version: "1.0"
  rule_version: "1.0"
  total: 21
  scored_at: <iso8601>
  scored_by: bruno|manual|rescore
  breakdown: { ... 10 elements × sizes ... }
  history: []                      # capped 50, populated by /bmad-bcp-rescore
```

## PULSE v0.5.0 Extension (companion repo)

- `pulse_estimation_method` accepts new value `bcp`.
- `track-start`: snapshot `bcp_at_start` in `pulse_metrics`.
- `track-done`: record `bcp_recorded` (h_per_bcp_actual, h_per_bcp_estimated, drift_pct).
- Dashboard: conditional "📊 BCP Productivity" section (throughput, h/BCP trend, drift, scope creep, top elements, forecast).
- PULSE never writes to `bcp.*` or to baseline file (read-only consumption).
- Friction nudge: `track-done` prints "Run /bmad-bcp-recalibrate <id>" when BCP block present.

## Implementation Plan (F-phases)

| Phase | Description | Estimate |
|---|---|---|
| F0 | Bootstrap repo (LICENSE, README, pyproject, release-please) | 3-4h |
| F1 | BCP rule + frontmatter schema + tests | 6-8h |
| F2 | `bmad-bcp-setup` (full setup pipeline) | 8-10h |
| F3 | `bmad-bcp-rule-card` + Bruno chat skill | 4-6h |
| F4 | `bmad-bcp-score` (auto + dry-run + persist + overwrite) | 12-16h |
| F5 | `bmad-bcp-rescore` (delta + history) | 6-8h |
| F6 | `bmad-bcp-recalibrate` (rolling baseline) | 6-8h |
| F7 | Frontmatter overwrite (integrated in F4) | 2-4h |
| F8 | Documentation (README EN+PT, integration guides, ATTRIBUTION) | 4-6h |
| F9 | PULSE v0.5.0 — `pulse_estimation_method=bcp` | 4-6h |
| F10 | PULSE v0.5.0 — dashboard "BCP Productivity" | 8-10h |
| F11 | Self-dogfooding (Bruno scores BCP's own stories) | 4h |
| F12 | Release v0.1.0 + design partner outreach | 4h |
| **Total** | | **~75-95h** (4 sprints, ~3 weeks elapsed solo) |

Critical path: F0 → F1 → F2 → F4 → F7 → F11 → F12. Parallel after F1: F2/F9, F8 continuous, F5/F6/F10 after predecessors.

## Testing Strategy

- Pyramid: ~50 unit / ~15 integration / 3 E2E.
- Coverage: unit ≥90%, integration ≥80%, E2E 100% of documented scenarios.
- E2E scenarios: full lifecycle / standalone-no-pulse / standalone-no-bcp.
- Tools: pytest + hypothesis (optional) + codecov + GitHub Actions.
- Cross-repo validation manual at PULSE v0.5.0 release (clone master, install both, sandbox E2E). Required pre-release; not on every commit.

## Risks & Mitigations (carried from spec + brief reviewers)

| Risk | Mitigation |
|---|---|
| LLM auto-score imprecise | F11 dogfooding ≥5 stories + prompt tuning + dry-run review default; ≥80% no-adjust as aspirational not statistical |
| CC BY-NC-ND interpreted as fork-friendly | ATTRIBUTION.md plain-English permissions table; LICENSE distinguishes MIT vs CC; tests validate immutability; legal posture as Phase 0 prerequisite |
| Immature baseline masks productivity | Suppress headline leverage until `is_seed: false`; show maturation progress (`2/5 samples`); not boolean |
| `customize.toml` conflicts with user edits | `--dry-run` pre-flight + `--force` explicit; never overwrite without consent |
| BCP overwrites Amelia's hours unnoticed | Per-story diff printed on every score; per-repo banner first run per author; documented `bcp.skip: true` per-story opt-out |
| Cross-module trigger broken in future BMAD | E2E tests isolate behavior; capability gate by version; design partner validates |
| Rescore history bloat | 50-entry cap with warn; "consider split" advisory if >50% delta |
| Goodhart: incentive to inflate BCP / under-report hours | Optional second-agent spot-check rescore; baseline anomaly detection (off by default; opt-in for multi-squad orgs) |
| Single-maintainer bus factor | Written succession plan post-design-partner; opt-in CI&T co-maintenance during F12; stable schema versioning |
| Cross-repo version skew (PULSE × BCP) | Published BCP↔PULSE compatibility matrix in both READMEs; setup probes PULSE version and warns |
| 4.13 seed credibility (2014 non-AI baseline) | Reframe as "uncalibrated reference"; suppress leverage during seed; cite source explicitly in docs |

## Configuration Keys

```yaml
# _bmad/config.yaml [bcp]
bcp_default_scorer: bruno              # bruno | manual
bcp_bruno_verbosity: standard          # concise | standard | verbose
bcp_bruno_coaching_mode: yes           # yes | metrics-only
bcp_bruno_question_threshold: 0.7
bcp_bruno_model: claude-sonnet-4-6
bcp_baseline_file: '{project-root}/_bmad-output/implementation-artifacts/bcp-baseline.yaml'
bcp_baseline_seed: 4.13
bcp_baseline_min_samples: 5
bcp_baseline_rolling_window: 10
bcp_default_categories: ['backend', 'web', 'mobile', 'fullstack']
bcp_overwrite_estimated_hours: yes
bcp_rule_path: '{module-root}/assets/bcp-rule.yaml'
bcp_log_file: '{project-root}/_bmad-output/implementation-artifacts/bcp-scoring-log.yaml'
```

## Setup Pipeline (`bmad-bcp-setup`)

1. Capability gate (BMAD ≥6.4.0)
2. Interactive prompts (skip if `--headless`)
3. Write `_bmad/config.yaml` `[bcp]` section (anti-zombie)
4. Register Bruno in `agent-manifest.csv` (anti-zombie)
5. Seed `bcp-baseline.yaml` with 4 standard categories
6. Inject `_bmad/custom/bmad-create-story.toml` (abort+`--force` if exists; pre-flight `--dry-run` available)
7. Print `.gitignore` snippet
8. Cleanup legacy directories (idempotent)
9. Detect PULSE → "✅ PULSE detected" or warn standalone mode
10. Confirm summary + Bruno greeting

## Detail Captured for Downstream PRD Work

### Audience signals

- Primary: BMAD-adopting CI&T-shaped squads (1–8 engineers).
- Secondary (Phase 0 prerequisite): named CI&T pilot squad with written commitment.
- Tertiary: hour-billing consultancies / agencies needing scope defense.
- IC pitch: "Bruno costs ~20 seconds; the score travels with the file; scope creep is captured automatically."

### Localization (decision: ADR 0001 accepted)

- **Policy:** PT-BR-primary for narrative, EN for code surface. Full table in `docs/ADR/0001-localization-strategy.md`.
- **EN (non-negotiable):** code identifiers, skill/agent slugs, paths, commands `/bmad-bcp-*`, YAML keys, frontmatter fields, JSON Schema, Conventional Commits, branch names, issue labels, `CHANGELOG.md` (release-please-managed), ATTRIBUTION.md primary, README root shell.
- **PT-BR-canônico:** `README.pt-BR.md` (full manual), integration guides, tech-refinement docs, Bruno persona dialogue + catchphrase ("Régua antes de régua"), dry-run review prose, error messages, user-facing prompts, ADR bodies, `bcp.history.note` / `delta_reason` free-text.
- **Submitter's language (PT-BR fully welcomed):** issue titles/bodies, PR descriptions, discussion threads, code review prose. Maintainer answers in submitter's language. PRs that ship changelog-relevant features append a one-line EN summary for `release-please`.
- **Hybrid:** Bruno auto-score prompt template (EN structure + PT-BR few-shot examples); ADRs (EN titles for grep, PT-BR-acceptable bodies); scoring log (EN structure, free-text in squad's language).
- **Reassessment trigger:** v0.2.0 planning, design partner identification (if outside Brazil → expedite EN expansion), or first externally-submitted EN issue revealing friction.
- **Evidence gap (partial fill):**
  - **CI&T headcount Brasil:** ~7.000 colaboradores (informado por Nidelson, 2026-05-08). Reforça a hipótese de concentração pt-BR no v0.1.0. Ainda owed: headcount não-Brasil (US, UK, Portugal, Singapore, Australia, Japan, China) para confirmar % de concentração.
  - Working-language real dos squads CI&T fora do Brasil — pendente.
  - BMAD-adjacent geo signal (PULSE clones/stars por região) — pendente.
- **Bruno runtime locale:** PT-BR by default; configurable via `bcp_bruno_locale: pt-BR | en`. Autodetection from BMAD locale is a v0.2.0 concern.

### Headless / CI mode

- `--non-interactive --confidence-threshold 0.85` mode auto-confirms above threshold or marks `bcp.needs_review: true` for async human pass.
- Required for Jira-webhook-driven story creation pipelines.

### License UX

- ATTRIBUTION.md ships plain-English permissions table.
- `bmad-bcp-rule-card --license` flag prints CC BY-NC-ND 4.0 summary inline.
- First-install consent screen prints NC clause explicitly.
- **Open question:** does NC clause restrict downstream BMAD users' commercial work? Requires written carve-out or licensing letter from CI&T as v0.1.0 prerequisite.

### Strategic positioning (carry into PRD intro)

- The module is the reference implementation for embedding ANY published licensed framework into BMAD without forking. BCP is instance #1.
- Vision-level thesis: "AI-assisted development makes subjective estimation obsolete." This frames the long-term roadmap; PRD should preserve it as North Star.

### Adjacent value propositions worth surfacing in PRD scope discussion

- BCP-as-a-service / cross-team aggregation: explicitly Out for v0.1.0; positioned as moat for v0.2.0+.
- Bruno as standalone CLI/GitHub Action for non-BMAD teams: v0.2.0+.
- Translation reports BCP↔story-points / BCP↔Jira complexity: migration on-ramp; Out for v0.1.0 but worth a stub.
- Co-marketing path with CI&T (official endorsement, link from CI&T BCP page): stretch success criterion.
- Thought-leadership content around the methodology: external to module but compounds adoption.

### Retroactive scoring (decision: IN for v0.1.0)

- **Decision:** retroactive scoring promoted from "deferred to F11 dogfooding" to **first-class v0.1.0 capability**. Reasoning: kills cold-start credibility crisis (no seed-mode leverage inflation); cuts time-to-first-value for buyer (install + retro-batch = same-day ROI conversation); buyer JTBD (Mary/John) is "explain the last 12 sprints with a defensible ruler", not "start measuring from now".
- **Skills:** `/bmad-bcp-score-batch <glob>` (parallel auto-score multiple existing stories) and `/bmad-bcp-backfill-baseline` (chain score-batch + recalibrate in chronological order to mature baseline immediately).
- **Audit:** retro entries set `bcp.scored_by: retroactive` and `delta_reason: 'retroactive scoring of done story'` in `bcp.history`. Idempotent (re-running on already-scored story is no-op or asks confirmation).
- **Confidence:** retro context is thinner than at-creation context — Bruno (when invoked) marks `bcp.needs_review: true` if confidence < threshold; humans validate batch-style.
- **Bulk cost:** `--dry-run-cost` flag previews estimated token spend before bulk LLM execution (e.g., 40 stories × ~3k tokens each ≈ 120k tokens Sonnet 4.6).
- **PULSE-less retro:** when `pulse_metrics.actual_hours` is absent, accept `--actual-hours` per-story (manual entry from timesheet/Jira/git timestamps) or skip baseline backfill (score only).
- **Order:** retro recalibration runs in chronological order so the rolling FIFO window preserves real temporal trend.

### Rejected / explicitly out for v0.1.0

- Auto-recalibrate hook on `bmad-pulse-track-done` (opt-in v0.2.0).
- Multi-tenant baselines beyond per-category granularity.
- Web UI / IDE plugin.
- ML-based auto-score calibration.
- Cross-team baseline aggregation.
- BCP becoming default `pulse_estimation_method` (always opt-in).

### Open questions (post-design)

1. Bruno auto-score prompt template (`assets/prompts/auto-score.md`) — initial draft in F4.
2. Migration story for ~40 existing SIP done-stories — retroactive scoring? Deferred to F11 dogfooding decision.
3. CI&T design partner identification — outreach during F12; **PRD must declare this Phase 0 hard gate**.
4. Metric: `auto_score_no_adjust_rate` — target ≥80%, measured from `bcp-scoring-log.yaml`. N=5–10 is small; revisit post-partner.
5. Bruno locale autodetection vs config.
6. Scoring log: gitignored vs redacted-commit for team reproducibility.
7. Seed value 4.13 vs 1.0 vs cited-2014 with explicit AI-era caveat. **Note:** 4.13 + 2014 origin not on CI&T's public page — provenance must be confirmed with design partner before being cited in docs.
8. Per-story consent UX: per-author banner? `bcp.skip: true` opt-out? `/bmad-bcp-revert <story>` skill?

### Success criteria (verbatim from spec, preserved)

- End-to-end SIP story scored→done lifecycle traceable.
- CI&T design partner identified and accepts initial spec.
- Both modules released: BCP v0.1.0 + PULSE v0.5.0.
- Documentation complete EN + PT-BR.
- All AC from PULSE #30 and BCP #1 satisfied.

### CI&T official BCP page — extracted verbatim positioning (for co-marketing alignment)

- Origin framing: "Re-Thinking Story Points" — Story Points criticized as non-normalized, subjective, prevents cross-team performance analysis and continuous-improvement demonstration.
- BCP self-description: "method to objectively measure, demonstrate and standardize software complexity" via business lens, 10 elements × 5 sizes (XS-XL) × Fibonacci.
- Examples of elements (CI&T verbatim): business rules (formula → multi-step iterative with decision points), UI elements (simple form additions → complex dynamic forms), new/existing business entities, interface to different entities, permissions.
- Five claimed pillars (CI&T's own pitch language, useful for co-marketing copy):
  1. Communication
  2. Normalized System
  3. Comparisons
  4. Best Practices
  5. Quality
- License attribution exact phrasing on CI&T page: "Business Complexity Points (BCP) is a software complexity normalization framework created by CI&T (www.ciandt.com) licensed under a Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License."
- External CI&T reading material referenced from the page (use in docs / `bmad-bcp-rule-card`):
  - Introduction: "Comparing Apples to Apples"
  - Article series: "Measure productivity in Agile before it's too late" — Parts 1, 2, 3
- **Not on the public page (open question):** the 4.13 h/BCP seed value, the 2014 origin year, and the explicit `h/BCP` productivity ratio do not appear in CI&T's public materials — confirm provenance with design partner before citing.

### Related references

- Spec (brainstorming record, source of truth on decisions): `/Users/nidelson/Projects/nidelson/sip/docs/superpowers/specs/2026-05-07-bcp-pulse-integration-design.md`.
- PULSE issue #30: https://github.com/nidelson/bmad-module-pulse/issues/30
- BCP issue #1: https://github.com/nidelson/bmad-module-bcp/issues/1
- BCP framework reference (CI&T): https://ciandt.com/us/en-us/complexitypoints
- PULSE README: `/Users/nidelson/Projects/nidelson/bmad-module-pulse/README.md`
- Tech refinement / ADRs: to be created in `bmad-module-bcp/docs/tech-refinement/` and `docs/ADR/` during implementation.
