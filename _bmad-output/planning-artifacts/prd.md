---
stepsCompleted:
  - step-01-init
  - step-02-discovery
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief.md
  - _bmad-output/planning-artifacts/product-brief-distillate.md
documentCounts:
  briefs: 1
  distillates: 1
  research: 0
  brainstorming: 0
  projectDocs: 0
  projectContext: 0
workflowType: 'prd'
projectType: 'greenfield'
classification:
  projectType: methodology_tool
  domain: delivery_management
  complexity: high
  projectContext: greenfield
classificationContext:
  - "Bruno is a facilitator/coach layer, not the core path; module runs end-to-end without him in --non-interactive mode (default above confidence threshold)."
  - "Schema-mediated paired-modules architecture (BCP↔PULSE) — neither imports the other; documented frontmatter contract is the integration surface."
  - "License split is load-bearing: MIT (code) + CC BY-NC-ND 4.0 (embedded CI&T BCP rule, immutable)."
  - "Retroactive scoring is first-class in v0.1.0 (`/bmad-bcp-score-batch`, `/bmad-bcp-backfill-baseline`) — kills cold-start crisis and cuts time-to-first-value for the buyer."
  - "Vision must carry: 'Medir entrega de software pela velocidade real com que valor verificável chega ao usuário, não pela energia humana consumida no caminho.' (Victor)"
  - "Open evidence gaps to address downstream: paying buyer cargo (Head of Delivery / COO), benchmark vs Story Points / Function Points (IFPUG/COSMIC), PMO-operacional voice, ROI math (h/sprint × R$/h)."
---

# Product Requirements Document - bmad-module-bcp

**Author:** Nidelson
**Date:** 2026-05-08
