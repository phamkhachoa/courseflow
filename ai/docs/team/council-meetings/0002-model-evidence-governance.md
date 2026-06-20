# AI Platform Product Council 0002

Date: 2026-06-16

## Topic

Move the AI Platform from portfolio registry to evidence-governed model lifecycle.

## Attendees

| Role | Focus |
|---|---|
| PO/BA Agent | Product evidence, KPI visibility, baseline accountability |
| SA AI Platform Agent | Artifact/model-card/evaluation contracts |
| SA AI Engineer Agent | Validation tooling and runtime compatibility |
| Governance Reviewer | Approval, audit, privacy and rollback evidence |

## Decision

Every model candidate or active baseline must have three platform evidence artifacts:

1. Model card.
2. Evaluation report.
3. Artifact manifest.

The current `IMPLICIT_ITEM_CF_V1` recommendation algorithm becomes the first registered evidence set. It remains a baseline, not a claim of advanced AI.

## Why

The platform must serve many domains, so a model cannot be accepted because it is merely implemented in a service. Each model needs enough evidence for product owners, architects, AI engineers and governance reviewers to reason about quality, lineage, dependencies, ownership and rollback.

## Actions

| Action | Owner | Status |
|---|---|---|
| Add model card for `IMPLICIT_ITEM_CF_V1` | SA AI Engineer Agent | done |
| Add evaluation report for baseline model | SA AI Engineer Agent | done |
| Add artifact manifest with source checksum and lineage links | SA AI Platform Agent | done |
| Add validator for evidence files | SA AI Engineer Agent | in progress |
| Make evidence validation part of platform tests | SA AI Engineer Agent | in progress |

## Next Council

Select the first non-LMS implementation slice that proves AI Platform reuse outside CourseFlow LMS. Candidate: Support Agent Assist because it exercises LLM/RAG/HITL governance without requiring deep recommender infrastructure.

