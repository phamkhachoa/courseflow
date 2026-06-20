# 0020 Enterprise Solution Blueprint Intake

Date: 2026-06-16

## Decision

Add a product front door that converts AI use-case requests into governed
solution blueprints before any team starts building datasets, models,
evaluation gates or promotion artifacts.

## Why

The AI Platform must serve CourseFlow LMS and other enterprise products through
one operating model. Promotion intake answers "can this artifact move forward?"
Solution blueprint intake answers the earlier question: "what platform path
should this business problem use, and what is missing before delivery starts?"

## Roles

| Role | Decision rights |
| --- | --- |
| PO/BA | Business objective, product owner, KPI, priority and data domain framing |
| SA AI Platform | Taxonomy module mapping, platform capability gaps, governance and runtime path |
| SA AI Engineer | Baseline approach, evaluation strategy, simulator requirement and artifact plan |

## Artifacts

| Artifact | Path |
| --- | --- |
| Request registry | `platform/intake/use-case-requests.yaml` |
| Blueprint projection | `platform/src/courseflow_ai_platform/solution_blueprint.py` |
| Blueprint report | `platform/intake/reports/use-case-blueprints-v1.yaml` |
| Tests | `platform/tests/test_solution_blueprint.py`, `platform/tests/test_cli.py` |
| CLI output | `solutionBlueprints` top-level key and optional report writer |

## Current Queue

| Queue | Requests |
| --- | --- |
| Ready for solution design | `enterprise-knowledge-assistant-discovery`, `lms-at-risk-prediction-baseline`, `support-sla-risk-discovery`, `operations-routing-optimization-simulator`, `finance-payment-fraud-scoring-discovery` |
| Needs data contract | none after data contract coverage in meeting 0022 |
| Needs evaluation strategy | none after the support SLA risk baseline |
| Needs privacy review | `finance-document-intelligence-discovery` |
| Needs simulator | none after the operations-routing policy simulator baseline |
| Needs platform build | none after the finance payment fraud baseline; forecasting remains a runtime-roadmap gap outside the current request queue |

## Validation Rules

| Rule | Purpose |
| --- | --- |
| Product and use-case IDs must exist | Prevent orphan enterprise requests |
| Request product must match use-case product | Prevent cross-product ownership drift |
| Target modules must exist in business capability coverage | Keep blueprint tied to platform taxonomy |
| Target modules must cover the requested use case | Stop fake capability claims |
| Ready requests cannot have blockers | Keep PO/BA queue honest |
| Role policy must include PO/BA, SA AI Platform and SA AI Engineer | Preserve the team operating model |

## Product Impact

| Stakeholder | Outcome |
| --- | --- |
| PO/BA | See which requests are ready and which need data, privacy or simulator work |
| SA AI Platform | See taxonomy coverage and roadmap module gaps across products |
| SA AI Engineer | See baseline, evaluation and artifact workstreams before implementation |
| Admin/Ops | Can combine blueprint, promotion intake and readiness into one release cockpit |

## Next Moves

1. Add backlog state transitions for completed solution-blueprint work.
2. Bind ready solution blueprints to backlog items and contract hardening work.
3. Add Admin/Ops UI projection that combines solution blueprint, promotion intake
   and promotion readiness queues.
