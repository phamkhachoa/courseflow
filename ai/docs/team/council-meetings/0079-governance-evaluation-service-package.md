# Council 0079: Governance Evaluation Service Package

Date: 2026-06-17

## Participants

| Role | Decision focus |
| --- | --- |
| SA AI Platform | Own the policy-enforced service boundary and enterprise reuse model |
| SA AI Engineer | Bind evaluation registry, promotion readiness and service contract tests |
| PO/BA | Ensure LMS, support, finance and operations can use the same release decision gate |
| Governance Reviewer | Validate HITL, maker-checker, rollback, identifier and secret guardrails |

## Decision

Package governance, safety and evaluation as `services/governance-evaluation-service`.

The service exposes:

| Route | Purpose |
| --- | --- |
| `POST /v1/governance-evaluation/assess` | Return release, promotion and safety decisions with gate evidence |
| `GET /v1/governance-evaluation/health` | Verify registry, promotion and route availability |
| `GET /v1/governance-evaluation/metrics` | Expose assessment, decision and privacy rejection counters |

## Enterprise Scope

| Product | Use |
| --- | --- |
| LMS CourseFlow | Recommendation, RAG tutor and auto-grading release checks |
| Support Platform | Support agent assist promotion and HITL checks |
| Billing/Finance | Payment fraud and document intelligence release checks |
| Enterprise Operations | Routing policy simulator release checks |
| AI Platform | Shared safety gateway and LLM adapter shadow governance |

## Guardrails

- Principals are scoped by tenant, product and use case.
- Direct identifiers and secret values are rejected at the service boundary.
- External auto-send is blocked unless an explicit policy allows it.
- Promotion decisions project maker-checker, gate readiness, rollback and freshness evidence.
- High-impact or high-risk requests return `review_required` even when gates are green.

## Evidence

| Artifact | Path |
| --- | --- |
| Platform runtime | `platform/src/courseflow_ai_platform/governance_evaluation_service.py` |
| Access policy | `platform/governance/policies/governance-evaluation-access-policy.yaml` |
| Service package | `services/governance-evaluation-service/service.yaml` |
| Service contract tests | `services/governance-evaluation-service/tests/test_service_contract.py` |
| Platform tests | `platform/tests/test_governance_evaluation_service.py` |
| Ops projection | `platform/governance/reports/governance-evaluation-service-v1.yaml` |
| Follow-up council | `docs/team/council-meetings/0080-governance-evaluation-ops-projection.md` |

## Outcome

`governance-safety-evaluation` is promoted from tooling to `service_integrated`.
This removes the last runtime gap from the AI module roadmap while preserving
production hardening work for risk UI, dashboard surfacing and live deployment evidence.
Dashboard surfacing is now covered by Council 0080 through the governance evaluation ops report,
operating cockpit projection and Admin/Ops dashboard rows.
